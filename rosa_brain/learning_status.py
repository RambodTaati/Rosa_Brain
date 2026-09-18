# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from rosa_brain.config import settings

DEFAULT_TOTAL_ROUNDS = 6

SKILL_FOCUS = {
    "skills_postgres": "skills_postgres",
    "skills_security": "skills_security_defensive",
    "skills_windows": "skills_windows",
    "skills_ubuntu": "skills_ubuntu",
    "skills_fullstack": "skills_fullstack_agent",
    "skills_pro_programmer": "skills_pro_programmer",
}


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def _corpus_summary() -> dict[str, Any]:
    root = settings.data_dir / "corpus"
    buckets = (
        "english",
        "persian",
        "understand_en",
        "understand_fa",
        "skills_postgres",
        "skills_security_defensive",
        "skills_windows",
        "skills_ubuntu",
        "skills_fullstack_agent",
        "skills_pro_programmer",
        "skills_quiz",
        "other",
    )
    out: dict[str, Any] = {k: [] for k in buckets}
    if not root.exists():
        return out
    for p in sorted(root.rglob("*.txt")):
        rel = str(p.relative_to(root)).replace("\\", "/")
        item = {"file": rel, "bytes": p.stat().st_size}
        key = "other"
        for k in buckets:
            if k == "other":
                continue
            if rel.startswith(k + "/") or rel.startswith(k):
                key = k
                break
        out[key].append(item)
    return out


def _clamp(x: float) -> float:
    return round(max(0.0, min(100.0, float(x))), 1)


def _pct(v: Any) -> float | None:
    if v is None:
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if x <= 1.0:
        x *= 100.0
    return _clamp(x)


def get_learning_status() -> dict[str, Any]:
    st = _read_json(settings.data_dir / "auto_learn_state.json") or {}
    hist = st.get("history") or []
    last = hist[-1] if hist else None
    trend = st.get("trend") or []
    phase = str(st.get("phase") or "idle")
    mode = str(st.get("mode") or "legacy")
    round_id = int(st.get("round_id") or 0)
    round_label = st.get("round_label") or phase
    phase_steps = int(st.get("phase_steps") or 0)
    round_min = int(st.get("round_min_steps") or 1)
    recent_loss = (last or {}).get("recent_avg_loss")
    if recent_loss is None:
        recent_loss = st.get("recent_avg_loss")
    acc = st.get("detect_accuracy")
    if acc is None and last:
        acc = last.get("detect_accuracy")
    quiz = st.get("quiz_accuracy")
    if quiz is None and last:
        quiz = last.get("quiz_accuracy")

    round_pct = float((last or {}).get("combined_percent") or 0)
    if not round_pct and round_min:
        round_pct = _clamp(100.0 * phase_steps / max(1, round_min))
    round_pct = max(round_pct, float(st.get("best_round_percent") or 0))

    completed_list = st.get("completed_rounds") or []
    if isinstance(completed_list, list) and completed_list and isinstance(completed_list[0], dict):
        completed = len(completed_list)
        rounds_detail = completed_list
    else:
        completed = int(completed_list) if not isinstance(completed_list, list) else len(completed_list)
        rounds_detail = []

    total_rounds = int(st.get("total_rounds") or DEFAULT_TOTAL_ROUNDS)

    if phase == "done":
        overall = 100.0
        round_pct = 100.0
    else:
        overall = _clamp(100.0 * (completed + round_pct / 100.0) / max(1, total_rounds))
        overall = max(overall, float(st.get("best_overall_percent") or 0))

    spark = ""
    if trend:
        blocks = "▁▂▃▄▅▆▇█"
        vals = [float(x.get("pct") or 0) for x in trend[-24:]]
        spark = "".join(blocks[min(7, max(0, int(v / 12.5)))] for v in vals)

    corpus = _corpus_summary()
    focus: list[str] = []
    if "understand_en" in phase or phase.startswith("understand_en"):
        focus = [x["file"] for x in corpus.get("understand_en", [])]
    elif "understand_fa" in phase or phase.startswith("understand_fa"):
        focus = [x["file"] for x in corpus.get("understand_fa", [])]
    elif phase == "english":
        focus = [x["file"] for x in corpus.get("english", [])]
    elif phase == "persian":
        focus = [x["file"] for x in corpus.get("persian", [])]
    else:
        for prefix, bucket in SKILL_FOCUS.items():
            if phase.startswith(prefix) or phase == bucket:
                focus = [x["file"] for x in corpus.get(bucket, [])]
                break
        if not focus and mode == "skills":
            focus = [x["file"] for x in corpus.get("skills_quiz", [])]

    # Freshness: last history event age
    last_ts = None
    if last and last.get("ts") is not None:
        try:
            last_ts = float(last["ts"])
        except (TypeError, ValueError):
            last_ts = None
    age_s = (time.time() - last_ts) if last_ts else None
    learner_likely_running = bool(age_s is not None and age_s < 90 and phase != "done")

    corpus_counts = {k: len(v) for k, v in corpus.items() if isinstance(v, list)}
    corpus_bytes = {
        k: sum(int(x.get("bytes") or 0) for x in v)
        for k, v in corpus.items()
        if isinstance(v, list)
    }

    roadmap = [
        {"id": "lang_mastery", "label": "زبان (EN/FA mastery)", "done": True},
        {"id": "understand", "label": "درک معنی (understand + detect)", "done": True},
        {"id": "skills_pg", "label": "PostgreSQL", "done": any(
            (r.get("label") or "").startswith("PostgreSQL") for r in rounds_detail
        )},
        {"id": "skills_sec", "label": "امنیت دفاعی", "done": any(
            "security" in (r.get("label") or "").lower() or "Defensive" in (r.get("label") or "")
            for r in rounds_detail
        )},
        {"id": "skills_os", "label": "Windows + Ubuntu", "done": any(
            "Windows" in (r.get("label") or "") or "Ubuntu" in (r.get("label") or "")
            for r in rounds_detail
        )},
        {"id": "skills_fs", "label": "Full-stack agent", "done": any(
            "Full-stack" in (r.get("label") or "") or "fullstack" in (r.get("label") or "").lower()
            for r in rounds_detail
        )},
        {"id": "skills_pro", "label": "Pro programmer", "done": any(
            "Pro programmer" in (r.get("label") or "") for r in rounds_detail
        )},
    ]

    return {
        "ok": True,
        "updated_at": time.time(),
        "mode": mode,
        "phase": phase,
        "phase_label": round_label,
        "round_id": round_id,
        "round_label": round_label,
        "skill": st.get("skill"),
        "total_rounds": total_rounds,
        "completed_rounds": completed,
        "completed_rounds_detail": rounds_detail,
        "roadmap": roadmap,
        "phase_steps": phase_steps,
        "round_min_steps": round_min,
        "round_target_loss": st.get("round_target_loss"),
        "acc_target": st.get("acc_target"),
        "detect_accuracy": acc,
        "heldout_accuracy": st.get("heldout_accuracy") or (last or {}).get("heldout_accuracy"),
        "train_detect_accuracy": st.get("train_detect_accuracy") or (last or {}).get("train_detect_accuracy"),
        "quiz_accuracy": quiz,
        "total_steps": st.get("total_steps") or (last or {}).get("total_steps"),
        "recent_avg_loss": recent_loss,
        "device": (last or {}).get("device") or st.get("device"),
        "checkpoint": str(settings.model_path),
        "checkpoint_exists": settings.model_path.exists(),
        "current_focus_files": focus,
        "corpus": corpus,
        "corpus_counts": corpus_counts,
        "corpus_bytes": corpus_bytes,
        "recent_history": hist[-20:],
        "trend": trend[-48:],
        "trend_sparkline": spark,
        "security_policy": st.get("security_policy") or "defensive_only_no_exploits",
        "learner_likely_running": learner_likely_running,
        "last_event_age_seconds": age_s,
        "method": {
            "engine": "from-scratch TinyBrainNet + class_head",
            "no_pretrained": True,
            "skills": ["language model", "intent/sentiment/NLI-style detection", "skills curriculum"],
            "order": [
                "EN/FA mastery",
                "EN/FA understand",
                "detect polish",
                "PostgreSQL",
                "defensive security",
                "Windows/Ubuntu",
                "full-stack agent",
                "pro programmer",
            ],
        },
        "progress": {
            "overall_percent": overall,
            "round_percent": round_pct,
            "overall_display": _pct(overall / 100.0) if overall <= 1 else overall,
            "round_display": round_pct,
            "english": {
                "combined_percent": 100.0 if mode in ("skills", "understand_polish") or phase == "done" else (
                    round_pct if "en" in phase else (100.0 if completed >= 3 else 0.0)
                ),
                "completed": True,
            },
            "persian": {
                "combined_percent": 100.0 if mode in ("skills", "understand_polish") or phase == "done" else (
                    round_pct if "fa" in phase else (100.0 if phase == "done" else 0.0)
                ),
                "completed": True,
            },
        },
        "metrics": {
            "loss": recent_loss,
            "loss_target": st.get("round_target_loss"),
            "detect_pct": _pct(acc),
            "heldout_pct": _pct(st.get("heldout_accuracy") or (last or {}).get("heldout_accuracy")),
            "quiz_pct": _pct(quiz),
            "acc_target_pct": _pct(st.get("acc_target")),
        },
    }


# --- web_languages enrichment (applied by apply_web_languages.py) ---
try:
    from rosa_brain.learning_status_web_patch import enrich_learning_status as _wl_enrich
    _wl_orig_get_learning_status = get_learning_status

    def get_learning_status():
        st = _wl_orig_get_learning_status()
        try:
            return _wl_enrich(st, settings.data_dir)
        except Exception:
            return st
except Exception:
    pass
