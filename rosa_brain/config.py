"""Runtime configuration for Rosa_Brain."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _default_root() -> Path:
    env = os.environ.get("ROSA_BRAIN_ROOT")
    if env:
        return Path(env)
    # Prefer Windows install path when present; else package parent.
    win = Path(r"D:\Rosa_Brain")
    if win.exists():
        return win
    return Path(__file__).resolve().parent.parent


@dataclass
class Settings:
    root: Path = field(default_factory=_default_root)
    host: str = field(default_factory=lambda: os.environ.get("ROSA_BRAIN_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.environ.get("ROSA_BRAIN_PORT", "8765")))
    # Tiny net dims — keep VRAM light by default
    vocab_size: int = 256  # byte-level
    embed_dim: int = 512
    hidden_dim: int = 1024
    num_layers: int = 6
    max_seq_len: int = 768
    # Resource gates
    min_free_ram_gb: float = 1.5
    min_free_vram_gb: float = 0.5
    # Tools sandbox
    max_shell_seconds: int = 15
    max_tool_output_chars: int = 8000
    max_web_bytes: int = 1_500_000

    @property
    def data_dir(self) -> Path:
        p = self.root / "data"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def workspace_dir(self) -> Path:
        p = self.root / "workspace"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def checkpoint_dir(self) -> Path:
        p = self.root / "checkpoints"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def db_path(self) -> Path:
        return self.data_dir / "rosa_memory.db"

    @property
    def model_path(self) -> Path:
        return self.checkpoint_dir / "tiny_net.pt"

    @property
    def skills_path(self) -> Path:
        return self.data_dir / "skills.json"


settings = Settings()
