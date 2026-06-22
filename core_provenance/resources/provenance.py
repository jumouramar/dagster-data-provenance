import ast
import importlib.metadata
import subprocess
import sys
import os
import hashlib
from typing import Any

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
    
    # Fallback caso o git não esteja instalado no container
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


def _installed_packages() -> dict[str, str | None]:
    # Analisa importações de todos os arquivos .py do repositório
    base_dir = os.getcwd()
    stdlib_modules = set(getattr(sys, "stdlib_module_names", ()))
    imported_modules: set[str] = set()
    
    # Ignora pastas de cache, ambiente virtual e logs do dagster
    ignore_dirs = {".git", "__pycache__", ".venv", "venv", "env", ".dagster", "storage", "logs"}

    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(root, fn)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=path)
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root_name = alias.name.split(".", 1)[0]
                        imported_modules.add(root_name)
                elif isinstance(node, ast.ImportFrom):
                    if node.level and node.module is None:
                        continue
                    if node.module:
                        root_name = node.module.split(".", 1)[0]
                        imported_modules.add(root_name)

    deps: dict[str, str | None] = {}
    module_to_distributions = importlib.metadata.packages_distributions()
    
    for module_name in sorted(imported_modules):
        if not module_name or module_name in stdlib_modules:
            continue
        dist_names = module_to_distributions.get(module_name) or [module_name]
        for dist_name in dist_names:
            try:
                deps[dist_name] = importlib.metadata.version(dist_name)
            except importlib.metadata.PackageNotFoundError:
                deps.setdefault(dist_name, None)
            except Exception:
                deps.setdefault(dist_name, None)

    if deps:
        return deps

    # Fallback se não encontrar imports
    return {
        dist.metadata["Name"]: dist.metadata.get("Version")
        for dist in importlib.metadata.distributions()
        if dist.metadata.get("Name")
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

    def _definition_hash(self) -> str | None:
        # Gera o hash dinâmico baseado em todo o repositório de código
        try:
            base = os.getcwd()
            h = hashlib.sha1()
            ignore_dirs = {".git", "__pycache__", ".venv", "venv", "env", ".dagster", "storage", "logs"}
            
            for root, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if d not in ignore_dirs]
                for fn in sorted(files):
                    if not fn.endswith(".py"):
                        continue
                    path = os.path.join(root, fn)
                    try:
                        with open(path, "rb") as f:
                            h.update(f.read())
                    except Exception:
                        pass
            return h.hexdigest()
        except Exception:
            return None

    def record_start(self, run_id: str, job_name: str | None = None, run_config: dict | None = None, start_time: float | None = None) -> None:
        self.setup_schema()
        asset_graph_hash = self._definition_hash()
        config_fingerprint = None
        filtered_run_config = None

        if run_config is not None:
            try:
                config_fingerprint = hashlib.sha1(str(run_config).encode("utf-8")).hexdigest()
                def _filter(obj: Any) -> Any:
                    if isinstance(obj, dict):
                        out: dict = {}
                        for k in sorted(obj.keys()):
                            kl = k.lower()
                            if any(s in kl for s in ("pass", "secret", "token", "key", "cred")):
                                continue
                            out[k] = _filter(obj[k])
                        return out
                    if isinstance(obj, list):
                        return [_filter(x) for x in obj]
                    return obj
                filtered_run_config = _filter(run_config)
            except Exception:
                pass

        deps = _installed_packages()

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
                    _git_hash(),
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