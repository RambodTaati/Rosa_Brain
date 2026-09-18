"""Sandboxed tools: limited filesystem under workspace + allowlisted shell."""

from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from rosa_brain.config import settings

# Allowlist: short, non-destructive commands only
_SHELL_ALLOW = re.compile(
    r"^(dir|ls|Get-ChildItem|Get-Content|type|cat|echo|pwd|cd|whoami|hostname|"
    r"python|python3|pip|nvidia-smi|date|Write-Output)\b",
    re.IGNORECASE,
)
_SHELL_DENY = re.compile(
    r"(rm\s|del\s|Remove-Item|format\s|shutdown|reboot|curl\s|wget\s|Invoke-WebRequest|"
    r"Start-Process|msiexec|reg\s|net\suser|scp\s|ssh\s)",
    re.IGNORECASE,
)


class ToolError(RuntimeError):
    pass


class SandboxTools:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or settings.workspace_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, rel: str) -> Path:
        rel = rel.replace("\\", "/").lstrip("/")
        target = (self.root / rel).resolve()
        try:
            target.relative_to(self.root)
        except ValueError as exc:
            raise ToolError(f"path escapes workspace: {rel}") from exc
        return target

    def list_dir(self, rel: str = ".") -> dict[str, Any]:
        path = self._safe_path(rel)
        if not path.exists():
            raise ToolError(f"not found: {rel}")
        if not path.is_dir():
            raise ToolError(f"not a directory: {rel}")
        items = []
        for child in sorted(path.iterdir()):
            items.append(
                {
                    "name": child.name,
                    "is_dir": child.is_dir(),
                    "size": child.stat().st_size if child.is_file() else None,
                }
            )
        return {"path": str(path), "items": items}

    def read_file(self, rel: str, max_chars: int | None = None) -> dict[str, Any]:
        path = self._safe_path(rel)
        if not path.is_file():
            raise ToolError(f"not a file: {rel}")
        limit = max_chars or settings.max_tool_output_chars
        data = path.read_text(encoding="utf-8", errors="replace")
        truncated = len(data) > limit
        return {
            "path": str(path),
            "content": data[:limit],
            "truncated": truncated,
            "chars": len(data),
        }

    def write_file(self, rel: str, content: str) -> dict[str, Any]:
        path = self._safe_path(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"path": str(path), "bytes": path.stat().st_size}

    def run_shell(self, command: str) -> dict[str, Any]:
        cmd = command.strip()
        if not cmd:
            raise ToolError("empty command")
        if _SHELL_DENY.search(cmd):
            raise ToolError("command denied by policy")
        if not _SHELL_ALLOW.match(cmd):
            raise ToolError(
                "command not on allowlist (dir/ls/cat/echo/python/nvidia-smi/...)"
            )
        # Force cwd into workspace; never inherit caller cwd outside sandbox
        t0 = time.time()
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=settings.max_shell_seconds,
                env={**os.environ, "ROSA_BRAIN_SANDBOX": "1"},
            )
            out = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
            out = out[: settings.max_tool_output_chars]
            return {
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "output": out,
                "seconds": round(time.time() - t0, 3),
                "cwd": str(self.root),
            }
        except subprocess.TimeoutExpired as exc:
            raise ToolError(f"timeout after {settings.max_shell_seconds}s") from exc

    def dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        name = name.strip().lower()
        if name in ("list_dir", "ls", "dir"):
            return self.list_dir(str(args.get("path", ".")))
        if name in ("read_file", "read", "cat"):
            return self.read_file(str(args.get("path", "")))
        if name in ("write_file", "write"):
            return self.write_file(str(args.get("path", "")), str(args.get("content", "")))
        if name in ("shell", "run_shell", "exec"):
            return self.run_shell(str(args.get("command", "")))
        raise ToolError(f"unknown tool: {name}")
