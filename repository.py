from dagster import Definitions, load_assets_from_modules

# 1. Importe os módulos de assets (basta importar o arquivo/módulo, não as funções isoladas)
from pipeline_random_calculator.assets import mean_calculator as random_assets

# 2. Importe os jobs
from pipeline_random_calculator.jobs.mean_calculator import mean_calculator_job

# 3. Importe a infraestrutura global de proveniência da nova pasta
from core_provenance.sensors.provenance_sensor import (
    provenance_start_sensor,
    provenance_success_sensor,
    provenance_failure_sensor,
    get_provenance_resource
)

# 4. Carregue todos os assets de uma vez
all_assets = load_assets_from_modules([
    random_assets,
])

# 5. Agrupe todos os jobs
all_jobs = [
    mean_calculator_job,
]

# 6. O objeto Definitions aplica os sensores globais a todos os jobs carregados
defs = Definitions(
    assets=all_assets,
    jobs=all_jobs,
    sensors=[
        provenance_start_sensor, 
        provenance_success_sensor, 
        provenance_failure_sensor
    ],
    resources={
        "provenance": get_provenance_resource(),
    },
)