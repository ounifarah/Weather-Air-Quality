import pandas as pd


def clean(weather: pd.DataFrame, air: pd.DataFrame, city: str) -> pd.DataFrame:
    """Join API responses and validate the resulting measurements."""
    weather = weather.copy()
    air = air.copy()
    weather["time"] = pd.to_datetime(weather["time"])
    air["time"] = pd.to_datetime(air["time"])

    df = weather.merge(air, on="time", how="left")
    df.insert(0, "city", city)

    humidity = df["relative_humidity_2m"].dropna()
    temperature = df["temperature_2m"].dropna()
    if not humidity.between(0, 100).all():
        raise ValueError("relative_humidity_2m contains values outside 0-100")
    if not temperature.between(-20, 60).all():
        raise ValueError("temperature_2m contains values outside -20-60")

    return df.drop_duplicates(subset=["city", "time"])

