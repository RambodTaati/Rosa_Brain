# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from rosa_brain.config import settings


def _path() -> Path:
    return settings.data_dir / "projects.json"


def _load() -> dict[str, Any]:
    p = _path()
    if not p.exists():
        return {"projects": []}
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return {"projects": []}


def _save(data: dict[str, Any]) -> None:
    _path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_projects() -> list[dict[str, Any]]:
    return list(_load().get("projects") or [])


def create_project(name: str, description: str = "") -> dict[str, Any]:
    name = (name or "").strip()
    if not name:
        raise ValueError("name required")
    data = _load()
    item = {
        "id": str(uuid.uuid4()),
        "name": name,
        "description": (description or "").strip(),
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    data.setdefault("projects", []).append(item)
    _save(data)
    return item


def delete_project(project_id: str) -> bool:
    data = _load()
    before = len(data.get("projects") or [])
    data["projects"] = [p for p in (data.get("projects") or []) if p.get("id") != project_id]
    _save(data)
    return len(data["projects"]) < before
