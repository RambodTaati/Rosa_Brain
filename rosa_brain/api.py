"""FastAPI HTTP surface for Rosa_Brain."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from rosa_brain import __version__
from rosa_brain.brain import Brain
from rosa_brain.config import settings
from rosa_brain.resources import get_status
from rosa_brain.learning_status import get_learning_status
from rosa_brain import skills_registry, mcp_registry, projects as projects_store

app = FastAPI(
    title="Rosa_Brain",
    version=__version__,
    description="From-scratch cognitive agent - no pretrained LLMs / no Ollama / no cloud model APIs",
)

_brain: Brain | None = None
STATIC_DIR = Path(__file__).resolve().parent / "static" / "app"


def get_brain() -> Brain:
    global _brain
    if _brain is None:
        _brain = Brain()
    return _brain


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None
    project_id: str | None = None


class LearnWebIn(BaseModel):
    url: str
    train: bool = False
    train_steps: int = Field(default=2, ge=1, le=20)


class ToolIn(BaseModel):
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class TrainIn(BaseModel):
    text: str = Field(..., min_length=1)
    steps: int = Field(default=3, ge=1, le=50)


class ExperienceIn(BaseModel):
    action: str
    success: bool = True
    detail: str = ""
    lesson: str = ""
    train: bool = False


class ProjectIn(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""


class SkillIn(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""
    body: str = ""
    enabled: bool = True


class McpIn(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""
    transport: str = "stdio"
    command: str = ""
    args: list[str] = Field(default_factory=list)
    url: str = ""
    enabled: bool = False


def _spa_index() -> FileResponse:
    index = STATIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(503, "UI not built yet")
    return FileResponse(index, media_type="text/html; charset=utf-8")


@app.get("/health")
def health() -> dict[str, Any]:
    from dataclasses import asdict
    st = get_status()
    d = asdict(st)
    return {
        "status": "ok" if d.get("ok", True) else "degraded",
        "version": __version__,
        "device": d.get("device"),
        "gpu_available": d.get("gpu_available"),
        "torch_version": d.get("torch_version"),
        "reason": d.get("reason") or d.get("message") or ("resources OK" if d.get("ok", True) else "degraded"),
        **{k: v for k, v in d.items() if k not in {"ok"}},
    }


@app.get("/v1/learning")
def learning() -> dict[str, Any]:
    return get_learning_status()


@app.get("/v1/resources")
def resources() -> dict[str, Any]:
    from dataclasses import asdict
    st = get_status()
    return asdict(st)


@app.post("/v1/chat")
def chat(payload: ChatIn) -> dict[str, Any]:
    brain = get_brain()
    # Attach enabled skills brief context when chatting
    skill_bits = []
    for s in skills_registry.list_skills():
        if s.get("enabled") and s.get("ready"):
            skill_bits.append(f"- {s.get('name')}: {s.get('description') or ''}")
    prefix = ""
    if payload.project_id:
        for p in projects_store.list_projects():
            if p.get("id") == payload.project_id:
                prefix += f"[project:{p.get('name')}] "
                break
    if skill_bits:
        prefix += "[skills]\n" + "\n".join(skill_bits[:8]) + "\n"
    msg = (prefix + payload.message).strip()
    out = brain.chat(msg)
    if isinstance(out, dict):
        out = dict(out)
        out.setdefault("session_id", payload.session_id)
        out.setdefault("project_id", payload.project_id)
        return out
    return {"reply": str(out), "session_id": payload.session_id, "project_id": payload.project_id}


@app.post("/v1/learn/web")
def learn_web(payload: LearnWebIn) -> dict[str, Any]:
    return get_brain().learn_web(payload.url, train=payload.train, train_steps=payload.train_steps)


@app.post("/v1/tools")
def tools(payload: ToolIn) -> dict[str, Any]:
    return get_brain().run_tool(payload.name, payload.args)


@app.post("/v1/train")
def train(payload: TrainIn) -> dict[str, Any]:
    return get_brain().train(payload.text, steps=payload.steps)


@app.post("/v1/experience")
def experience(payload: ExperienceIn) -> dict[str, Any]:
    return get_brain().record_experience(
        action=payload.action,
        success=payload.success,
        detail=payload.detail,
        lesson=payload.lesson,
        train=payload.train,
    )


@app.post("/v1/classify")
def classify_meaning(payload: dict[str, Any]) -> dict[str, Any]:
    import json
    import os
    import time as _time
    from rosa_brain.model import ModelManager

    os.environ.setdefault("ROSA_BRAIN_ROOT", r"D:\Rosa_Brain")
    text = str(payload.get("message") or payload.get("text") or "").strip()
    if not text:
        return {"ok": False, "error": "empty"}
    mgr = ModelManager()
    loaded = mgr.load_if_exists()
    if not loaded:
        _time.sleep(0.15)
        loaded = mgr.load_if_exists(force=True)
    if not loaded:
        return {
            "ok": False,
            "error": "checkpoint_missing",
            "checkpoint": str(settings.model_path),
            "exists": settings.model_path.exists(),
        }
    out = mgr.classify(text)
    labels: dict[Any, Any] = {}
    lp = settings.data_dir / "label_map.json"
    if lp.exists():
        labels = json.loads(lp.read_text(encoding="utf-8-sig"))
    lid = out["label_id"]
    name = labels.get(str(lid), labels.get(lid, f"label_{lid}"))
    return {
        "ok": True,
        "text": text,
        "label_id": lid,
        "label": name,
        "confidence": out["confidence"],
        "loaded": loaded,
        "checkpoint": str(settings.model_path),
        "train_steps": mgr.train_steps,
    }


# ---- Projects ----
@app.get("/v1/projects")
def list_projects() -> dict[str, Any]:
    return {"projects": projects_store.list_projects()}


@app.post("/v1/projects")
def create_project(payload: ProjectIn) -> dict[str, Any]:
    try:
        return projects_store.create_project(payload.name, payload.description)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.delete("/v1/projects/{project_id}")
def delete_project(project_id: str) -> dict[str, Any]:
    ok = projects_store.delete_project(project_id)
    if not ok:
        raise HTTPException(404, "not found")
    return {"ok": True}


# ---- Skills ----
@app.get("/v1/skills")
def list_skills() -> dict[str, Any]:
    return {"skills": skills_registry.list_skills()}


@app.post("/v1/skills")
def create_skill(payload: SkillIn) -> dict[str, Any]:
    try:
        return skills_registry.upsert_skill(payload.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.put("/v1/skills/{skill_id}")
def update_skill(skill_id: str, payload: SkillIn) -> dict[str, Any]:
    try:
        return skills_registry.upsert_skill(payload.model_dump(), skill_id=skill_id)
    except KeyError as e:
        raise HTTPException(404, "not found") from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.delete("/v1/skills/{skill_id}")
def delete_skill(skill_id: str) -> dict[str, Any]:
    if not skills_registry.delete_skill(skill_id):
        raise HTTPException(404, "not found")
    return {"ok": True}


@app.post("/v1/skills/{skill_id}/prepare")
def prepare_skill(skill_id: str) -> dict[str, Any]:
    try:
        return skills_registry.prepare_skill(skill_id)
    except KeyError as e:
        raise HTTPException(404, "not found") from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


# ---- MCP ----
@app.get("/v1/mcp")
def list_mcp() -> dict[str, Any]:
    return {"servers": mcp_registry.list_servers()}


@app.post("/v1/mcp")
def create_mcp(payload: McpIn) -> dict[str, Any]:
    try:
        return mcp_registry.upsert_server(payload.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.put("/v1/mcp/{server_id}")
def update_mcp(server_id: str, payload: McpIn) -> dict[str, Any]:
    try:
        return mcp_registry.upsert_server(payload.model_dump(), server_id=server_id)
    except KeyError as e:
        raise HTTPException(404, "not found") from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.delete("/v1/mcp/{server_id}")
def delete_mcp(server_id: str) -> dict[str, Any]:
    if not mcp_registry.delete_server(server_id):
        raise HTTPException(404, "not found")
    return {"ok": True}


@app.post("/v1/mcp/{server_id}/prepare")
def prepare_mcp(server_id: str) -> dict[str, Any]:
    try:
        return mcp_registry.prepare_server(server_id)
    except KeyError as e:
        raise HTTPException(404, "not found") from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


# ---- SPA ----
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/")
def spa_root() -> FileResponse:
    return _spa_index()


@app.get("/training")
@app.get("/skills")
@app.get("/mcp")
def spa_routes() -> FileResponse:
    return _spa_index()
