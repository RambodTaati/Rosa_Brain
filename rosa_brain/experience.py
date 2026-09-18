"""Experience / self-improve: log outcomes, distill lessons, optional online train."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from rosa_brain.config import settings


class ExperienceStore:
    def __init__(self, memory, model_manager) -> None:
        self.memory = memory
        self.model = model_manager
        self.skills_path = settings.skills_path
        self._ensure_skills()

    def _ensure_skills(self) -> None:
        if not self.skills_path.exists():
            self.skills_path.write_text(
                json.dumps({"skills": [], "updated_ts": time.time()}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def load_skills(self) -> dict[str, Any]:
        self._ensure_skills()
        return json.loads(self.skills_path.read_text(encoding="utf-8"))

    def save_skills(self, data: dict[str, Any]) -> None:
        data["updated_ts"] = time.time()
        self.skills_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def record(
        self,
        action: str,
        success: bool,
        detail: str,
        lesson: str = "",
        train: bool = False,
    ) -> dict[str, Any]:
        if not lesson.strip():
            lesson = self._distill(action, success, detail)
        oid = self.memory.add_outcome(action, success, detail, lesson)
        skills = self.load_skills()
        skills.setdefault("skills", []).append(
            {
                "id": oid,
                "ts": time.time(),
                "action": action,
                "success": success,
                "lesson": lesson,
            }
        )
        # keep last 200 skills
        skills["skills"] = skills["skills"][-200:]
        self.save_skills(skills)
        train_result = None
        if train and lesson:
            train_result = self.model.train_on_text(
                f"Lesson: {lesson}\nContext: {action}\nDetail: {detail}",
                steps=2,
            )
        return {
            "outcome_id": oid,
            "lesson": lesson,
            "skills_count": len(skills["skills"]),
            "train_result": train_result,
        }

    def _distill(self, action: str, success: bool, detail: str) -> str:
        status = "worked" if success else "failed"
        tip = "repeat this pattern" if success else "avoid this approach; try a simpler step"
        return f"When doing '{action}', it {status}. Note: {detail[:240]}. Tip: {tip}."

    def relevant_lessons(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        hits = self.memory.search_semantic(query, top_k=top_k)
        return [h for h in hits if h.get("source") in ("lesson", "web", "manual")]
