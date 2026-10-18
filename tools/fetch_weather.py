"""Fetch Open-Meteo forecast for each day of the Tohoku trip (2026-10-20..31)."""
import json
import urllib.request
from pathlib import Path

# (day, date, area, latitude, longitude)
STOPS = [
    (1, "2026-10-20", "仙台市區", 38.2682, 140.8682),
    (2, "2026-10-21", "藏王溫泉", 38.1444, 140.4472),
    (3, "2026-10-22", "田澤湖／角館", 39.7217, 140.6833),
    (4, "2026-10-23", "弘前（乳頭溫泉鄉→）", 40.6033, 140.4606),
    (5, "2026-10-24", "青森市", 40.8244, 140.7400),
    (6, "2026-10-25", "青森市", 40.8244, 140.7400),
    (7, "2026-10-26", "十和田湖／奧入瀨", 40.4722, 140.9800),
    (8, "2026-10-27", "盛岡（八幡平→）", 39.7036, 141.1525),
    (9, "2026-10-28", "一關（平泉→）", 38.9286, 141.1067),
    (10, "2026-10-29", "松島", 38.3717, 141.0586),
    (11, "2026-10-30", "仙台市區", 38.2682, 140.8682),
    (12, "2026-10-31", "仙台機場", 38.1397, 140.9170),
]

WMO = {
    0: "☀️ 晴", 1: "🌤 大致晴", 2: "⛅ 多雲", 3: "☁️ 陰",
    45: "🌫 霧", 48: "🌫 凍霧",
    51: "🌦 毛毛雨", 53: "🌦 毛毛雨", 55: "🌧 毛毛雨", 56: "🌧 凍毛毛雨", 57: "🌧 凍毛毛雨",
    61: "🌧 雨", 63: "🌧 雨", 65: "🌧 大雨", 66: "🌧 凍雨", 67: "🌧 凍雨",
    71: "🌨 小雪", 73: "🌨 雪", 75: "❄️ 大雪", 77: "❄️ 雪粒",
    80: "🌦 陣雨", 81: "🌦 陣雨", 82: "⛈ 強陣雨",
    85: "🌨 陣雪", 86: "🌨 陣雪",
    95: "⛈ 雷雨", 96: "⛈ 雷雨冰雹", 99: "⛈ 雷雨冰雹",
}


def fetch(lat: float, lon: float) -> dict:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,"
        "precipitation_sum,snowfall_sum,wind_speed_10m_max,wind_gusts_10m_max"
        "&timezone=Asia%2FTokyo&start_date=2026-10-20&end_date=2026-10-31"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "trip-weather-check"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def main() -> None:
    out = []
    for day, date, area, lat, lon in STOPS:
        d = fetch(lat, lon)["daily"]
        i = d["time"].index(date)
        rec = {
            "day": day,
            "date": date,
            "area": area,
            "weather": WMO.get(d["weather_code"][i], f"code {d['weather_code'][i]}"),
            "tmax": d["temperature_2m_max"][i],
            "tmin": d["temperature_2m_min"][i],
            "pop": d["precipitation_probability_max"][i],
            "precip": d["precipitation_sum"][i],
            "snow": d["snowfall_sum"][i],
            "wind": d["wind_speed_10m_max"][i],
            "gust": d["wind_gusts_10m_max"][i],
        }
        out.append(rec)
        print(
            f"Day{day:<2} {date[5:]} {area:<14} {rec['weather']:<8} "
            f"{rec['tmin']:>4.1f}~{rec['tmax']:.1f}°C  "
            f"雨{rec['pop'] if rec['pop'] is not None else '-':>3}%  "
            f"雪{rec['snow']:>4.1f}mm  風{rec['wind']:>4.1f}km/h"
        )
    p = Path(__file__).resolve().parent.parent / "_data" / "weather.json"
    from datetime import datetime, timezone

    payload = {"fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"), "days": out}
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nwrote {p}")


if __name__ == "__main__":
    main()
