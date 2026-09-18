# -*- coding: utf-8 -*-
"""Optional larger TinyBrainNet dims for RTX 5090 ~24GB. Import-safe; env overrides.

Usage (PowerShell before training):
  $env:ROSA_EMBED_DIM="384"
  $env:ROSA_HIDDEN_DIM="1536"
  $env:ROSA_NUM_LAYERS="6"
  $env:ROSA_MAX_SEQ_LEN="512"

Default bump when ROSA_LARGE_MODEL=1: embed=384, hidden=1536, layers=6, seq=512
~ tens of millions of params — fits comfortably in 24GB with room for activations.
Does NOT auto-replace existing checkpoint dims (ModelManager must match checkpoint).
"""
from __future__ import annotations

import os
from rosa_brain import config as cfg


def apply_capacity_env() -> dict:
    large = os.environ.get("ROSA_LARGE_MODEL", "").strip() in ("1", "true", "yes")
    defaults = {
        "embed_dim": 384 if large else cfg.settings.embed_dim,
        "hidden_dim": 1536 if large else cfg.settings.hidden_dim,
        "num_layers": 6 if large else cfg.settings.num_layers,
        "max_seq_len": 512 if large else cfg.settings.max_seq_len,
    }
    ed = int(os.environ.get("ROSA_EMBED_DIM", defaults["embed_dim"]))
    hd = int(os.environ.get("ROSA_HIDDEN_DIM", defaults["hidden_dim"]))
    nl = int(os.environ.get("ROSA_NUM_LAYERS", defaults["num_layers"]))
    ml = int(os.environ.get("ROSA_MAX_SEQ_LEN", defaults["max_seq_len"]))
    # nhead must divide embed_dim
    if ed % 8 == 0:
        pass
    elif ed % 4 != 0:
        ed = max(128, ed - (ed % 4))
    cfg.settings.embed_dim = ed
    cfg.settings.hidden_dim = hd
    cfg.settings.num_layers = nl
    cfg.settings.max_seq_len = ml
    return {"embed_dim": ed, "hidden_dim": hd, "num_layers": nl, "max_seq_len": ml, "large": large}


if os.environ.get("ROSA_LARGE_MODEL") or os.environ.get("ROSA_EMBED_DIM"):
    apply_capacity_env()
