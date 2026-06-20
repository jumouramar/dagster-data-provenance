import json
import psycopg2
from dagster import asset

import settings

_DB = settings.POSTGRES_CONN


@asset(group_name="weather")
def load_weather(context, transform_weather: dict) -> None:
    """Inserts raw and daily weather data into PostgreSQL."""
    raw = transform_weather["raw"]
    daily = transform_weather["daily"]
    run_id = context.run_id

    conn = psycopg2.connect(**_DB)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO etl.weather_raw
                        (city, latitude, longitude, source, hourly_count, raw_payload, dagster_run_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        raw["city"],
                        raw["latitude"],
                        raw["longitude"],
                        raw["source"],
                        raw["hourly_count"],
                        json.dumps(raw["payload"]),
                        run_id,
                    ),
                )
                raw_id = cur.fetchone()[0]

                for row in daily:
                    cur.execute(
                        """
                        INSERT INTO etl.weather_daily
                            (raw_id, city, date, temp_max_c, temp_min_c, temp_mean_c,
                             humidity_mean, wind_max_kmh, precipitation_mm, dagster_run_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            raw_id,
                            raw["city"],
                            row["date"],
                            row["temp_max_c"],
                            row["temp_min_c"],
                            row["temp_mean_c"],
                            row["humidity_mean"],
                            row["wind_max_kmh"],
                            row["precipitation_mm"],
                            run_id,
                        ),
                    )

        context.log.info(
            f"Loaded raw_id={raw_id} + {len(daily)} daily rows for {raw['city']}"
        )
    finally:
        conn.close()
