import logging
import traceback
from dagster import (
    DefaultSensorStatus,
    DagsterRunStatus,
    RunStatusSensorContext,
    run_status_sensor,
)
from core_provenance.utils import make_provenance_resource

logger = logging.getLogger("dagster.daemon.provenance")
logger.setLevel(logging.INFO)

@run_status_sensor(
    run_status=DagsterRunStatus.STARTED, default_status=DefaultSensorStatus.RUNNING
)
def provenance_start_sensor(context: RunStatusSensorContext):
    run = context.dagster_run
    logger.info(f"[DEBUG-PROV] Sensor STARTED acionado para run_id: {run.run_id}")
    try:
        prov = make_provenance_resource()

        stats = context.instance.get_run_stats(run.run_id)
        start_time = stats.start_time if stats else None

        prov.record_start(
            run_id=run.run_id,
            job_name=run.job_name,
            run_config=run.run_config,
            start_time=start_time,
        )

        prov.record_config_asset(run_id=run.run_id, run_config=run.run_config)

        context.log.info(f"Proveniência de execução iniciada para o run_id: {run.run_id}")
    except Exception as e:
        logger.error(f"[ERROR-PROV] Falha ao gravar proveniência (STARTED): {e}")
        logger.error(traceback.format_exc())
