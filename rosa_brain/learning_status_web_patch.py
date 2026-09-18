# -*- coding: utf-8 -*-
"""Helpers to merge web_languages status into learning_status payloads.

apply_web_languages.py patches learning_status.py to call enrich_learning_status().
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def enrich_learning_status(status: dict[str, Any], data_dir: Path) -> dict[str, Any]:
    wl = _read_json(data_dir / "web_languages_state.json") or {}
    q = _read_json(data_dir / "web_languages_queue.json") or {}
    exam = _read_json(data_dir / "web_languages_exam_results.json") or {}
    corpus_dir = data_dir / "corpus" / "skills_web_languages"
    files = []
    total_bytes = 0
    if corpus_dir.exists():
        for p in sorted(corpus_dir.glob("*.txt")):
            b = p.stat().st_size
            total_bytes += b
            files.append({"file": p.name, "bytes": b})
    status["web_languages"] = {
        "queue": q,
        "state": {
            "mode": wl.get("mode"),
            "phase": wl.get("phase"),
            "round_id": wl.get("round_id"),
            "round_label": wl.get("round_label"),
            "phase_steps": wl.get("phase_steps"),
            "quiz_accuracy": wl.get("quiz_accuracy"),
            "best_overall_percent": wl.get("best_overall_percent"),
            "completed_rounds": len(wl.get("completed_rounds") or []),
            "updated_at": wl.get("updated_at"),
        },
        "exam": {
            "heldout_accuracy": exam.get("heldout_accuracy"),
            "grade": exam.get("grade"),
            "n_heldout": exam.get("n_heldout"),
            "timestamp_iso": exam.get("timestamp_iso"),
        },
        "corpus_files": files,
        "corpus_bytes": total_bytes,
        "ready": bool(q.get("ready")),
    }
    # If web mode is active in auto state, surface label
    if status.get("mode") == "web_languages" or wl.get("phase"):
        status.setdefault("roadmap", [])
        # append roadmap item if missing
        if not any(r.get("id") == "skills_web" for r in status.get("roadmap") or []):
            done = str(wl.get("phase") or "") == "done"
            status["roadmap"].append({
                "id": "skills_web",
                "label": "Web languages (HTML..Vue)",
                "done": done,
            })
    status["updated_at"] = time.time()
    return status
