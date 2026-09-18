"""Bootstrap training for Rosa_Brain tiny net (from-scratch, GPU)."""
from __future__ import annotations

import json
import time
from pathlib import Path

from rosa_brain.config import settings
from rosa_brain.model import ModelManager


def load_corpus() -> str:
    corpus_dir = settings.data_dir / "corpus"
    parts: list[str] = []
    if corpus_dir.exists():
        for p in sorted(corpus_dir.glob("*.txt")):
            parts.append(p.read_text(encoding="utf-8", errors="replace"))
    if not parts:
        parts.append(
            "Rosa Brain. Independent Python brain. Learn. Remember. Improve.\n"
            "من رزا برین هستم و یاد می‌گیرم.\n"
        )
    text = "\n\n".join(parts)
    # Repeat to give enough sliding windows
    while len(text.encode("utf-8")) < 8192:
        text = text + "\n" + text
    return text


def main() -> None:
    steps = int(__import__("os").environ.get("ROSA_TRAIN_STEPS", "200"))
    chunk_steps = 20
    mgr = ModelManager()
    mgr.load_if_exists()
    text = load_corpus()
    print(json.dumps({"event": "start", "device": mgr.device, "steps": steps, "bytes": len(text.encode("utf-8")), "params": sum(p.numel() for p in mgr.net.parameters())}, ensure_ascii=False))
    t0 = time.time()
    remaining = steps
    history: list[dict] = []
    while remaining > 0:
        n = min(chunk_steps, remaining)
        result = mgr.train_on_text(text, steps=n)
        remaining -= n
        history.append({"avg_loss": result["avg_loss"], "train_steps_total": result["train_steps_total"], "device": result["device"]})
        print(json.dumps({"event": "progress", **history[-1], "remaining": remaining}, ensure_ascii=False), flush=True)
    elapsed = time.time() - t0
    out = {
        "event": "done",
        "elapsed_sec": round(elapsed, 2),
        "train_steps_total": mgr.train_steps,
        "checkpoint": str(settings.model_path),
        "final_avg_loss": history[-1]["avg_loss"] if history else None,
        "history": history,
    }
    log_path = settings.data_dir / "train_log.json"
    log_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
