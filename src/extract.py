from typing import Any

import pandas as pd
import requests

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


def extract(
    city: str,
    latitude: float,
    longitude: float,
    forecast_days: int = 2,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch weather and air-quality data for one city."""
    weather_params: dict[str, Any] = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m",
        "timezone": "Africa/Tunis",
        "forecast_days": forecast_days,
    }
    air_params: dict[str, Any] = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "pm10,pm2_5",
        "timezone": "Africa/Tunis",
        "forecast_days": forecast_days,
    }

    weather_response = requests.get(WEATHER_URL, params=weather_params, timeout=30)
    weather_response.raise_for_status()
    air_response = requests.get(AIR_QUALITY_URL, params=air_params, timeout=30)
    air_response.raise_for_status()

    weather = pd.DataFrame(weather_response.json()["hourly"])
    air = pd.DataFrame(air_response.json()["hourly"])
    return weather, air

