"""
modules/weather.py
===================
Weather forecast using Open-Meteo API — completely FREE, no API key needed.
Fetches current conditions + 7-day forecast based on lat/lon.

Falls back to synthetic data if network is unavailable.
"""

from __future__ import annotations
import logging
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

# WMO weather code descriptions
WMO_CODES = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Foggy", "🌫️"),
    48: ("Icy fog", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    53: ("Drizzle", "🌦️"),
    55: ("Heavy drizzle", "🌧️"),
    61: ("Light rain", "🌧️"),
    63: ("Rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    71: ("Light snow", "🌨️"),
    73: ("Snow", "❄️"),
    75: ("Heavy snow", "❄️"),
    80: ("Rain showers", "🌦️"),
    81: ("Heavy showers", "🌧️"),
    82: ("Violent showers", "⛈️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm + hail", "⛈️"),
    99: ("Heavy thunderstorm", "⛈️"),
}


def get_weather(lat: float, lon: float) -> dict | None:
    """
    Fetch current weather + 7-day forecast from Open-Meteo.

    Returns
    -------
    {
        "location":   str,
        "current":    { temp, humidity, windspeed, rainfall, condition, icon },
        "forecast":   [ { date, max_temp, min_temp, rainfall, condition, icon }, ... ]
        "hourly_temp": [ float, ... ]  # next 24h
        "hourly_time": [ str, ... ]
    }
    or None if fetch failed.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude":               lat,
        "longitude":              lon,
        "current":                "temperature_2m,relative_humidity_2m,windspeed_10m,precipitation,weathercode",
        "daily":                  "weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum",
        "hourly":                 "temperature_2m",
        "timezone":               "auto",
        "forecast_days":          7,
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("Weather fetch failed: %s", exc)
        return _demo_weather(lat, lon)

    try:
        cur  = data["current"]
        daily = data["daily"]
        hourly = data.get("hourly", {})

        wcode = int(cur.get("weathercode", 0))
        cond, icon = WMO_CODES.get(wcode, ("Unknown", "🌡️"))

        current = {
            "temp":      round(float(cur["temperature_2m"]), 1),
            "humidity":  round(float(cur["relative_humidity_2m"]), 1),
            "windspeed": round(float(cur["windspeed_10m"]), 1),
            "rainfall":  round(float(cur.get("precipitation", 0)), 1),
            "condition": cond,
            "icon":      icon,
        }

        forecast = []
        for i in range(len(daily["time"])):
            dc, di = WMO_CODES.get(int(daily["weathercode"][i]), ("—", "🌡️"))
            forecast.append({
                "date":     daily["time"][i],
                "max_temp": round(float(daily["temperature_2m_max"][i]), 1),
                "min_temp": round(float(daily["temperature_2m_min"][i]), 1),
                "rainfall": round(float(daily["precipitation_sum"][i]), 1),
                "condition": dc,
                "icon":      di,
            })

        return {
            "location":    f"{lat:.3f}°N, {lon:.3f}°E",
            "current":     current,
            "forecast":    forecast,
            "hourly_temp": [round(float(v), 1) for v in hourly.get("temperature_2m", [])[:24]],
            "hourly_time": hourly.get("time", [])[:24],
        }

    except Exception as exc:
        logger.warning("Weather parse failed: %s", exc)
        return _demo_weather(lat, lon)


def get_weather_by_city(city: str) -> dict | None:
    """Geocode a city name then fetch weather."""
    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    try:
        resp = requests.get(geo_url, params={"name": city, "count": 1}, timeout=8)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            return None
        r   = results[0]
        lat = float(r["latitude"])
        lon = float(r["longitude"])
        data = get_weather(lat, lon)
        if data:
            data["location"] = f"{r.get('name','?')}, {r.get('country','?')}"
        return data
    except Exception as exc:
        logger.warning("Geocoding failed: %s", exc)
        return None


# ── Demo fallback ─────────────────────────────────────────────────────────────

def _demo_weather(lat: float, lon: float) -> dict:
    import random
    random.seed(int(abs(lat * lon) * 100) % 999)
    temp = round(random.uniform(22, 38), 1)
    return {
        "location": f"{lat:.3f}°N, {lon:.3f}°E (demo)",
        "current": {
            "temp":      temp,
            "humidity":  round(random.uniform(40, 85), 1),
            "windspeed": round(random.uniform(5, 25), 1),
            "rainfall":  round(random.uniform(0, 5), 1),
            "condition": "Partly cloudy",
            "icon":      "⛅",
        },
        "forecast": [
            {
                "date":      f"2024-0{i+1}-01" if i < 9 else f"2024-{i+1}-01",
                "max_temp":  round(temp + random.uniform(-3, 4), 1),
                "min_temp":  round(temp - random.uniform(4, 10), 1),
                "rainfall":  round(random.uniform(0, 12), 1),
                "condition": "Partly cloudy",
                "icon":      "⛅",
            }
            for i in range(7)
        ],
        "hourly_temp": [round(temp + (i % 6 - 3) * 0.8, 1) for i in range(24)],
        "hourly_time": [f"{i:02d}:00" for i in range(24)],
    }
