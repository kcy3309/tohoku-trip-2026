"""Download all Google Sheets tabs as CSV into tohoku-trip/_data/.

Also fetches the workbook as XLSX once and extracts Google-Maps cell
hyperlinks (invisible to CSV export) into _data/links.json.
"""
import csv
import io
import json
import re
import sys
import time
import urllib.request

SHEET_ID = "1fghx2Ia-DjQP17P0pkORvKy8DYs6CJkNLRneWugE07c"
SHEETS = {
    "cost": 1720512521,
    "overview": 1657173016,
    "sos": 357752140,
    "day1": 342708440,
    "day2": 1007441707,
    "day3": 1995694136,
    "day4": 1420322031,
    "day5": 238425947,
    "day6": 656145342,
    "day7": 2144016530,
    "day8": 1673038146,
    "day9": 1106711764,
    "day10": 511297076,
    "day11": 272275928,
    "day12": 1016624163,
    "spots": 1941865860,
    "hotels": 1108692429,
    "alerts": 1448958356,
    "charging": 1381745251,
    "snow": 1185653546,
}


def fetch_csv(gid: int) -> str:
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8-sig")


LINK_RE = re.compile(r"(maps\.app\.goo\.gl|google\.[a-z.]+/maps|goo\.gl/maps)", re.I)


def fetch_links() -> dict:
    """Extract Google-Maps cell hyperlinks from the XLSX export.

    Returns {sheet_title: {row_number: {col_letter: url}}}.
    """
    import openpyxl

    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        blob = resp.read()
    wb = openpyxl.load_workbook(io.BytesIO(blob))
    out: dict = {}
    for ws in wb.worksheets:
        cells: dict = {}
        for row in ws.iter_rows():
            for c in row:
                target = c.hyperlink.target if c.hyperlink else None
                if target and LINK_RE.search(target):
                    cells.setdefault(str(c.row), {})[c.column_letter] = target
        if cells:
            out[ws.title] = cells
    return out


def main() -> None:
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "_data"
    for name, gid in SHEETS.items():
        for attempt in range(3):
            try:
                text = fetch_csv(gid)
                path = f"{out_dir}/{name}.csv"
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.write(text)
                rows = len(list(csv.reader(io.StringIO(text))))
                print(f"OK  {name:10s} gid={gid:<12} rows={rows}")
                break
            except Exception as exc:  # noqa: BLE001
                print(f"ERR {name} attempt {attempt + 1}: {exc}")
            time.sleep(2)
        time.sleep(0.8)
    try:
        links = fetch_links()
        path = f"{out_dir}/links.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(links, f, ensure_ascii=False, indent=1)
        n = sum(len(cols) for sheet in links.values() for cols in sheet.values())
        print(f"OK  links.json: {len(links)} sheets, {n} maps hyperlinks")
    except ImportError:
        print("SKIP links.json: openpyxl not installed (pip install openpyxl)")
    except Exception as exc:  # noqa: BLE001
        print(f"ERR links.json: {exc}")


if __name__ == "__main__":
    main()
