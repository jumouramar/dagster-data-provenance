import inspect
import os
import logging
import traceback
from dagster import (
    DagsterEventType,
    DefaultSensorStatus,
    DagsterRunStatus,
    RunStatusSensorContext,
    run_status_sensor,
)
from core_provenance.resources.provenance import ProvenanceResource

logger = logging.getLogger("dagster.daemon.provenance")
logger.setLevel(logging.INFO)


def _get_source_from_assets_def(assets_def) -> str | None:
    try:
        return inspect.getsource(assets_def.op.compute_fn.decorated_fn)
    except Exception:
        pass
    try:
        return inspect.getsource(assets_def.op.compute_fn)
    except Exception:
        return None


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
    run_status=DagsterRunStatus.STARTED, default_status=DefaultSensorStatus.RUNNING
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
            start_time=start_time,
        )

        record_config_asset(
            prov=prov,
            run_id=run.run_id,
            run_config=run.run_config,
        )

        context.log.info(
            f"Proveniência de execução iniciada para o run_id: {run.run_id}"
        )
    except Exception as e:
        logger.error(f"[ERROR-PROV] Falha ao gravar proveniência (STARTED): {e}")
        logger.error(traceback.format_exc())


@run_status_sensor(
    run_status=DagsterRunStatus.SUCCESS, default_status=DefaultSensorStatus.RUNNING
)
def provenance_success_sensor(context: RunStatusSensorContext):
    run = context.dagster_run
    logger.info(f"[DEBUG-PROV] Sensor SUCCESS acionado para run_id: {run.run_id}")
    try:
        prov = get_provenance_resource()

        stats = context.instance.get_run_stats(run.run_id)
        start_time = stats.start_time if stats else None
        end_time = stats.end_time if stats else None

        prov.record_success(run_id=run.run_id, start_time=start_time, end_time=end_time)

        # Fallback: ASSET_MATERIALIZATION é emitido para TODOS os assets,
        # inclusive os com -> None onde o IOManager não é chamado (sem HANDLED_OUTPUT).
        # ON CONFLICT DO NOTHING preserva dados do IOManager (com return_value).
        key_to_def: dict[str, tuple] = {}
        try:
            for asset_key, assets_def in context.repository_def.assets_defs_by_key.items():
                key_to_def[asset_key.to_user_string()] = (assets_def, asset_key)
        except Exception as exc:
            logger.warning(f"[PROV] Não foi possível construir mapa de assets: {exc}")

        mat_logs = context.instance.all_logs(
            run.run_id, of_type=DagsterEventType.ASSET_MATERIALIZATION
        )
        logger.info(f"[PROV] {len(mat_logs)} eventos ASSET_MATERIALIZATION para run {run.run_id}")

        for log in mat_logs:
            ev = log.dagster_event
            if not ev or not ev.asset_key:
                continue

            key_str = ev.asset_key.to_user_string()
            upstream_assets: list[str] = []
            asset_code = None

            entry = key_to_def.get(key_str)
            if entry:
                assets_def, asset_key_obj = entry
                try:
                    upstream_assets = [
                        d.to_user_string()
                        for d in (assets_def.asset_deps.get(asset_key_obj) or set())
                    ]
                except Exception:
                    pass
                asset_code = _get_source_from_assets_def(assets_def)

            try:
                prov.record_asset_materialization_fallback(
                    run_id=run.run_id,
                    asset_key=key_str,
                    asset_code=asset_code,
                    return_type="NoneType",
                    upstream_assets=upstream_assets,
                    finished_at=log.timestamp,
                )
            except Exception as e:
                logger.warning(f"[PROV] Fallback para {key_str} falhou: {e}")

        context.log.info(
            f"Proveniência de execução concluída com sucesso para o run_id: {run.run_id}"
        )
    except Exception as e:
        logger.error(f"[ERROR-PROV] Falha ao gravar proveniência (SUCCESS): {e}")
        logger.error(traceback.format_exc())


@run_status_sensor(
    run_status=DagsterRunStatus.FAILURE, default_status=DefaultSensorStatus.RUNNING
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

        context.log.info(
            f"Proveniência de falha registrada para o run_id: {run.run_id}"
        )
    except Exception as e:
        logger.error(f"[ERROR-PROV] Falha ao gravar proveniência (FAILURE): {e}")
        logger.error(traceback.format_exc())

def record_config_asset(prov: ProvenanceResource, run_id: str, run_config: dict):
    if not run_config:
        return

    def _filter(obj):
        if isinstance(obj, dict):
            out = {}
            for k in sorted(obj.keys()):
                kl = k.lower()
                if any(s in kl for s in ("pass", "secret", "token", "key", "cred")):
                    continue
                out[k] = _filter(obj[k])
            return out

        if isinstance(obj, list):
            return [_filter(x) for x in obj]

        return obj

    prov.record_asset_output(
        run_id=run_id,
        asset_key="config",
        asset_code=None,
        return_value=_filter(run_config),
        return_type="RunConfig",
        upstream_assets=[],
    )