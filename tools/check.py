"""Sanity checks for built index.html: JSON blob parses, JS syntax valid via node."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
html = (ROOT / "index.html").read_text(encoding="utf-8")

m = re.search(r'<script id="trip-data" type="application/json">(.*?)</script>', html, re.S)
assert m, "trip-data blob missing"
assert "__DATA__" not in html and "__BUILD_AT__" not in html, "unreplaced placeholder"
blob = m.group(1).replace("<\\/", "</")
data = json.loads(blob)
print("JSON OK. keys:", ", ".join(sorted(data.keys())))

assert len(data["days"]) == 12, "days != 12"
assert len(data["overview"]) == 12, "overview != 12"
assert len(data["hotels"]) == 11, "hotels != 11"
assert len(data["geo"]) >= 30, "geo too few"
assert len(data["route"]) == 12, "route stops != 12"
print("counts OK: days=12 overview=12 hotels=11 geo=%d route=12" % len(data["geo"]))

map_items = sum(1 for d in data["days"] for it in d["items"] if it.get("map"))
hotel_maps = sum(1 for o in data["overview"] if o.get("hotelMap"))
spot_maps = sum(1 for s in data["spots"] if s.get("map"))
assert map_items >= 30, f"day items with map link too few: {map_items}"
assert hotel_maps >= 5, f"overview hotels with map link too few: {hotel_maps}"
print(f"maps OK: day-items={map_items} overview-hotels={hotel_maps} spots={spot_maps}")

meal = data["cost"]["meal"]
assert len(meal["rows"]) == 12, "meal rows != 12"
inc = sum(1 for r in meal["rows"] for k in ("b", "l", "d") if r[k]["inc"])
assert inc == 10, f"meal included cells != 10: {inc}"
assert meal["perPerson"] == 48900, f"per person != 48900: {meal['perPerson']}"
print(f"meal budget OK: rows=12 included=10 per-person=¥{meal['perPerson']:,} 3-pax={meal['hkdLow']}–{meal['hkdHigh']}")

scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
assert scripts, "no inline script"
js = ROOT / "_data" / "_check.js"
js.write_text(scripts[-1], encoding="utf-8")
r = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True)
if r.returncode != 0:
    print("JS SYNTAX ERROR:\n", r.stderr)
    sys.exit(1)
print("JS syntax OK (%d bytes)" % len(scripts[-1]))
