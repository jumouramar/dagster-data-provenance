from dagster import asset
from pydantic import ValidationError

from pipeline_weather_rj.models.open_meteo import OpenMeteoForecastResponse


@asset(group_name="weather_rj")
def validate_weather_rj(context, extract_weather_rj: dict) -> dict:
    try:
        OpenMeteoForecastResponse.model_validate(extract_weather_rj["payload"])
    except ValidationError as e:
        raise ValueError(f"Rio de Janeiro: payload validation failed\n{e}") from e
    context.log.info("Rio de Janeiro: validation passed")
    return extract_weather_rj
