"""Web learning: fetch URL, extract text, store knowledge, optional train."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from rosa_brain.config import settings


def _clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


class WebLearner:
    def __init__(self, memory, model_manager, timeout: float = 20.0) -> None:
        self.memory = memory
        self.model = model_manager
        self.timeout = timeout

    def fetch(self, url: str) -> dict[str, Any]:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("only http/https allowed")
        if not parsed.netloc:
            raise ValueError("invalid url")
        headers = {"User-Agent": "RosaBrain/0.1 (+local cognitive agent; no cloud LLM)"}
        with httpx.Client(follow_redirects=True, timeout=self.timeout, headers=headers) as client:
            resp = client.get(url)
            resp.raise_for_status()
            raw = resp.content[: settings.max_web_bytes]
            ctype = resp.headers.get("content-type", "")
            if "html" in ctype or raw.lstrip().startswith((b"<!DOCTYPE", b"<html", b"<HTML")):
                text = _clean_text(raw.decode(resp.encoding or "utf-8", errors="replace"))
            else:
                text = raw.decode("utf-8", errors="replace")
        title = None
        if "html" in ctype.lower() or text[:20].lower().find("<!doctype") >= 0 or text[:10].lower().find("<html") >= 0:
            soup_title = BeautifulSoup(raw, "lxml").title
            if soup_title and soup_title.string:
                title = soup_title.string.strip()
        return {
            "url": str(resp.url),
            "status_code": resp.status_code,
            "chars": len(text),
            "text": text,
            "title": title,
        }

    def learn(self, url: str, train: bool = False, train_steps: int = 2) -> dict[str, Any]:
        page = self.fetch(url)
        # Store compact knowledge chunk (cap for memory)
        snippet = page["text"][:6000]
        title = page.get("title") or page["url"]
        knowledge = f"[web] {title}\n{snippet}"
        sid = self.memory.add_semantic(
            knowledge,
            source="web",
            meta={"url": page["url"], "chars": page["chars"]},
        )
        self.memory.add_episode("system", f"Learned from web: {page['url']}", meta={"semantic_id": sid})
        train_result = None
        if train:
            train_result = self.model.train_on_text(snippet, steps=train_steps)
        return {
            "url": page["url"],
            "title": title,
            "chars": page["chars"],
            "semantic_id": sid,
            "stored_chars": len(snippet),
            "trained": bool(train),
            "train_result": train_result,
            "preview": snippet[:400],
        }
