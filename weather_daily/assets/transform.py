from dagster import asset

from weather_daily.src.transform_weather_daily import TransformWeatherDaily

_transformer = TransformWeatherDaily()


@asset(group_name="weather")
def transform_weather(context, validate_weather: dict) -> list[dict]:
    city = validate_weather["city"]
    daily = [
        {**row, "city": city}
        for row in _transformer.transform(validate_weather["payload"]["hourly"])
    ]
    for row in daily:
        context.log.info(
            f"{row['date']}: temp {row['temp_min_c']}–{row['temp_max_c']}°C, "
            f"humidity {row['humidity_min']}–{row['humidity_max']}%, "
            f"wind max {row['wind_max_kmh']} km/h, "
            f"precip {row['precipitation_mm']}mm ({row['precipitation_hours']}h)"
        )
    return daily
