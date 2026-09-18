# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(r"D:\Rosa_Brain")
api = ROOT / "rosa_brain" / "api.py"
fragment = Path(__file__).with_name("root_block.txt")
text = api.read_text(encoding="utf-8")
root_block = fragment.read_text(encoding="utf-8")
if not root_block.endswith("\n"):
    root_block += "\n"

if "from rosa_brain.learning_status import get_learning_status" not in text:
    text = text.replace(
        "from rosa_brain.resources import get_status\n",
        "from rosa_brain.resources import get_status\nfrom rosa_brain.learning_status import get_learning_status\n",
        1,
    )
if "HTMLResponse" not in text:
    text = text.replace(
        "from fastapi import FastAPI, HTTPException\n",
        "from fastapi import FastAPI, HTTPException\nfrom fastapi.responses import HTMLResponse\n",
        1,
    )

pattern = re.compile(r'@app\.get\("/"[\s\S]*?(?=@app\.get\("/health"\))')
if not pattern.search(text):
    raise SystemExit("root block missing")
text = pattern.sub(root_block, text, count=1)
api.write_text(text, encoding="utf-8")
ast.parse(text)
print("api patched")

os.environ["ROSA_BRAIN_ROOT"] = str(ROOT)
out = subprocess.check_output("netstat -ano", shell=True, text=True, errors="ignore")
for line in out.splitlines():
    if ":8765" in line and "LISTENING" in line:
        pid = line.split()[-1]
        subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
        print("killed", pid)
time.sleep(1)
subprocess.Popen([str(ROOT / ".venv/Scripts/python.exe"), "-m", "rosa_brain"], cwd=str(ROOT), env={**os.environ})
time.sleep(3)
j = json.loads(urllib.request.urlopen("http://127.0.0.1:8765/v1/learning").read().decode("utf-8"))
print("overall", j.get("progress", {}).get("overall_percent"))
print("en", j.get("progress", {}).get("english", {}).get("combined_percent"))
print("fa", j.get("progress", {}).get("persian", {}).get("combined_percent"))
b = urllib.request.urlopen("http://127.0.0.1:8765/").read().decode("utf-8")
print("ui_ok", "پیشرفت کل" in b and "bar-fill" in b)
