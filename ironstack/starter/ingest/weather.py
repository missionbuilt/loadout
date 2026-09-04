#!/usr/bin/env python3
"""Look up the weather a session was trained in, so nobody has to type it.

    python ingest/weather.py 40.35 -80.05 2026-09-03 18 America/New_York

Open-Meteo, no API key. The forecast endpoint covers roughly the last three
months; older dates fall back to the archive. Every failure returns None —
a workout log is never blocked because the weather service was down.
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from datetime import date

FORECAST = "https://api.open-meteo.com/v1/forecast"
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
TIMEOUT = 8

WMO = {
    0: "clear", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "freezing fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    56: "freezing drizzle", 57: "freezing drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    66: "freezing rain", 67: "freezing rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "rain showers", 81: "rain showers", 82: "heavy rain showers",
    85: "snow showers", 86: "heavy snow showers",
    95: "thunderstorms", 96: "thunderstorms with hail", 99: "thunderstorms with hail",
}

COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def compass(degrees) -> str:
    return COMPASS[int((float(degrees) % 360) / 22.5 + 0.5) % 16]


def _get(url: str, params: dict) -> dict:
    query = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{url}?{query}", timeout=TIMEOUT) as response:
        return json.loads(response.read().decode())


def to_environment(payload: dict, hour: int) -> dict:
    """Pick the hour the session started out of an hourly payload."""
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    if not times:
        return {}
    index = min(hour, len(times) - 1)
    for i, stamp in enumerate(times):
        if stamp.endswith(f"T{hour:02d}:00"):
            index = i
            break

    def value(key):
        series = hourly.get(key) or []
        return series[index] if index < len(series) else None

    env = {}
    temp = value("temperature_2m")
    if temp is not None:
        env["temp_f"] = round(float(temp))
    humidity = value("relative_humidity_2m")
    if humidity is not None:
        env["humidity_pct"] = round(float(humidity))
    code = value("weather_code")
    if code is not None and int(code) in WMO:
        env["conditions"] = WMO[int(code)]
    speed = value("wind_speed_10m")
    if speed is not None:
        direction = value("wind_direction_10m")
        env["wind"] = (f"{compass(direction)} " if direction is not None else "") + f"{round(float(speed))} mph"
    return env


def fetch(lat: float, lon: float, day: str, hour: int = 12, timezone: str = "auto"):
    """-> an `environment` fragment, or None if the lookup didn't work."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": day,
        "end_date": day,
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,weather_code",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "timezone": timezone,
    }
    days_back = (date.today() - date.fromisoformat(day)).days
    endpoints = [FORECAST, ARCHIVE] if days_back < 90 else [ARCHIVE, FORECAST]
    for endpoint in endpoints:
        try:
            env = to_environment(_get(endpoint, params), hour)
            if env:
                return env
        except Exception:
            continue
    return None


def main(argv: list) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 1
    lat, lon, day = float(argv[0]), float(argv[1]), argv[2]
    hour = int(argv[3]) if len(argv) > 3 else 12
    tz = argv[4] if len(argv) > 4 else "auto"
    env = fetch(lat, lon, day, hour, tz)
    if env is None:
        print("no weather (lookup failed)", file=sys.stderr)
        return 2
    print(json.dumps(env, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
