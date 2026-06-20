from dagster import asset

from pipeline_weather_rj.src.transform_weather_daily import TransformWeatherDaily

_transformer = TransformWeatherDaily()


@asset(group_name="weather")
def transform_weather(context, validate_weather: dict) -> dict:
    daily = _transformer.transform(validate_weather["payload"]["hourly"])

    for row in daily:
        context.log.info(
            f"{row['date']}: temp {row['temp_min_c']}–{row['temp_max_c']}°C, "
            f"humidity {row['humidity_min']}–{row['humidity_max']}%, "
            f"wind max {row['wind_max_kmh']} km/h, "
            f"precip {row['precipitation_mm']}mm ({row['precipitation_hours']}h)"
        )

    return {"raw": validate_weather, "daily": daily}
