"""Slice 1 tests: import, resources, memory, model forward, HTTP health/chat."""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["ROSA_BRAIN_ROOT"] = str(ROOT)
sys.path.insert(0, str(ROOT))


def test_import():
    import rosa_brain
    from rosa_brain import api, brain, config, memory, model, resources

    assert rosa_brain.__version__
    print("PASS import", rosa_brain.__version__)


def test_resources():
    from rosa_brain.resources import get_status

    st = get_status()
    d = st.to_dict()
    assert "cpu_percent" in d
    assert "ram_available_gb" in d
    assert "recommended_device" in d
    print("PASS resources", d["recommended_device"], "cuda_built=", d["torch_cuda_built"], "gpu=", d["gpu_available"])


def test_memory():
    from rosa_brain.memory import MemoryStore

    db = ROOT / "data" / "test_slice1.db"
    if db.exists():
        db.unlink()
    store = MemoryStore(db_path=db)
    eid = store.add_episode("user", "hello episode")
    rows = store.recent_episodes(5)
    assert any(r["id"] == eid for r in rows)
    sid = store.add_semantic("rosa is independent", source="test")
    hits = store.search_semantic("independent", top_k=3)
    assert hits and hits[0]["id"] == sid
    print("PASS memory", eid, sid)


def test_model_forward():
    from rosa_brain.model import ModelManager

    mm = ModelManager()
    probe = mm.forward_probe("rosa test")
    assert probe["logits_shape"][0] == 1
    assert probe["embedding_dim"] > 0
    print("PASS model_forward", probe)


def test_http():
    import httpx
    import uvicorn
    from rosa_brain.api import app

    host, port = "127.0.0.1", 18765
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)

    def run():
        server.run()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    deadline = time.time() + 30
    with httpx.Client(timeout=5.0) as client:
        while time.time() < deadline:
            try:
                h = client.get(f"http://{host}:{port}/health")
                if h.status_code == 200:
                    break
            except Exception:
                time.sleep(0.2)
        else:
            raise RuntimeError("server did not start")
        h = client.get(f"http://{host}:{port}/health")
        assert h.status_code == 200
        health = h.json()
        assert health["status"] in ("ok", "degraded")
        r = client.post(
            f"http://{host}:{port}/v1/chat",
            json={"message": "سلام رزا — hello"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "reply" in body and body["reply"]
        print("PASS http", health, "reply_len=", len(body["reply"]))
    server.should_exit = True


if __name__ == "__main__":
    test_import()
    test_resources()
    test_memory()
    test_model_forward()
    test_http()
    print("SLICE1 ALL PASS")
