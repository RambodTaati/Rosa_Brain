# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from rosa_brain.config import settings


def _path() -> Path:
    return settings.data_dir / "skills_registry.json"


def _load() -> dict[str, Any]:
    p = _path()
    if not p.exists():
        return {"skills": []}
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return {"skills": []}


def _save(data: dict[str, Any]) -> None:
    _path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_skills() -> list[dict[str, Any]]:
    return list(_load().get("skills") or [])


def get_skill(skill_id: str) -> dict[str, Any] | None:
    for s in list_skills():
        if s.get("id") == skill_id:
            return s
    return None


def upsert_skill(payload: dict[str, Any], skill_id: str | None = None) -> dict[str, Any]:
    data = _load()
    skills = list(data.get("skills") or [])
    now = time.time()
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("name required")
    body = str(payload.get("body") or payload.get("content") or "").strip()
    description = str(payload.get("description") or "").strip()
    enabled = bool(payload.get("enabled", True))
    if skill_id:
        for i, s in enumerate(skills):
            if s.get("id") == skill_id:
                s.update({
                    "name": name,
                    "description": description,
                    "body": body,
                    "enabled": enabled,
                    "updated_at": now,
                })
                skills[i] = s
                data["skills"] = skills
                _save(data)
                return s
        raise KeyError(skill_id)
    item = {
        "id": str(uuid.uuid4()),
        "name": name,
        "description": description,
        "body": body,
        "enabled": enabled,
        "ready": bool(body),
        "created_at": now,
        "updated_at": now,
    }
    skills.append(item)
    data["skills"] = skills
    _save(data)
    return item


def delete_skill(skill_id: str) -> bool:
    data = _load()
    before = len(data.get("skills") or [])
    data["skills"] = [s for s in (data.get("skills") or []) if s.get("id") != skill_id]
    _save(data)
    return len(data["skills"]) < before


def set_enabled(skill_id: str, enabled: bool) -> dict[str, Any]:
    s = get_skill(skill_id)
    if not s:
        raise KeyError(skill_id)
    return upsert_skill({**s, "enabled": enabled}, skill_id=skill_id)


def prepare_skill(skill_id: str) -> dict[str, Any]:
    """Mark skill ready for use after basic validation."""
    s = get_skill(skill_id)
    if not s:
        raise KeyError(skill_id)
    body = str(s.get("body") or "").strip()
    if len(body) < 8:
        raise ValueError("skill body too short to prepare")
    s = upsert_skill({**s, "enabled": True}, skill_id=skill_id)
    data = _load()
    for i, item in enumerate(data.get("skills") or []):
        if item.get("id") == skill_id:
            item["ready"] = True
            item["prepared_at"] = time.time()
            data["skills"][i] = item
            _save(data)
            return item
    return s
