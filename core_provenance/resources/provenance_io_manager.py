import inspect
import json
from typing import Any

from dagster import ConfigurableIOManager, InputContext, OutputContext

from core_provenance.resources.provenance import ProvenanceResource

# Module-level store keyed by "{run_id}::{asset_key}" so it survives any
# Pydantic model re-instantiation that Dagster may do between steps.
_RUN_STORE: dict[str, Any] = {}


def _store_key(run_id: str, asset_key: str) -> str:
    return f"{run_id}::{asset_key}"


def _serialize(obj: Any) -> Any:
    try:
        return json.loads(json.dumps(obj, default=str))
    except Exception:
        return str(obj)


def _get_source(context: OutputContext) -> str | None:
    try:
        fn = context.op_def.compute_fn.decorated_fn
        return inspect.getsource(fn)
    except Exception:
        pass
    try:
        return inspect.getsource(context.op_def.compute_fn)
    except Exception:
        return None


def _get_upstreams(context: OutputContext) -> list[str]:
    try:
        fn = context.op_def.compute_fn.decorated_fn
        sig = inspect.signature(fn)
        return [p for p in sig.parameters if p != "context"]
    except Exception:
        return []


class ProvenanceIOManager(ConfigurableIOManager):
    host: str
    port: int
    dbname: str
    user: str
    password: str
    environment: str

    def _provenance(self) -> ProvenanceResource:
        return ProvenanceResource(
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=self.user,
            password=self.password,
            environment=self.environment,
        )

    def handle_output(self, context: OutputContext, obj: Any) -> None:
        asset_key = str(context.asset_key) if context.asset_key is not None else context.name
        _RUN_STORE[_store_key(context.run_id, asset_key)] = obj

        asset_code = _get_source(context)
        upstream_assets = _get_upstreams(context)
        return_value = _serialize(obj)
        return_type = type(obj).__name__

        try:
            self._provenance().record_asset_output(
                run_id=context.run_id,
                asset_key=asset_key,
                asset_code=asset_code,
                return_value=return_value,
                return_type=return_type,
                upstream_assets=upstream_assets,
            )
        except Exception as e:
            context.log.warning(f"[provenance] Falha ao gravar asset_provenance para {asset_key}: {e}")

    def load_input(self, context: InputContext) -> Any:
        asset_key = str(context.asset_key) if context.asset_key is not None else context.name
        upstream = context.upstream_output
        if upstream is None:
            return None
        # Each step may run in a separate subprocess, so _RUN_STORE is not reliable.
        # Read the value from PostgreSQL where handle_output already persisted it.
        try:
            prov = self._provenance()
            prov.setup_asset_schema()
            with prov._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    "SELECT return_value FROM asset_provenance WHERE run_id = %s AND asset_key = %s",
                    (upstream.run_id, asset_key),
                )
                row = cur.fetchone()
            return row[0] if row else None
        except Exception as e:
            context.log.warning(f"[provenance] Falha ao carregar valor para {asset_key}: {e}")
            return None
