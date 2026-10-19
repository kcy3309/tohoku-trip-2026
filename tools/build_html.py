"""Inject data.json into template.html -> index.html."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "_data" / "data.json"
TPL = ROOT / "template.html"
OUT = ROOT / "index.html"

payload = json.loads(DATA.read_text(encoding="utf-8"))
# Escape for safe embedding inside <script type="application/json">
blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
html = TPL.read_text(encoding="utf-8")
assert "__DATA__" in html, "placeholder missing"
assert "__BUILD_AT__" in html, "build stamp placeholder missing"
build_at = datetime.now(timezone(timedelta(hours=8))).strftime("%Y/%m/%d %H:%M")
html = html.replace("__BUILD_AT__", build_at)
OUT.write_text(html.replace("__DATA__", blob), encoding="utf-8")
print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes) · buildAt={build_at} (UTC+8)")
