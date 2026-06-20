import importlib.metadata
import subprocess
import sys

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
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
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
                    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """)
            conn.commit()

    def record(self, run_id: str) -> None:
        self.setup_schema()
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pipeline_provenance
                    (run_id, environment_name, python_version, dependencies, git_hash)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    run_id,
                    self.environment,
                    sys.version,
                    Json(_installed_packages()),
                    _git_hash(),
                ),
            )
