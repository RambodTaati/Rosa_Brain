# -*- coding: utf-8 -*-
from pathlib import Path
import re

p = Path(r"D:\Rosa_Brain\rosa_brain\api.py")
text = p.read_text(encoding="utf-8")

# Ensure HTMLResponse import
if "HTMLResponse" not in text:
    text = text.replace(
        "from fastapi import FastAPI, HTTPException\n",
        "from fastapi import FastAPI, HTTPException\nfrom fastapi.responses import HTMLResponse\n",
        1,
    )

# Remove any existing root handler block between get_brain and /health or previous root
# Replace from @app.get("/") ... until @app.get("/health")
root_fn = '''
@app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    st = get_status()
    status = "ok" if st.ok else "degraded"
    html = f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Rosa_Brain</title>
  <style>
    body {{ font-family: Tahoma, "Segoe UI", sans-serif; margin: 2rem; background:#0b1020; color:#e8eefc; }}
    a {{ color:#8ec5ff; }}
    code, pre {{ background:#151b2f; padding:.2rem .4rem; border-radius:6px; direction:ltr; unicode-bidi:embed; }}
    pre {{ display:block; padding:0.8rem; }}
    .card {{ max-width:720px; background:#121829; border:1px solid #243049; border-radius:14px; padding:1.25rem 1.5rem; }}
    li {{ margin: .35rem 0; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Rosa_Brain</h1>
    <p>نسخه {__version__} — وضعیت: <b>{status}</b> — دستگاه: <b>{st.recommended_device}</b></p>
    <p>این ریشهٔ API است. برای تست سریع:</p>
    <ul>
      <li><a href="/health">/health</a></li>
      <li><a href="/v1/resources">/v1/resources</a></li>
      <li><a href="/docs">/docs</a> (مستندات تعاملی)</li>
    </ul>
    <p>چت با POST به <code>/v1/chat</code> با JSON مثل:</p>
    <pre>{{"message":"سلام"}}</pre>
  </div>
</body>
</html>"""
    return HTMLResponse(content=html, media_type="text/html; charset=utf-8")


'''

pattern = re.compile(r'@app\.get\("/"[\s\S]*?(?=@app\.get\("/health"\))')
if pattern.search(text):
    text = pattern.sub(root_fn, text, count=1)
    print("replaced existing root")
elif '@app.get("/health")' in text:
    text = text.replace('@app.get("/health")', root_fn + '@app.get("/health")', 1)
    print("inserted root")
else:
    raise SystemExit("cannot find health route")

p.write_text(text, encoding="utf-8")
# verify persian exists in source
src = p.read_text(encoding="utf-8")
assert "نسخه" in src and "سلام" in src
print("source ok")

# restart
import subprocess, time, urllib.request, os
os.environ["ROSA_BRAIN_ROOT"] = r"D:\Rosa_Brain"
out = subprocess.check_output("netstat -ano", shell=True, text=True, errors="ignore")
pids = set()
for line in out.splitlines():
    if ":8765" in line and "LISTENING" in line:
        pids.add(line.split()[-1])
for pid in pids:
    subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
    print("killed", pid)
time.sleep(1)
subprocess.Popen(
    [r"D:\Rosa_Brain\.venv\Scripts\python.exe", "-m", "rosa_brain"],
    cwd=r"D:\Rosa_Brain",
    env={**os.environ},
)
time.sleep(3)
req = urllib.request.Request("http://127.0.0.1:8765/")
with urllib.request.urlopen(req, timeout=5) as r:
    raw = r.read()
    ctype = r.headers.get("Content-Type")
    body = raw.decode("utf-8")
print("content-type:", ctype)
print("has_persian:", "نسخه" in body and "سلام" in body and "مستندات" in body)
print("no_qmarks_title:", "????" not in body)
# show a snippet around نسخه
i = body.find("نسخه")
print("snippet:", body[i:i+80] if i>=0 else body[200:280])