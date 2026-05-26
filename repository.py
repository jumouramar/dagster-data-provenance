from dagster import Definitions

from pipeline_random_calculator import (
    mean_asset,
    mean_calculator_job,
    random_numbers_asset,
)
from pipeline_weather_rj import (
    extract_weather_rj,
    weather_rj_job,
    weather_rj_daily_schedule,
)

defs = Definitions(
    assets=[random_numbers_asset, mean_asset, extract_weather_rj],
    jobs=[mean_calculator_job, weather_rj_job],
    schedules=[weather_rj_daily_schedule],
)
