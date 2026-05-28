CREATE SCHEMA IF NOT EXISTS etl;

CREATE TABLE IF NOT EXISTS etl.weather_raw (
    id              SERIAL PRIMARY KEY,
    city            TEXT NOT NULL,
    latitude        FLOAT NOT NULL,
    longitude       FLOAT NOT NULL,
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    api_url         TEXT NOT NULL,
    raw_payload     JSONB NOT NULL,
    dagster_run_id  TEXT
);

CREATE TABLE IF NOT EXISTS etl.weather_transformed (
    id               SERIAL PRIMARY KEY,
    raw_id           INT REFERENCES etl.weather_raw(id),
    city             TEXT NOT NULL,
    date             DATE NOT NULL,
    temp_max_c       FLOAT,
    temp_min_c       FLOAT,
    temp_mean_c      FLOAT,
    humidity_mean    FLOAT,
    wind_max_kmh     FLOAT,
    precipitation_mm FLOAT,
    transformed_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    dagster_run_id   TEXT
);
