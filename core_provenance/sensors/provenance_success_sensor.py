import logging
import traceback
from dagster import (
    DagsterEventType,
    DefaultSensorStatus,
    DagsterRunStatus,
    RunStatusSensorContext,
    run_status_sensor,
)
from core_provenance.utils import get_asset_source, make_provenance_resource

logger = logging.getLogger("dagster.daemon.provenance")
logger.setLevel(logging.INFO)


@run_status_sensor(
    run_status=DagsterRunStatus.SUCCESS, default_status=DefaultSensorStatus.RUNNING
)
def provenance_success_sensor(context: RunStatusSensorContext):
    run = context.dagster_run
    logger.info(f"[DEBUG-PROV] Sensor SUCCESS acionado para run_id: {run.run_id}")
    try:
        prov = make_provenance_resource()

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
                asset_code = get_asset_source(assets_def)

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