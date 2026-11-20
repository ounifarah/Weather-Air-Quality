import time
from typing import Any

import pandas as pd
import requests

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


def _get(url: str, params: dict[str, Any], retries: int = 3) -> requests.Response:
    """GET with a few retries, so one temporary network error does not fail the run."""
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, params=params, timeout=(10, 90))
            response.raise_for_status()
            return response
        except requests.RequestException:
            if attempt == retries:
                raise
            time.sleep(2 * attempt)


def _as_list(payload: Any) -> list[dict]:
    """The API returns one object for one location and a list for several."""
    return payload if isinstance(payload, list) else [payload]


def extract_all(
    cities: dict[str, tuple[float, float]],
    forecast_days: int = 2,
) -> dict[str, tuple[pd.DataFrame, pd.DataFrame]]:
    """Fetch weather and air quality for every city with just two requests."""
    names = list(cities)
    base: dict[str, Any] = {
        "latitude": ",".join(str(cities[n][0]) for n in names),
        "longitude": ",".join(str(cities[n][1]) for n in names),
        "timezone": "Africa/Tunis",
        "forecast_days": forecast_days,
    }
    weather_json = _as_list(
        _get(
            WEATHER_URL,
            {**base, "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m"},
        ).json()
    )
    air_json = _as_list(_get(AIR_QUALITY_URL, {**base, "hourly": "pm10,pm2_5"}).json())

    if len(weather_json) != len(names) or len(air_json) != len(names):
        raise ValueError("The API returned a different number of locations than requested")

    return {
        name: (pd.DataFrame(weather["hourly"]), pd.DataFrame(air["hourly"]))
        for name, weather, air in zip(names, weather_json, air_json)
    }
