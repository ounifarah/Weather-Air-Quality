# Weather & Air Quality Data Pipeline: Step-by-Step Walkthrough

A beginner-friendly guide to building a real data engineering project: a program that collects weather and air-quality data for Tunisian cities every day, cleans it, stores it in a database, and shows it in a dashboard.

## 0. What you will build

In one sentence: **every day, your program asks a free weather service for data, cleans it, saves it in a database, and a dashboard shows it.**

```text
Open-Meteo API  ->  Python (clean)  ->  PostgreSQL  ->  Power BI dashboard
                         ^
                  Airflow runs it every day
```

**Everything is free:** Open-Meteo (no account, no key), Python, PostgreSQL, Docker, Airflow, Power BI Desktop, GitHub.

**The 6 stages (do them in order, one at a time):**

1. Get the data
2. Clean it
3. Save it in a database
4. Automate it
5. Show it in a dashboard
6. Polish it for your portfolio

**Time:** about 4 weeks at a few hours per week. After stage 3 you already have something real. After stage 4 it becomes a true pipeline.

**Rule:** at the end of each stage there is a "Done when" line. Do not move on until you can say yes.

## 1. Setup

### 1.1 For stages 1 and 2: Google Colab

Go to colab.research.google.com, sign in, click **New notebook**. Nothing to install.

### 1.2 For stages 3 to 6: your computer

Install these (all free):

- **Python 3.11 or newer** (python.org)
- **VS Code** (code editor)
- **Git** and a **GitHub** account
- **Docker Desktop** (runs the database and Airflow for you)
- **Power BI Desktop** (Windows only; if you do not use Windows, see stage 5 for an alternative)

Create a folder called `weather-pipeline` and open it in VS Code. Create a virtual environment in the terminal:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

pip install requests pandas sqlalchemy psycopg2-binary
```

### 1.3 Folder structure

```text
weather-pipeline/
  README.md
  docker-compose.yml
  requirements.txt
  sql/
    create_tables.sql
  src/
    extract.py
    transform.py
    load.py
    etl.py
  dags/
    weather_dag.py
  tests/
  dashboard/
```

Create a GitHub repo now and commit after every stage.

## 2. Stage 1: Get the data

### 2.1 What is an API?

An API is a website address that answers with **data** instead of a web page. You send a question (which city, which measures, which days) and it sends back the data.

### 2.2 Weather data

In Colab, run this:

```python
import requests
import pandas as pd

url = "https://api.open-meteo.com/v1/forecast"
params = {
    "latitude": 36.8065,
    "longitude": 10.1815,
    "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m",
    "timezone": "Africa/Tunis",
    "forecast_days": 2,
}

data = requests.get(url, params=params).json()
weather = pd.DataFrame(data["hourly"])
weather.head()
```

### 2.3 Air-quality data

```python
url_air = "https://air-quality-api.open-meteo.com/v1/air-quality"
params_air = {
    "latitude": 36.8065,
    "longitude": 10.1815,
    "hourly": "pm10,pm2_5",
    "timezone": "Africa/Tunis",
    "forecast_days": 2,
}

data_air = requests.get(url_air, params=params_air).json()
air = pd.DataFrame(data_air["hourly"])
air.head()
```

PM10 and PM2.5 measure tiny dust particles in the air. Higher means worse air.

### 2.4 Several cities

Put your cities in a dictionary so you can loop over them:

```python
CITIES = {
    "Tunis":   (36.8065, 10.1815),
    "Sfax":    (34.7406, 10.7603),
    "Sousse":  (35.8256, 10.6369),
    "Bizerte": (37.2744, 9.8739),
    "Gabes":   (33.8815, 10.0982),
}
```

The coordinates are approximate city centers. That is enough for this project.

### 2.5 Old data (optional, for a bigger dataset)

Open-Meteo also has an archive service with past weather. The address is `https://archive-api.open-meteo.com/v1/archive`, and it takes `start_date` and `end_date` (format `2024-01-01`). Check its documentation page for the exact variables. This lets you start with months of history instead of 2 days.

**Done when:** you can see a table of weather and a table of air quality for Tunis in your notebook.

## 3. Stage 2: Clean the data

Real data is never perfect. Cleaning means making it consistent and trustworthy.

### 3.1 Steps

1. Convert the `time` column from text to a real date and time.
2. Add a `city` column.
3. Join weather and air quality in one table (they share the `time` column).
4. Check for missing values.
5. Check that values are realistic (for example, humidity must be between 0 and 100).

### 3.2 Code

```python
def clean(weather, air, city):
    weather = weather.copy()
    air = air.copy()

    weather["time"] = pd.to_datetime(weather["time"])
    air["time"] = pd.to_datetime(air["time"])

    df = weather.merge(air, on="time", how="left")
    df.insert(0, "city", city)

    # checks
    print("missing values per column:")
    print(df.isna().sum())

    assert df["relative_humidity_2m"].dropna().between(0, 100).all(), "humidity out of range"
    assert df["temperature_2m"].dropna().between(-20, 60).all(), "temperature out of range"

    df = df.drop_duplicates(subset=["city", "time"])
    return df

df = clean(weather, air, "Tunis")
df.head()
```

The `assert` lines stop the program with a clear message if something looks wrong. This is a simple form of **data quality check**, and recruiters like seeing it.

**Done when:** you have one clean table with columns `city`, `time`, `temperature_2m`, `relative_humidity_2m`, `wind_speed_10m`, `pm10`, `pm2_5`.

## 4. Stage 3: Save it in a database

### 4.1 Why a database?

A notebook forgets everything when you close it. A database remembers, and a dashboard can read from it.

### 4.2 Start PostgreSQL with Docker

Create `docker-compose.yml` in your project folder:

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: weather
      POSTGRES_PASSWORD: weather
      POSTGRES_DB: weather
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

Then in the terminal:

```bash
docker compose up -d
```

You now have a real PostgreSQL database running on your computer.

The username and password above are only for practice on your own machine. When you share the project, keep real passwords out of GitHub (use a `.env` file and add it to `.gitignore`).

### 4.3 Create the table

File `sql/create_tables.sql`:

```sql
CREATE TABLE IF NOT EXISTS hourly_measurements (
    city                 TEXT      NOT NULL,
    time                 TIMESTAMP NOT NULL,
    temperature_2m       REAL,
    relative_humidity_2m REAL,
    wind_speed_10m       REAL,
    pm10                 REAL,
    pm2_5                REAL,
    PRIMARY KEY (city, time)
);
```

The **primary key** `(city, time)` means each city can have only one row per hour. This protects you from duplicates.

Run it with any SQL tool (DBeaver is free) connected to `localhost:5432`, database `weather`, user `weather`.

### 4.4 Load the data (without duplicates)

A good pipeline can run twice and give the same result. This is called being **idempotent**. We get it with an "upsert": insert the row, or update it if it already exists.

```python
from sqlalchemy import create_engine, text

engine = create_engine("postgresql+psycopg2://weather:weather@localhost:5432/weather")

UPSERT = text("""
INSERT INTO hourly_measurements
    (city, time, temperature_2m, relative_humidity_2m, wind_speed_10m, pm10, pm2_5)
VALUES
    (:city, :time, :temperature_2m, :relative_humidity_2m, :wind_speed_10m, :pm10, :pm2_5)
ON CONFLICT (city, time) DO UPDATE SET
    temperature_2m       = EXCLUDED.temperature_2m,
    relative_humidity_2m = EXCLUDED.relative_humidity_2m,
    wind_speed_10m       = EXCLUDED.wind_speed_10m,
    pm10                 = EXCLUDED.pm10,
    pm2_5                = EXCLUDED.pm2_5
""")

def load(df):
    rows = df.astype(object).where(df.notna(), None).to_dict("records")
    with engine.begin() as conn:
        conn.execute(UPSERT, rows)
    print(f"{len(rows)} rows saved")
```

Test it: run `load(df)` twice, then check with SQL:

```sql
SELECT city, COUNT(*) FROM hourly_measurements GROUP BY city;
```

The count must **not** double after the second run.

**Done when:** your table has rows for your cities and running the load twice creates no duplicates.

## 5. Stage 4: Automate it

Now turn your notebook code into a proper program, then make it run by itself.

### 5.1 Split the code into three functions

Move your code from the notebook into files in `src/`:

- `extract.py`: `extract(city, lat, lon)` calls both APIs and returns two tables
- `transform.py`: `clean(weather, air, city)` (the function from stage 2)
- `load.py`: `load(df)` (the function from stage 3)
- `etl.py`: ties them together

```python
# src/etl.py
from extract import extract
from transform import clean
from load import load

CITIES = {
    "Tunis": (36.8065, 10.1815),
    "Sfax": (34.7406, 10.7603),
    "Sousse": (35.8256, 10.6369),
    "Bizerte": (37.2744, 9.8739),
    "Gabes": (33.8815, 10.0982),
}

def run_etl():
    for city, (lat, lon) in CITIES.items():
        try:
            weather, air = extract(city, lat, lon)
            df = clean(weather, air, city)
            load(df)
        except Exception as e:
            print(f"{city} failed: {e}")

if __name__ == "__main__":
    run_etl()
```

Run it with `python src/etl.py`. If it works, you have a pipeline. It just does not run by itself yet.

The `try/except` means one failing city does not stop the others.

### 5.2 Schedule it with Airflow

Apache Airflow is the standard tool for scheduling data pipelines, so it is worth learning. It is also the heaviest part of this project, so go slowly.

1. Follow the **"Running Airflow in Docker"** page in the official Airflow documentation. It gives you a ready `docker-compose.yaml`. Use the official page for the exact current commands, because they change between versions.
2. Put your `src/` code where Airflow can import it (the official setup mounts a `dags` folder; place your code next to it).
3. Create `dags/weather_dag.py`:

```python
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from etl import run_etl

with DAG(
    dag_id="weather_daily",
    start_date=datetime(2026, 11, 16),
    schedule="@daily",
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
) as dag:
    PythonOperator(task_id="run_etl", python_callable=run_etl)
```

4. Open the Airflow web page (usually `localhost:8080`), turn the DAG on, and click **Trigger** to run it once.

**Inside Docker, `localhost` means the container itself.** To reach your Postgres from Airflow, put both in the same compose network and use the database service name (`db`) as the host instead of `localhost`. This is the most common beginner problem, so if the load fails, check the host name first.

### 5.3 Make it better (once it works)

- Split `run_etl` into three Airflow tasks: extract, transform, load
- Add logging instead of `print`
- Add an alert or a visible failure if an API call fails

**Alternative if Airflow is too heavy at first:** run `python src/etl.py` every day with Windows Task Scheduler or cron, finish the dashboard, and add Airflow afterward. A working small pipeline beats a broken big one.

**Done when:** the pipeline runs on its own each day and the table gets new rows.

## 6. Stage 5: Dashboard

### 6.1 Power BI

1. Open Power BI Desktop, click **Get data**, choose **PostgreSQL database**.
2. Server: `localhost`, database: `weather`. Enter the username and password.
3. Load `hourly_measurements`.

### 6.2 Pages to build

**Page 1: Overview**

- Cards: latest temperature, latest PM2.5, hottest city today
- City slicer (dropdown)

**Page 2: Trends**

- Line chart: temperature over time by city
- Line chart: PM2.5 over time by city

**Page 3: Comparison**

- Bar chart: average PM10 and PM2.5 by city
- Table: min, max and average by city

Useful measures to create in DAX:

```text
Avg Temp = AVERAGE(hourly_measurements[temperature_2m])
Max PM2.5 = MAX(hourly_measurements[pm2_5])
```

Keep it simple and readable: few colors, clear titles, one idea per chart.

### 6.3 If you do not use Windows

Power BI Desktop only runs on Windows. Two free alternatives that connect to Postgres: **Metabase** (runs in Docker) or a small **Streamlit** app in Python. Either works well for a portfolio.

**Done when:** the dashboard shows your database data and updates when you refresh.

## 7. Stage 6: Polish for your portfolio

### 7.1 Quality and tests

- Write 3 or 4 small tests: the cleaning function rejects impossible values, the load does not create duplicates, the city list is complete
- Move passwords to a `.env` file and out of the code
- Add a `requirements.txt`

### 7.2 README

Your README should include:

1. One-sentence description and a dashboard screenshot at the top
2. The architecture diagram (the arrow diagram from section 0 is fine, or draw it in draw.io)
3. Tools used and why
4. How to run it (short, copy-paste commands)
5. What the data is and its limits (for example: forecast and modeled data, not station measurements)
6. Ideas for next steps

### 7.3 Make it stand out (pick one or two)

- Add a **data quality report** table that records how many rows failed checks each day
- Add **dbt** to build clean summary tables (daily averages per city) with SQL
- Run the whole thing with **one command** using Docker Compose
- Add **GitHub Actions** to run your tests on every push

### 7.4 CV bullets (fill in real numbers only when true)

- Built an automated ETL pipeline ingesting hourly weather and air-quality data for 5 Tunisian cities from a public API into PostgreSQL, orchestrated with Apache Airflow
- Designed an idempotent loading process with upserts and data-quality checks
- Delivered a Power BI dashboard for temperature and air-quality trends

## 8. Weekly plan

| Week | Do | Done when |
| --- | --- | --- |
| 1 | Setup, stage 1 and 2 in Colab | Clean table for 5 cities |
| 2 | Stage 3: Docker, Postgres, upsert | No duplicates after two runs |
| 3 | Stage 4: split code, run ETL script, then Airflow | DAG runs and adds rows |
| 4 | Stage 5 and 6: dashboard, README, GitHub | Public repo with screenshots |

## 9. Common problems and fixes

- **API returns an error or empty data:** print the response and read the message; check that the variable names match the Open-Meteo documentation exactly.
- **Cannot connect to Postgres:** is Docker running? Did you run `docker compose up -d`? Check the port, user and password.
- **Airflow cannot reach the database:** use the service name `db`, not `localhost`.
- **Duplicate rows:** the primary key or the upsert is missing.
- **Time looks shifted by hours:** keep the `timezone` parameter the same everywhere.
- **Everything feels too big:** go back to the "Done when" line of the current stage and only do that.

## 10. Resources

- Open-Meteo documentation (weather, air quality and archive APIs)
- Official Apache Airflow documentation: "Running Airflow in Docker"
- PostgreSQL tutorial (postgresqltutorial.com)
- Power BI documentation for connecting to PostgreSQL

Start with stage 1 today. When something fails, copy the full error message and ask for help. Errors are a normal part of the work.
