from dagster import asset
from utils.clients.open_meteo import OpenMeteoClient

_RJ = {"name": "Rio de Janeiro", "latitude": -22.9068, "longitude": -43.1729}


@asset(group_name="weather_rj")
def extract_weather_rj(context) -> dict:
    client = OpenMeteoClient()
    payload = client.get_forecast(latitude=_RJ["latitude"], longitude=_RJ["longitude"])
    hours = len(payload.get("hourly", {}).get("time", []))

    context.log.info(f"Rio de Janeiro: {hours} hourly records fetched")
    return {
        "city": _RJ["name"],
        "latitude": _RJ["latitude"],
        "longitude": _RJ["longitude"],
        "payload": payload,
    }
