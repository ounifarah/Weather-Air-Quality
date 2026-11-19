# Weather & Air Quality Pipeline

An ETL pipeline that collects hourly weather and air-quality forecasts for
Tunisian cities from Open-Meteo, cleans the data, and stores it in PostgreSQL.

## Project structure

```text
weather-pipeline/
├── dags/                  # Airflow DAGs
├── dashboard/             # Power BI files and exported images
├── sql/                   # Database schema
├── src/                   # Extract, transform, and load code
├── tests/                 # Automated tests
├── .env.example
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Quick start

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
docker compose up -d
```

Copy `.env.example` to `.env`, then run:

```powershell
python src\etl.py
```

The pipeline uses modeled forecast data from Open-Meteo, not measurements from
local weather stations.

