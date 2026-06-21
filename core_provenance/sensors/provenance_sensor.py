import os
import logging
import traceback
from dagster import (
    run_status_sensor, 
    DagsterRunStatus, 
    RunStatusSensorContext, 
    DefaultSensorStatus
)
from core_provenance.resources.provenance import ProvenanceResource

logger = logging.getLogger("dagster.daemon.provenance")
logger.setLevel(logging.INFO)

def get_provenance_resource() -> ProvenanceResource:
    return ProvenanceResource(
        host=os.getenv("PROVENANCE_HOST", "postgres"),
        port=int(os.getenv("PROVENANCE_PORT", "5432")),
        dbname=os.getenv("PROVENANCE_DB", "dagster"),
        user=os.getenv("PROVENANCE_USER", "dagster"),
        password=os.getenv("PROVENANCE_PASSWORD", "dagster"),
        environment=os.getenv("ENVIRONMENT", "development"),
    )

@run_status_sensor(
    run_status=DagsterRunStatus.STARTED,
    default_status=DefaultSensorStatus.RUNNING
)
def provenance_start_sensor(context: RunStatusSensorContext):
    run = context.dagster_run
    logger.info(f"[DEBUG-PROV] Sensor STARTED acionado para run_id: {run.run_id}")
    try:
        prov = get_provenance_resource()
        
        # Busca os timestamps reais da run via instância do Dagster
        stats = context.instance.get_run_stats(run.run_id)
        start_time = stats.start_time if stats else None
        
        prov.record_start(
            run_id=run.run_id, 
            job_name=run.job_name, 
            run_config=run.run_config,
            start_time=start_time
        )
        
        context.log.info(f"Proveniência de execução iniciada para o run_id: {run.run_id}")
    except Exception as e:
        logger.error(f"[ERROR-PROV] Falha ao gravar proveniência (STARTED): {e}")
        logger.error(traceback.format_exc())

@run_status_sensor(
    run_status=DagsterRunStatus.SUCCESS,
    default_status=DefaultSensorStatus.RUNNING
)
def provenance_success_sensor(context: RunStatusSensorContext):
    run = context.dagster_run
    logger.info(f"[DEBUG-PROV] Sensor SUCCESS acionado para run_id: {run.run_id}")
    try:
        prov = get_provenance_resource()
        
        stats = context.instance.get_run_stats(run.run_id)
        start_time = stats.start_time if stats else None
        end_time = stats.end_time if stats else None
        
        prov.record_success(
            run_id=run.run_id,
            start_time=start_time,
            end_time=end_time
        )
        
        context.log.info(f"Proveniência de execução concluída com sucesso para o run_id: {run.run_id}")
    except Exception as e:
        logger.error(f"[ERROR-PROV] Falha ao gravar proveniência (SUCCESS): {e}")
        logger.error(traceback.format_exc())

@run_status_sensor(
    run_status=DagsterRunStatus.FAILURE,
    default_status=DefaultSensorStatus.RUNNING
)
def provenance_failure_sensor(context: RunStatusSensorContext):
    run = context.dagster_run
    logger.info(f"[DEBUG-PROV] Sensor FAILURE acionado para run_id: {run.run_id}")
    try:
        prov = get_provenance_resource()
        
        stats = context.instance.get_run_stats(run.run_id)
        start_time = stats.start_time if stats else None
        end_time = stats.end_time if stats else None
        
        error_message = None
        if hasattr(context, "failure_event") and context.failure_event and context.failure_event.message:
            error_message = context.failure_event.message
            
        prov.record_failure(
            run_id=run.run_id, 
            error_message=error_message,
            start_time=start_time,
            end_time=end_time
        )
        
        context.log.info(f"Proveniência de falha registrada para o run_id: {run.run_id}")
    except Exception as e:
        logger.error(f"[ERROR-PROV] Falha ao gravar proveniência (FAILURE): {e}")
        logger.error(traceback.format_exc())