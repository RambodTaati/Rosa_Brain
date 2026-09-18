# -*- coding: utf-8 -*-
"""Understanding mastery: English meaning detection first, then Persian."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from rosa_brain.config import settings
from rosa_brain.model import ModelManager

ROUNDS = [
    {"id": 1, "phase": "understand_en", "min_steps": 20000, "target_loss": 0.35, "label": "EN understand R1", "acc_target": 0.55},
    {"id": 2, "phase": "understand_en", "min_steps": 25000, "target_loss": 0.25, "label": "EN understand R2", "acc_target": 0.70},
    {"id": 3, "phase": "understand_en", "min_steps": 30000, "target_loss": 0.18, "label": "EN understand R3", "acc_target": 0.82},
    {"id": 4, "phase": "understand_fa", "min_steps": 15000, "target_loss": 0.30, "label": "FA understand R1", "acc_target": 0.50},
    {"id": 5, "phase": "understand_fa", "min_steps": 20000, "target_loss": 0.22, "label": "FA understand R2", "acc_target": 0.65},
]


def state_path() -> Path:
    return settings.data_dir / "auto_learn_state.json"


def load_state() -> dict:
    p = state_path()
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8-sig"))
    return {"mode": "understand", "phase_steps": 0, "history": [], "trend": [], "completed_rounds": []}


def save_state(st: dict) -> None:
    st["history"] = (st.get("history") or [])[-400:]
    st["trend"] = (st.get("trend") or [])[-300:]
    state_path().write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def load_pairs() -> list[tuple[str, int]]:
    p = settings.data_dir / "understand_pairs.jsonl"
    out = []
    raw = p.read_text(encoding="utf-8-sig")
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
            out.append((o["text"], int(o["label"])))
        except Exception:
            continue
    if not out:
        raise RuntimeError("no valid understand pairs")
    return out


def load_heldout() -> list[tuple[str, int]]:
    p = settings.data_dir / "understand_heldout.jsonl"
    if not p.exists():
        return []
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

def load_lm_corpus(phase: str) -> str:
    folder = "understand_en" if "en" in phase else "understand_fa"
    corpus = settings.data_dir / "corpus" / folder
    parts = [x.read_text(encoding="utf-8", errors="replace") for x in sorted(corpus.glob("*.txt"))]
    extra = settings.data_dir / "corpus" / ("english" if "en" in phase else "persian")
    if extra.exists():
        parts += [x.read_text(encoding="utf-8", errors="replace") for x in sorted(extra.glob("*.txt"))]
    text = "\n\n".join(parts)
    while len(text.encode("utf-8")) < 150_000:
        text = text + "\n\n" + text
    return text


def eval_acc(mgr: ModelManager, pairs: list[tuple[str, int]], n: int = 64) -> float:
    if not pairs:
        return 0.0
    correct = 0
    for i in range(n):
        text, label = pairs[i % len(pairs)]
        pred = mgr.classify(text)["label_id"]
        if pred == label:
            correct += 1
    return correct / n


def train_round(mgr: ModelManager, st: dict, rnd: dict, pairs: list[tuple[str, int]], held: list[tuple[str, int]] | None = None, chunk: int = 20) -> None:
    phase = rnd["phase"]
    held = held or []
    text = load_lm_corpus(phase)
    same = int(st.get("round_id") or 0) == int(rnd["id"])
    resume = int(st.get("phase_steps") or 0) if same else 0
    st.update({
        "mode": "understand",
        "phase": phase,
        "round_id": rnd["id"],
        "round_label": rnd["label"],
        "round_min_steps": rnd["min_steps"],
        "round_target_loss": rnd["target_loss"],
        "acc_target": rnd.get("acc_target", 0.5),
        "phase_steps": resume,
        "total_rounds": len(ROUNDS),
        "active_phase": phase,
    })
    save_state(st)
    print(json.dumps({"event": "round_start", "round": rnd, "resume_steps": resume, "device": mgr.device}, ensure_ascii=False), flush=True)

    recent = []
    recent_acc = []
    while True:
        try:
            cls_steps = max(1, int(chunk * 0.7))
            lm_steps = max(1, chunk - cls_steps)
            r1 = mgr.train_understand(pairs, steps=cls_steps)
            r2 = mgr.train_on_text(text, steps=lm_steps)
            avg = (float(r1["avg_loss"]) + float(r2["avg_loss"])) / 2
            st["phase_steps"] = int(st.get("phase_steps") or 0) + chunk
            st["total_steps"] = int(r2["train_steps_total"])
        except Exception as exc:
            print(json.dumps({"event": "train_error", "error": str(exc)}, ensure_ascii=False), flush=True)
            time.sleep(2)
            continue

        recent.append(avg)
        recent = recent[-20:]
        avg_recent = sum(recent) / len(recent)
        if st["phase_steps"] % 100 < chunk:
            acc_train = eval_acc(mgr, pairs, n=48)
            acc_hold = eval_acc(mgr, held, n=min(64, max(8, len(held)))) if held else acc_train
            acc = 0.35 * acc_train + 0.65 * acc_hold
            recent_acc.append(acc)
            recent_acc = recent_acc[-10:]
            st["train_detect_accuracy"] = acc_train
            st["heldout_accuracy"] = acc_hold
        acc_now = sum(recent_acc) / len(recent_acc) if recent_acc else 0.0

        steps_pct = min(100.0, 100.0 * st["phase_steps"] / max(1, rnd["min_steps"]))
        start_ref, target = 2.5, float(rnd["target_loss"])
        loss_pct = 100.0 if avg_recent <= target else max(0.0, min(100.0, 100.0 * (start_ref - avg_recent) / max(1e-6, start_ref - target)))
        acc_target = float(rnd.get("acc_target") or 0.5)
        acc_pct = min(100.0, 100.0 * acc_now / max(1e-6, acc_target))
        combined = min(100.0, 0.45 * steps_pct + 0.25 * loss_pct + 0.30 * acc_pct)
        combined = max(combined, float(st.get("best_round_percent") or 0))

        completed = len(st.get("completed_rounds") or [])
        overall = min(100.0, 100.0 * (completed + combined / 100.0) / len(ROUNDS))
        overall = max(overall, float(st.get("best_overall_percent") or 0))
        st["best_round_percent"] = combined
        st["best_overall_percent"] = overall
        st["detect_accuracy"] = acc_now

        row = {
            "event": "progress",
            "phase": phase,
            "round_id": rnd["id"],
            "round_label": rnd["label"],
            "phase_steps": st["phase_steps"],
            "total_steps": st["total_steps"],
            "recent_avg_loss": avg_recent,
            "detect_accuracy": acc_now,
            "heldout_accuracy": st.get("heldout_accuracy"),
            "train_detect_accuracy": st.get("train_detect_accuracy"),
            "steps_percent": round(steps_pct, 1),
            "loss_percent": round(loss_pct, 1),
            "acc_percent": round(acc_pct, 1),
            "combined_percent": round(combined, 1),
            "device": mgr.device,
            "ts": time.time(),
        }
        st.setdefault("history", []).append(row)
        st.setdefault("trend", []).append({"t": row["ts"], "pct": row["combined_percent"], "loss": avg_recent, "acc": acc_now, "steps": st["phase_steps"], "round_id": rnd["id"]})
        print(json.dumps(row, ensure_ascii=False), flush=True)
        save_state(st)

        if (
            st["phase_steps"] >= rnd["min_steps"]
            and avg_recent <= rnd["target_loss"]
            and acc_now >= acc_target
            and len(recent) >= 8
        ):
            done = {"event": "round_done", "round_id": rnd["id"], "loss": avg_recent, "acc": acc_now, "steps": st["phase_steps"]}
            print(json.dumps(done, ensure_ascii=False), flush=True)
            st.setdefault("completed_rounds", []).append(done)
            st["best_round_percent"] = 0.0
            save_state(st)
            return


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk", type=int, default=20)
    ap.add_argument("--start-round", type=int, default=1)
    args = ap.parse_args()
    mgr = ModelManager()
    loaded = mgr.load_if_exists()
    print(json.dumps({"event": "model", "loaded": loaded, "params": sum(p.numel() for p in mgr.net.parameters()), "device": mgr.device}, ensure_ascii=False), flush=True)
    pairs = load_pairs()
    held = load_heldout()
    st = load_state()
    # fresh understand path if coming from language mastery done
    if st.get("mode") != "understand" or st.get("phase") == "done":
        st = {"mode": "understand", "phase_steps": 0, "history": [], "trend": [], "completed_rounds": []}
        # keep old language state backup
        bak = settings.data_dir / "auto_learn_state_language_done.json"
        if not bak.exists() and state_path().exists():
            bak.write_text(state_path().read_text(encoding="utf-8-sig"), encoding="utf-8")
        save_state(st)

    start_i = max(0, int(args.start_round) - 1)
    completed_ids = {c.get("round_id") for c in st.get("completed_rounds") or []}
    if st.get("round_id") and int(st.get("phase_steps") or 0) < int(st.get("round_min_steps") or 10**12) and st.get("phase") != "done":
        start_i = int(st["round_id"]) - 1
    elif completed_ids:
        start_i = max(start_i, len([r for r in ROUNDS if r["id"] in completed_ids]))

    for rnd in ROUNDS[start_i:]:
        if int(st.get("round_id") or 0) != rnd["id"]:
            st["best_round_percent"] = 0.0
            st["phase_steps"] = 0
        train_round(mgr, st, rnd, pairs, held=held, chunk=args.chunk)

    st["phase"] = "done"
    st["round_label"] = "Understanding path complete"
    st["best_overall_percent"] = 100.0
    save_state(st)
    print(json.dumps({"event": "understand_path_done"}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
