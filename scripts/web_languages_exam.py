# -*- coding: utf-8 -*-
"""Held-out web languages exam (NLL preference scoring, local TinyBrainNet only)."""
from __future__ import annotations

import json
import time
from pathlib import Path

import torch
import torch.nn.functional as F

from rosa_brain.config import settings
from rosa_brain.model import ModelManager


def load_jsonl(path: Path, skill: str | None = None) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        if skill is None or o.get("skill") == skill:
            out.append(o)
    return out


def nll_preference_correct(mgr: ModelManager, item: dict) -> tuple[bool, float, float]:
    correct = f"Q: {item['question']} A: {item['answer']}"
    wrong = f"Q: {item['question']} A: not related placeholder answer"

    def nll(text: str) -> float:
        raw = text.encode("utf-8", errors="replace")
        if len(raw) < 4:
            raw = raw + b" ...."
        ids = torch.tensor(
            [list(raw[: min(len(raw), settings.max_seq_len)])],
            dtype=torch.long,
            device=mgr.device,
        )
        if ids.size(1) < 2:
            return 99.0
        inp, tgt = ids[:, :-1], ids[:, 1:]
        out = mgr.net(inp)
        loss = F.cross_entropy(out["logits"].reshape(-1, mgr.net.vocab_size), tgt.reshape(-1))
        return float(loss.item())

    c, w = nll(correct), nll(wrong)
    return (c < w), c, w


def score_items(mgr: ModelManager, items: list[dict]) -> tuple[float, list[dict]]:
    if not items:
        return 0.0, []
    ok = 0
    rows: list[dict] = []
    mgr.net.eval()
    with torch.no_grad():
        for i, it in enumerate(items):
            good, c, w = nll_preference_correct(mgr, it)
            if good:
                ok += 1
            rows.append(
                {
                    "i": i,
                    "ok": good,
                    "nll_correct": round(c, 4),
                    "nll_wrong": round(w, 4),
                    "question": (it.get("question") or "")[:160],
                }
            )
    return ok / len(items), rows


def grade_letter(acc: float) -> str:
    if acc >= 0.9:
        return "A"
    if acc >= 0.8:
        return "B"
    if acc >= 0.7:
        return "C"
    if acc >= 0.6:
        return "D"
    return "F"


def main() -> None:
    mgr = ModelManager()
    loaded = mgr.load_if_exists()
    params = int(sum(p.numel() for p in mgr.net.parameters()))
    held_path = settings.data_dir / "web_languages_exam_heldout.jsonl"
    quiz_path = settings.data_dir / "skills_quiz.jsonl"
    held = load_jsonl(held_path, "web_languages_exam")
    practice = load_jsonl(quiz_path, "web_languages")
    held_acc, held_rows = score_items(mgr, held)
    prac_acc, prac_rows = score_items(mgr, practice)
    letter = grade_letter(held_acc)
    result = {
        "timestamp": time.time(),
        "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "device": str(mgr.device),
        "params": params,
        "checkpoint_loaded": bool(loaded),
        "heldout_accuracy": round(held_acc, 4),
        "practice_quiz_accuracy": round(prac_acc, 4),
        "n_heldout": len(held),
        "n_practice": len(practice),
        "grade": letter,
        "baseline": True,
        "per_item": {
            "heldout": held_rows,
            "practice_quiz": prac_rows[:40],
        },
        "notes": (
            "NLL preference scoring identical to auto_skills.quiz_accuracy "
            "(correct Q+A vs wrong placeholder). Local TinyBrainNet only; no cloud LLMs. "
            "Original curriculum; no W3Schools verbatim text."
        ),
    }
    out = settings.data_dir / "web_languages_exam_results.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    # also save explicit baseline copy when first run
    base = settings.data_dir / "web_languages_exam_results_baseline.json"
    if not base.exists():
        base.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "event": "web_languages_exam_summary",
        "heldout_accuracy": result["heldout_accuracy"],
        "practice_quiz_accuracy": result["practice_quiz_accuracy"],
        "grade": letter,
        "n_heldout": result["n_heldout"],
        "n_practice": result["n_practice"],
        "device": result["device"],
        "params": params,
        "checkpoint_loaded": bool(loaded),
        "results_path": str(out),
    }
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
