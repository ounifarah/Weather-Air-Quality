import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from cities import CITIES  # noqa: E402

st.set_page_config(page_title="Tunisia Weather & Air Quality", layout="wide")

LABELS = {
    "temperature_2m": "Temperature (°C)",
    "relative_humidity_2m": "Humidity (%)",
    "wind_speed_10m": "Wind speed (km/h)",
    "pm10": "PM10 (µg/m³)",
    "pm2_5": "PM2.5 (µg/m³)",
}
UNITS = {
    "temperature_2m": "°C",
    "relative_humidity_2m": "%",
    "wind_speed_10m": "km/h",
    "pm10": "µg/m³",
    "pm2_5": "µg/m³",
}
SCALES = {
    "temperature_2m": "RdYlBu_r",
    "relative_humidity_2m": "Blues",
    "wind_speed_10m": "Teal",
    "pm10": "YlOrBr",
    "pm2_5": "YlOrBr",
}
DEFAULT_TREND_CITIES = ["Tunis", "Sfax", "Sousse", "Gabes", "Bizerte"]
BLUE = "#1E5AA8"

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
.stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp label, .stApp li,
[data-testid="stMetricValue"], [data-testid="stMetricLabel"], .stTabs button {
    font-family: 'Plus Jakarta Sans', sans-serif;
}
.block-container {padding-top: 2.2rem; max-width: 1360px;}
#MainMenu, footer {visibility: hidden;}
.headline {font-size: 2.5rem; line-height: 1.15; font-weight: 800; color: #10233B;
           letter-spacing: -0.02em; margin: 0 0 0.5rem 0; max-width: 18em;}
.lede {font-size: 1.05rem; color: #4B607A; max-width: 44em; margin: 0 0 0.9rem 0;}
.status {font-size: 0.9rem; color: #4B607A; margin-bottom: 1.6rem;}
.dot {display: inline-block; width: 9px; height: 9px; border-radius: 50%;
      margin-right: 8px; background: #1F9D6B;}
.dot.stale {background: #D98A1D;}
[data-testid="stMetric"] {border-left: 3px solid #1E5AA8; padding: 2px 0 2px 16px;}
[data-testid="stMetricLabel"] p {color: #4B607A; font-size: 0.9rem; font-weight: 500;}
[data-testid="stMetricValue"] {color: #10233B; font-size: 2rem; font-weight: 700;}
.stTabs [data-baseweb="tab-list"] {gap: 28px; border-bottom: 1px solid #D5DFEC;}
.stTabs [data-baseweb="tab"] {padding: 10px 2px; font-weight: 600; font-size: 1rem;}
h3 {font-weight: 700; color: #10233B;}
.note {font-size: 0.85rem; color: #4B607A;}
</style>
""",
    unsafe_allow_html=True,
)


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


@st.cache_data
def to_csv(data: pd.DataFrame) -> bytes:
    return data.to_csv(index=False).encode("utf-8")


def latest_per_city(data: pd.DataFrame, now: pd.Timestamp) -> pd.DataFrame:
    """Most recent hour that is not in the future, for each city."""
    past = data[data["time"] <= now.floor("h")]
    source = past if not past.empty else data
    return source.sort_values("time").groupby("city").tail(1).reset_index(drop=True)


def extreme(frame: pd.DataFrame, col: str):
    sub = frame.dropna(subset=[col])
    return None if sub.empty else sub.loc[sub[col].idxmax()]


def kpi(slot, label: str, row, col: str) -> None:
    if row is None:
        slot.metric(label, "No data")
    else:
        slot.metric(f"{label}: {row['city']}", f"{row[col]:.1f} {UNITS[col]}")


def style(fig, height: int):
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(family="Plus Jakarta Sans, sans-serif", color="#10233B"),
    )
    return fig


try:
    df = load_data()
except Exception:
    st.error("Could not reach the database. It may be waking up, so refresh in a few seconds.")
    st.stop()

if df.empty:
    st.warning("The database is empty. Run the pipeline first.")
    st.stop()

now_tn = pd.Timestamp.now(tz="Africa/Tunis").tz_localize(None)  # times are stored in Tunis local time
current = latest_per_city(df, now_tn)
stale = df["time"].max() < now_tn
shown_hour = current["time"].max()

with st.sidebar:
    st.markdown("### Controls")
    metric = st.selectbox("Measure", list(LABELS), format_func=LABELS.get)
    all_cities = sorted(df["city"].unique())
    defaults = [c for c in DEFAULT_TREND_CITIES if c in all_cities]
    trend_cities = st.multiselect("Cities in the trend chart", all_cities, default=defaults)
    if st.button("Refresh data"):
        st.cache_data.clear()
        st.rerun()
    st.markdown(
        f"<p class='note'>{df['city'].nunique()} cities, {len(df):,} hourly records, "
        f"{df['time'].min():%d %b} to {df['time'].max():%d %b %Y}.</p>",
        unsafe_allow_html=True,
    )

status_text = (
    f"Data may be outdated. The newest record is from {df['time'].max():%d %b %Y, %H:%M}."
    if stale
    else f"Showing conditions for {shown_hour:%A %d %B, %H:%M} (Tunisia time)."
)
st.markdown(
    "<div class='headline'>Weather and air quality across Tunisia</div>"
    "<p class='lede'>Hourly temperature, humidity, wind and airborne dust for all 24 "
    "governorates, refreshed every day by an automated data pipeline.</p>"
    f"<div class='status'><span class='dot{' stale' if stale else ''}'></span>{status_text}</div>",
    unsafe_allow_html=True,
)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Governorates tracked", df["city"].nunique())
k2.metric("National average", f"{current['temperature_2m'].mean():.1f} °C")
kpi(k3, "Hottest", extreme(current, "temperature_2m"), "temperature_2m")
kpi(k4, "Highest PM10", extreme(current, "pm10"), "pm10")
kpi(k5, "Windiest", extreme(current, "wind_speed_10m"), "wind_speed_10m")

st.write("")
tab_overview, tab_trends, tab_data = st.tabs(["Overview", "Trends", "Data"])

with tab_overview:
    st.markdown(f"### {LABELS[metric]} right now")
    left, right = st.columns([3, 2], gap="large")

    coords = pd.DataFrame(
        [{"city": c, "lat": lat, "lon": lon} for c, (lat, lon) in CITIES.items()]
    )
    map_df = current.merge(coords, on="city")
    vals = map_df[metric]
    span = vals.max() - vals.min()
    if pd.isna(span) or span == 0:
        span = 1
    map_df["marker"] = (10 + 18 * (vals - vals.min()) / span).fillna(10)

    with left:
        fig_map = px.scatter_map(
            map_df,
            lat="lat",
            lon="lon",
            color=metric,
            size="marker",
            size_max=24,
            hover_name="city",
            hover_data={metric: ":.1f", "lat": False, "lon": False, "marker": False},
            labels={metric: LABELS[metric]},
            color_continuous_scale=SCALES[metric],
            map_style="carto-positron",
            center={"lat": 34.2, "lon": 9.6},
            zoom=5.2,
        )
        fig_map.update_layout(coloraxis_colorbar=dict(title="", thickness=12, len=0.6))
        st.plotly_chart(style(fig_map, 620))

    with right:
        ranking = current.dropna(subset=[metric])
        fig_rank = px.bar(
            ranking,
            x=metric,
            y="city",
            orientation="h",
            color=metric,
            color_continuous_scale=SCALES[metric],
            labels={metric: LABELS[metric], "city": ""},
        )
        fig_rank.update_coloraxes(showscale=False)
        fig_rank.update_layout(yaxis=dict(categoryorder="total ascending", tickfont=dict(size=12)))
        fig_rank.update_xaxes(showgrid=True, gridcolor="#E3EAF4")
        st.plotly_chart(style(fig_rank, 620))

with tab_trends:
    st.markdown(f"### {LABELS[metric]} over time")
    if trend_cities:
        view = df[df["city"].isin(trend_cities)]
        fig_line = px.line(
            view,
            x="time",
            y=metric,
            color="city",
            labels={metric: LABELS[metric], "time": "", "city": ""},
            color_discrete_sequence=px.colors.qualitative.Bold,
        )
        fig_line.update_traces(line=dict(width=2.4))
        fig_line.add_vline(x=now_tn.to_pydatetime(), line_dash="dot", line_color="#7B8CA5")
        fig_line.update_layout(hovermode="x unified", legend=dict(orientation="h", y=1.08, title=None))
        fig_line.update_yaxes(gridcolor="#E3EAF4")
        st.plotly_chart(style(fig_line, 480))
        st.markdown(
            "<p class='note'>The dotted line marks the current time. Values to its right are forecasts.</p>",
            unsafe_allow_html=True,
        )
    else:
        st.info("Choose at least one city in the sidebar to draw the chart.")

with tab_data:
    st.markdown("### Latest values by governorate")
    latest = current.set_index("city")[["time", *LABELS]]
    latest[list(LABELS)] = latest[list(LABELS)].round(1)
    st.dataframe(latest.rename(columns=LABELS))

    st.markdown("### Averages and peaks over the whole period")
    summary = df.groupby("city").agg(
        avg_temp=("temperature_2m", "mean"),
        avg_hum=("relative_humidity_2m", "mean"),
        avg_wind=("wind_speed_10m", "mean"),
        avg_pm10=("pm10", "mean"),
        max_pm10=("pm10", "max"),
        avg_pm25=("pm2_5", "mean"),
        max_pm25=("pm2_5", "max"),
    ).round(1)
    summary.columns = [
        "Avg temperature (°C)",
        "Avg humidity (%)",
        "Avg wind (km/h)",
        "Avg PM10 (µg/m³)",
        "Peak PM10 (µg/m³)",
        "Avg PM2.5 (µg/m³)",
        "Peak PM2.5 (µg/m³)",
    ]
    st.dataframe(summary)
    st.markdown(
        "<p class='note'>The period includes forecast hours, so averages mix past and predicted values.</p>",
        unsafe_allow_html=True,
    )
    st.download_button(
        "Download all data (CSV)",
        to_csv(df),
        file_name="tunisia_weather_air_quality.csv",
        mime="text/csv",
    )

st.divider()
st.markdown(
    "<p class='note'>Weather comes from Open-Meteo. Air quality comes from CAMS (Copernicus "
    "Atmosphere Monitoring Service) through Open-Meteo. All values are model-based forecasts, "
    "not station measurements, and city coordinates are approximate.</p>",
    unsafe_allow_html=True,
)