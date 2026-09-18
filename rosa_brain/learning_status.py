# -*- coding: utf-8 -*-
"""Read auto-learn progress for dashboard/API."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from rosa_brain.config import settings

PHASE_TARGETS = {
    "english": {
        "min_steps": int(os.environ.get("ROSA_EN_STEPS", "8000")),
        "target_loss": float(os.environ.get("ROSA_EN_TARGET_LOSS", "0.45")),
        "weight": 0.6,
    },
    "persian": {
        "min_steps": int(os.environ.get("ROSA_FA_STEPS", "5000")),
        "target_loss": float(os.environ.get("ROSA_FA_TARGET_LOSS", "0.50")),
        "weight": 0.4,
    },
}


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _corpus_summary() -> dict[str, Any]:
    root = settings.data_dir / "corpus"
    out: dict[str, Any] = {"english": [], "persian": [], "other": []}
    if not root.exists():
        return out
    for p in sorted(root.rglob("*.txt")):
        rel = str(p.relative_to(root)).replace("\\", "/")
        item = {"file": rel, "bytes": p.stat().st_size}
        if rel.startswith("english/"):
            out["english"].append(item)
        elif rel.startswith("persian/"):
            out["persian"].append(item)
        else:
            out["other"].append(item)
    return out


def _phase_label(phase: str) -> str:
    return {
        "english": "English (conversational meaning)",
        "persian": "Persian (after English)",
        "done": "Curriculum complete",
        "language": "Legacy mixed language",
        "idle": "Idle",
    }.get(phase, phase or "idle")


def _clamp_pct(x: float) -> float:
    return round(max(0.0, min(100.0, float(x))), 1)


def _loss_progress(loss: float | None, target: float, start_ref: float = 3.0) -> float | None:
    if loss is None:
        return None
    if loss <= target:
        return 100.0
    span = max(1e-6, start_ref - target)
    return _clamp_pct(100.0 * (start_ref - loss) / span)


def _phase_progress(phase: str, phase_steps: int, recent_loss: float | None, completed: bool) -> dict[str, Any]:
    cfg = PHASE_TARGETS.get(phase, {"min_steps": 1, "target_loss": 0.5, "weight": 0.0})
    min_steps = int(cfg["min_steps"])
    target_loss = float(cfg["target_loss"])
    steps_pct = 100.0 if completed else _clamp_pct(100.0 * phase_steps / max(1, min_steps))
    loss_pct = 100.0 if completed else _loss_progress(recent_loss, target_loss)
    if completed:
        combined = 100.0
    elif loss_pct is None:
        combined = steps_pct
    else:
        combined = _clamp_pct(0.6 * steps_pct + 0.4 * loss_pct)
    return {
        "phase": phase,
        "min_steps": min_steps,
        "target_loss": target_loss,
        "steps_done": (min_steps if completed else phase_steps),
        "steps_percent": steps_pct,
        "loss_percent": loss_pct,
        "combined_percent": combined,
        "completed": completed,
    }


def get_learning_status() -> dict[str, Any]:
    st = _read_json(settings.data_dir / "auto_learn_state.json") or {}
    wl = _read_json(settings.data_dir / "web_languages_state.json") or {}
    q = _read_json(settings.data_dir / "web_languages_queue.json") or {}
    lang_log = _read_json(settings.data_dir / "train_language_log.json")
    hist = st.get("history") or []
    last = hist[-1] if hist else None
    phase = str(st.get("phase") or st.get("active_phase") or "idle")
    mode = str(st.get("mode") or "")
    phase_steps = int(st.get("phase_steps") or 0)
    recent_loss = None
    if last:
        recent_loss = last.get("recent_avg_loss") or last.get("chunk_loss") or last.get("avg_loss")
    corpus = _corpus_summary()

    skills_complete = bool(st.get("skills_path_complete")) or (
        mode in ("web_languages", "web") and bool(st.get("skills_completed_rounds"))
    ) or (phase == "done" and mode == "skills")
    skills_rounds = st.get("skills_completed_rounds") or (
        st.get("completed_rounds") if mode == "skills" or skills_complete else []
    )
    if isinstance(skills_rounds, list) and len(skills_rounds) >= 10:
        skills_complete = True

    web_progress = {
        "mode": wl.get("mode") or (mode if mode == "web_languages" else None),
        "phase": wl.get("phase") or (phase if mode == "web_languages" else None),
        "round_id": wl.get("round_id") or (st.get("round_id") if mode == "web_languages" else None),
        "round_label": wl.get("round_label") or st.get("round_label"),
        "phase_steps": wl.get("phase_steps") if wl else (st.get("phase_steps") if mode == "web_languages" else 0),
        "best_overall_percent": wl.get("best_overall_percent"),
        "completed_rounds": len(wl.get("completed_rounds") or st.get("web_completed_rounds") or []),
        "queue_ready": bool(q.get("ready")),
    }

    # Curriculum overall must NOT claim "fully intelligent agent"
    # Cap: skills path 70% of "training readiness"; web adds up to +25%; never 100% AGI
    skills_pct = 70.0 if skills_complete else min(70.0, 7.0 * len(skills_rounds or []))
    web_pct = 0.0
    if web_progress.get("phase") == "done":
        web_pct = 25.0
    elif web_progress.get("round_id"):
        try:
            web_pct = min(25.0, 5.0 * float(web_progress.get("round_id") or 0))
        except Exception:
            web_pct = 5.0
    agent_core_pct = 5.0  # local agent loop present
    overall = _clamp_pct(skills_pct + web_pct + agent_core_pct)

    agent_ready = {
        "chat_agent": True,
        "tools": True,
        "skills_registry": (settings.data_dir / "skills_registry.json").exists(),
        "mcp": (settings.data_dir / "mcp_registry.json").exists(),
        "cloud_llm": False,
    }

    return {
        "ok": True,
        "updated_at": time.time(),
        "mode": mode or phase,
        "phase": phase,
        "phase_label": _phase_label(phase),
        "phase_steps": phase_steps,
        "total_steps": st.get("total_steps") or (last or {}).get("total_steps") or (lang_log or {}).get("train_steps_total"),
        "last_chunk_loss": (last or {}).get("chunk_loss") or (last or {}).get("avg_loss"),
        "recent_avg_loss": recent_loss,
        "device": (last or {}).get("device") or st.get("device"),
        "skills_path_complete": skills_complete,
        "skills_completed_rounds": skills_rounds,
        "web_languages": web_progress,
        "web_progress": web_progress,
        "agent_ready": agent_ready,
        "checkpoint": str(settings.model_path),
        "checkpoint_exists": settings.model_path.exists(),
        "corpus": corpus,
        "recent_history": hist[-12:],
        "progress": {
            "overall_percent": overall,
            "skills_path_percent": skills_pct,
            "web_languages_percent": web_pct,
            "agent_core_percent": agent_core_pct,
            "note": "overall_percent is training/readiness toward a stronger LOCAL agent — NOT a claim of full AGI / fully intelligent agent",
        },
        "honest_limitations": [
            "No cloud LLM.",
            "overall_percent is curriculum/readiness, not general intelligence.",
            "Tiny/from-scratch net + tools + skills — stronger in trained domains, not omniscient.",
        ],
        "legacy_language_log": {
            "final_avg_loss": (lang_log or {}).get("final_avg_loss"),
            "train_steps_total": (lang_log or {}).get("train_steps_total"),
        } if lang_log else None,
    }
