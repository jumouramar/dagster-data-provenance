import requests


class OpenMeteoClient:
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    HOURLY_VARS = "temperature_2m,relativehumidity_2m,windspeed_10m,precipitation"

    def __init__(self, timezone: str = "America/Sao_Paulo", timeout: int = 30):
        self.timezone = timezone
        self.timeout = timeout

    def get_forecast_by_date(self, latitude: float, longitude: float, date: str) -> dict:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": self.HOURLY_VARS,
            "timezone": self.timezone,
            "start_date": date,
            "end_date": date,
        }
        response = requests.get(self.BASE_URL, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()
