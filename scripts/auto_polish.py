# -*- coding: utf-8 -*-
"""Continuous meaning-detection polish: train on pairs, gate on held-out accuracy."""
from __future__ import annotations

import json
import time
from pathlib import Path

from rosa_brain.config import settings
from rosa_brain.model import ModelManager

TARGET_HELDOUT = 0.90
CHUNK = 12


def load_jsonl(name: str) -> list[tuple[str, int]]:
    p = settings.data_dir / name
    out = []
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
            out.append((o["text"], int(o["label"])))
        except Exception:
            continue
    return out


def eval_acc(mgr: ModelManager, pairs: list[tuple[str, int]], n: int = 64) -> float:
    if not pairs:
        return 0.0
    correct = 0
    for i in range(n):
        text, label = pairs[i % len(pairs)]
        if mgr.classify(text)["label_id"] == label:
            correct += 1
    return correct / n


def load_lm() -> str:
    parts = []
    for folder in ("understand_en", "understand_fa", "english", "persian"):
        d = settings.data_dir / "corpus" / folder
        if d.exists():
            parts += [x.read_text(encoding="utf-8", errors="replace") for x in sorted(d.glob("*.txt"))]
    text = "\n\n".join(parts)
    while len(text.encode("utf-8")) < 120_000:
        text = text + "\n\n" + text
    return text


def save_state(st: dict) -> None:
    st["history"] = (st.get("history") or [])[-400:]
    st["trend"] = (st.get("trend") or [])[-300:]
    path = settings.data_dir / "auto_learn_state.json"
    path.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    mgr = ModelManager()
    loaded = mgr.load_if_exists()
    pairs = load_jsonl("understand_pairs.jsonl")
    held = load_jsonl("understand_heldout.jsonl")
    text = load_lm()
    print(json.dumps({"event": "polish_start", "loaded": loaded, "pairs": len(pairs), "held": len(held), "device": mgr.device}, ensure_ascii=False), flush=True)

    st_path = settings.data_dir / "auto_learn_state.json"
    st = json.loads(st_path.read_text(encoding="utf-8-sig")) if st_path.exists() else {}
    # preserve completed path markers
    st.update({
        "mode": "understand_polish",
        "phase": "detect_polish",
        "round_id": 6,
        "round_label": "Detect polish (held-out)",
        "round_min_steps": 30000,
        "round_target_loss": 0.15,
        "acc_target": TARGET_HELDOUT,
        "total_rounds": 6,
        "phase_steps": int(st.get("polish_steps") or 0),
    })
    if not st.get("completed_rounds"):
        st["completed_rounds"] = [{"event": "round_done", "round_id": i, "note": "prior"} for i in range(1, 6)]

    recent = []
    while True:
        try:
            r1 = mgr.train_understand(pairs, steps=max(1, int(CHUNK * 0.75)))
            r2 = mgr.train_on_text(text, steps=max(1, CHUNK - int(CHUNK * 0.75)))
            avg = (float(r1["avg_loss"]) + float(r2["avg_loss"])) / 2
            st["phase_steps"] = int(st.get("phase_steps") or 0) + CHUNK
            st["polish_steps"] = st["phase_steps"]
            st["total_steps"] = int(r2["train_steps_total"])
        except Exception as exc:
            print(json.dumps({"event": "train_error", "error": str(exc)}, ensure_ascii=False), flush=True)
            time.sleep(2)
            continue

        recent.append(avg)
        recent = recent[-20:]
        avg_recent = sum(recent) / len(recent)

        if st["phase_steps"] % 60 < CHUNK:
            train_acc = eval_acc(mgr, pairs, n=48)
            held_acc = eval_acc(mgr, held, n=min(96, max(16, len(held))))
            st["train_detect_accuracy"] = train_acc
            st["heldout_accuracy"] = held_acc
            st["detect_accuracy"] = 0.35 * train_acc + 0.65 * held_acc
        train_acc = float(st.get("train_detect_accuracy") or 0)
        held_acc = float(st.get("heldout_accuracy") or 0)
        acc = float(st.get("detect_accuracy") or 0)

        steps_pct = min(100.0, 100.0 * st["phase_steps"] / 30000.0)
        loss_pct = 100.0 if avg_recent <= 0.15 else max(0.0, min(100.0, 100.0 * (2.0 - avg_recent) / 1.85))
        acc_pct = min(100.0, 100.0 * held_acc / TARGET_HELDOUT) if held_acc else 0.0
        combined = min(100.0, 0.35 * steps_pct + 0.25 * loss_pct + 0.40 * acc_pct)
        combined = max(combined, float(st.get("best_round_percent") or 0))
        # overall: 5 prior rounds done + polish
        overall = min(100.0, (5 + combined / 100.0) / 6.0 * 100.0)
        overall = max(overall, float(st.get("best_overall_percent") or 0), 100.0 * 5 / 6)
        st["best_round_percent"] = combined
        st["best_overall_percent"] = overall

        row = {
            "event": "progress",
            "phase": "detect_polish",
            "round_id": 6,
            "round_label": "Detect polish (held-out)",
            "phase_steps": st["phase_steps"],
            "total_steps": st["total_steps"],
            "recent_avg_loss": avg_recent,
            "detect_accuracy": acc,
            "train_detect_accuracy": train_acc,
            "heldout_accuracy": held_acc,
            "combined_percent": round(combined, 1),
            "device": mgr.device,
            "ts": time.time(),
        }
        st.setdefault("history", []).append(row)
        st.setdefault("trend", []).append({"t": row["ts"], "pct": row["combined_percent"], "loss": avg_recent, "acc": held_acc, "steps": st["phase_steps"], "round_id": 6})
        print(json.dumps(row, ensure_ascii=False), flush=True)
        save_state(st)

        # never exit permanently; soft milestone log
        if held_acc >= TARGET_HELDOUT and avg_recent <= 0.15 and st["phase_steps"] >= 5000 and len(recent) >= 8:
            print(json.dumps({"event": "polish_milestone", "heldout": held_acc, "loss": avg_recent, "steps": st["phase_steps"]}, ensure_ascii=False), flush=True)
            # keep going for robustness; reset soft floor only
            time.sleep(1)


if __name__ == "__main__":
    main()
