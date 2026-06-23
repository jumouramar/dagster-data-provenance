import json
from typing import Any

from dagster import ConfigurableIOManager, InputContext, OutputContext

from core_provenance.resources.provenance import ProvenanceResource
from core_provenance.utils import get_asset_source, get_asset_upstreams


def _serialize(obj: Any) -> Any:
    try:
        return json.loads(json.dumps(obj, default=str))
    except Exception:
        return str(obj)


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
        asset_key = (
            "/".join(context.asset_key.path) if context.asset_key is not None else context.name
        )
        asset_code = get_asset_source(context.op_def)
        upstream_assets = get_asset_upstreams(context.op_def)
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
            context.log.warning(
                f"[provenance] Falha ao gravar asset_provenance para {asset_key}: {e}"
            )

    def load_input(self, context: InputContext) -> Any:
        asset_key = (
            "/".join(context.asset_key.path) if context.asset_key is not None else context.name
        )
        upstream = context.upstream_output
        if upstream is None:
            return None
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
            context.log.warning(
                f"[provenance] Falha ao carregar valor para {asset_key}: {e}"
            )
            return None
