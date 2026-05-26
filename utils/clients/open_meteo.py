import requests


class OpenMeteoClient:
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    HOURLY_VARS = "temperature_2m,relativehumidity_2m,windspeed_10m,precipitation"

    def __init__(self, timezone: str = "America/Sao_Paulo", forecast_days: int = 1, timeout: int = 30):
        self.timezone = timezone
        self.forecast_days = forecast_days
        self.timeout = timeout

    def get_forecast(self, latitude: float, longitude: float) -> dict:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": self.HOURLY_VARS,
            "timezone": self.timezone,
            "forecast_days": self.forecast_days,
        }
        response = requests.get(self.BASE_URL, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()
