import sys
import hashlib
from typing import Any

import psycopg2
from dagster import ConfigurableResource
from psycopg2.extras import Json

from core_provenance.utils import definition_hash, filter_secrets, git_hash, installed_packages


class ProvenanceResource(ConfigurableResource):
    host: str
    port: int
    dbname: str
    user: str
    password: str
    environment: str

    def _connect(self):
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=self.user,
            password=self.password,
        )

    def setup_schema(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_provenance (
                    id              SERIAL PRIMARY KEY,
                    run_id          TEXT        UNIQUE NOT NULL,
                    environment_name TEXT       NOT NULL,
                    python_version  TEXT        NOT NULL,
                    dependencies    JSONB,
                    git_hash        TEXT,
                    job_name        TEXT,
                    asset_graph_hash TEXT,
                    config_fingerprint TEXT,
                    run_config      JSONB,
                    status          TEXT,
                    started_at      TIMESTAMPTZ,
                    finished_at     TIMESTAMPTZ,
                    duration_ms     BIGINT,
                    error_message   TEXT,
                    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """)
            conn.commit()

    def record_start(self, run_id: str, job_name: str | None = None, run_config: dict | None = None, start_time: float | None = None) -> None:
        self.setup_schema()
        asset_graph_hash = definition_hash()
        config_fingerprint = None
        filtered_run_config = None

        if run_config is not None:
            try:
                config_fingerprint = hashlib.sha1(str(run_config).encode("utf-8")).hexdigest()
                filtered_run_config = filter_secrets(run_config)
            except Exception:
                pass

        deps = installed_packages()

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pipeline_provenance
                    (run_id, environment_name, python_version, dependencies, git_hash, job_name, asset_graph_hash, config_fingerprint, run_config, status, started_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(to_timestamp(%s), NOW()))
                ON CONFLICT (run_id) DO UPDATE SET
                    dependencies = EXCLUDED.dependencies,
                    git_hash = EXCLUDED.git_hash,
                    job_name = EXCLUDED.job_name,
                    asset_graph_hash = EXCLUDED.asset_graph_hash,
                    config_fingerprint = EXCLUDED.config_fingerprint,
                    run_config = EXCLUDED.run_config,
                    started_at = COALESCE(EXCLUDED.started_at, pipeline_provenance.started_at),
                    status = CASE 
                        WHEN pipeline_provenance.status IN ('SUCCESS', 'FAILED') THEN pipeline_provenance.status 
                        ELSE EXCLUDED.status 
                    END
                """,
                (
                    run_id,
                    self.environment,
                    sys.version,
                    Json(deps),
                    git_hash(),
                    job_name,
                    asset_graph_hash,
                    config_fingerprint,
                    Json(filtered_run_config) if filtered_run_config is not None else None,
                    "RUNNING",
                    start_time
                ),
            )

    def record_success(self, run_id: str, start_time: float | None = None, end_time: float | None = None) -> None:
        self.setup_schema()
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pipeline_provenance (run_id, environment_name, python_version, status, started_at, finished_at)
                VALUES (%s, %s, %s, %s, to_timestamp(%s), COALESCE(to_timestamp(%s), NOW()))
                ON CONFLICT (run_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    started_at = COALESCE(EXCLUDED.started_at, pipeline_provenance.started_at),
                    finished_at = EXCLUDED.finished_at,
                    duration_ms = (EXTRACT(EPOCH FROM (EXCLUDED.finished_at - COALESCE(EXCLUDED.started_at, pipeline_provenance.started_at))) * 1000)::BIGINT,
                    error_message = NULL
                """,
                (run_id, self.environment, sys.version, "SUCCESS", start_time, end_time),
            )

    def record_failure(self, run_id: str, error_message: str | None = None, start_time: float | None = None, end_time: float | None = None) -> None:
        self.setup_schema()
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pipeline_provenance (run_id, environment_name, python_version, status, started_at, finished_at, error_message)
                VALUES (%s, %s, %s, %s, to_timestamp(%s), COALESCE(to_timestamp(%s), NOW()), %s)
                ON CONFLICT (run_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    started_at = COALESCE(EXCLUDED.started_at, pipeline_provenance.started_at),
                    finished_at = EXCLUDED.finished_at,
                    duration_ms = (EXTRACT(EPOCH FROM (EXCLUDED.finished_at - COALESCE(EXCLUDED.started_at, pipeline_provenance.started_at))) * 1000)::BIGINT,
                    error_message = EXCLUDED.error_message
                """,
                (run_id, self.environment, sys.version, "FAILED", start_time, end_time, error_message),
            )

    def setup_asset_schema(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS asset_provenance (
                    id              SERIAL PRIMARY KEY,
                    run_id          TEXT        NOT NULL,
                    asset_key       TEXT        NOT NULL,
                    asset_code      TEXT,
                    return_value    JSONB,
                    return_type     TEXT,
                    upstream_assets JSONB,
                    finished_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (run_id, asset_key)
                )
            """)
            conn.commit()

    def record_asset_output(
        self,
        run_id: str,
        asset_key: str,
        asset_code: str | None,
        return_value: Any,
        return_type: str,
        upstream_assets: list[str],
    ) -> None:
        self.setup_asset_schema()
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO asset_provenance
                    (run_id, asset_key, asset_code, return_value, return_type, upstream_assets)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id, asset_key) DO UPDATE SET
                    asset_code      = EXCLUDED.asset_code,
                    return_value    = EXCLUDED.return_value,
                    return_type     = EXCLUDED.return_type,
                    upstream_assets = EXCLUDED.upstream_assets,
                    finished_at     = NOW()
                """,
                (
                    run_id,
                    asset_key,
                    asset_code,
                    Json(return_value),
                    return_type,
                    Json(upstream_assets),
                ),
            )

    def record_asset_materialization_fallback(
        self,
        run_id: str,
        asset_key: str,
        asset_code: str | None,
        return_type: str,
        upstream_assets: list[str],
        finished_at: float | None = None,
    ) -> None:
        """Fallback para assets com -> None que o IOManager não captura.
        ON CONFLICT DO NOTHING garante que dados do IOManager nunca são sobrescritos.
        """
        self.setup_asset_schema()
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO asset_provenance
                    (run_id, asset_key, asset_code, return_value, return_type,
                     upstream_assets, finished_at)
                VALUES (%s, %s, %s, NULL, %s, %s, COALESCE(to_timestamp(%s), NOW()))
                ON CONFLICT (run_id, asset_key) DO NOTHING
                """,
                (run_id, asset_key, asset_code, return_type, Json(upstream_assets), finished_at),
            )

    def record_config_asset(self, run_id: str, run_config: dict) -> None:
        if not run_config:
            return
        self.record_asset_output(
            run_id=run_id,
            asset_key="config",
            asset_code=None,
            return_value=filter_secrets(run_config),
            return_type="RunConfig",
            upstream_assets=[],
        )