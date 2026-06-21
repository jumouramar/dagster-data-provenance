from dagster import asset
from pydantic import ValidationError

from weather_daily.models.open_meteo import OpenMeteoForecastResponse


@asset(group_name="weather")
def validate_weather(context, extract_weather: dict) -> dict:
    try:
        OpenMeteoForecastResponse.model_validate(extract_weather["payload"])
    except ValidationError as e:
        raise ValueError(f"{extract_weather['city']}: payload validation failed\n{e}") from e
    context.log.info(f"{extract_weather['city']}: validation passed")
    return extract_weather
