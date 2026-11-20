import os
import sys
from typing import Optional

import altair as alt
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from cities import CITIES  # noqa: E402

st.set_page_config(
    page_title="Tunisia Weather & Air Quality",
    page_icon="🌍",
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

# Show a warning if the newest non-future row is older than this.
STALE_AFTER_HOURS = 6

# History window options for the sidebar (None = everything).
HISTORY_OPTIONS = {
    "Last 7 days": 7,
    "Last 14 days": 14,
    "Last 30 days": 30,
    "Last 90 days": 90,
    "All data": None,
}

# Approximate US EPA breakpoints (upper bound, label), applied to hourly values.
PM25_LEVELS = [
    (9.0, "🟢 Good"),
    (35.4, "🟡 Moderate"),
    (55.4, "🟠 Unhealthy for sensitive groups"),
    (125.4, "🔴 Unhealthy"),
    (225.4, "🟣 Very unhealthy"),
    (float("inf"), "🟤 Hazardous"),
]
PM10_LEVELS = [
    (54, "🟢 Good"),
    (154, "🟡 Moderate"),
    (254, "🟠 Unhealthy for sensitive groups"),
    (354, "🔴 Unhealthy"),
    (424, "🟣 Very unhealthy"),
    (float("inf"), "🟤 Hazardous"),
]


# --------------------------------------------------------------------------
# Data access
# --------------------------------------------------------------------------
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


def tunis_now() -> pd.Timestamp:
    """Current hour in Tunis local time, timezone-naive.

    The pipeline is assumed to request `timezone=Africa/Tunis` from Open-Meteo,
    so the stored `time` values are Tunis local time. If that ever changes,
    this is the one place to update.
    """
    return pd.Timestamp.now(tz="Africa/Tunis").tz_localize(None).floor("h")


@st.cache_data(ttl=600)
def load_data(days: Optional[int]) -> pd.DataFrame:
    """Load hourly rows, optionally only the last `days` days (plus forecast)."""
    if days is None:
        query = text("SELECT * FROM hourly_measurements ORDER BY time")
        params = {}
    else:
        cutoff = (tunis_now() - pd.Timedelta(days=days)).to_pydatetime()
        query = text(
            "SELECT * FROM hourly_measurements WHERE time >= :cutoff ORDER BY time"
        )
        params = {"cutoff": cutoff}

    data = pd.read_sql(query, get_engine(), params=params)
    data["time"] = pd.to_datetime(data["time"])
    # Safety net: a duplicated (time, city) pair would break pivots below.
    # The real fix is a UNIQUE constraint + upsert in the pipeline.
    return data.drop_duplicates(subset=["time", "city"], keep="last")


@st.cache_data(ttl=600)
def csv_bytes(days: Optional[int]) -> bytes:
    """CSV is built once per window, not on every Streamlit rerun."""
    return load_data(days).to_csv(index=False).encode("utf-8")


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def latest_per_city(data: pd.DataFrame, now: pd.Timestamp) -> pd.DataFrame:
    """Most recent hour that is not in the future, for each city."""
    past = data[data["time"] <= now]
    source = past if not past.empty else data
    return source.sort_values("time").groupby("city").tail(1).reset_index(drop=True)


def extreme_row(frame: pd.DataFrame, column: str):
    """Row with the highest value in `column`, or None if there is no data."""
    valid = frame.dropna(subset=[column])
    if valid.empty:
        return None
    return valid.loc[valid[column].idxmax()]


def show_kpi(slot, title: str, row, field: str, unit: str) -> None:
    if row is None:
        slot.metric(title, "n/a")
    else:
        slot.metric(f"{title} · {row['city']}", f"{row[field]:.1f} {unit}")


def pm_category(value, levels) -> str:
    if pd.isna(value):
        return "n/a"
    for upper, label in levels:
        if value <= upper:
            return label
    return levels[-1][1]


def value_to_hex(value, vmin: float, vmax: float) -> str:
    """Blue (low) to red (high); grey when there is no value."""
    if pd.isna(value):
        return "#999999"
    t = 0.5 if vmax <= vmin else (value - vmin) / (vmax - vmin)
    low, high = (59, 130, 246), (239, 68, 68)
    r, g, b = (round(lo + (hi - lo) * t) for lo, hi in zip(low, high))
    return f"#{r:02x}{g:02x}{b:02x}"


# --------------------------------------------------------------------------
# Sidebar (part 1: needs to run before loading data)
# --------------------------------------------------------------------------
with st.sidebar:
    st.header("Filters")
    window_label = st.selectbox("History shown", list(HISTORY_OPTIONS), index=1)
    days = HISTORY_OPTIONS[window_label]

df = load_data(days)
if df.empty:
    st.warning(
        "No data found for this period. Pick a longer window, or run the pipeline first."
    )
    st.stop()

now = tunis_now()
current = latest_per_city(df, now)
past = df[df["time"] <= now]
n_cities = df["city"].nunique()

# --------------------------------------------------------------------------
# Header + data freshness
# --------------------------------------------------------------------------
st.title("🌍 Tunisia Weather & Air Quality Monitor")
st.caption(
    f"Hourly weather and air quality for {n_cities} Tunisian cities, "
    "collected every day by an automated data pipeline."
)

if past.empty:
    st.warning("Only forecast data is available; there are no past observations yet.")
else:
    newest = past["time"].max()
    age_hours = (now - newest) / pd.Timedelta(hours=1)
    if age_hours > STALE_AFTER_HOURS:
        st.warning(
            f"Latest data is from {newest:%d %b %Y, %H:%M} ({age_hours:.0f} h ago). "
            "The pipeline may have stalled, so the 'now' values below could be outdated."
        )
    else:
        st.caption(f"Data as of {newest:%d %b %Y, %H:%M} (Tunis time).")

# --------------------------------------------------------------------------
# Sidebar (part 2)
# --------------------------------------------------------------------------
with st.sidebar:
    metric = st.selectbox("Measure", list(LABELS), format_func=LABELS.get)
    all_cities = sorted(df["city"].unique())
    defaults = [c for c in DEFAULT_TREND_CITIES if c in all_cities]
    trend_cities = st.multiselect("Cities in the trend chart", all_cities, default=defaults)
    st.divider()
    st.caption(f"{n_cities} cities · {len(df):,} hourly rows in view")
    st.caption(f"Data from {df['time'].min():%d %b %Y} to {df['time'].max():%d %b %Y}")

tab_overview, tab_trends, tab_data = st.tabs(["Overview", "Trends", "Data"])

# --------------------------------------------------------------------------
# Overview
# --------------------------------------------------------------------------
with tab_overview:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Cities tracked", n_cities)
    show_kpi(k2, "Hottest now", extreme_row(current, "temperature_2m"), "temperature_2m", "°C")
    show_kpi(k3, "Highest PM10", extreme_row(current, "pm10"), "pm10", "µg/m³")
    show_kpi(k4, "Windiest now", extreme_row(current, "wind_speed_10m"), "wind_speed_10m", "km/h")

    left, right = st.columns([1, 1])

    with left:
        st.subheader(f"Ranking: {LABELS[metric]}")
        ranking = current.dropna(subset=[metric])[["city", metric]]
        if ranking.empty:
            st.info("No data for this measure yet.")
        else:
            chart = (
                alt.Chart(ranking)
                .mark_bar()
                .encode(
                    x=alt.X(f"{metric}:Q", title=LABELS[metric]),
                    y=alt.Y("city:N", sort="-x", title=None),
                    tooltip=["city", alt.Tooltip(f"{metric}:Q", title=LABELS[metric], format=".1f")],
                )
                .properties(height=max(300, 22 * len(ranking)))
            )
            st.altair_chart(chart, width="stretch")

    with right:
        st.subheader(f"Map: {LABELS[metric]}")
        coords = pd.DataFrame(
            [{"city": c, "lat": lat, "lon": lon} for c, (lat, lon) in CITIES.items()]
        )
        coords = coords.merge(current[["city", metric]], on="city", how="left")
        vmin, vmax = coords[metric].min(), coords[metric].max()
        coords["color"] = coords[metric].map(lambda v: value_to_hex(v, vmin, vmax))
        coords["size"] = 9000
        st.map(coords, latitude="lat", longitude="lon", color="color", size="size")
        st.caption("Colour scale: blue = lowest value, red = highest value, grey = no data.")

    st.subheader("Air quality right now")
    aq = current.dropna(subset=["pm2_5", "pm10"], how="all").copy()
    if aq.empty:
        st.info("No air quality data available yet.")
    else:
        aq["PM2.5 level"] = aq["pm2_5"].map(lambda v: pm_category(v, PM25_LEVELS))
        aq["PM10 level"] = aq["pm10"].map(lambda v: pm_category(v, PM10_LEVELS))
        aq = (
            aq.sort_values("pm2_5", ascending=False)
            .set_index("city")
            .rename(columns={"pm2_5": LABELS["pm2_5"], "pm10": LABELS["pm10"]})
        )
        st.dataframe(
            aq[[LABELS["pm2_5"], "PM2.5 level", LABELS["pm10"], "PM10 level"]].round(1),
            width="stretch",
        )
        st.caption(
            "Levels use approximate US EPA categories applied to hourly values, so they are "
            "indicative only. For reference, the WHO 2021 24-hour guidelines are "
            "15 µg/m³ for PM2.5 and 45 µg/m³ for PM10."
        )

# --------------------------------------------------------------------------
# Trends
# --------------------------------------------------------------------------
with tab_trends:
    st.subheader(LABELS[metric])
    if trend_cities:
        view = df[df["city"].isin(trend_cities)]
        st.line_chart(
            view.pivot_table(index="time", columns="city", values=metric, aggfunc="last")
        )
    else:
        st.info("Pick at least one city in the sidebar.")

    st.subheader("Summary by city")
    if past.empty:
        st.info("No past observations to summarise yet.")
    else:
        st.caption(
            f"Past observations only (no forecast hours), "
            f"{past['time'].min():%d %b} to {past['time'].max():%d %b %Y}. "
            "Max is shown next to the mean because averages hide pollution spikes."
        )
        summary = past.groupby("city")[list(LABELS)].agg(["mean", "max"]).round(1)
        summary.columns = [f"{LABELS[col]} · {stat}" for col, stat in summary.columns]
        st.dataframe(summary, width="stretch")

# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
with tab_data:
    st.subheader("Latest values by city")
    table = current.set_index("city")[["time", *LABELS]].rename(columns=LABELS)
    st.dataframe(table, width="stretch")
    st.download_button(
        f"Download data in view (CSV) · {window_label.lower()}",
        csv_bytes(days),
        file_name="tunisia_weather_air_quality.csv",
        mime="text/csv",
    )

st.divider()
st.caption(
    "Sources: weather from Open-Meteo; air quality from CAMS (Copernicus Atmosphere "
    "Monitoring Service) via Open-Meteo. Values are model-based estimates and forecasts, "
    "not station measurements. City coordinates are approximate."
)