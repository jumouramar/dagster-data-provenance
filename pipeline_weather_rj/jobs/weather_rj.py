from dagster import define_asset_job, ScheduleDefinition

weather_rj_job = define_asset_job(
    name="weather_rj_job",
    selection=["extract_weather_rj", "validate_weather_rj"],
)

weather_rj_daily_schedule = ScheduleDefinition(
    job=weather_rj_job,
    cron_schedule="0 6 * * *",
)
