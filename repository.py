import os

from dagster import Definitions, load_assets_from_modules

from pipeline_random_calculator.assets import mean_calculator as random_assets
from pipeline_random_calculator.jobs.mean_calculator import mean_calculator_job

from weather_daily.assets.extract import extract_weather
from weather_daily.assets.validate import validate_weather
from weather_daily.assets.transform import transform_weather
from weather_daily.assets.load import load_weather
from weather_daily.jobs.weather_rj import weather_daily, weather_daily_schedule

from core_provenance.sensors.provenance_sensor import (
    provenance_start_sensor,
    provenance_success_sensor,
    provenance_failure_sensor,
    get_provenance_resource,
)
from core_provenance.resources.provenance_io_manager import ProvenanceIOManager

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
        "provenance": get_provenance_resource(),
        "io_manager": ProvenanceIOManager(
            host=os.getenv("PROVENANCE_HOST", "postgres"),
            port=int(os.getenv("PROVENANCE_PORT", "5432")),
            dbname=os.getenv("PROVENANCE_DB", "dagster"),
            user=os.getenv("PROVENANCE_USER", "dagster"),
            password=os.getenv("PROVENANCE_PASSWORD", "dagster"),
            environment=os.getenv("ENVIRONMENT", "development"),
        ),
    },
)
