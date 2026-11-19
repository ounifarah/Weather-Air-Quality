import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

COLUMNS = [
    "city",
    "time",
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "pm10",
    "pm2_5",
]

UPSERT = text(
    """
    INSERT INTO hourly_measurements
        (city, time, temperature_2m, relative_humidity_2m,
         wind_speed_10m, pm10, pm2_5)
    VALUES
        (:city, :time, :temperature_2m, :relative_humidity_2m,
         :wind_speed_10m, :pm10, :pm2_5)
    ON CONFLICT (city, time) DO UPDATE SET
        temperature_2m = EXCLUDED.temperature_2m,
        relative_humidity_2m = EXCLUDED.relative_humidity_2m,
        wind_speed_10m = EXCLUDED.wind_speed_10m,
        pm10 = EXCLUDED.pm10,
        pm2_5 = EXCLUDED.pm2_5
    """
)


def get_database_url() -> str:
    """Read the database address from the DATABASE_URL environment variable."""
    url = os.environ["DATABASE_URL"]
    return url.replace("postgresql://", "postgresql+psycopg2://", 1)


def load(df: pd.DataFrame) -> int:
    """Upsert cleaned measurements and return the number of submitted rows."""
    part = df[COLUMNS]
    rows = part.astype(object).where(part.notna(), None).to_dict("records")
    engine = create_engine(get_database_url(), pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            connection.execute(UPSERT, rows)
    finally:
        engine.dispose()
    return len(rows)