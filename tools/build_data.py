"""Parse downloaded CSVs into a single data.json for the trip page."""
import csv
import io
import json
import re
import sys
import unicodedata
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "_data"


def load_links() -> dict:
    path = DATA_DIR / "links.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_weather() -> dict:
    path = DATA_DIR / "weather.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def sheet_links(links: dict, sheet: str, row_no: int) -> dict[str, str]:
    """Hyperlinks on a 1-based xlsx row: {col_letter: url}."""
    return links.get(sheet, {}).get(str(row_no), {})


def read_rows(name: str) -> list[list[str]]:
    text = (DATA_DIR / f"{name}.csv").read_text(encoding="utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    width = max((len(r) for r in rows), default=0)
    return [r + [""] * (width - len(r)) for r in rows]


def cell(row: list[str], idx: int) -> str:
    return row[idx].strip() if idx < len(row) else ""


def find_header(rows: list[list[str]], first_col: str) -> int:
    for i, row in enumerate(rows):
        if cell(row, 0).startswith(first_col):
            return i
    return -1


def clean(value: str) -> str:
    value = value.replace("​", "").strip()
    return value


def tidy_payment(value: str) -> str:
    """Strip stray quote artifacts left by the CSV export in payment cells."""
    lines = [ln.strip().strip('"').strip() for ln in value.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


MERIDIEM = {"下午": 12, "晚上": 12, "傍晚": 12}


def tidy_time(value: str) -> str:
    """Normalize time cells like '下午 13:30:00' -> '13:30'."""
    v = value.strip()
    if not v:
        return v
    m = re.match(r"^(上午|下午|早上|晚上|凌晨|傍晚)\s*(\d{1,2})(:\d{2})(:\d{2})?$", v)
    if m:
        era, hh, mm = m.group(1), int(m.group(2)), m.group(3)
        if era in MERIDIEM and hh < 12:
            hh += MERIDIEM[era]
        return f"{hh:02d}{mm}"
    m = re.match(r"^(\d{1,2}:\d{2}):\d{2}$", v)
    if m:
        return m.group(1)
    return v


# ---------------- overview ----------------

def parse_overview(links: dict):
    rows = read_rows("overview")
    header_i = find_header(rows, "Day")
    # header: Day,日期,星期,路線,當日開車時間,住宿地點,住宿型態及膳食安排,當日亮點,+膳食col
    days = []
    for i, row in enumerate(rows[header_i + 1 :], start=header_i + 2):
        d = cell(row, 0)
        m = re.match(r"Day\s*(\d+)", d)
        if not m:
            continue
        meal_cell = cell(row, 8) if len(row) > 8 else ""
        meals = [x for x in re.split(r"[\n/／]+", meal_cell) if x.strip()]
        rec = {
            "day": int(m.group(1)),
            "date": cell(row, 1),
            "route": cell(row, 3),
            "drive": cell(row, 4),
            "hotel": cell(row, 5),
            "mealPlan": cell(row, 6),
            "highlights": cell(row, 7),
            "meals": meals,
        }
        hotel_map = sheet_links(links, "行程概覽", i).get("F", "")
        if hotel_map:
            rec["hotelMap"] = hotel_map
        days.append(rec)
    decisions = []
    for row in rows:
        v = cell(row, 0)
        if v.startswith("•"):
            decisions.append(v.lstrip("• ").strip())
    header_line = cell(rows[0], 0)
    sub_line = cell(rows[1], 0)
    return days, decisions, header_line, sub_line


# ---------------- day sheets ----------------

URL_RE = re.compile(r"https?://\S+")


def parse_day(day_no: int, links: dict) -> dict:
    rows = read_rows(f"day{day_no}")
    sheet = f"Day{day_no}"
    title = cell(rows[0], 0)
    summary = cell(rows[1], 0) if len(rows) > 1 else ""
    drive = ""
    warnings: list[str] = []
    header_i = -1
    for i, row in enumerate(rows):
        v = cell(row, 0)
        if v.startswith("🚗"):
            drive = re.sub(r"^🚗\s*開車時間統計：?", "", v).strip()
        elif v.startswith("⚠️"):
            warnings.append(v.lstrip("⚠️ ").strip())
        elif v == "時段":
            header_i = i
            break
    items: list[dict] = []
    bus = {"title": "", "mapUrl": "", "times": []}
    for row_no, row in enumerate(rows[header_i + 1 :], start=header_i + 2):
        c0, c1, c2, c3, c4, c5, c6, c7 = (cell(row, i) for i in range(8))
        if c0.startswith("https://"):
            bus["mapUrl"] = c0
            title_cell = c2 or c3
            if title_cell:
                bus["title"] = title_cell
            continue
        if bus["title"] and re.fullmatch(r"\d{1,2}:\d{2}", c3) and re.fullmatch(r"\d{1,2}:\d{2}", c4):
            bus["times"].append({"depart": c3, "arrive": c4})
            continue
        is_time = lambda s: bool(re.fullmatch(r"\d{1,2}:\d{2}", s))
        if not c0 and not c1 and not c2 and (c3 or c4) and not is_time(c3):
            continue  # bus-timetable header / labels row
        if not any([c0, c1, c2, c3, c4, c5, c6, c7]):
            continue
        item = {
            "time": tidy_time(c0),
            "type": c1,
            "name": c2,
            "detail": c3,
            "parking": c4,
            "ref": c5,
            "note": c6,
            "payment": tidy_payment(c7),
        }
        row_links = sheet_links(links, sheet, row_no)
        for col, key in (("C", "map"), ("D", "detailMap"), ("E", "parkingMap"), ("F", "refMap"), ("G", "noteMap")):
            if row_links.get(col):
                item[key] = row_links[col]
        items.append(item)
    out = {
        "day": day_no,
        "title": title,
        "summary": summary,
        "drive": drive,
        "warnings": warnings,
        "items": items,
    }
    if bus["times"]:
        out["bus"] = bus
    return out


# ---------------- cost ----------------

# 每人單價（JPY），依行程概覽「膳食安排」推估；included=True 表示住宿／機票已含
MEAL_BUDGET = [
    {"day": 1, "date": "10/20", "b": {"t": "機場／機上", "inc": True},
     "l": {"t": "機上餐", "inc": True}, "d": {"t": "利久 牛舌", "j": 2300}},
    {"day": 2, "date": "10/21", "b": {"t": "蘭亭（含早）", "inc": True},
     "l": {"t": "秋保溫泉街", "j": 1300}, "d": {"t": "藏王山形牛會席（含）", "inc": True}},
    {"day": 3, "date": "10/22", "b": {"t": "藏王（含早）", "inc": True},
     "l": {"t": "七日町小店", "j": 1300}, "d": {"t": "角館武家屋敷", "j": 1800}},
    {"day": 4, "date": "10/23", "b": {"t": "便利店", "j": 450},
     "l": {"t": "鶴の湯食堂", "j": 1600}, "d": {"t": "菊富士（已訂）", "j": 4000}},
    {"day": 5, "date": "10/24", "b": {"t": "便利店", "j": 450},
     "l": {"t": "三忠／蕎麥", "j": 1200}, "d": {"t": "味噌咖哩拉麵", "j": 1100}},
    {"day": 6, "date": "10/25", "b": {"t": "魚菜中心海鮮丼", "j": 1200},
     "l": {"t": "ASPAM 周邊", "j": 1500}, "d": {"t": "回轉壽司あすか", "j": 1900}},
    {"day": 7, "date": "10/26", "b": {"t": "便利店", "j": 450},
     "l": {"t": "奧入瀨溪流", "j": 1500}, "d": {"t": "秋田鄉土自助（含）", "inc": True}},
    {"day": 8, "date": "10/27", "b": {"t": "Yuze（含早）", "inc": True},
     "l": {"t": "盛岡冷麵", "j": 1300}, "d": {"t": "民宿煮食", "j": 1500}},
    {"day": 9, "date": "10/28", "b": {"t": "便利店", "j": 450},
     "l": {"t": "三彩館ふじせい", "j": 1300}, "d": {"t": "前澤牛壽喜燒（含）", "inc": True}},
    {"day": 10, "date": "10/29", "b": {"t": "絕景之館（含早）", "inc": True},
     "l": {"t": "松島牡蠣吃到飽", "j": 3500}, "d": {"t": "松島吃蠔", "j": 3500}},
    {"day": 11, "date": "10/30", "b": {"t": "鹽釜魚市場海鮮丼", "j": 1400},
     "l": {"t": "仔虎燒肉（已訂）", "j": 2800}, "d": {"t": "民宿煮食", "j": 1500}},
    {"day": 12, "date": "10/31", "b": {"t": "仙台朝市", "j": 800},
     "l": {"t": "機場輕食", "j": 800}, "d": {"t": "回港機上餐", "inc": True}},
]


def build_meal_budget() -> dict:
    rows = []
    for m in MEAL_BUDGET:
        def cell(e):
            if e.get("inc"):
                return {"t": e["t"], "inc": True, "j": 0}
            return {"t": e["t"], "inc": False, "j": e.get("j", 0)}
        b, l, d = cell(m["b"]), cell(m["l"]), cell(m["d"])
        rows.append({"day": m["day"], "date": m["date"], "b": b, "l": l, "d": d,
                     "sub": b["j"] + l["j"] + d["j"]})
    snacks = 8000
    per_person = sum(r["sub"] for r in rows) + snacks
    return {
        "rows": rows,
        "snacks": snacks,
        "perPerson": per_person,
        "perPersonLow": 45000,
        "perPersonHigh": 55000,
        "totalLow": 140000,
        "totalHigh": 160000,
        "hkdLow": "HK$7,000",
        "hkdHigh": "HK$8,000",
        "rate": "¥1 ≈ HK$0.05",
        "notes": [
            "估算方式：依行程概覽「膳食安排」逐日推估每人日圓花費，取東北一般物價與已訂餐廳價位中位數；「✓ 包餐」為住宿或機票已含。",
            "區間已含 ±10% 浮動（已訂餐廳實際帳單差異、零食咖啡多寡）；含 6 晚住宿包餐、4 天機上餐。",
        ],
    }


def parse_cost() -> dict:
    rows = read_rows("cost")
    hotels, flights, rental = [], [], []
    tolls, toll_notes = [], []
    in_toll = False
    totals = {}
    for row in rows:
        c0 = cell(row, 0)
        if c0 == "過路費總表":
            in_toll = True
            toll_notes.append(cell(row, 1))
            continue
        if in_toll:
            v = cell(row, 0)
            if v.startswith("預估整趟"):
                toll_notes.append(v)
                continue
            if v in ("Day", "收費段落") or not v:
                continue
            if re.match(r"Day\s*\d", v):
                tolls.append({"day": v, "segment": cell(row, 1), "amount": cell(row, 2)})
            continue
        if re.match(r"Day\s*\d", c0):
            name, jpy, hkd = cell(row, 1), cell(row, 2), cell(row, 3)
            meal, flight_hkd = cell(row, 4), cell(row, 5)
            r_name, r_jpy, r_hkd = cell(row, 7), cell(row, 8), cell(row, 9)
            if name or jpy or hkd:
                hotels.append({"day": c0, "name": name, "jpy": jpy, "hkd": hkd, "meal": meal})
            if flight_hkd:
                flights.append({"day": c0, "note": meal, "hkd": flight_hkd})
            if r_name or r_jpy or r_hkd:
                rental.append({"item": r_name, "jpy": r_jpy, "hkd": r_hkd})
        elif c0 == "Total":
            totals = {"hotelHKD": cell(row, 3), "flightHKD": cell(row, 5), "rentalHKD": cell(row, 9)}

    def hkd_num(s: str) -> float:
        m = re.sub(r"[^\d.]", "", s or "")
        return float(m) if m else 0.0

    sheet_total = totals.get("rentalHKD", "")
    detail_total = sum(hkd_num(r["hkd"]) for r in rental)
    # The sheet's rental Total uses =SUM(J2:J7), which misses ETC tolls and the
    # newly added travel insurance; trust the line-item sum when they disagree.
    rental_total = sheet_total
    rental_total_note = ""
    if detail_total and abs(detail_total - hkd_num(sheet_total)) >= 1:
        rental_total = f"${detail_total:,.0f}"
        rental_total_note = (
            f"租車合計以明細加總為準：試算表 Total 公式（SUM J2:J7）未涵蓋 ETC 過路費與旅遊保險，"
            f"故試算表顯示 {sheet_total}、明細加總為 {rental_total}。"
        )
    totals["rentalHKDDetail"] = rental_total
    totals["rentalNote"] = rental_total_note
    return {
        "hotels": hotels,
        "flights": flights,
        "rental": rental,
        "totals": totals,
        "tolls": tolls,
        "tollNotes": toll_notes,
        "meal": build_meal_budget(),
    }


# ---------------- spots / hotels / alerts / snow ----------------

KEY_MAP = {
    "縣份": "county",
    "所在Day": "day",
    "名稱": "name",
    "類型": "type",
    "類別": "category",
    "詳細說明": "detail",
    "參考網址/電話": "ref",
    "備註/預約需求": "note",
    "備註": "note",
    "Day/日期": "day",
    "地點": "place",
    "住宿型態": "hotel",
    "訂房狀態": "status",
    "訂房緊急度": "urgency",
    "JPY": "jpy",
    "HKD": "hkd",
    "地點": "place",
    "官方最新資訊": "info",
    "建議行動": "action",
    "日期": "date",
    "行程": "route",
    "雪風險": "snowRisk",
    "結冰風險": "iceRisk",
    "自駕注意程度": "caution",
    "雪胎價值": "tireValue",
}


def parse_table(name: str, first_col: str) -> tuple[list[dict], list[str]]:
    rows = read_rows(name)
    header_i = find_header(rows, first_col)
    headers = [cell(rows[header_i], i) for i in range(len(rows[header_i]))]
    keys = []
    for i, h in enumerate(headers):
        base = re.sub(r"[（(].*?[）)]", "", h).strip()
        keys.append(KEY_MAP.get(base, KEY_MAP.get(h.strip(), base or f"col{i}")))
    out = []
    for row in rows[header_i + 1 :]:
        if not cell(row, 0):
            continue
        rec = {keys[i]: clean(cell(row, i)) for i in range(len(keys)) if cell(row, i)}
        out.append(rec)
    return out, keys


# ---------------- sos ----------------

def parse_sos() -> dict:
    rows = read_rows("sos")
    flat = []
    for row in rows:
        line = next((clean(c) for c in row if c.strip()), "")
        if line:
            flat.append(line)
    hotlines_raw = flat[0] if flat else ""
    hotlines = []
    for line in hotlines_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if "：" in line:
            name, rest = line.split("：", 1)
            pm = re.search(r"\+?[\d][\d\-() ]{6,}", rest)
            phone = pm.group(0).strip() if pm else ""
            note = rest.replace(phone, "").strip() if phone else rest.strip()
            hotlines.append({"name": name.strip(), "phone": phone, "note": note})
        else:
            hotlines.append({"name": line, "phone": "", "note": ""})
    steps, phrases = [], []
    mode = None
    buffer = None
    for line in flat[1:]:
        if line.startswith("一、"):
            mode = "steps"
            continue
        if line.startswith("實用救命日文"):
            mode = "phrases"
            continue
        if mode == "steps":
            steps.append(line)
        elif mode == "phrases":
            if line.startswith("日文："):
                if buffer:
                    buffer["ja"] = line[3:].strip()
            elif line.startswith("英文："):
                if buffer:
                    buffer["en"] = line[3:].strip()
                    phrases.append(buffer)
                    buffer = None
            elif line.startswith("提示："):
                if buffer:
                    buffer["tip"] = line[3:].strip()
            else:
                if buffer:
                    phrases.append(buffer)
                buffer = {"zh": line}
    if buffer:
        phrases.append(buffer)
    title = "緊急聯絡與事故處理"
    return {"title": title, "hotlines": hotlines, "steps": steps, "phrases": phrases}


# ---------------- charging ----------------

def parse_charging() -> list[dict]:
    rows = read_rows("charging")
    sections = []
    current = None
    for row in rows:
        c0, c1, c2, c3 = (cell(row, i) for i in range(4))
        if c0 and not c1 and re.match(r"\d+\.", c0):
            current = {"title": c0, "items": []}
            sections.append(current)
            continue
        if c0 == "項目" and current is not None:
            continue
        if c0 and current is not None:
            current["items"].append({"name": c0, "qty": c1, "spec": c2, "use": c3})
    return sections


def normalize_name(s: str) -> str:
    """First line + drop trailing bracket annotations, for loose name matching."""
    s = unicodedata.normalize("NFKC", s).split("\n")[0].strip()
    s = re.sub(r"[（(].*?[）)]", "", s).strip()
    return s


def build_name_to_map(links: dict) -> dict[str, str]:
    """Collect {normalized_name: maps_url} from all day sheets + overview."""
    index: dict[str, str] = {}

    def add(text: str, url: str) -> None:
        if not text or text.startswith("http"):
            return
        key = normalize_name(text)
        if key and key not in index:
            index[key] = url

    for day_no in range(1, 13):
        rows = read_rows(f"day{day_no}")
        for row_no, cols in links.get(f"Day{day_no}", {}).items():
            url = next(iter(cols.values()))
            ri = int(row_no) - 1
            if 0 <= ri < len(rows):
                row = rows[ri]
                for ci in (2, 3, 4, 5, 6):
                    if ci < len(row):
                        add(row[ci], url)
    ov_rows = read_rows("overview")
    for row_no, cols in links.get("行程概覽", {}).items():
        url = cols.get("F", "")
        ri = int(row_no) - 1
        if url and 0 <= ri < len(ov_rows) and ri < len(ov_rows[ri]):
            add(ov_rows[ri][5], url)
    return index


def main() -> None:
    links = load_links()
    overview_days, decisions, overview_title, overview_sub = parse_overview(links)
    days = [parse_day(n, links) for n in range(1, 13)]
    cost = parse_cost()
    spots, spot_keys = parse_table("spots", "縣份")
    name_to_map = build_name_to_map(links)
    spot_map_hits = 0
    for s in spots:
        url = name_to_map.get(normalize_name(s.get("name", "")))
        if url:
            s["map"] = url
            spot_map_hits += 1
    hotels, hotel_keys = parse_table("hotels", "Day")
    alerts, alert_keys = parse_table("alerts", "類別")
    snow, snow_keys = parse_table("snow", "日期")
    sos = parse_sos()
    charging = parse_charging()
    weather = load_weather()

    data = {
        "meta": {
            "title": "日本東北自駕遊行程表",
            "subtitle": overview_title,
            "flightLine": overview_sub,
            "range": "2026/10/20 – 2026/10/31",
            "nights": "11 晚 12 天｜仙台機場進出",
            "travelers": "2 位成人 ＋ 1 位長輩",
            "dailyDrive": "每日開車目標 ≤ 3 小時",
        },
        "overview": overview_days,
        "decisions": decisions,
        "days": days,
        "cost": cost,
        "spots": spots,
        "spotKeys": spot_keys,
        "hotels": hotels,
        "hotelKeys": hotel_keys,
        "alerts": alerts,
        "snow": snow,
        "sos": sos,
        "charging": charging,
        "weather": weather.get("days", []),
        "weatherFetchedAt": weather.get("fetchedAt", ""),
    }

    out_path = DATA_DIR / "data.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {out_path}")
    print(f"  overview days: {len(overview_days)}")
    print(f"  day sheets: {len(days)}, items: {sum(len(d['items']) for d in days)}")
    print(f"  cost: hotels={len(cost['hotels'])} flights={len(cost['flights'])} rental={len(cost['rental'])} tolls={len(cost['tolls'])}")
    print(f"  spots={len(spots)} hotels={len(hotels)} alerts={len(alerts)} snow={len(snow)}")
    print(f"  sos: hotlines={len(sos['hotlines'])} steps={len(sos['steps'])} phrases={len(sos['phrases'])}")
    print(f"  charging sections={len(charging)} items={sum(len(s['items']) for s in charging)}")
    print(f"  decisions={len(decisions)}")
    map_items = sum(1 for d in days for it in d["items"] if "map" in it)
    hotel_maps = sum(1 for o in overview_days if "hotelMap" in o)
    print(f"  maps: day-items={map_items} overview-hotels={hotel_maps} spots={spot_map_hits}/{len(spots)}")
    print(f"  weather: {len(weather.get('days', []))} days (fetchedAt={weather.get('fetchedAt', '-')})")


if __name__ == "__main__":
    main()
