from dagster import Definitions

import settings
from pipeline_random_calculator import (
    ProvenanceResource,
    mean_asset,
    mean_calculator_job,
    provenance_asset,
    random_numbers_asset,
)
from weather_daily import (
    extract_weather,
    validate_weather,
    transform_weather,
    load_weather,
    weather_daily,
    weather_daily_schedule,
)

defs = Definitions(
    assets=[
        provenance_asset,
        random_numbers_asset,
        mean_asset,
        extract_weather,
        validate_weather,
        transform_weather,
        load_weather,
    ],
    jobs=[mean_calculator_job, weather_daily],
    schedules=[weather_daily_schedule],
    resources={
        "provenance": ProvenanceResource(
            host=settings.PROVENANCE_HOST,
            port=settings.PROVENANCE_PORT,
            dbname=settings.PROVENANCE_DB,
            user=settings.PROVENANCE_USER,
            password=settings.PROVENANCE_PASSWORD,
            environment=settings.ENVIRONMENT,
        ),
    },
)
