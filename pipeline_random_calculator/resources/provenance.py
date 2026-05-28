import importlib.metadata
import subprocess
import sys
import os
import hashlib

import psycopg2
from dagster import ConfigurableResource
from psycopg2.extras import Json


def _git_hash() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass

    try:
        git_head = os.path.join(os.getcwd(), ".git", "HEAD")
        if os.path.isfile(git_head):
            with open(git_head, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content.startswith("ref:"):
                ref = content.split(":", 1)[1].strip()
                ref_path = os.path.join(os.getcwd(), ".git", *ref.split("/"))
                if os.path.isfile(ref_path):
                    with open(ref_path, "r", encoding="utf-8") as rf:
                        return rf.read().strip()
            else:
                return content
    except Exception:
        pass

    return None


def _installed_packages() -> dict[str, str]:
    return {
        dist.metadata["Name"]: dist.metadata["Version"]
        for dist in importlib.metadata.distributions()
        if dist.metadata["Name"]
    }


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
                    run_id          TEXT        NOT NULL,
                    environment_name TEXT       NOT NULL,
                    python_version  TEXT        NOT NULL,
                    dependencies    JSONB,
                    git_hash        TEXT,
                    job_name        TEXT,
                    asset_graph_hash TEXT,
                    config_fingerprint TEXT,
                    status          TEXT,
                    started_at      TIMESTAMPTZ,
                    finished_at     TIMESTAMPTZ,
                    duration_ms     BIGINT,
                    error_message   TEXT,
                    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """)
            cur.execute(
                "ALTER TABLE pipeline_provenance ADD COLUMN IF NOT EXISTS status TEXT"
            )
            cur.execute(
                "ALTER TABLE pipeline_provenance ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ"
            )
            cur.execute(
                "ALTER TABLE pipeline_provenance ADD COLUMN IF NOT EXISTS finished_at TIMESTAMPTZ"
            )
            cur.execute(
                "ALTER TABLE pipeline_provenance ADD COLUMN IF NOT EXISTS duration_ms BIGINT"
            )
            cur.execute(
                "ALTER TABLE pipeline_provenance ADD COLUMN IF NOT EXISTS error_message TEXT"
            )
            cur.execute(
                "ALTER TABLE pipeline_provenance ADD COLUMN IF NOT EXISTS job_name TEXT"
            )
            cur.execute(
                "ALTER TABLE pipeline_provenance ADD COLUMN IF NOT EXISTS asset_graph_hash TEXT"
            )
            cur.execute(
                "ALTER TABLE pipeline_provenance ADD COLUMN IF NOT EXISTS config_fingerprint TEXT"
            )
            conn.commit()

    def _definition_hash(self) -> str | None:
        try:
            base = os.path.join(os.getcwd(), "pipeline_random_calculator")
            if not os.path.isdir(base):
                return None
            h = hashlib.sha1()
            for root, _dirs, files in os.walk(base):
                for fn in sorted(files):
                    if not fn.endswith(".py"):
                        continue
                    path = os.path.join(root, fn)
                    try:
                        with open(path, "rb") as f:
                            h.update(f.read())
                    except Exception:
                        # skip unreadable files
                        pass
            return h.hexdigest()
        except Exception:
            return None


    def record_start(self, run_id: str, context=None) -> None:
        self.setup_schema()
        job_name = None
        asset_graph_hash = None
        config_fingerprint = None
        if context is not None:
            job_name = getattr(context, "job_name", None)
            if job_name is None:
                asset_key = getattr(context, "asset_key", None)
                if asset_key is not None:
                    try:
                        job_name = ".".join(asset_key.path)
                    except Exception:
                        job_name = str(asset_key)
            # compute definition hash (based on package files)
            asset_graph_hash = self._definition_hash()
            # try to fingerprint run config if available
            run_config = getattr(context, "run_config", None)
            if run_config is not None:
                try:
                    config_fingerprint = hashlib.sha1(str(run_config).encode("utf-8")).hexdigest()
                except Exception:
                    config_fingerprint = None
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pipeline_provenance
                    (run_id, environment_name, python_version, dependencies, git_hash, job_name, asset_graph_hash, config_fingerprint, status, started_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """,
                (
                    run_id,
                    self.environment,
                    sys.version,
                    Json(_installed_packages()),
                    _git_hash(),
                    job_name,
                    asset_graph_hash,
                    config_fingerprint,
                    "RUNNING",
                ),
            )

    def record_success(self, run_id: str) -> None:
        self.setup_schema()
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_provenance
                SET
                    status = %s,
                    finished_at = NOW(),
                    duration_ms = (EXTRACT(EPOCH FROM (NOW() - COALESCE(started_at, recorded_at))) * 1000)::BIGINT,
                    error_message = NULL
                WHERE run_id = %s
                """,
                ("SUCCESS", run_id),
            )

    def record_failure(self, run_id: str, error_message: str | None = None) -> None:
        self.setup_schema()
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_provenance
                SET
                    status = %s,
                    finished_at = NOW(),
                    duration_ms = (EXTRACT(EPOCH FROM (NOW() - COALESCE(started_at, recorded_at))) * 1000)::BIGINT,
                    error_message = %s
                WHERE run_id = %s
                """,
                ("FAILED", error_message, run_id),
            )
