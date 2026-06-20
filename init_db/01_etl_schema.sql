CREATE SCHEMA IF NOT EXISTS etl;

CREATE TABLE IF NOT EXISTS etl.weather_daily (
    id               SERIAL PRIMARY KEY,
    city             TEXT NOT NULL,
    date             DATE NOT NULL,
    temp_max_c       FLOAT,
    temp_min_c       FLOAT,
    temp_mean_c      FLOAT,
    humidity_mean    FLOAT,
    wind_max_kmh     FLOAT,
    precipitation_mm FLOAT,
    UNIQUE (city, date)
);
