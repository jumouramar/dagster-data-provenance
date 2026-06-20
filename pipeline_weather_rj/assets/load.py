from dagster import asset
from utils.clients.postgres import PostgresClient
import settings

_db = PostgresClient(**settings.POSTGRES_CONN)


@asset(group_name="weather")
def load_weather(context, transform_weather: dict) -> None:
    raw = transform_weather["raw"]
    daily = transform_weather["daily"]
    run_id = context.run_id

    [raw_id] = _db.insert_batch(
        "etl", "weather_raw",
        [{
            "city": raw["city"],
            "latitude": raw["latitude"],
            "longitude": raw["longitude"],
            "source": raw["source"],
            "hourly_count": raw["hourly_count"],
            "raw_payload": raw["payload"],
            "dagster_run_id": run_id,
        }],
        returning="id",
    )

    _db.insert_batch(
        "etl", "weather_daily",
        [{**row, "raw_id": raw_id, "city": raw["city"], "dagster_run_id": run_id}
         for row in daily],
    )

    context.log.info(f"Loaded raw_id={raw_id} + {len(daily)} daily rows for {raw['city']}")
