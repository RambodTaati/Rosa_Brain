"""Resource manager: CPU/RAM/GPU VRAM awareness and work-gating."""

from __future__ import annotations

import platform
import time
from dataclasses import asdict, dataclass
from typing import Any

import psutil

from rosa_brain.config import settings


@dataclass
class ResourceStatus:
    ok: bool
    reason: str
    timestamp: float
    platform: str
    cpu_percent: float
    cpu_count: int
    ram_total_gb: float
    ram_available_gb: float
    ram_percent: float
    gpu_available: bool
    gpu_name: str | None
    gpu_vram_total_gb: float | None
    gpu_vram_allocated_gb: float | None
    gpu_vram_reserved_gb: float | None
    gpu_vram_free_ish_gb: float | None
    torch_version: str | None
    torch_cuda_built: bool
    recommended_device: str
    can_train: bool
    can_infer: bool
    suggested_batch_size: int
    suggested_seq_len: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _torch_info() -> dict[str, Any]:
    out: dict[str, Any] = {
        "torch_version": None,
        "torch_cuda_built": False,
        "gpu_available": False,
        "gpu_name": None,
        "gpu_vram_total_gb": None,
        "gpu_vram_allocated_gb": None,
        "gpu_vram_reserved_gb": None,
        "gpu_vram_free_ish_gb": None,
    }
    try:
        import torch
    except Exception:
        return out

    out["torch_version"] = getattr(torch, "__version__", None)
    out["torch_cuda_built"] = bool(getattr(torch.version, "cuda", None))
    cuda_ok = bool(torch.cuda.is_available())
    out["gpu_available"] = cuda_ok
    if not cuda_ok:
        return out

    try:
        idx = torch.cuda.current_device()
        props = torch.cuda.get_device_properties(idx)
        total = float(props.total_memory) / (1024**3)
        allocated = float(torch.cuda.memory_allocated(idx)) / (1024**3)
        reserved = float(torch.cuda.memory_reserved(idx)) / (1024**3)
        free_ish = max(0.0, total - reserved)
        out.update(
            {
                "gpu_name": props.name,
                "gpu_vram_total_gb": round(total, 3),
                "gpu_vram_allocated_gb": round(allocated, 3),
                "gpu_vram_reserved_gb": round(reserved, 3),
                "gpu_vram_free_ish_gb": round(free_ish, 3),
            }
        )
    except Exception as exc:  # pragma: no cover
        out["gpu_name"] = f"error:{exc}"
    return out


def get_status() -> ResourceStatus:
    vm = psutil.virtual_memory()
    ram_avail = vm.available / (1024**3)
    ram_total = vm.total / (1024**3)
    ti = _torch_info()

    reasons: list[str] = []
    can_infer = True
    can_train = True

    if ram_avail < settings.min_free_ram_gb:
        can_train = False
        reasons.append(
            f"RAM low: {ram_avail:.2f}GB free < {settings.min_free_ram_gb}GB"
        )
        if ram_avail < 0.75:
            can_infer = False

    if ti["gpu_available"]:
        free_v = ti["gpu_vram_free_ish_gb"] or 0.0
        if free_v < settings.min_free_vram_gb:
            can_train = False
            reasons.append(
                f"VRAM tight: ~{free_v:.2f}GB free-ish < {settings.min_free_vram_gb}GB"
            )
        device = "cuda"
        # Scale batch/seq with free VRAM
        if free_v >= 8:
            batch, seq = 16, min(512, settings.max_seq_len * 2)
        elif free_v >= 4:
            batch, seq = 8, settings.max_seq_len
        elif free_v >= 1:
            batch, seq = 4, min(192, settings.max_seq_len)
        else:
            batch, seq = 1, min(128, settings.max_seq_len)
            can_train = False
            reasons.append("VRAM too low for safe training; infer-only")
    else:
        device = "cpu"
        batch, seq = 2, min(128, settings.max_seq_len)
        if not ti["torch_version"]:
            can_infer = False
            can_train = False
            reasons.append("torch not importable")
        else:
            reasons.append(
                "CUDA not available to torch — using CPU "
                "(install CUDA wheel if GPU expected)"
            )

    ok = can_infer
    reason = "; ".join(reasons) if reasons else "resources OK"

    return ResourceStatus(
        ok=ok,
        reason=reason,
        timestamp=time.time(),
        platform=platform.platform(),
        cpu_percent=float(psutil.cpu_percent(interval=0.05)),
        cpu_count=int(psutil.cpu_count() or 1),
        ram_total_gb=round(ram_total, 3),
        ram_available_gb=round(ram_avail, 3),
        ram_percent=float(vm.percent),
        gpu_available=bool(ti["gpu_available"]),
        gpu_name=ti["gpu_name"],
        gpu_vram_total_gb=ti["gpu_vram_total_gb"],
        gpu_vram_allocated_gb=ti["gpu_vram_allocated_gb"],
        gpu_vram_reserved_gb=ti["gpu_vram_reserved_gb"],
        gpu_vram_free_ish_gb=ti["gpu_vram_free_ish_gb"],
        torch_version=ti["torch_version"],
        torch_cuda_built=bool(ti["torch_cuda_built"]),
        recommended_device=device,
        can_train=can_train and can_infer,
        can_infer=can_infer,
        suggested_batch_size=batch,
        suggested_seq_len=seq,
    )


def require_capacity(kind: str = "infer") -> ResourceStatus:
    """Raise RuntimeError if work should be refused."""
    st = get_status()
    if kind == "train" and not st.can_train:
        raise RuntimeError(f"refusing train: {st.reason}")
    if kind == "infer" and not st.can_infer:
        raise RuntimeError(f"refusing infer: {st.reason}")
    return st


def pick_device() -> str:
    return get_status().recommended_device
