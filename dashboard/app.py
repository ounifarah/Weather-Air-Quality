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
    "relative_humidity_2m": "Tealgrn",
    "wind_speed_10m": "Viridis",
    "pm10": "YlOrRd",
    "pm2_5": "YlOrRd",
}
DISPLAY_NAMES = {"Gabes": "Gabès", "Beja": "Béja", "Medenine": "Médenine", "Kebili": "Kébili"}
DEFAULT_TREND_CITIES = ["Tunis", "Sfax", "Sousse", "Gabes", "Bizerte"]

ICONS = {
    "grid": '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>'
    '<rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
    "thermo": '<path d="M14 4v10.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z"/>',
    "pin": '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    "cloud": '<path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/>',
    "wind": '<path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2"/><path d="M9.6 4.6A2 2 0 1 1 11 8H2"/>'
    '<path d="M12.6 19.4A2 2 0 1 0 14 16H2"/>',
}

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
.stApp {background: #0A1420;}
[data-testid="stSidebar"] {background: #0E1B2B; border-right: 1px solid #1B2D44;}
[data-testid="stHeader"] {background: transparent;}
.stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp label, .stApp li, .stTabs button,
.card, .headline, .lede, .status {font-family: 'Plus Jakarta Sans', sans-serif;}
.block-container {padding-top: 2.2rem; max-width: 1360px;}
#MainMenu, footer {visibility: hidden;}
.headline {font-size: 2.5rem; line-height: 1.15; font-weight: 800; color: #F1F6FC;
           letter-spacing: -0.02em; margin: 0 0 0.5rem 0; max-width: 18em;}
.lede {font-size: 1.05rem; color: #93A7C2; max-width: 44em; margin: 0 0 0.9rem 0;}
.status {font-size: 0.9rem; color: #93A7C2; margin-bottom: 1.6rem;}
.dot {display: inline-block; width: 9px; height: 9px; border-radius: 50%;
      margin-right: 8px; background: #2BC48A;}
.dot.stale {background: #F2A93B;}
.cards {display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 16px;}
.card {background: #101E30; border: 1px solid #1E3148; border-radius: 12px; padding: 18px 20px 16px;}
.card-label {display: flex; align-items: center; gap: 8px; font-size: 0.78rem; font-weight: 600;
             letter-spacing: 0.06em; text-transform: uppercase; color: #8CA2BF;}
.card-label svg {width: 15px; height: 15px; stroke: #4FB3E8; fill: none; stroke-width: 2;
                 stroke-linecap: round; stroke-linejoin: round;}
.card-title {font-size: 1.45rem; font-weight: 700; color: #F1F6FC; margin: 10px 0 4px;}
.card-value {font-size: 2.6rem; font-weight: 800; color: #F1F6FC; line-height: 1.1;}
.card-unit {font-size: 1.2rem; font-weight: 600; color: #7F95B2; margin-left: 6px;}
.card-foot {font-size: 0.85rem; color: #7F95B2; margin-top: 8px;}
.stTabs [data-baseweb="tab-list"] {gap: 28px; border-bottom: 1px solid #1E3148;}
.stTabs [data-baseweb="tab"] {padding: 10px 2px; font-weight: 600; font-size: 1rem;}
h3 {font-weight: 700; color: #F1F6FC;}
.note {font-size: 0.85rem; color: #7F95B2;}
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


def card(icon: str, label: str, title: str, value: str, unit: str, foot: str) -> str:
    return (
        "<div class='card'>"
        f"<div class='card-label'><svg viewBox='0 0 24 24'>{ICONS[icon]}</svg>{label}</div>"
        f"<div class='card-title'>{title}</div>"
        f"<div class='card-value'>{value}<span class='card-unit'>{unit}</span></div>"
        f"<div class='card-foot'>{foot}</div>"
        "</div>"
    )


def extreme_card(icon: str, label: str, row, col: str, foot: str) -> str:
    if row is None:
        return card(icon, label, "No data", "—", "", foot)
    name = DISPLAY_NAMES.get(row["city"], row["city"])
    return card(icon, label, name, f"{row[col]:.1f}", UNITS[col], foot)


def style(fig, height: int):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(family="Plus Jakarta Sans, sans-serif", color="#C9D6EA"),
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
    "governorates, refreshed every hour by an automated data pipeline</p>"
    f"<div class='status'><span class='dot{' stale' if stale else ''}'></span>{status_text}</div>",
    unsafe_allow_html=True,
)

cards = [
    card("grid", "Coverage", "Governorates", str(df["city"].nunique()), "cities", "Monitored hourly"),
    card("thermo", "National average", "Tunisia", f"{current['temperature_2m'].mean():.1f}", "°C",
         "Average of all governorates"),
    extreme_card("pin", "Hottest location", extreme(current, "temperature_2m"), "temperature_2m",
                 "Current temperature"),
    extreme_card("cloud", "Highest PM10", extreme(current, "pm10"), "pm10", "Airborne dust right now"),
    extreme_card("wind", "Windiest location", extreme(current, "wind_speed_10m"), "wind_speed_10m",
                 "Current wind speed"),
]
st.markdown(f"<div class='cards'>{''.join(cards)}</div>", unsafe_allow_html=True)

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
            map_style="carto-darkmatter",
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
        fig_rank.update_xaxes(showgrid=True, gridcolor="#1E3148")
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
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_line.update_traces(line=dict(width=2.4))
        fig_line.add_vline(x=now_tn.to_pydatetime(), line_dash="dot", line_color="#7F95B2")
        fig_line.update_layout(hovermode="x unified", legend=dict(orientation="h", y=1.08, title=None))
        fig_line.update_yaxes(gridcolor="#1E3148")
        fig_line.update_xaxes(gridcolor="#1E3148")
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
