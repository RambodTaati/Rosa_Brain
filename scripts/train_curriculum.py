# -*- coding: utf-8 -*-
"""Curriculum trainer: language first, then code."""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from rosa_brain.config import settings
from rosa_brain.model import ModelManager


PHASE_GLOBS = {
    "language": ["01_*.txt", "02_*.txt", "03_*.txt", "04_*.txt", "05_*.txt"],
    "code": ["code/*.txt", "code/*.py.txt"],
}


def load_phase(phase: str) -> str:
    corpus = settings.data_dir / "corpus"
    parts: list[str] = []
    for pattern in PHASE_GLOBS.get(phase, []):
        for p in sorted(corpus.glob(pattern)):
            parts.append(p.read_text(encoding="utf-8", errors="replace"))
    if not parts:
        raise SystemExit(f"no corpus files for phase={phase} under {corpus}")
    text = "\n\n".join(parts)
    target = 32_768 if phase == "language" else 65_536
    while len(text.encode("utf-8")) < target:
        text = text + "\n\n" + text
    return text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["language", "code"], default="language")
    ap.add_argument("--steps", type=int, default=int(os.environ.get("ROSA_TRAIN_STEPS", "1000")))
    ap.add_argument("--chunk", type=int, default=25)
    args = ap.parse_args()

    mgr = ModelManager()
    mgr.load_if_exists()
    text = load_phase(args.phase)
    print(json.dumps({
        "event": "start",
        "phase": args.phase,
        "device": mgr.device,
        "steps": args.steps,
        "bytes": len(text.encode("utf-8")),
        "params": sum(p.numel() for p in mgr.net.parameters()),
        "embed_dim": settings.embed_dim,
        "layers": settings.num_layers,
        "max_seq_len": settings.max_seq_len,
    }, ensure_ascii=False), flush=True)

    t0 = time.time()
    remaining = args.steps
    history = []
    while remaining > 0:
        n = min(args.chunk, remaining)
        result = mgr.train_on_text(text, steps=n)
        remaining -= n
        row = {
            "avg_loss": result["avg_loss"],
            "train_steps_total": result["train_steps_total"],
            "device": result["device"],
            "remaining": remaining,
        }
        history.append(row)
        print(json.dumps({"event": "progress", **row}, ensure_ascii=False), flush=True)

    out = {
        "event": "done",
        "phase": args.phase,
        "elapsed_sec": round(time.time() - t0, 2),
        "train_steps_total": mgr.train_steps,
        "checkpoint": str(settings.model_path),
        "final_avg_loss": history[-1]["avg_loss"] if history else None,
        "history": history,
    }
    log = settings.data_dir / f"train_{args.phase}_log.json"
    log.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
