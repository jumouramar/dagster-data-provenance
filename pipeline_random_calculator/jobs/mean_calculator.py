from dagster import (
    define_asset_job,
)

mean_calculator_job = define_asset_job(
    name="mean_calculadora_job",
    selection=["provenance_asset", "random_numbers_asset", "mean_asset"],
)
