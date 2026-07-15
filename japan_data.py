"""
japan_data.py
Pulls real weather + season + time-of-day context for Hana's location.
Uses Open-Meteo (no API key required) so the pipeline has zero cost/friction here.
"""

import datetime
import requests

WEATHER_CODES = {
    0: "clear sky", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "foggy", 48: "foggy with frost", 51: "light drizzle", 53: "drizzle",
    55: "heavy drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 80: "light rain showers",
    81: "rain showers", 82: "violent rain showers", 95: "thunderstorm",
    96: "thunderstorm with hail", 99: "severe thunderstorm with hail",
}


def get_season(dt: datetime.date) -> str:
    m = dt.month
    if m in (3, 4, 5):
        return "spring"
    if m in (6, 7):
        return "early summer / tsuyu (rainy season)"
    if m in (8,):
        return "high summer"
    if m in (9, 10, 11):
        return "autumn"
    return "winter"


def get_daypart(hour: int) -> str:
    if 4 <= hour < 10:
        return "morning"
    if 10 <= hour < 16:
        return "midday"
    if 16 <= hour < 19:
        return "evening"
    return "night"


def fetch_weather(lat: float, lon: float) -> dict:
    """
    Returns current + today's weather summary for the given coordinates.
    Falls back to a gentle default if the API is unreachable, so the
    pipeline never hard-fails just because of weather.
    """
    try:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m"
            "&daily=temperature_2m_max,temperature_2m_min,weather_code,sunrise,sunset"
            "&timezone=Asia%2FTokyo"
        )
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        current = data.get("current", {})
        daily = data.get("daily", {})

        code = current.get("weather_code", 0)
        return {
            "description": WEATHER_CODES.get(code, "changeable weather"),
            "temp_c": current.get("temperature_2m"),
            "temp_max_c": daily.get("temperature_2m_max", [None])[0],
            "temp_min_c": daily.get("temperature_2m_min", [None])[0],
            "humidity": current.get("relative_humidity_2m"),
            "wind_kph": current.get("wind_speed_10m"),
            "sunrise": daily.get("sunrise", [None])[0],
            "sunset": daily.get("sunset", [None])[0],
            "source": "open-meteo",
        }
    except Exception as e:
        return {
            "description": "soft overcast light",
            "temp_c": 18,
            "temp_max_c": 21,
            "temp_min_c": 14,
            "humidity": 60,
            "wind_kph": 8,
            "sunrise": None,
            "sunset": None,
            "source": f"fallback ({e})",
        }


def get_context(lat: float, lon: float, now: datetime.datetime = None) -> dict:
    """Single entry point: everything hana_story.py needs about 'today'."""
    now = now or datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))  # JST
    weather = fetch_weather(lat, lon)
    return {
        "date": now.strftime("%Y-%m-%d"),
        "weekday": now.strftime("%A"),
        "hour": now.hour,
        "daypart": get_daypart(now.hour),
        "season": get_season(now.date()),
        "weather": weather,
    }


if __name__ == "__main__":
    ctx = get_context(35.3192, 139.5467)
    import json
    print(json.dumps(ctx, indent=2, ensure_ascii=False))
