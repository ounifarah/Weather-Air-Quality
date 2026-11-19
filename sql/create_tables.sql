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

