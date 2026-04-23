import numpy as np
from dagster import AssetExecutionContext, asset


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
