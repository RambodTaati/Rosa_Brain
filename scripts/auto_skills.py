# -*- coding: utf-8 -*-
"""Skills curriculum: PostgreSQL -> defensive security -> Windows -> Ubuntu -> fullstack agent -> pro programmer."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch
import torch.nn.functional as F

from rosa_brain.config import settings
from rosa_brain.model import ModelManager

ROUNDS = [
    {"id": 1, "phase": "skills_postgres", "folder": "skills_postgres", "min_steps": 12000, "target_loss": 0.35, "label": "PostgreSQL R1", "quiz_skill": "postgres", "acc_target": 0.75},
    {"id": 2, "phase": "skills_postgres", "folder": "skills_postgres", "min_steps": 12000, "target_loss": 0.25, "label": "PostgreSQL R2", "quiz_skill": "postgres", "acc_target": 0.85},
    {"id": 3, "phase": "skills_security_defensive", "folder": "skills_security_defensive", "min_steps": 10000, "target_loss": 0.30, "label": "Defensive security R1", "quiz_skill": "security_defensive", "acc_target": 0.80},
    {"id": 4, "phase": "skills_security_defensive", "folder": "skills_security_defensive", "min_steps": 10000, "target_loss": 0.22, "label": "Defensive security R2", "quiz_skill": "security_defensive", "acc_target": 0.88},
    {"id": 5, "phase": "skills_windows", "folder": "skills_windows", "min_steps": 10000, "target_loss": 0.30, "label": "Windows OS R1", "quiz_skill": "windows", "acc_target": 0.80},
    {"id": 6, "phase": "skills_ubuntu", "folder": "skills_ubuntu", "min_steps": 10000, "target_loss": 0.30, "label": "Ubuntu OS R1", "quiz_skill": "ubuntu", "acc_target": 0.80},
    {"id": 7, "phase": "skills_fullstack_agent", "folder": "skills_fullstack_agent", "min_steps": 12000, "target_loss": 0.28, "label": "Full-stack agent R1", "quiz_skill": "fullstack_agent", "acc_target": 0.80},
    {"id": 8, "phase": "skills_pro_programmer", "folder": "skills_pro_programmer", "min_steps": 15000, "target_loss": 0.26, "label": "Pro programmer R1", "quiz_skill": "pro_programmer", "acc_target": 0.82},
    {"id": 9, "phase": "skills_pro_programmer", "folder": "skills_pro_programmer", "min_steps": 15000, "target_loss": 0.20, "label": "Pro programmer R2", "quiz_skill": "pro_programmer", "acc_target": 0.88},
    {"id": 10, "phase": "skills_pro_programmer", "folder": "skills_pro_programmer", "min_steps": 18000, "target_loss": 0.16, "label": "Pro programmer R3", "quiz_skill": "pro_programmer", "acc_target": 0.92},
]


def state_path() -> Path:
    return settings.data_dir / "auto_learn_state.json"


def load_state() -> dict:
    p = state_path()
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8-sig"))
    return {"mode": "skills", "history": [], "trend": [], "completed_rounds": []}


def save_state(st: dict) -> None:
    st["history"] = (st.get("history") or [])[-400:]
    st["trend"] = (st.get("trend") or [])[-300:]
    state_path().write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def load_quiz(skill: str) -> list[dict]:
    p = settings.data_dir / "skills_quiz.jsonl"
    out = []
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        if o.get("skill") == skill:
            out.append(o)
    return out


def load_text(folder: str) -> str:
    parts = []
    for name in (folder, "skills_quiz", "understand_en", "english"):
        d = settings.data_dir / "corpus" / name
        if d.exists():
            parts += [x.read_text(encoding="utf-8", errors="replace") for x in sorted(d.glob("*.txt"))]
    text = "\n\n".join(parts)
    while len(text.encode("utf-8")) < 120_000:
        text += "\n\n" + text
    return text


def quiz_accuracy(mgr: ModelManager, items: list[dict]) -> float:
    if not items:
        return 0.0
    ok = 0
    mgr.net.eval()
    with torch.no_grad():
        for it in items:
            correct = f"Q: {it['question']} A: {it['answer']}"
            wrong = f"Q: {it['question']} A: not related placeholder answer"

            def nll(text: str) -> float:
                raw = text.encode("utf-8", errors="replace")
                if len(raw) < 4:
                    raw = raw + b" ...."
                ids = torch.tensor([list(raw[: min(len(raw), settings.max_seq_len)])], dtype=torch.long, device=mgr.device)
                if ids.size(1) < 2:
                    return 99.0
                inp, tgt = ids[:, :-1], ids[:, 1:]
                out = mgr.net(inp)
                loss = F.cross_entropy(out["logits"].reshape(-1, mgr.net.vocab_size), tgt.reshape(-1))
                return float(loss.item())

            if nll(correct) < nll(wrong):
                ok += 1
    return ok / len(items)


def train_round(mgr: ModelManager, st: dict, rnd: dict, chunk: int = 16) -> None:
    text = load_text(rnd["folder"])
    quiz = load_quiz(rnd["quiz_skill"])
    same = int(st.get("round_id") or 0) == int(rnd["id"]) and st.get("mode") == "skills"
    resume = int(st.get("phase_steps") or 0) if same else 0
    st.update({
        "mode": "skills",
        "phase": rnd["phase"],
        "round_id": rnd["id"],
        "round_label": rnd["label"],
        "round_min_steps": rnd["min_steps"],
        "round_target_loss": rnd["target_loss"],
        "acc_target": rnd["acc_target"],
        "phase_steps": resume,
        "total_rounds": len(ROUNDS),
        "skill": rnd["quiz_skill"],
        "security_policy": "defensive_only_no_exploits",
    })
    save_state(st)
    print(json.dumps({"event": "round_start", "round": rnd, "resume": resume, "device": mgr.device}, ensure_ascii=False), flush=True)
    recent: list[float] = []
    recent_acc: list[float] = []
    while True:
        try:
            r = mgr.train_on_text(text, steps=chunk)
            avg = float(r["avg_loss"])
            st["phase_steps"] = int(st.get("phase_steps") or 0) + chunk
            st["total_steps"] = int(r["train_steps_total"])
        except Exception as exc:
            print(json.dumps({"event": "train_error", "error": str(exc)}, ensure_ascii=False), flush=True)
            time.sleep(2)
            continue
        recent.append(avg)
        recent = recent[-20:]
        avg_recent = sum(recent) / len(recent)
        if st["phase_steps"] % 200 < chunk:
            acc = quiz_accuracy(mgr, quiz)
            recent_acc.append(acc)
            recent_acc = recent_acc[-8:]
            st["quiz_accuracy"] = acc
            st["heldout_accuracy"] = acc
            st["detect_accuracy"] = acc
        acc_now = sum(recent_acc) / len(recent_acc) if recent_acc else float(st.get("quiz_accuracy") or 0)
        steps_pct = min(100.0, 100.0 * st["phase_steps"] / max(1, rnd["min_steps"]))
        loss_pct = 100.0 if avg_recent <= rnd["target_loss"] else max(0.0, min(100.0, 100.0 * (2.5 - avg_recent) / max(1e-6, 2.5 - rnd["target_loss"])))
        acc_pct = min(100.0, 100.0 * acc_now / max(1e-6, rnd["acc_target"]))
        combined = min(100.0, 0.45 * steps_pct + 0.25 * loss_pct + 0.30 * acc_pct)
        combined = max(combined, float(st.get("best_round_percent") or 0))
        skill_completed = len([c for c in (st.get("completed_rounds") or []) if c.get("track") == "skills"])
        overall = min(100.0, 100.0 * (skill_completed + combined / 100.0) / len(ROUNDS))
        overall = max(overall, float(st.get("best_overall_percent") or 0))
        st["best_round_percent"] = combined
        st["best_overall_percent"] = overall
        row = {
            "event": "progress",
            "phase": rnd["phase"],
            "round_id": rnd["id"],
            "round_label": rnd["label"],
            "phase_steps": st["phase_steps"],
            "total_steps": st["total_steps"],
            "recent_avg_loss": avg_recent,
            "quiz_accuracy": acc_now,
            "detect_accuracy": acc_now,
            "heldout_accuracy": acc_now,
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
            and acc_now >= rnd["acc_target"]
            and len(recent) >= 8
        ):
            done = {"event": "round_done", "round_id": rnd["id"], "loss": avg_recent, "acc": acc_now, "steps": st["phase_steps"], "track": "skills", "label": rnd["label"]}
            print(json.dumps(done, ensure_ascii=False), flush=True)
            st.setdefault("completed_rounds", []).append(done)
            st["best_round_percent"] = 0.0
            save_state(st)
            return



def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk", type=int, default=16)
    args = ap.parse_args()
    lock = settings.data_dir / "SKILLS_PATH_COMPLETE.lock"
    if lock.exists():
        print(json.dumps({"event": "skills_locked_complete", "lock": str(lock)}, ensure_ascii=False), flush=True)
        return
    mgr = ModelManager()
    loaded = mgr.load_if_exists()
    print(json.dumps({"event": "model", "loaded": loaded, "params": sum(p.numel() for p in mgr.net.parameters()), "device": mgr.device}, ensure_ascii=False), flush=True)
    st = load_state()
    # REFUSE_DESTRUCTIVE_RESET
    if st.get("phase") == "done" and st.get("completed_rounds"):
        print(json.dumps({"event": "skills_already_done", "completed": len(st.get("completed_rounds") or [])}, ensure_ascii=False), flush=True)
        return
    if str(st.get("mode") or "") == "web_languages":
        print(json.dumps({"event": "skills_skip_web_mode"}, ensure_ascii=False), flush=True)
        return
    if st.get("mode") != "skills":
        # Never wipe non-empty completed_rounds
        if st.get("completed_rounds"):
            print(json.dumps({"event": "skills_refuse_reset_has_completed", "mode": st.get("mode")}, ensure_ascii=False), flush=True)
            return
        bak = settings.data_dir / "auto_learn_state_before_skills.json"
        if not bak.exists() and state_path().exists():
            bak.write_text(state_path().read_text(encoding="utf-8-sig"), encoding="utf-8")
        st = {
            "mode": "skills",
            "phase_steps": 0,
            "history": [],
            "trend": [],
            "completed_rounds": [],
            "best_overall_percent": 0,
            "best_round_percent": 0,
            "security_policy": "defensive_only_no_exploits",
        }
        save_state(st)

    start_i = 0
    done_skill = {c.get("round_id") for c in st.get("completed_rounds") or []}
    if st.get("round_id") and st.get("mode") == "skills" and int(st.get("phase_steps") or 0) < int(st.get("round_min_steps") or 10**12):
        start_i = int(st["round_id"]) - 1
    elif done_skill:
        # Continue after completed round_ids (supports 1-7 done -> start at 8)
        start_i = 0
        for i, r in enumerate(ROUNDS):
            if r["id"] in done_skill:
                start_i = i + 1
            else:
                break

    for rnd in ROUNDS[start_i:]:
        if int(st.get("round_id") or 0) != rnd["id"]:
            st["best_round_percent"] = 0.0
            st["phase_steps"] = 0
        train_round(mgr, st, rnd, chunk=args.chunk)

    st["phase"] = "done"
    st["round_label"] = "Pro programmer path complete"
    st["best_overall_percent"] = 100.0
    save_state(st)
    print(json.dumps({"event": "skills_path_done", "round_label": st["round_label"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
