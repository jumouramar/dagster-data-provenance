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
    run_status=DagsterRunStatus.FAILURE, default_status=DefaultSensorStatus.RUNNING
)
def provenance_failure_sensor(context: RunStatusSensorContext):
    run = context.dagster_run
    logger.info(f"[DEBUG-PROV] Sensor FAILURE acionado para run_id: {run.run_id}")
    try:
        prov = make_provenance_resource()

        stats = context.instance.get_run_stats(run.run_id)
        start_time = stats.start_time if stats else None
        end_time = stats.end_time if stats else None

        error_message = None
        if (
            hasattr(context, "failure_event")
            and context.failure_event
            and context.failure_event.message
        ):
            error_message = context.failure_event.message

        prov.record_failure(
            run_id=run.run_id,
            error_message=error_message,
            start_time=start_time,
            end_time=end_time,
        )

        context.log.info(f"Proveniência de falha registrada para o run_id: {run.run_id}")
    except Exception as e:
        logger.error(f"[ERROR-PROV] Falha ao gravar proveniência (FAILURE): {e}")
        logger.error(traceback.format_exc())