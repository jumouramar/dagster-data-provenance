from dagster import Definitions

from pipeline_random_calculator import (
    mean_asset,
    mean_calculator_job,
    random_numbers_asset,
)

defs = Definitions(
    assets=[random_numbers_asset, mean_asset],
    jobs=[mean_calculator_job],
)
