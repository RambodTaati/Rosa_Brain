# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from rosa_brain.config import settings


def _path() -> Path:
    return settings.data_dir / "mcp_registry.json"


def _load() -> dict[str, Any]:
    p = _path()
    if not p.exists():
        return {"servers": []}
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return {"servers": []}


def _save(data: dict[str, Any]) -> None:
    _path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_servers() -> list[dict[str, Any]]:
    return list(_load().get("servers") or [])


def get_server(server_id: str) -> dict[str, Any] | None:
    for s in list_servers():
        if s.get("id") == server_id:
            return s
    return None


def upsert_server(payload: dict[str, Any], server_id: str | None = None) -> dict[str, Any]:
    data = _load()
    servers = list(data.get("servers") or [])
    now = time.time()
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("name required")
    transport = str(payload.get("transport") or "stdio").strip().lower()
    command = str(payload.get("command") or "").strip()
    args = payload.get("args") or []
    if not isinstance(args, list):
        args = [str(args)]
    url = str(payload.get("url") or "").strip()
    env = payload.get("env") or {}
    if not isinstance(env, dict):
        env = {}
    # Never persist secret values from UI blindly as privileged tokens in frontend;
    # store only non-secret metadata labels if provided.
    enabled = bool(payload.get("enabled", False))
    description = str(payload.get("description") or "").strip()

    if transport == "stdio" and not command:
        raise ValueError("command required for stdio transport")
    if transport in ("sse", "http") and not url:
        raise ValueError("url required for sse/http transport")

    if server_id:
        for i, s in enumerate(servers):
            if s.get("id") == server_id:
                s.update({
                    "name": name,
                    "description": description,
                    "transport": transport,
                    "command": command,
                    "args": [str(a) for a in args],
                    "url": url,
                    "env_keys": sorted(list(env.keys())),
                    "enabled": enabled,
                    "updated_at": now,
                })
                servers[i] = s
                data["servers"] = servers
                _save(data)
                return s
        raise KeyError(server_id)

    item = {
        "id": str(uuid.uuid4()),
        "name": name,
        "description": description,
        "transport": transport,
        "command": command,
        "args": [str(a) for a in args],
        "url": url,
        "env_keys": sorted(list(env.keys())),
        "enabled": enabled,
        "ready": False,
        "created_at": now,
        "updated_at": now,
    }
    servers.append(item)
    data["servers"] = servers
    _save(data)
    return item


def delete_server(server_id: str) -> bool:
    data = _load()
    before = len(data.get("servers") or [])
    data["servers"] = [s for s in (data.get("servers") or []) if s.get("id") != server_id]
    _save(data)
    return len(data["servers"]) < before


def set_enabled(server_id: str, enabled: bool) -> dict[str, Any]:
    s = get_server(server_id)
    if not s:
        raise KeyError(server_id)
    return upsert_server({**s, "enabled": enabled, "env": {}}, server_id=server_id)


def prepare_server(server_id: str) -> dict[str, Any]:
    s = get_server(server_id)
    if not s:
        raise KeyError(server_id)
    transport = s.get("transport")
    if transport == "stdio" and not s.get("command"):
        raise ValueError("missing command")
    if transport in ("sse", "http") and not s.get("url"):
        raise ValueError("missing url")
    data = _load()
    for i, item in enumerate(data.get("servers") or []):
        if item.get("id") == server_id:
            item["ready"] = True
            item["enabled"] = True
            item["prepared_at"] = time.time()
            data["servers"][i] = item
            _save(data)
            return item
    return s
