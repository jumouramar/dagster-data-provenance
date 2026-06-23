from dagster import asset
from pipelines.weather_daily.clients.postgres import PostgresClient
import settings

_db = PostgresClient(**settings.POSTGRES_CONN)


@asset(group_name="weather")
def load_weather(context, transform_weather: list) -> None:
    _db.upsert_batch(
        "etl", "weather_daily",
        transform_weather,
        conflict_columns=["city", "date"],
    )
    city = transform_weather[0]["city"] if transform_weather else "?"
    context.log.info(f"Loaded {len(transform_weather)} daily rows for {city}")
