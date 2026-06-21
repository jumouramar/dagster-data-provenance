import os

from dagster import Definitions

from pipeline_random_calculator import (
    ProvenanceResource,
    mean_asset,
    mean_calculator_job,
    provenance_asset,
    random_numbers_asset,
)

defs = Definitions(
    assets=[provenance_asset, random_numbers_asset, mean_asset],
    jobs=[mean_calculator_job],
    resources={
        "provenance": ProvenanceResource(
            host=os.getenv("PROVENANCE_HOST"),
            port=int(os.getenv("PROVENANCE_PORT")),
            dbname=os.getenv("PROVENANCE_DB"),
            user=os.getenv("PROVENANCE_USER"),
            password=os.getenv("PROVENANCE_PASSWORD"),
            environment=os.getenv("ENVIRONMENT"),
        ),
    },
)
