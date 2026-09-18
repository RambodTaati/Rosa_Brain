# -*- coding: utf-8 -*-
from pathlib import Path
import re

p = Path(r"D:\Rosa_Brain\rosa_brain\api.py")
text = p.read_text(encoding="utf-8")

if "learning_status" not in text:
    text = text.replace(
        "from rosa_brain.resources import get_status\n",
        "from rosa_brain.resources import get_status\nfrom rosa_brain.learning_status import get_learning_status\n",
        1,
    )

# Ensure HTMLResponse import
if "HTMLResponse" not in text:
    text = text.replace(
        "from fastapi import FastAPI, HTTPException\n",
        "from fastapi import FastAPI, HTTPException\nfrom fastapi.responses import HTMLResponse\n",
        1,
    )

root_fn = r'''
@app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    learn = get_learning_status()
    st = get_status()
    status = "ok" if st.ok else "degraded"
    phase = learn.get("phase_label") or learn.get("phase")
    focus = learn.get("current_focus_files") or []
    focus_html = "".join(f"<li><code>{f}</code></li>" for f in focus[:12]) or "<li>(هنوز فایسی برای فاز فعلی نیست)</li>"
    hist = learn.get("recent_history") or []
    hist_rows = ""
    for h in reversed(hist[-8:]):
        hist_rows += (
            "<tr>"
            f"<td>{h.get('phase','')}</td>"
            f"<td>{h.get('phase_steps', h.get('train_steps_total',''))}</td>"
            f"<td>{(h.get('recent_avg_loss') or h.get('chunk_loss') or h.get('avg_loss') or '')}</td>"
            f"<td>{h.get('device','')}</td>"
            "</tr>"
        )
    if not hist_rows:
        hist_rows = "<tr><td colspan=4>هنوز تاریخچهٔ زنده نیست — auto-learn را روشن کن</td></tr>"

    en_n = len((learn.get("corpus") or {}).get("english") or [])
    fa_n = len((learn.get("corpus") or {}).get("persian") or [])
    method = learn.get("method") or {}

    html = f"""<!doctype html>
<html lang=\"fa\" dir=\"rtl\">
<head>
  <meta charset=\"utf-8\" />
  <meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <meta http-equiv=\"refresh\" content=\"5\" />
  <title>Rosa_Brain Learning</title>
  <style>
    body {{ font-family: Tahoma, \"Segoe UI\", sans-serif; margin: 1.5rem; background:#0b1020; color:#e8eefc; }}
    a {{ color:#8ec5ff; }}
    code, pre {{ background:#151b2f; padding:.15rem .35rem; border-radius:6px; direction:ltr; unicode-bidi:embed; }}
    .grid {{ display:grid; gap:1rem; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }}
    .card {{ background:#121829; border:1px solid #243049; border-radius:14px; padding:1rem 1.2rem; }}
    h1,h2 {{ margin-top:0; }}
    table {{ width:100%; border-collapse: collapse; direction:ltr; }}
    th, td {{ border-bottom:1px solid #243049; padding:.35rem .4rem; text-align:left; font-size:0.92rem; }}
    .ok {{ color:#7dffa0; }}
    .muted {{ color:#9fb0d0; font-size:0.9rem; }}
  </style>
</head>
<body>
  <div class=\"card\">
    <h1>Rosa_Brain — داشبورد یادگیری</h1>
    <p class=\"muted\">نسخه {__version__} | سیستم: <span class=\"ok\">{status}</span> | دستگاه پیشنهادی: <b>{st.recommended_device}</b> | رفرش خودکار هر ۵ ثانیه</p>
  </div>

  <div class=\"grid\" style=\"margin-top:1rem\">
    <div class=\"card\">
      <h2>الان چه یاد می‌گیرد؟</h2>
      <p><b>فاز:</b> {phase}</p>
      <p><b>قدم‌های این فاز:</b> {learn.get('phase_steps', 0)}</p>
      <p><b>قدم‌های کل:</b> {learn.get('total_steps') or '—'}</p>
      <p><b>Loss اخیر:</b> {learn.get('recent_avg_loss') or learn.get('last_chunk_loss') or '—'}</p>
      <p><b>دستگاه آموزش:</b> {learn.get('device') or st.recommended_device}</p>
      <p><b>چک‌پوینت:</b> <code>{learn.get('checkpoint')}</code> ({'هست' if learn.get('checkpoint_exists') else 'نیست'})</p>
      <h3>فایل‌های فاز فعلی</h3>
      <ul>{focus_html}</ul>
      <p class=\"muted\">کورپوس: انگلیسی {en_n} فایل | فارسی {fa_n} فایل</p>
    </div>

    <div class=\"card\">
      <h2>چطور یاد می‌گیرد؟</h2>
      <ul>
        <li>موتور: شبکهٔ ازصفر PyTorch (بدون مدل آماده)</li>
        <li>واحد یادگیری: بایت/کاراکتر</li>
        <li>هدف: پیش‌بینی بایت بعدی (cross-entropy)</li>
        <li>حلقه: خواندن کورپوس ← آموزش تکه‌ای ← ذخیره وزن ← به‌روز کردن وضعیت</li>
        <li>ترتیب: <b>انگلیسی</b> بعد <b>فارسی</b></li>
        <li>GPU/RAM قبل از آموزش چک می‌شود</li>
      </ul>
      <p class=\"muted\">method: {method.get('engine')} | objective: {method.get('objective')}</p>
      <p>
        <a href=\"/v1/learning\">JSON وضعیت یادگیری</a> ·
        <a href=\"/health\">/health</a> ·
        <a href=\"/docs\">/docs</a> ·
        <a href=\"/v1/resources\">/v1/resources</a>
      </p>
    </div>
  </div>

  <div class=\"card\" style=\"margin-top:1rem\">
    <h2>پیشرفت تازه</h2>
    <table>
      <thead><tr><th>phase</th><th>steps</th><th>loss</th><th>device</th></tr></thead>
      <tbody>{hist_rows}</tbody>
    </table>
  </div>
</body>
</html>"""
    return HTMLResponse(content=html, media_type="text/html; charset=utf-8")


@app.get("/v1/learning")
def learning() -> dict:
    return get_learning_status()


'''

# Replace existing root function through next route decorator before health OR insert
pattern = re.compile(r'@app\.get\("/"[\s\S]*?(?=@app\.get\("/health"\))')
if pattern.search(text):
    text = pattern.sub(root_fn, text, count=1)
else:
    text = text.replace('@app.get("/health")', root_fn + '@app.get("/health")', 1)

# Remove duplicate /v1/learning if any extra
# (root_fn includes it once)

# If /v1/learning appears twice, keep first
parts = text.split('@app.get("/v1/learning")')
if len(parts) > 2:
    # keep first occurrence only — crude but ok
    text = parts[0] + '@app.get("/v1/learning")' + parts[1]
    # drop remaining by cutting at next def after second? simpler rebuild skip
    pass

p.write_text(text, encoding="utf-8")
print("api patched")

# syntax check
import ast
ast.parse(p.read_text(encoding="utf-8"))
print("syntax ok")