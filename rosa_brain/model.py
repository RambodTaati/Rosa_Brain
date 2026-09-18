"""Tiny from-scratch byte-level encoder/decoder (random init, trainable)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import time
import torch
import torch.nn as nn
import torch.nn.functional as F

from rosa_brain.config import settings
from rosa_brain.resources import pick_device, require_capacity


class TinyBrainNet(nn.Module):
    """Character/byte LM + pooled embedding encoder — no external weights."""

    def __init__(
        self,
        vocab_size: int | None = None,
        embed_dim: int | None = None,
        hidden_dim: int | None = None,
        num_layers: int | None = None,
    ) -> None:
        super().__init__()
        vs = vocab_size or settings.vocab_size
        ed = embed_dim or settings.embed_dim
        hd = hidden_dim or settings.hidden_dim
        nl = num_layers or settings.num_layers
        self.vocab_size = vs
        self.embed_dim = ed
        self.embed = nn.Embedding(vs, ed)
        self.pos = nn.Embedding(settings.max_seq_len, ed)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=ed,
            nhead=4,
            dim_feedforward=hd,
            batch_first=True,
            activation="gelu",
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=nl)
        self.lm_head = nn.Linear(ed, vs)
        self.pool = nn.Linear(ed, ed)
        self.num_labels = 16
        self.class_head = nn.Linear(ed, self.num_labels)
        # Random init is default for nn modules — no pretrained load.

    def encode_bytes(self, text: str, max_len: int | None = None) -> torch.Tensor:
        ml = max_len or settings.max_seq_len
        raw = text.encode("utf-8", errors="replace")[:ml]
        if not raw:
            raw = b" "
        ids = list(raw)
        return torch.tensor(ids, dtype=torch.long)

    def forward(self, token_ids: torch.Tensor) -> dict[str, torch.Tensor]:
        """
        token_ids: (B, T) long
        returns logits (B, T, V) and pooled embedding (B, E)
        """
        b, t = token_ids.shape
        if t > settings.max_seq_len:
            token_ids = token_ids[:, : settings.max_seq_len]
            t = token_ids.shape[1]
        pos = torch.arange(t, device=token_ids.device).unsqueeze(0).expand(b, t)
        x = self.embed(token_ids) + self.pos(pos)
        # causal-ish mask for autoregressive training signal
        mask = torch.triu(torch.ones(t, t, device=token_ids.device), diagonal=1).bool()
        h = self.encoder(x, mask=mask)
        logits = self.lm_head(h)
        pooled = torch.tanh(self.pool(h.mean(dim=1)))
        cls = self.class_head(pooled)
        return {"logits": logits, "embedding": pooled, "hidden": h, "class_logits": cls}

    @torch.no_grad()
    def embed_text(self, text: str, device: str | None = None) -> list[float]:
        device = device or pick_device()
        self.eval()
        ids = self.encode_bytes(text).unsqueeze(0).to(device)
        self.to(device)
        out = self.forward(ids)
        return out["embedding"][0].detach().float().cpu().tolist()

    @torch.no_grad()
    def generate(self, prompt: str, max_new: int = 64, temperature: float = 0.9) -> str:
        device = pick_device()
        self.eval()
        self.to(device)
        ids = self.encode_bytes(prompt).tolist()
        for _ in range(max_new):
            ctx = ids[-settings.max_seq_len :]
            x = torch.tensor([ctx], dtype=torch.long, device=device)
            logits = self.forward(x)["logits"][0, -1]
            if temperature <= 0:
                nxt = int(torch.argmax(logits).item())
            else:
                probs = F.softmax(logits / temperature, dim=-1)
                nxt = int(torch.multinomial(probs, 1).item())
            ids.append(nxt)
            if nxt == 10:  # newline often ends a short reply
                break
        try:
            return bytes(ids[len(self.encode_bytes(prompt)) :]).decode(
                "utf-8", errors="replace"
            )
        except Exception:
            return ""


class ModelManager:
    def __init__(self) -> None:
        self.device = pick_device()
        self.net = TinyBrainNet()
        self.net.to(self.device)
        self.optimizer = torch.optim.AdamW(self.net.parameters(), lr=3e-4)
        self._loaded = False
        self.train_steps = 0
        self._ckpt_mtime = None

    def load_if_exists(self, force: bool = False) -> bool:
        path = settings.model_path
        if not path.exists():
            return False
        last_err = None
        for attempt in range(8):
            try:
                # skip tiny/partial writes
                if path.stat().st_size < 10_000:
                    time.sleep(0.05 * (attempt + 1))
                    continue
                blob = torch.load(path, map_location=self.device, weights_only=False)
                # architecture guard
                if int(blob.get("embed_dim", self.net.embed_dim)) != int(self.net.embed_dim):
                    return False
                self.net.load_state_dict(blob["state_dict"])
                self.train_steps = int(blob.get("train_steps", 0))
                self.net.to(self.device)
                try:
                    self._ckpt_mtime = path.stat().st_mtime
                except Exception:
                    self._ckpt_mtime = None
                return True
            except Exception as exc:
                last_err = exc
                time.sleep(0.05 * (attempt + 1))
        return False


    def save(self) -> Path:
        settings.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "state_dict": self.net.state_dict(),
            "train_steps": self.train_steps,
            "device": self.device,
            "vocab_size": self.net.vocab_size,
            "embed_dim": self.net.embed_dim,
        }
        tmp_path = settings.model_path.with_suffix(".pt.tmp")
        torch.save(payload, tmp_path)
        tmp_path.replace(settings.model_path)
        return settings.model_path


    def forward_probe(self, text: str = "hello rosa") -> dict[str, Any]:
        require_capacity("infer")
        self.net.eval()
        ids = self.net.encode_bytes(text).unsqueeze(0).to(self.device)
        with torch.no_grad():
            out = self.net(ids)
        return {
            "device": self.device,
            "cuda": self.device.startswith("cuda"),
            "logits_shape": list(out["logits"].shape),
            "embedding_dim": int(out["embedding"].shape[-1]),
            "train_steps": self.train_steps,
            "loaded_checkpoint": self._loaded,
        }

    def train_on_text(self, text: str, steps: int = 3) -> dict[str, Any]:
        require_capacity("train")
        st = require_capacity("train")
        seq_len = min(int(st.suggested_seq_len), int(settings.max_seq_len))
        self.net.train()
        raw = text.encode("utf-8", errors="replace")
        if len(raw) < 8:
            raw = (raw + b" " * 8)[:64]
        losses: list[float] = []
        for _ in range(max(1, steps)):
            # sliding window samples
            if len(raw) <= seq_len + 1:
                chunk = raw
            else:
                start = torch.randint(0, len(raw) - seq_len - 1, (1,)).item()
                chunk = raw[start : start + seq_len + 1]
            ids = torch.tensor([list(chunk)], dtype=torch.long, device=self.device)
            inp, tgt = ids[:, :-1], ids[:, 1:]
            out = self.net(inp)
            loss = F.cross_entropy(
                out["logits"].reshape(-1, self.net.vocab_size),
                tgt.reshape(-1),
            )
            self.optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.net.parameters(), 1.0)
            self.optimizer.step()
            self.train_steps += 1
            losses.append(float(loss.item()))
        self.save()
        return {
            "steps": len(losses),
            "losses": losses,
            "avg_loss": sum(losses) / max(1, len(losses)),
            "train_steps_total": self.train_steps,
            "device": self.device,
            "saved": str(settings.model_path),
        }

    def info(self) -> dict[str, Any]:
        n = sum(p.numel() for p in self.net.parameters())
        return {
            "parameters": n,
            "device": self.device,
            "embed_dim": self.net.embed_dim,
            "vocab_size": self.net.vocab_size,
            "train_steps": self.train_steps,
            "checkpoint": str(settings.model_path),
            "checkpoint_exists": settings.model_path.exists(),
            "pretrained_external_weights": False,
        }


    def train_understand(self, pairs: list[tuple[str, int]], steps: int = 10) -> dict:
        require_capacity("train")
        st = require_capacity("train")
        seq_len = min(int(st.suggested_seq_len), int(settings.max_seq_len))
        self.net.train()
        losses: list[float] = []
        if not pairs:
            return {"steps": 0, "avg_loss": None}
        for _ in range(max(1, steps)):
            text, label = pairs[torch.randint(0, len(pairs), (1,)).item()]
            raw = text.encode("utf-8", errors="replace")
            if len(raw) < 4:
                raw = (raw + b" " * 8)[:32]
            if len(raw) <= seq_len + 1:
                chunk = raw
            else:
                start = int(torch.randint(0, len(raw) - seq_len - 1, (1,)).item())
                chunk = raw[start : start + seq_len + 1]
            ids = torch.tensor([list(chunk)], dtype=torch.long, device=self.device)
            inp, tgt = ids[:, :-1], ids[:, 1:]
            out = self.net(inp)
            lm = F.cross_entropy(out["logits"].reshape(-1, self.net.vocab_size), tgt.reshape(-1))
            y = torch.tensor([int(label)], dtype=torch.long, device=self.device)
            cls = F.cross_entropy(out["class_logits"], y)
            loss = lm + 2.5 * cls
            self.optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.net.parameters(), 1.0)
            self.optimizer.step()
            self.train_steps += 1
            losses.append(float(loss.item()))
        self.save()
        return {
            "steps": len(losses),
            "avg_loss": sum(losses) / max(1, len(losses)),
            "train_steps_total": self.train_steps,
            "device": self.device,
            "saved": str(settings.model_path),
        }

    @torch.no_grad()
    def classify(self, text: str) -> dict:
        self.net.eval()
        self.net.to(self.device)
        ids = self.net.encode_bytes(text).unsqueeze(0).to(self.device)
        out = self.net(ids)
        probs = torch.softmax(out["class_logits"][0], dim=-1)
        pred = int(torch.argmax(probs).item())
        return {"label_id": pred, "confidence": float(probs[pred].item()), "probs": probs.detach().cpu().tolist()}

