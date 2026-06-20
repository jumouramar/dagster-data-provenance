from dagster import asset
from utils.clients.postgres import PostgresClient
import settings

_db = PostgresClient(**settings.POSTGRES_CONN)


@asset(group_name="weather")
def load_weather(context, transform_weather: dict) -> None:
    raw = transform_weather["raw"]
    daily = transform_weather["daily"]

    _db.upsert_batch(
        "etl", "weather_daily",
        [{**row, "city": raw["city"]} for row in daily],
        conflict_columns=["city", "date"],
    )

    context.log.info(f"Loaded {len(daily)} daily rows for {raw['city']}")
