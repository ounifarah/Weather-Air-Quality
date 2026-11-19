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
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response
        except requests.RequestException:
            if attempt == retries:
                raise
            time.sleep(2 * attempt)


def extract(
    city: str,
    latitude: float,
    longitude: float,
    forecast_days: int = 2,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch weather and air-quality data for one city."""
    base: dict[str, Any] = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "Africa/Tunis",
        "forecast_days": forecast_days,
    }
    weather_response = _get(
        WEATHER_URL,
        {**base, "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m"},
    )
    air_response = _get(AIR_QUALITY_URL, {**base, "hourly": "pm10,pm2_5"})

    weather = pd.DataFrame(weather_response.json()["hourly"])
    air = pd.DataFrame(air_response.json()["hourly"])
    return weather, air