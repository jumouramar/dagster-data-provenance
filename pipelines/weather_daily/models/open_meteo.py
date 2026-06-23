from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field

Temperature = Annotated[Optional[float], Field(ge=-20.0, le=60.0)]
Humidity = Annotated[Optional[float], Field(ge=0.0, le=100.0)]
WindSpeed = Annotated[Optional[float], Field(ge=0.0)]
Precipitation = Annotated[Optional[float], Field(ge=0.0)]


class HourlyUnits(BaseModel):
    time: str
    temperature_2m: str
    relativehumidity_2m: str
    windspeed_10m: str
    precipitation: str


class HourlyData(BaseModel):
    time: list[str]
    temperature_2m: list[Temperature]
    relativehumidity_2m: list[Humidity]
    windspeed_10m: list[WindSpeed]
    precipitation: list[Precipitation]


class OpenMeteoForecastResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    latitude: float
    longitude: float
    generationtime_ms: float
    utc_offset_seconds: int
    timezone: str
    timezone_abbreviation: str
    elevation: float
    hourly_units: HourlyUnits
    hourly: HourlyData
