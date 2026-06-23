from dagster import Definitions, load_assets_from_modules

from pipeline_random_calculator.assets import mean_calculator as random_assets
from pipeline_random_calculator.jobs.mean_calculator import mean_calculator_job

from weather_daily.assets.extract import extract_weather
from weather_daily.assets.validate import validate_weather
from weather_daily.assets.transform import transform_weather
from weather_daily.assets.load import load_weather
from weather_daily.jobs.weather_rj import weather_daily, weather_daily_schedule

from core_provenance.sensors import (
    provenance_start_sensor,
    provenance_success_sensor,
    provenance_failure_sensor,
)
from core_provenance.utils import make_provenance_resource, make_provenance_io_manager

defs = Definitions(
    assets=[
        *load_assets_from_modules([random_assets]),
        extract_weather,
        validate_weather,
        transform_weather,
        load_weather,
    ],
    jobs=[mean_calculator_job, weather_daily],
    schedules=[weather_daily_schedule],
    sensors=[
        provenance_start_sensor,
        provenance_success_sensor,
        provenance_failure_sensor,
    ],
    resources={
        "provenance": make_provenance_resource(),
        "io_manager": make_provenance_io_manager(),
    },
)
