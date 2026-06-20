from dagster import RunConfig, ScheduleDefinition, define_asset_job

from weather_daily.config import WeatherExtractConfig

_RIO_DE_JANEIRO = WeatherExtractConfig(
    city="Rio de Janeiro",
    latitude=-22.9068,
    longitude=-43.1729,
    interval="hourly",
)

weather_daily = define_asset_job(
    name="weather_daily",
    selection=["extract_weather", "validate_weather", "transform_weather", "load_weather"],
    config=RunConfig(ops={"extract_weather": _RIO_DE_JANEIRO}),
)

weather_daily_schedule = ScheduleDefinition(
    job=weather_daily,
    cron_schedule="0 6 * * *",
)
