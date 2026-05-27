import importlib.metadata
import subprocess
import sys
import os

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
