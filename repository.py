from dagster import Definitions

import settings
from pipeline_random_calculator import (
    ProvenanceResource,
    mean_asset,
    mean_calculator_job,
    provenance_asset,
    random_numbers_asset,
)
from pipeline_weather_rj import (
    extract_weather_rj,
    validate_weather_rj,
    transform_weather_rj,
    load_weather_rj,
    weather_rj_job,
    weather_rj_daily_schedule,
)

defs = Definitions(
    assets=[
        provenance_asset,
        random_numbers_asset,
        mean_asset,
        extract_weather_rj,
        validate_weather_rj,
        transform_weather_rj,
        load_weather_rj,
    ],
    jobs=[mean_calculator_job, weather_rj_job],
    schedules=[weather_rj_daily_schedule],
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
