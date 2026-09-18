# -*- coding: utf-8 -*-
"""LocalAgent: perceive → plan → tools/skills → structured reply (no cloud LLM)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from rosa_brain.config import settings
try:
    from rosa_brain.resources import get_status
except Exception:  # pragma: no cover
    def get_status():
        class _S:
            def to_dict(self):
                return {"ok": True, "recommended_device": "unknown"}
        return _S()
from rosa_brain.tools import SandboxTools, ToolError

try:
    from rosa_brain import skills_registry
except Exception:  # pragma: no cover
    skills_registry = None  # type: ignore

try:
    from rosa_brain import mcp_registry
except Exception:  # pragma: no cover
    mcp_registry = None  # type: ignore

try:
    from rosa_brain.learning_status import get_learning_status
except Exception:  # pragma: no cover
    get_learning_status = None  # type: ignore


_PERSIAN_RE = re.compile(r"[\u0600-\u06FF]")


def _is_persian(text: str) -> bool:
    return bool(_PERSIAN_RE.search(text or ""))


def _enabled_prepared_skills(limit: int = 8) -> list[dict[str, Any]]:
    if skills_registry is None:
        return []
    out = []
    try:
        for s in skills_registry.list_skills():
            if not s.get("enabled"):
                continue
            ready = s.get("ready") or s.get("prepared") or bool(s.get("body"))
            if not ready:
                continue
            out.append(s)
            if len(out) >= limit:
                break
    except Exception:
        return []
    return out


def _skill_snippets(query: str, limit: int = 4, max_chars: int = 1200) -> list[dict[str, str]]:
    skills = _enabled_prepared_skills(limit=20)
    q = (query or "").lower()
    scored: list[tuple[int, dict]] = []
    for s in skills:
        blob = f"{s.get('name','')} {s.get('description','')} {s.get('body','')}".lower()
        score = sum(1 for tok in re.findall(r"[a-z0-9_]{3,}", q) if tok in blob)
        if score or not q:
            scored.append((score, s))
    scored.sort(key=lambda x: (-x[0], x[1].get("name") or ""))
    snippets = []
    for _, s in scored[:limit]:
        body = str(s.get("body") or "")[:max_chars]
        snippets.append({
            "id": str(s.get("id") or ""),
            "name": str(s.get("name") or ""),
            "description": str(s.get("description") or ""),
            "text": body,
        })
    return snippets


class LocalAgent:
    """Structured local agent loop — tools + skills + memory, no cloud generate spam."""

    INTENTS = ("chat", "tool", "code_help", "learn_web", "resources", "skill_use", "project", "status")

    def __init__(
        self,
        tools: SandboxTools | None = None,
        memory_search: Callable[[str, int], list] | None = None,
        model_info: Callable[[], dict] | None = None,
    ) -> None:
        self.tools = tools or SandboxTools()
        self.memory_search = memory_search
        self.model_info = model_info

    def perceive(self, user_text: str) -> dict[str, Any]:
        recall = []
        if self.memory_search:
            try:
                recall = self.memory_search(user_text, 3) or []
            except Exception:
                recall = []
        skills = _skill_snippets(user_text)
        intent = self.classify_intent(user_text)
        return {
            "text": user_text,
            "intent": intent,
            "persian": _is_persian(user_text),
            "recall": recall,
            "skills": skills,
            "resources": (get_status().to_dict() if hasattr(get_status(), "to_dict") else {}),
        }

    def classify_intent(self, text: str) -> str:
        t = (text or "").lower().strip()
        # strip skill prefix injected by API
        if t.startswith("[skills]") or t.startswith("[project:"):
            # keep original for tool parse; classify on last meaningful line
            lines = [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("- ") and not ln.strip().startswith("[")]
            if lines:
                t = lines[-1].lower().strip()
                text = lines[-1]
        if t.startswith("/resources") or "وضعیت منابع" in text or "resource status" in t:
            return "resources"
        if t.startswith("/status") or t.startswith("/agent") or "وضعیت عامل" in text or "agent status" in t:
            return "status"
        if t.startswith("/project") or "پروژه" in text and ("بساز" in text or "لیست" in text):
            return "project"
        if self._extract_url(text) and (
            "learn" in t or "بیاموز" in text or "یاد بگیر" in text or t.startswith("/learn") or t.startswith("http")
        ):
            return "learn_web"
        if any(t.startswith(p) for p in ("/tool", "/ls", "/read", "/write", "/shell", "/search", "tool:", "run:")):
            return "tool"
        if re.search(r"\b(list files|read file|write file|run shell|search workspace)\b", t):
            return "tool"
        if any(k in t for k in ("code", "function", "bug", "refactor", "postgres", "sql", "python", "typescript", "react")) or any(
            k in text for k in ("کد", "برنامه", "باگ", "تابع", "پایگاه")
        ):
            return "code_help"
        if any(k in t for k in ("skill", "how do i", "how to")) or "مهارت" in text or "چطور" in text:
            return "skill_use"
        return "chat"

    def plan(self, intent: str, user_text: str) -> list[str]:
        plans = {
            "tool": ["parse tool request(s)", "run up to 3 sandboxed tools", "summarize results"],
            "code_help": ["load prepared skills", "recall memory", "structure step-by-step answer"],
            "skill_use": ["select relevant skills", "extract snippets", "reply with steps"],
            "learn_web": ["extract URL", "fetch+store", "optional train"],
            "resources": ["collect CPU/RAM/GPU", "report"],
            "status": ["build readiness report", "summarize training/tools/skills"],
            "project": ["resolve project context", "reply with local project guidance"],
            "chat": ["greeting or short local reply", "offer tools/skills"],
        }
        return plans.get(intent, plans["chat"])

    def use_tools(self, user_text: str, max_calls: int = 3) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        requests = self._parse_multi_tools(user_text)[:max_calls]
        if not requests:
            try:
                requests = [self._parse_tool_request(user_text)]
            except ValueError as exc:
                return [{"type": "tool", "ok": False, "error": str(exc)}]
        for parsed in requests[:max_calls]:
            try:
                result = self.tools.dispatch(parsed["name"], parsed["args"])
                actions.append({"type": "tool", "ok": True, "name": parsed["name"], "args": parsed["args"], "result": result})
            except (ToolError, ValueError) as exc:
                actions.append({"type": "tool", "ok": False, "name": parsed.get("name"), "error": str(exc)})
        return actions

    def reply(self, perception: dict[str, Any], plan: list[str], actions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        intent = perception["intent"]
        user_text = perception["text"]
        fa = perception.get("persian")
        actions = actions or []
        skills_used = [s["name"] for s in (perception.get("skills") or []) if s.get("name")]
        readiness = self.readiness_report()
        readiness_summary = (
            f"agent={readiness.get('chat_agent',{}).get('ready')} "
            f"skills={readiness.get('skills',{}).get('prepared_enabled')} "
            f"tools={readiness.get('tools',{}).get('count')} "
            f"train={readiness.get('training',{}).get('mode')}"
        )

        if intent == "tool":
            if not actions:
                actions = self.use_tools(user_text)
            body = self._format_tool_actions(actions, fa)
        elif intent in ("code_help", "skill_use"):
            body = self._format_skill_reply(user_text, perception, fa)
            actions.append({"type": "skill_context", "ok": True, "skills": skills_used[:6]})
        elif intent == "resources":
            r = perception.get("resources") or get_status().to_dict()
            body = (
                f"Resources OK={r.get('ok')} device={r.get('recommended_device')} "
                f"RAM free={r.get('ram_available_gb')}GB GPU={r.get('gpu_name')}"
            )
            actions.append({"type": "resources", "ok": True, "result": r})
        elif intent == "status":
            body = self._format_status(readiness, fa)
            actions.append({"type": "status", "ok": True, "result": readiness})
        elif intent == "learn_web":
            body = "Web learn requested — use Brain.web path / /learn <url>."
            actions.append({"type": "learn_web", "ok": False, "error": "delegated_to_brain"})
        elif intent == "project":
            body = "پروژه محلی: از /ls و /read در workspace استفاده کنید." if fa else "Local project: use /ls and /read in workspace."
            actions.append({"type": "project", "ok": True})
        else:
            body = self._chat_reply(user_text, fa)

        return {
            "reply": body,
            "intent": intent,
            "plan": plan,
            "actions": actions,
            "skills_used": skills_used[:8],
            "readiness_summary": readiness_summary,
            "readiness": readiness,
        }

    def handle(self, user_text: str) -> dict[str, Any]:
        perception = self.perceive(user_text)
        plan = self.plan(perception["intent"], user_text)
        actions: list[dict[str, Any]] = []
        if perception["intent"] == "tool":
            actions = self.use_tools(user_text, max_calls=3)
        return self.reply(perception, plan, actions)

    def readiness_report(self) -> dict[str, Any]:
        tools_list = ["list_dir", "read_file", "write_file", "shell", "search_workspace"]
        skills = _enabled_prepared_skills(50)
        mcp_n = 0
        if mcp_registry is not None:
            try:
                mcp_n = len([m for m in mcp_registry.list_mcp() if m.get("enabled")])
            except Exception:
                try:
                    mcp_n = len(mcp_registry.list_servers())  # type: ignore
                except Exception:
                    mcp_n = 0
        training: dict[str, Any] = {"mode": "unknown", "skills_path_complete": False, "web_progress": None}
        if get_learning_status is not None:
            try:
                ls = get_learning_status()
                training = {
                    "mode": ls.get("mode") or ls.get("phase"),
                    "skills_path_complete": bool(ls.get("skills_path_complete")),
                    "web_progress": ls.get("web_languages") or ls.get("web_progress"),
                    "overall_percent": (ls.get("progress") or {}).get("overall_percent"),
                    "honest_note": ls.get("honest_limitations") or ls.get("limitations"),
                }
            except Exception as exc:
                training["error"] = str(exc)
        model = {}
        if self.model_info:
            try:
                model = self.model_info() or {}
            except Exception:
                model = {}
        chat_ready = True  # structured agent always available locally
        return {
            "training": training,
            "tools": {"count": len(tools_list), "names": tools_list, "sandbox": True},
            "skills": {
                "prepared_enabled": len(skills),
                "names": [s.get("name") for s in skills[:12]],
            },
            "mcp": {"enabled_servers": mcp_n},
            "chat_agent": {
                "ready": chat_ready,
                "loop": "perceive→plan→tools/skills→reply",
                "cloud_llm": False,
                "intents": list(self.INTENTS),
            },
            "model": model,
            "limitations": [
                "No cloud LLM — replies are structured templates + tools + skill snippets + tiny local net.",
                "Not a fully intelligent AGI; overall% is curriculum progress, not general intelligence.",
                "Shell tools are allowlisted and workspace-sandboxed.",
                "Offensive security content is refused by policy.",
            ],
        }

    # ----- helpers -----
    def _extract_url(self, text: str) -> str | None:
        m = re.search(r"https?://[^\s<>\"']+", text or "")
        return m.group(0) if m else None

    def _parse_multi_tools(self, text: str) -> list[dict[str, Any]]:
        """Allow multiple /ls /read /write /search lines in one turn."""
        out = []
        for line in (text or "").splitlines():
            line = line.strip()
            if not line:
                continue
            if any(line.startswith(p) for p in ("/ls", "/read", "/write", "/shell", "/search", "tool:", "run:")):
                try:
                    out.append(self._parse_tool_request(line))
                except ValueError:
                    continue
        return out

    def _parse_tool_request(self, text: str) -> dict[str, Any]:
        t = text.strip()
        # drop API skill prefix noise: take last command-like line if needed
        if "\n" in t and not t.startswith("/"):
            for line in reversed(t.splitlines()):
                if line.strip().startswith(("/", "tool:", "run:")):
                    t = line.strip()
                    break
        if t.startswith("/ls"):
            return {"name": "list_dir", "args": {"path": t[3:].strip() or "."}}
        if t.startswith("/search"):
            q = t[7:].strip()
            return {"name": "search_workspace", "args": {"query": q}}
        if t.startswith("/read"):
            return {"name": "read_file", "args": {"path": t[5:].strip()}}
        if t.startswith("/write"):
            body = t[6:].strip()
            if "|" in body:
                path, content = body.split("|", 1)
            else:
                parts = body.split(None, 1)
                path = parts[0] if parts else ""
                content = parts[1] if len(parts) > 1 else ""
            return {"name": "write_file", "args": {"path": path.strip(), "content": content.lstrip()}}
        if t.startswith("/shell") or t.startswith("run:"):
            cmd = t.split(":", 1)[-1] if t.startswith("run:") else t[6:]
            return {"name": "shell", "args": {"command": cmd.strip()}}
        m = re.match(r"tool:\s*(\w+)\s*(.*)$", t, re.I)
        if m:
            name = m.group(1)
            rest = m.group(2).strip()
            args: dict[str, Any] = {}
            for part in rest.split():
                if "=" in part:
                    k, v = part.split("=", 1)
                    args[k] = v
            if name in ("ls", "list_dir") and "path" not in args:
                args["path"] = rest or "."
            if name in ("search", "search_workspace") and "query" not in args:
                args["query"] = rest
            if name in ("read", "read_file") and "path" not in args:
                args["path"] = rest
            if name in ("shell", "run_shell") and "command" not in args:
                args["command"] = rest
            return {"name": name, "args": args}
        raise ValueError("could not parse tool request; try /ls /read /write /shell /search")

    def _format_tool_actions(self, actions: list[dict[str, Any]], fa: bool) -> str:
        parts = []
        for a in actions:
            if not a.get("ok"):
                parts.append(f"Tool error ({a.get('name')}): {a.get('error')}")
                continue
            res = a.get("result")
            if isinstance(res, (dict, list)):
                res_s = json.dumps(res, ensure_ascii=False, indent=2)[:4000]
            else:
                res_s = str(res)[:4000]
            parts.append(f"Tool `{a.get('name')}` OK:\n{res_s}")
        if not parts:
            return "ابزار نتیجه‌ای نداشت." if fa else "No tool results."
        return "\n\n".join(parts)

    def _format_skill_reply(self, user_text: str, perception: dict[str, Any], fa: bool) -> str:
        skills = perception.get("skills") or []
        recall = perception.get("recall") or []
        steps = []
        if fa:
            steps.append("پاسخ ساخت‌یافتهٔ محلی (بدون مدل ابری):")
            steps.append(f"۱) درخواست: {user_text[:200]}")
            if skills:
                steps.append("۲) مهارت‌های آماده‌شدهٔ مرتبط:")
                for s in skills[:3]:
                    steps.append(f"   • {s.get('name')}: {(s.get('description') or '')[:120]}")
                    if s.get("text"):
                        steps.append("     " + s["text"][:400].replace("\n", "\n     "))
            else:
                steps.append("۲) مهارت آماده‌ای پیدا نشد — از کورپوس آموزش‌دیده و حافظه استفاده می‌شود.")
            if recall:
                steps.append("۳) حافظهٔ مرتبط:")
                for r in recall[:2]:
                    steps.append("   - " + str(r.get("text") or r)[:160])
            steps.append("۴) گام بعدی: جزئیات بیشتر بپرسید یا از /ls /read /search استفاده کنید.")
        else:
            steps.append("Structured local answer (no cloud LLM):")
            steps.append(f"1) Request: {user_text[:200]}")
            if skills:
                steps.append("2) Relevant prepared skills:")
                for s in skills[:3]:
                    steps.append(f"   • {s.get('name')}: {(s.get('description') or '')[:120]}")
                    if s.get("text"):
                        steps.append("     " + s["text"][:400].replace("\n", "\n     "))
            else:
                steps.append("2) No prepared skill match — using trained corpus/memory context.")
            if recall:
                steps.append("3) Related memory:")
                for r in recall[:2]:
                    steps.append("   - " + str(r.get("text") or r)[:160])
            steps.append("4) Next: ask for detail or use /ls /read /search in workspace.")
        return "\n".join(steps)

    def _format_status(self, readiness: dict[str, Any], fa: bool) -> str:
        if fa:
            return (
                f"آمادگی عامل: chat={readiness['chat_agent'].get('ready')} "
                f"skills={readiness['skills'].get('prepared_enabled')} "
                f"tools={readiness['tools'].get('count')} "
                f"train_mode={readiness['training'].get('mode')} "
                f"skills_done={readiness['training'].get('skills_path_complete')}\n"
                "محدودیت: عامل کاملاً هوشمند عمومی نیست؛ درصد آموزش ≠ هوش کامل."
            )
        return (
            f"Agent readiness: chat={readiness['chat_agent'].get('ready')} "
            f"skills={readiness['skills'].get('prepared_enabled')} "
            f"tools={readiness['tools'].get('count')} "
            f"train_mode={readiness['training'].get('mode')} "
            f"skills_done={readiness['training'].get('skills_path_complete')}\n"
            "Limitation: not a fully general intelligent agent; training % ≠ AGI."
        )

    def _chat_reply(self, user_text: str, fa: bool) -> str:
        t = user_text.strip().lower()
        greetings = ("سلام", "hi", "hello", "hey", "درود", "صبح بخیر", "good morning")
        if any(g in t for g in greetings) or t in greetings:
            if fa or _is_persian(user_text):
                return "سلام! من Rosa_Brain هستم — عامل محلی با ابزار و مهارت‌های آماده‌شده. بپرسید یا /ls بزنید."
            return "Hello! I am Rosa_Brain — a local agent with tools and prepared skills. Ask away or try /ls."
        if fa or _is_persian(user_text):
            return (
                "پیام دریافت شد. برای کمک کدی/مهارتی جزئیات بدهید؛ "
                "برای فایل‌ها از /ls /read /search استفاده کنید. (بدون LLM ابری)"
            )
        return (
            "Got it. For code/skill help, give details; for files use /ls /read /search. "
            "(Local structured agent — no cloud LLM.)"
        )
