"""Slices 2–4 tests: tools, web learn (local HTML file via http server), experience/train."""

from __future__ import annotations

import os
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["ROSA_BRAIN_ROOT"] = str(ROOT)
sys.path.insert(0, str(ROOT))


def test_tools():
    from rosa_brain.tools import SandboxTools, ToolError

    tools = SandboxTools(ROOT / "workspace")
    tools.write_file("note.txt", "hello sandbox")
    listed = tools.list_dir(".")
    assert any(i["name"] == "note.txt" for i in listed["items"])
    read = tools.read_file("note.txt")
    assert "hello sandbox" in read["content"]
    sh = tools.run_shell("echo rosa-ok")
    assert sh["ok"] and "rosa-ok" in sh["output"]
    try:
        tools.run_shell("rm -rf /")
        raise AssertionError("dangerous shell should fail")
    except ToolError:
        pass
    try:
        tools.read_file("../secrets.txt")
        raise AssertionError("path escape should fail")
    except ToolError:
        pass
    print("PASS tools")


def test_web_and_experience():
    from rosa_brain.brain import Brain

    # local page
    site = ROOT / "workspace" / "site"
    site.mkdir(parents=True, exist_ok=True)
    (site / "page.html").write_text(
        "<html><head><title>RosaDoc</title></head><body><p>Rosa learns from web text about independence.</p></body></html>",
        encoding="utf-8",
    )

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(site), **k)

        def log_message(self, *args):
            return

    httpd = ThreadingHTTPServer(("127.0.0.1", 18766), Handler)
    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    th.start()
    brain = Brain()
    learned = brain.web.learn("http://127.0.0.1:18766/page.html", train=True, train_steps=1)
    assert learned["semantic_id"]
    assert learned["trained"]
    exp = brain.experience.record("web_learn_test", True, "fetched local page", train=False)
    assert exp["lesson"]
    chat = brain.chat("/ls")
    assert chat["intent"] == "tool"
    httpd.shutdown()
    print("PASS web+experience+toolchat", learned["chars"], exp["outcome_id"])


def test_api_new_endpoints():
    import threading
    import time

    import httpx
    import uvicorn
    from rosa_brain.api import app

    host, port = "127.0.0.1", 18767
    server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    with httpx.Client(timeout=30.0) as client:
        for _ in range(50):
            try:
                if client.get(f"http://{host}:{port}/health").status_code == 200:
                    break
            except Exception:
                time.sleep(0.2)
        tools = client.post(
            f"http://{host}:{port}/v1/tools",
            json={"name": "write_file", "args": {"path": "api_note.txt", "content": "via api"}},
        )
        assert tools.status_code == 200
        train = client.post(
            f"http://{host}:{port}/v1/train",
            json={"text": "Rosa Brain trains from scratch on local text.", "steps": 1},
        )
        assert train.status_code == 200
        exp = client.post(
            f"http://{host}:{port}/v1/experience",
            json={"action": "unit_test", "success": True, "detail": "api ok"},
        )
        assert exp.status_code == 200
        # learn web against the same local server from previous test may be down; start tiny one
        print("PASS api tools/train/experience", train.json().get("avg_loss"))
    server.should_exit = True


if __name__ == "__main__":
    test_tools()
    test_web_and_experience()
    test_api_new_endpoints()
    print("SLICES 2-4 ALL PASS")
