"""Think–act–reflect cognitive loop (simple but real)."""

from __future__ import annotations

import json
import re
from typing import Any

from rosa_brain.experience import ExperienceStore
from rosa_brain.learn_web import WebLearner
from rosa_brain.memory import MemoryStore
from rosa_brain.model import ModelManager
from rosa_brain.resources import get_status
from rosa_brain.tools import SandboxTools, ToolError
from rosa_brain.agent_runtime import LocalAgent


class Brain:
    def __init__(self) -> None:
        self.model = ModelManager()
        self.model.load_if_exists()
        self.memory = MemoryStore(embed_fn=self.model.net.embed_text)
        self.tools = SandboxTools()
        self.web = WebLearner(self.memory, self.model)
        self.experience = ExperienceStore(self.memory, self.model)
        self.agent = LocalAgent(
            tools=self.tools,
            memory_search=lambda q, k: self.memory.search_semantic(q, top_k=k),
            model_info=self.model.info,
        )

    def think(self, user_text: str) -> dict[str, Any]:
        resources = get_status().to_dict()
        recall = self.memory.search_semantic(user_text, top_k=3)
        lessons = self.experience.relevant_lessons(user_text, top_k=2)
        recent = self.memory.recent_episodes(limit=6)
        intent = self._classify_intent(user_text)
        plan = self._plan(intent, user_text)
        return {
            "intent": intent,
            "plan": plan,
            "recall": recall,
            "lessons": lessons,
            "recent": recent,
            "resources": {
                "device": resources.get("recommended_device"),
                "can_train": resources.get("can_train"),
                "ram_available_gb": resources.get("ram_available_gb"),
                "gpu_available": resources.get("gpu_available"),
            },
        }

    def act(self, thought: dict[str, Any], user_text: str) -> dict[str, Any]:
        intent = thought["intent"]
        actions: list[dict[str, Any]] = []
        tool_result = None
        gen_text = ""

        if intent == "tool":
            try:
                parsed = self._parse_tool_request(user_text)
                tool_result = self.tools.dispatch(parsed["name"], parsed["args"])
                actions.append({"type": "tool", "ok": True, "name": parsed["name"], "result": tool_result})
            except (ToolError, ValueError) as exc:
                actions.append({"type": "tool", "ok": False, "error": str(exc)})
        elif intent == "learn_web":
            url = self._extract_url(user_text)
            if not url:
                actions.append({"type": "learn_web", "ok": False, "error": "no URL found"})
            else:
                train = "train" in user_text.lower()
                result = self.web.learn(url, train=train)
                actions.append({"type": "learn_web", "ok": True, "result": result})
                tool_result = result
        elif intent == "train":
            result = self.model.train_on_text(user_text, steps=3)
            actions.append({"type": "train", "ok": True, "result": result})
            tool_result = result
        elif intent == "resources":
            actions.append({"type": "resources", "ok": True, "result": get_status().to_dict()})
        else:
            meaning = self._detect_meaning(user_text)
            thought["meaning"] = meaning
            gen_text = self._meaningful_reply(user_text, meaning)
            actions.append({"type": "meaning_reply", "ok": True, "text": gen_text, "meaning": meaning})

        reply = self._compose_reply(intent, user_text, actions, thought, gen_text)
        return {"actions": actions, "reply": reply, "tool_result": tool_result}

    def reflect(self, user_text: str, thought: dict[str, Any], acted: dict[str, Any]) -> dict[str, Any]:
        ok = all(a.get("ok", True) for a in acted.get("actions") or [{"ok": True}])
        detail = acted.get("reply", "")[:300]
        action_names = ",".join(a.get("type", "?") for a in acted.get("actions") or [])
        lesson_rec = self.experience.record(
            action=action_names or thought.get("intent", "chat"),
            success=ok,
            detail=detail,
            train=False,
        )
        self.memory.add_episode("user", user_text)
        self.memory.add_episode(
            "assistant",
            acted.get("reply", ""),
            meta={"intent": thought.get("intent"), "ok": ok},
        )
        return {"ok": ok, "experience": lesson_rec}

    def chat(self, user_text: str) -> dict[str, Any]:
        # Greetings: keep meaning-detection path; questions/requests: LocalAgent
        meaning_pre = None
        try:
            meaning_pre = self._detect_meaning(user_text)
        except Exception:
            meaning_pre = None
        lab = str((meaning_pre or {}).get("label") or "")
        is_greeting = lab in ("intent_greeting", "greeting", "hello", "salam")
        t = (user_text or "").strip().lower()
        if t in ("سلام", "hi", "hello", "hey", "درود", "سلام!"):
            is_greeting = True

        if not is_greeting:
            agent_out = self.agent.handle(user_text)
            # If agent says chat but meaning detector wants greeting reply, fall through
            if agent_out.get("intent") != "chat" or any(
                x in t for x in ("/", "tool", "code", "چطور", "how", "postgres", "sql", "وضعیت")
            ) or agent_out.get("intent") in ("tool", "code_help", "skill_use", "resources", "status", "project", "learn_web"):
                reflection = self.reflect(user_text, {"intent": agent_out.get("intent"), "plan": agent_out.get("plan")}, {"reply": agent_out.get("reply"), "actions": agent_out.get("actions")})
                return {
                    "reply": agent_out.get("reply"),
                    "intent": agent_out.get("intent"),
                    "meaning": meaning_pre,
                    "plan": agent_out.get("plan"),
                    "actions": agent_out.get("actions"),
                    "skills_used": agent_out.get("skills_used"),
                    "readiness_summary": agent_out.get("readiness_summary"),
                    "reflection": reflection,
                    "resources": (agent_out.get("readiness") or {}).get("training") or self.think(user_text).get("resources"),
                    "model": self.model.info(),
                }

        thought = self.think(user_text)
        acted = self.act(thought, user_text)
        reflection = self.reflect(user_text, thought, acted)
        ready = self.agent.readiness_report()
        return {
            "reply": acted["reply"],
            "intent": thought["intent"],
            "meaning": thought.get("meaning"),
            "plan": thought["plan"],
            "actions": acted["actions"],
            "skills_used": [],
            "readiness_summary": f"agent={ready['chat_agent'].get('ready')} skills={ready['skills'].get('prepared_enabled')}",
            "reflection": reflection,
            "resources": thought["resources"],
            "model": self.model.info(),
        }

    def agent_status(self) -> dict[str, Any]:
        return self.agent.readiness_report()




    def _detect_meaning(self, text: str) -> dict:
        from rosa_brain.config import settings
        t = text.strip()
        tl = t.lower()
        if any(x in t for x in ("سلام", "درود", "صبح بخیر")) or any(tl.startswith(x) for x in ("hi", "hello", "hey", "good morning")):
            return {"label": "intent_greeting", "confidence": 0.99, "source": "heuristic"}
        if any(x in t for x in ("خداحافظ", "فعلا")) or any(x in tl for x in ("bye", "goodbye")):
            return {"label": "intent_goodbye", "confidence": 0.99, "source": "heuristic"}
        if any(x in t for x in ("ممنون", "مرسی")) or "thank" in tl:
            return {"label": "intent_thanks", "confidence": 0.99, "source": "heuristic"}
        if "?" in t or "؟" in t:
            return {"label": "intent_question", "confidence": 0.9, "source": "heuristic"}
        try:
            out = self.model.classify(t)
            labels = {}
            lp = settings.data_dir / "label_map.json"
            if lp.exists():
                raw = json.loads(lp.read_text(encoding="utf-8-sig"))
                labels = {int(k): v for k, v in raw.items()}
            lid = int(out["label_id"])
            return {"label": labels.get(lid, f"label_{lid}"), "confidence": float(out.get("confidence") or 0), "source": "class_head", "label_id": lid}
        except Exception:
            return {"label": "intent_statement", "confidence": 0.0, "source": "fallback"}

    def _meaningful_reply(self, user_text: str, meaning: dict) -> str:
        label = str(meaning.get("label") or "")
        conf = float(meaning.get("confidence") or 0)
        is_fa = any("؀" <= ch <= "ۿ" for ch in user_text)
        fa = {
            "intent_greeting": "سلام! من Rosa_Brain هستم. می‌توانی با من حرف بزنی، پروژه بسازی، یا از تب‌های آموزش / Skills / MCP استفاده کنی.",
            "intent_goodbye": "خداحافظ! هر وقت برگشتی آمادهام.",
            "intent_thanks": "خواهش می‌کنم. اگر کار دیگری داشتی بگو.",
            "intent_question": "سؤالت را فهمیدم. لطفاً واضح‌تر بپرس یا /resources را بزن.",
            "intent_request": "درخواستت را گرفتم. برای کار سیستم از /ls یا /read استفاده کن.",
            "intent_statement": "متوجه شدم. بگو چه کمکی می‌خواهی.",
            "sentiment_positive": "خوشحالم که حس خوبی داری.",
            "sentiment_negative": "متأسفم که ناراحتی.",
        }
        en = {
            "intent_greeting": "Hello! I am Rosa_Brain. You can chat, create a project, or use Training / Skills / MCP.",
            "intent_goodbye": "Goodbye! I will be here when you return.",
            "intent_thanks": "You're welcome. Tell me if you need anything else.",
            "intent_question": "I recognized a question. Please ask more specifically, or try /resources.",
            "intent_request": "Got your request. For system tasks try /ls or /read <path>.",
            "intent_statement": "Understood. What should we do next?",
            "sentiment_positive": "Glad you feel good.",
            "sentiment_negative": "Sorry you feel bad.",
        }
        table = fa if is_fa else en
        if label in table and conf >= 0.35:
            return table[label]
        if is_fa:
            return "پیامت را گرفتم. نیت‌سنجی کار می‌کند؛ سلام کن، سؤال بپرس، یا از Skills/MCP استفاده کن."
        return "I received your message. Meaning detection works. Try a greeting, a clear question, or Skills/MCP."


    def _classify_intent(self, text: str) -> str:
        t = text.lower().strip()
        if t.startswith("/resources") or "وضعیت منابع" in text or "resource status" in t:
            return "resources"
        if t.startswith("/train") or t.startswith("train:") or "یاد بگیر از این متن" in text:
            return "train"
        if self._extract_url(text) and (
            "learn" in t or "بیاموز" in text or "یاد بگیر" in text or t.startswith("/learn")
        ):
            return "learn_web"
        if self._extract_url(text) and t.startswith("http"):
            return "learn_web"
        if any(
            t.startswith(p)
            for p in ("/tool", "/ls", "/read", "/write", "/shell", "tool:", "run:")
        ) or re.search(r"\b(list files|read file|write file|run shell)\b", t):
            return "tool"
        return "chat"

    def _plan(self, intent: str, text: str) -> list[str]:
        if intent == "tool":
            return ["parse tool request", "run sandboxed tool", "summarize result"]
        if intent == "learn_web":
            return ["fetch URL", "extract text", "store semantic memory", "optional train"]
        if intent == "train":
            return ["check resources", "online-train tiny net", "save checkpoint"]
        if intent == "resources":
            return ["collect CPU/RAM/GPU metrics", "report"]
        return ["detect meaning", "reply clearly", "store episode"]

    def _parse_tool_request(self, text: str) -> dict[str, Any]:
        t = text.strip()
        # Formats:
        # /ls [path]
        # /read path
        # /write path | content
        # /shell command
        # tool: ls path=.
        if t.startswith("/ls"):
            path = t[3:].strip() or "."
            return {"name": "list_dir", "args": {"path": path}}
        if t.startswith("/read"):
            path = t[5:].strip()
            return {"name": "read_file", "args": {"path": path}}
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
            if name in ("read", "read_file") and "path" not in args:
                args["path"] = rest
            if name in ("shell", "run_shell") and "command" not in args:
                args["command"] = rest
            return {"name": name, "args": args}
        raise ValueError("could not parse tool request; try /ls /read /write /shell")

    def _extract_url(self, text: str) -> str | None:
        m = re.search(r"https?://[^\s<>\"']+", text)
        return m.group(0) if m else None

    def _compose_reply(
        self,
        intent: str,
        user_text: str,
        actions: list[dict[str, Any]],
        thought: dict[str, Any],
        gen_text: str,
    ) -> str:
        if intent == "resources":
            r = (actions[0].get("result") or {}) if actions else {}
            return (
                f"Resources OK={r.get('ok')} device={r.get('recommended_device')} "
                f"RAM free={r.get('ram_available_gb')}GB GPU={r.get('gpu_name')} "
                f"VRAM free~={r.get('gpu_vram_free_ish_gb')} | {r.get('reason')}"
            )
        if intent == "tool":
            a = actions[0] if actions else {}
            if not a.get("ok"):
                return f"Tool error: {a.get('error')}"
            return f"Tool `{a.get('name')}` OK:\n{a.get('result')}"
        if intent == "learn_web":
            a = actions[0] if actions else {}
            if not a.get("ok"):
                return f"Web learn failed: {a.get('error')}"
            res = a.get("result") or {}
            return (
                f"Learned from {res.get('url')} ({res.get('stored_chars')} chars stored). "
                f"title={res.get('title')}. trained={res.get('trained')}"
            )
        if intent == "train":
            a = actions[0] if actions else {}
            res = a.get("result") or {}
            return f"Trained tiny net: avg_loss={res.get('avg_loss')} steps_total={res.get('train_steps_total')}"
        # chat: clear meaning-based reply only
        return (gen_text or "").strip()
