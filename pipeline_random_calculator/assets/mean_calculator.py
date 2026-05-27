import numpy as np
from dagster import AssetExecutionContext, asset

from pipeline_random_calculator.resources import ProvenanceResource


@asset
def provenance_asset(
    context: AssetExecutionContext, provenance: ProvenanceResource
) -> str:
    run_id = context.run_id
    provenance.record_start(run_id)
    context.log.info(f"Proveniência de execução iniciada para o run_id: {run_id}")
    return run_id


@asset
def random_numbers_asset(context: AssetExecutionContext) -> list:
    numbers = [round(np.random.uniform(10.0, 50.0), 2) for _ in range(10)]
    context.log.info(f"Dados gerados (10): {numbers}")
    return numbers


@asset
def mean_asset(context: AssetExecutionContext, random_numbers_asset: list) -> float:
    average = round(float(np.mean(random_numbers_asset)), 4)
    context.log.info(f"Média = {average}")
    return average
