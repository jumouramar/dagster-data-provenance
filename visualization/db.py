import json
import re

import settings
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def _normalize_key(key: str) -> str:
    parts = re.findall(r"'([^']+)'", key)
    return "/".join(parts) if parts else key


def _engine() -> Engine:
    return create_engine(
        f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}",
        pool_size=3,
        max_overflow=5,
        pool_recycle=1800,
    )


def get_run_ids(job_name: str | None = None) -> list[str]:
    if job_name:
        query = text("""
            SELECT DISTINCT ap.run_id
            FROM asset_provenance ap
            JOIN runs r ON ap.run_id = r.run_id
            WHERE r.pipeline_name = :job_name
            ORDER BY ap.run_id DESC
            LIMIT 100
        """)
        params = {"job_name": job_name}
    else:
        query = text("""
            SELECT DISTINCT ap.run_id
            FROM asset_provenance ap
            JOIN runs r ON ap.run_id = r.run_id
            ORDER BY ap.run_id DESC
            LIMIT 100
        """)
        params = {}
    with _engine().connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [r[0] for r in rows]


def get_job_names() -> list[str]:
    with _engine().connect() as conn:
        rows = conn.execute(
            text("""
                SELECT DISTINCT pipeline_name
                FROM runs
                WHERE pipeline_name IS NOT NULL
                ORDER BY pipeline_name
            """)
        ).fetchall()
    return [r[0] for r in rows]


def get_assets_for_run(run_id: str) -> list[dict]:
    if run_id == "__all__":
        query = text("""
            SELECT DISTINCT ON (ap.asset_key)
                ap.run_id, ap.asset_key, ap.asset_code, ap.return_value,
                ap.return_type, ap.upstream_assets, ap.finished_at,
                r.pipeline_name AS job_name
            FROM asset_provenance ap
            LEFT JOIN runs r ON ap.run_id = r.run_id
            ORDER BY ap.asset_key, ap.finished_at DESC
        """)
        params = {}
    else:
        query = text("""
            SELECT ap.run_id, ap.asset_key, ap.asset_code, ap.return_value,
                   ap.return_type, ap.upstream_assets, ap.finished_at,
                   r.pipeline_name AS job_name
            FROM asset_provenance ap
            LEFT JOIN runs r ON ap.run_id = r.run_id
            WHERE ap.run_id = :run_id
            ORDER BY ap.finished_at
        """)
        params = {"run_id": run_id}

    with _engine().connect() as conn:
        rows = conn.execute(query, params).fetchall()

    return [
        {
            "run_id":          r[0],
            "asset_key":       _normalize_key(r[1]),
            "asset_code":      r[2],
            "return_value":    r[3],
            "return_type":     r[4],
            "upstream_assets": r[5] if isinstance(r[5], list) else json.loads(r[5] or "[]"),
            "finished_at":     str(r[6]),
            "job_name":        r[7],
        }
        for r in rows
    ]
