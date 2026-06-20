from dagster import RunConfig, ScheduleDefinition, define_asset_job

from pipeline_weather_rj.config import WeatherExtractConfig

_RIO_DE_JANEIRO = WeatherExtractConfig(
    city="Rio de Janeiro",
    latitude=-22.9068,
    longitude=-43.1729,
    interval="hourly",
)

weather_rj_job = define_asset_job(
    name="weather_rj_job",
    selection=["extract_weather", "validate_weather", "transform_weather", "load_weather"],
    config=RunConfig(ops={"extract_weather": _RIO_DE_JANEIRO}),
)

weather_rj_daily_schedule = ScheduleDefinition(
    job=weather_rj_job,
    cron_schedule="0 6 * * *",
)
