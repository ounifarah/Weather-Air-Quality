import pandas as pd
import pytest

from src.transform import clean


def test_clean_joins_data_and_removes_duplicate_times() -> None:
    weather = pd.DataFrame(
        {
            "time": ["2026-01-01T00:00", "2026-01-01T00:00"],
            "temperature_2m": [15.0, 15.0],
            "relative_humidity_2m": [60.0, 60.0],
            "wind_speed_10m": [5.0, 5.0],
        }
    )
    air = pd.DataFrame(
        {
            "time": ["2026-01-01T00:00"],
            "pm10": [10.0],
            "pm2_5": [5.0],
        }
    )

    result = clean(weather, air, "Tunis")

    assert len(result) == 1
    assert result.iloc[0]["city"] == "Tunis"


def test_clean_rejects_impossible_humidity() -> None:
    weather = pd.DataFrame(
        {
            "time": ["2026-01-01T00:00"],
            "temperature_2m": [15.0],
            "relative_humidity_2m": [101.0],
            "wind_speed_10m": [5.0],
        }
    )
    air = pd.DataFrame(
        {"time": ["2026-01-01T00:00"], "pm10": [10.0], "pm2_5": [5.0]}
    )

    with pytest.raises(ValueError, match="humidity"):
        clean(weather, air, "Tunis")

