import os
import sys

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from cities import CITIES  # noqa: E402

st.set_page_config(
    page_title="Tunisia Weather & Air Quality",
    page_icon="",
    layout="wide",
)

LABELS = {
    "temperature_2m": "Temperature (°C)",
    "relative_humidity_2m": "Humidity (%)",
    "wind_speed_10m": "Wind speed (km/h)",
    "pm10": "PM10 (µg/m³)",
    "pm2_5": "PM2.5 (µg/m³)",
}
DEFAULT_TREND_CITIES = ["Tunis", "Sfax", "Sousse", "Gabes", "Bizerte"]


def database_url() -> str:
    try:
        url = st.secrets["DATABASE_URL"]
    except Exception:
        from dotenv import load_dotenv

        load_dotenv()
        url = os.environ["DATABASE_URL"]
    return url.replace("postgresql://", "postgresql+psycopg2://", 1)


@st.cache_resource
def get_engine():
    return create_engine(database_url(), pool_pre_ping=True)


@st.cache_data(ttl=600)
def load_data() -> pd.DataFrame:
    data = pd.read_sql("SELECT * FROM hourly_measurements ORDER BY time", get_engine())
    data["time"] = pd.to_datetime(data["time"])
    return data


def latest_per_city(data: pd.DataFrame) -> pd.DataFrame:
    """Most recent hour that is not in the future, for each city."""
    now = pd.Timestamp.now(tz="Africa/Tunis").tz_localize(None).floor("h")
    past = data[data["time"] <= now]
    source = past if not past.empty else data
    return source.sort_values("time").groupby("city").tail(1).reset_index(drop=True)


st.title(" Tunisia Weather & Air Quality Monitor")
st.caption(
    "Hourly weather and air quality for the 24 governorates of Tunisia, "
    "collected every day by an automated data pipeline."
)

df = load_data()
if df.empty:
    st.warning("The database is empty. Run the pipeline first.")
    st.stop()

current = latest_per_city(df)

with st.sidebar:
    st.header("Filters")
    metric = st.selectbox("Measure", list(LABELS), format_func=LABELS.get)
    all_cities = sorted(df["city"].unique())
    defaults = [c for c in DEFAULT_TREND_CITIES if c in all_cities]
    trend_cities = st.multiselect("Cities in the trend chart", all_cities, default=defaults)
    st.divider()
    st.caption(f"{df['city'].nunique()} cities · {len(df):,} hourly rows")
    st.caption(f"Data from {df['time'].min():%d %b %Y} to {df['time'].max():%d %b %Y}")

tab_overview, tab_trends, tab_data = st.tabs(["Overview", "Trends", "Data"])

with tab_overview:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Cities tracked", df["city"].nunique())

    hottest = current.loc[current["temperature_2m"].idxmax()]
    k2.metric("Hottest now", hottest["city"], f"{hottest['temperature_2m']:.1f} °C")

    pm_rows = current.dropna(subset=["pm10"])
    if not pm_rows.empty:
        dusty = pm_rows.loc[pm_rows["pm10"].idxmax()]
        k3.metric("Highest PM10 now", dusty["city"], f"{dusty['pm10']:.1f} µg/m³")

    windy = current.loc[current["wind_speed_10m"].idxmax()]
    k4.metric("Windiest now", windy["city"], f"{windy['wind_speed_10m']:.1f} km/h")

    left, right = st.columns([1, 1])
    with left:
        st.subheader(f"Ranking: {LABELS[metric]}")
        ranking = current.dropna(subset=[metric]).set_index("city")[metric]
        st.bar_chart(ranking.sort_values(ascending=False))
    with right:
        st.subheader("Map of tracked cities")
        coords = pd.DataFrame(
            [{"city": c, "lat": lat, "lon": lon} for c, (lat, lon) in CITIES.items()]
        )
        st.map(coords, latitude="lat", longitude="lon")

with tab_trends:
    st.subheader(LABELS[metric])
    if trend_cities:
        view = df[df["city"].isin(trend_cities)]
        st.line_chart(view.pivot(index="time", columns="city", values=metric))
    else:
        st.info("Pick at least one city in the sidebar.")

    st.subheader("Average by city")
    summary = df.groupby("city")[list(LABELS)].mean().round(1)
    st.dataframe(summary.rename(columns=LABELS), use_container_width=True)

with tab_data:
    st.subheader("Latest values by city")
    table = current.set_index("city")[["time", *LABELS]].rename(columns=LABELS)
    st.dataframe(table, use_container_width=True)
    st.download_button(
        "Download all data (CSV)",
        df.to_csv(index=False).encode("utf-8"),
        file_name="tunisia_weather_air_quality.csv",
        mime="text/csv",
    )

st.divider()
st.caption(
    "Sources: weather from Open-Meteo; air quality from CAMS (Copernicus Atmosphere "
    "Monitoring Service) via Open-Meteo. Values are model-based forecasts, not station "
    "measurements. City coordinates are approximate."
)
