from dagster import Config


class WeatherExtractConfig(Config):
    city: str
    latitude: float
    longitude: float
    interval: str = "hourly"
