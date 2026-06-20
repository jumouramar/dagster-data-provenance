CREATE SCHEMA IF NOT EXISTS etl;

CREATE TABLE IF NOT EXISTS etl.weather_daily (
    id                  SERIAL PRIMARY KEY,
    city                TEXT NOT NULL,
    date                DATE NOT NULL,
    temp_max_c          FLOAT,
    temp_min_c          FLOAT,
    temp_mean_c         FLOAT,
    humidity_min        FLOAT,
    humidity_mean       FLOAT,
    humidity_max        FLOAT,
    wind_mean_kmh       FLOAT,
    wind_max_kmh        FLOAT,
    precipitation_mm    FLOAT,
    precipitation_hours INT,
    UNIQUE (city, date)
);
