from dagster import AssetExecutionContext, asset
from utils.clients.open_meteo import OpenMeteoClient

from pipeline_weather_rj.config import WeatherExtractConfig


@asset(group_name="weather")
def extract_weather(context: AssetExecutionContext, config: WeatherExtractConfig) -> dict:
    client = OpenMeteoClient()
    payload = client.get_forecast(latitude=config.latitude, longitude=config.longitude)
    hourly_count = len(payload.get(config.interval, {}).get("time", []))

    context.log.info(f"{config.city}: {hourly_count} {config.interval} records fetched")
    return {
        "city": config.city,
        "latitude": config.latitude,
        "longitude": config.longitude,
        "source": "open-meteo",
        "hourly_count": hourly_count,
        "payload": payload,
    }
