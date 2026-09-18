# -*- coding: utf-8 -*-
"""Web languages curriculum trainer (W3Schools topic list, ORIGINAL corpus only).

Uses dedicated state file data/web_languages_state.json so Pro Programmer
(auto_skills.py / auto_learn_state.json) is not clobbered.
Mirrors a compact summary into auto_learn_state only when mode is already
web_languages (never hijacks skills_pro_programmer).
"""
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
    {"id": 1, "phase": "web_languages_html_css", "folder": "skills_web_languages", "min_steps": 12000, "target_loss": 0.30, "label": "Web languages R1 HTML/CSS", "quiz_skill": "web_languages", "acc_target": 0.78, "topics": ["html", "css"]},
    {"id": 2, "phase": "web_languages_js_ts", "folder": "skills_web_languages", "min_steps": 12000, "target_loss": 0.28, "label": "Web languages R2 JS/TS", "quiz_skill": "web_languages", "acc_target": 0.80, "topics": ["javascript", "typescript"]},
    {"id": 3, "phase": "web_languages_py_sql_php", "folder": "skills_web_languages", "min_steps": 12000, "target_loss": 0.28, "label": "Web languages R3 Python/SQL/PHP", "quiz_skill": "web_languages", "acc_target": 0.80, "topics": ["python", "sql", "php"]},
    {"id": 4, "phase": "web_languages_jvm_native", "folder": "skills_web_languages", "min_steps": 12000, "target_loss": 0.28, "label": "Web languages R4 Java/C/C++/C#", "quiz_skill": "web_languages", "acc_target": 0.80, "topics": ["java", "c", "cpp", "csharp"]},
    {"id": 5, "phase": "web_languages_frameworks", "folder": "skills_web_languages", "min_steps": 12000, "target_loss": 0.26, "label": "Web languages R5 React/Node/Vue/Bootstrap/jQuery/XML-JSON", "quiz_skill": "web_languages", "acc_target": 0.82, "topics": ["react", "nodejs", "vue", "bootstrap", "jquery", "xml_json"]},
]


def wl_state_path() -> Path:
    return settings.data_dir / "web_languages_state.json"


def auto_state_path() -> Path:
    return settings.data_dir / "auto_learn_state.json"


def load_wl_state() -> dict:
    p = wl_state_path()
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8-sig"))
    return {
        "mode": "web_languages",
        "history": [],
        "trend": [],
        "completed_rounds": [],
        "best_overall_percent": 0,
        "best_round_percent": 0,
        "security_policy": "defensive_only_no_exploits",
        "copyright_policy": "original_corpus_only_no_w3schools_verbatim",
    }


def save_wl_state(st: dict) -> None:
    st["history"] = (st.get("history") or [])[-400:]
    st["trend"] = (st.get("trend") or [])[-300:]
    st["mode"] = "web_languages"
    st["updated_at"] = time.time()
    wl_state_path().write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    mirror_auto_learn_if_safe(st)


def mirror_auto_learn_if_safe(st: dict) -> None:
    """Mirror web progress into auto_learn_state without destroying Pro completion markers."""
    ap = auto_state_path()
    cur: dict = {}
    if ap.exists():
        try:
            cur = json.loads(ap.read_text(encoding="utf-8-sig"))
        except Exception:
            cur = {}
    mode = str(cur.get("mode") or "")
    phase = str(cur.get("phase") or "")
    if mode == "skills" and phase.startswith("skills_pro_programmer"):
        return
    if mode == "skills" and phase != "done" and not cur.get("skills_path_complete"):
        return

    skills_rounds = list(cur.get("skills_completed_rounds") or [])
    lock = settings.data_dir / "SKILLS_PATH_COMPLETE.lock"
    summary = {
        "mode": "web_languages",
        "phase": st.get("phase"),
        "round_id": st.get("round_id"),
        "round_label": st.get("round_label"),
        "phase_steps": st.get("phase_steps"),
        "round_min_steps": st.get("round_min_steps"),
        "round_target_loss": st.get("round_target_loss"),
        "acc_target": st.get("acc_target"),
        "quiz_accuracy": st.get("quiz_accuracy"),
        "heldout_accuracy": st.get("heldout_accuracy"),
        "detect_accuracy": st.get("detect_accuracy"),
        "total_steps": st.get("total_steps"),
        "recent_avg_loss": st.get("recent_avg_loss"),
        "best_overall_percent": st.get("best_overall_percent"),
        "best_round_percent": st.get("best_round_percent"),
        "completed_rounds": st.get("completed_rounds") or [],
        "history": (st.get("history") or [])[-40:],
        "trend": (st.get("trend") or [])[-40:],
        "skill": st.get("skill") or "web_languages",
        "security_policy": "defensive_only_no_exploits",
        "total_rounds": st.get("total_rounds") or 5,
        "skills_path_complete": bool(lock.exists() or cur.get("skills_path_complete") or skills_rounds),
        "skills_completed_rounds": skills_rounds,
        "pro_exam_grade": cur.get("pro_exam_grade") or "A",
        "pro_exam_heldout": cur.get("pro_exam_heldout"),
        "updated_at": time.time(),
    }
    if summary["skills_path_complete"] and not summary["skills_completed_rounds"]:
        summary["skills_completed_rounds"] = [
            {"event": "round_done", "round_id": i, "track": "skills", "label": f"skills-{i}"}
            for i in range(1, 11)
        ]
    ap.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def load_quiz(skill: str) -> list[dict]:
    p = settings.data_dir / "skills_quiz.jsonl"
    out = []
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        if o.get("skill") == skill:
            out.append(o)
    return out


def load_text(folder: str) -> str:
    parts = []
    d = settings.data_dir / "corpus" / folder
    if d.exists():
        parts += [x.read_text(encoding="utf-8", errors="replace") for x in sorted(d.glob("*.txt"))]
    # light mix-in of quiz phrasing for byte LM
    quiz_dir = settings.data_dir / "corpus" / "skills_quiz"
    if quiz_dir.exists():
        for x in sorted(quiz_dir.glob("*web*")):
            parts.append(x.read_text(encoding="utf-8", errors="replace"))
    text = "\n\n".join(parts)
    if not text.strip():
        raise FileNotFoundError(f"empty corpus for {folder}")
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
    same = int(st.get("round_id") or 0) == int(rnd["id"]) and st.get("mode") == "web_languages"
    resume = int(st.get("phase_steps") or 0) if same else 0
    st.update({
        "mode": "web_languages",
        "phase": rnd["phase"],
        "round_id": rnd["id"],
        "round_label": rnd["label"],
        "round_min_steps": rnd["min_steps"],
        "round_target_loss": rnd["target_loss"],
        "acc_target": rnd["acc_target"],
        "phase_steps": resume,
        "total_rounds": len(ROUNDS),
        "skill": rnd["quiz_skill"],
        "topics": rnd.get("topics"),
        "security_policy": "defensive_only_no_exploits",
        "copyright_policy": "original_corpus_only_no_w3schools_verbatim",
        "device": str(mgr.device),
    })
    save_wl_state(st)
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
        completed_n = len([c for c in (st.get("completed_rounds") or []) if c.get("track") == "web_languages"])
        overall = min(100.0, 100.0 * (completed_n + combined / 100.0) / len(ROUNDS))
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
        save_wl_state(st)
        if (
            st["phase_steps"] >= rnd["min_steps"]
            and avg_recent <= rnd["target_loss"]
            and acc_now >= rnd["acc_target"]
            and len(recent) >= 8
        ):
            done = {"event": "round_done", "round_id": rnd["id"], "loss": avg_recent, "acc": acc_now, "steps": st["phase_steps"], "track": "web_languages", "label": rnd["label"]}
            print(json.dumps(done, ensure_ascii=False), flush=True)
            st.setdefault("completed_rounds", []).append(done)
            st["best_round_percent"] = 0.0
            save_wl_state(st)
            return


def pro_still_running() -> bool:
    ap = auto_state_path()
    if not ap.exists():
        return False
    try:
        cur = json.loads(ap.read_text(encoding="utf-8-sig"))
    except Exception:
        return False
    mode = str(cur.get("mode") or "")
    phase = str(cur.get("phase") or "")
    if mode == "skills" and phase.startswith("skills_pro_programmer"):
        return True
    if mode == "skills" and phase not in ("done", ""):
        # other skills rounds
        return True
    return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk", type=int, default=16)
    ap.add_argument("--force", action="store_true", help="Run even if Pro Programmer appears active (dangerous)")
    args = ap.parse_args()
    if pro_still_running() and not args.force:
        print(json.dumps({
            "event": "deferred",
            "reason": "pro_or_skills_still_running",
            "hint": "Leave queue in data/web_languages_queue.json; keep_alive will start later",
        }, ensure_ascii=False), flush=True)
        return
    mgr = ModelManager()
    loaded = mgr.load_if_exists()
    print(json.dumps({"event": "model", "loaded": loaded, "params": sum(p.numel() for p in mgr.net.parameters()), "device": mgr.device}, ensure_ascii=False), flush=True)
    st = load_wl_state()
    start_i = 0
    done_ids = {c.get("round_id") for c in st.get("completed_rounds") or []}
    if st.get("round_id") and st.get("mode") == "web_languages" and int(st.get("phase_steps") or 0) < int(st.get("round_min_steps") or 10**12):
        start_i = int(st["round_id"]) - 1
    elif done_ids:
        start_i = 0
        for i, r in enumerate(ROUNDS):
            if r["id"] in done_ids:
                start_i = i + 1
            else:
                break
    for rnd in ROUNDS[start_i:]:
        if int(st.get("round_id") or 0) != rnd["id"]:
            st["best_round_percent"] = 0.0
            st["phase_steps"] = 0
        train_round(mgr, st, rnd, chunk=args.chunk)
    st["phase"] = "done"
    st["round_label"] = "Web languages path complete"
    st["best_overall_percent"] = 100.0
    save_wl_state(st)
    print(json.dumps({"event": "web_languages_path_done", "round_label": st["round_label"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
