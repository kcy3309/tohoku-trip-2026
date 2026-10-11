"""Attach map coordinates to data.json (curated list, Nominatim-verified offline-first)."""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "_data" / "data.json"

# Curated coordinates (WGS84), verified against official locations.
GEO: dict[str, dict] = {
    "仙台機場": {"lat": 38.1397, "lng": 140.9170, "kind": "airport"},
    "奥州秋保温泉 蘭亭": {"lat": 38.2268, "lng": 140.7070, "kind": "hotel", "day": 1, "map": "https://maps.app.goo.gl/xhNxo14ifyhdu8dM6"},
    "青葉城址（仙台城跡）": {"lat": 38.2534, "lng": 140.8632, "kind": "spot", "day": 1},
    "仙台市區": {"lat": 38.2688, "lng": 140.8686, "kind": "spot"},
    "磊々峡 （秋保溫泉旁溪谷）": {"lat": 38.2222, "lng": 140.6997, "kind": "spot", "day": 2},
    "藏王エコーライン兜風（御釜展望）": {"lat": 38.1358, "lng": 140.4836, "kind": "spot", "day": 2},
    "藏王空中纜車（藏王ロープウェイ）": {"lat": 38.1422, "lng": 140.4425, "kind": "spot", "day": 2},
    "蔵王四季のホテル": {"lat": 38.1444, "lng": 140.4472, "kind": "hotel", "day": 2},
    "文翔館": {"lat": 38.2489, "lng": 140.3350, "kind": "spot", "day": 3},
    "寶珠山立石寺（山寺）": {"lat": 38.3214, "lng": 140.4339, "kind": "spot", "day": 3},
    "角館武家屋敷通り": {"lat": 39.5986, "lng": 140.5625, "kind": "spot", "day": 3},
    "西木温泉ふれあいプラザクリオン": {"lat": 39.6036, "lng": 140.5614, "kind": "hotel", "day": 3},
    "田澤湖": {"lat": 39.7217, "lng": 140.6833, "kind": "spot", "day": 4},
    "鶴の湯溫泉 日歸入浴": {"lat": 39.7994, "lng": 140.7925, "kind": "spot", "day": 4},
    "Guest House Chara": {"lat": 40.6033, "lng": 140.4606, "kind": "hotel", "day": 4},
    "弘前市蘋果公園": {"lat": 40.6039, "lng": 140.4561, "kind": "spot", "day": 5},
    "弘前城": {"lat": 40.6053, "lng": 140.4603, "kind": "spot", "day": 5},
    "最多可容納8人團體旅程- Kamiya": {"lat": 40.8244, "lng": 140.7400, "kind": "hotel", "day": 5},
    "青森県觀光物產館 ASPAM": {"lat": 40.8244, "lng": 140.7594, "kind": "spot", "day": 6},
    "A-FACTORY": {"lat": 40.8269, "lng": 140.7578, "kind": "spot", "day": 6},
    "青森魚菜中心「買る・盛る・食べる」自助海鮮丼": {"lat": 40.8239, "lng": 140.7503, "kind": "spot", "day": 6},
    "八甲田纜車（八甲田ロープウェー）": {"lat": 40.4836, "lng": 140.7592, "kind": "spot", "day": 7},
    "奧入瀨溪流精華段": {"lat": 40.4722, "lng": 140.9800, "kind": "spot", "day": 7},
    "Jalan Yuze Hotel Resort": {"lat": 39.4333, "lng": 140.5167, "kind": "hotel", "day": 7},
    "八幡平アスピーテライン兜風": {"lat": 39.9586, "lng": 140.8528, "kind": "spot", "day": 8},
    "盛岡城跡公園": {"lat": 39.7014, "lng": 141.1369, "kind": "spot", "day": 8},
    "在日本IwateMorioka的出租單位": {"lat": 39.7036, "lng": 141.1525, "kind": "hotel", "day": 8},
    "中尊寺金色堂": {"lat": 39.0008, "lng": 141.1081, "kind": "spot", "day": 9},
    "毛越寺": {"lat": 38.9908, "lng": 141.1069, "kind": "spot", "day": 9},
    "猊鼻溪乘船": {"lat": 38.9236, "lng": 141.0686, "kind": "spot", "day": 9},
    "厳美渓温泉 いつくし園": {"lat": 38.9286, "lng": 141.1067, "kind": "hotel", "day": 9},
    "瑞巖寺／五大堂": {"lat": 38.3700, "lng": 141.0611, "kind": "spot", "day": 10},
    "松島遊船": {"lat": 38.3717, "lng": 141.0586, "kind": "spot", "day": 10},
    "円通院 紅葉夜楓點燈": {"lat": 38.3736, "lng": 141.0581, "kind": "spot", "day": 10},
    "松島温泉 ホテル 絶景の館": {"lat": 38.3706, "lng": 141.0561, "kind": "hotel", "day": 10},
    "鹽釜魚市場": {"lat": 38.3181, "lng": 140.9653, "kind": "spot", "day": 11},
    "仙台朝市": {"lat": 38.2594, "lng": 140.8822, "kind": "spot", "day": 12},
    "仙台泉PREMIUM OUTLETS": {"lat": 38.2319, "lng": 140.8681, "kind": "spot", "day": 11},
    "Kunimaru先生的公寓": {"lat": 38.2650, "lng": 140.8750, "kind": "hotel", "day": 11},
}

# Route polyline: night-by-night lodging order (Day1..Day11) + airport ends.
ROUTE = [
    "仙台機場",
    "奥州秋保温泉 蘭亭",
    "蔵王四季のホテル",
    "西木温泉ふれあいプラザクリオン",
    "Guest House Chara",
    "最多可容納8人團體旅程- Kamiya",
    "Jalan Yuze Hotel Resort",
    "在日本IwateMorioka的出租單位",
    "厳美渓温泉 いつくし園",
    "松島温泉 ホテル 絶景の館",
    "Kunimaru先生的公寓",
    "仙台機場",
]


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    missing = [k for k in ROUTE if k not in GEO]
    if missing:
        raise SystemExit(f"missing route coords: {missing}")
    data["geo"] = [{"name": k, **v} for k, v in GEO.items()]
    data["route"] = ROUTE
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"geo points: {len(data['geo'])}, route stops: {len(ROUTE)}")


if __name__ == "__main__":
    main()
