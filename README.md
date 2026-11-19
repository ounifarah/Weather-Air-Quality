# Tunisia Weather & Air Quality Monitor

A Streamlit website that displays hourly weather and air-quality forecasts for
Tunisia's 24 governorates. The application reads historical and forecast data
from PostgreSQL and presents current values, rankings, trends, a map, and a CSV
download.

## Website features

- Current temperature, humidity, wind speed, PM10, and PM2.5 values
- Coverage for all 24 Tunisian governorates
- Hottest, dustiest, and windiest locations
- A metric ranking chart
- A map of tracked governorates
- Configurable city trend charts
- Average measurements by governorate
- Downloadable CSV data

## Data sources

- Weather forecasts: Open-Meteo
- Air-quality forecasts: CAMS through Open-Meteo

The values are modeled forecasts, not measurements from local weather stations.
Governorate coordinates are approximate.

## Technologies

- Python
- Streamlit
- pandas
- PostgreSQL
- SQLAlchemy
- Docker Compose
- Apache Airflow
- GitHub Actions

## Project structure

```text
Weather & Air Quality/
├── dashboard/
│   └── app.py             # Streamlit website
├── dags/
│   └── weather_dag.py     # Daily Airflow DAG
├── sql/
│   └── create_tables.sql  # PostgreSQL table schema
├── src/
│   ├── cities.py          # 24 governorate coordinates
│   ├── etl.py             # ETL orchestration
│   ├── extract.py         # Open-Meteo API requests
│   ├── transform.py       # Data cleaning and validation
│   └── load.py            # PostgreSQL upsert
├── tests/
│   └── test_transform.py  # Transform tests
├── .env.example
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## How the pipeline works

1. The ETL reads each governorate and its coordinates from `src/cities.py`.
2. `extract.py` requests weather and air-quality forecast data from Open-Meteo.
3. `transform.py` combines and cleans the weather and air-quality records.
4. `load.py` inserts or updates hourly rows in PostgreSQL.
5. The Streamlit dashboard reads the records and shows the latest available hour.

The database table uses `(city, time)` as its primary key, so repeated pipeline
runs update existing measurements instead of creating duplicate rows.

## Run locally

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start PostgreSQL

```powershell
docker compose up -d
```

### 3. Configure the database connection

Copy `.env.example` to `.env`. The default local connection is:

```text
DATABASE_URL=postgresql+psycopg2://weather:weather@localhost:5432/weather
```

### 4. Load the data

```powershell
python src\etl.py
```

The ETL loads 48 forecast hours for each of the 24 governorates.

### 5. Start the website

```powershell
streamlit run dashboard\app.py
```

Open the local URL shown by Streamlit, usually
`http://localhost:8501`.

## Automated collection

The pipeline can be scheduled with the Airflow DAG in `dags/weather_dag.py`.
The DAG runs `run_etl()` every day and does not backfill previous schedules.

The ETL also contains retry and error handling for API requests and reports the
number of governorates successfully loaded.

## Run tests

```powershell
pytest
```

## Streamlit deployment

The dashboard supports a database connection through Streamlit secrets or the
`DATABASE_URL` environment variable.

For Streamlit Community Cloud, add this secret:

```toml
DATABASE_URL = "postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DATABASE"
```

The PostgreSQL database must already contain the `hourly_measurements` table and
data produced by the ETL pipeline.

