import json
import os
import re

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def _normalize_key(key: str) -> str:
    """Normalize asset keys stored in legacy formats to plain path strings.

    Handles: "AssetKey(['a', 'b'])" and "['a', 'b']" → "a/b"
    """
    parts = re.findall(r"'([^']+)'", key)
    return "/".join(parts) if parts else key


def _engine() -> Engine:
    user = os.getenv("PROVENANCE_USER", "dagster")
    password = os.getenv("PROVENANCE_PASSWORD", "dagster")
    host = os.getenv("PROVENANCE_HOST", "postgres")
    port = os.getenv("PROVENANCE_PORT", "5432")
    dbname = os.getenv("PROVENANCE_DB", "dagster")
    return create_engine(
        f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}",
        pool_size=3,
        max_overflow=5,
        pool_recycle=1800,
    )


def get_run_ids() -> list[str]:
    with _engine().connect() as conn:
        rows = conn.execute(
            text("SELECT DISTINCT run_id FROM asset_provenance ORDER BY run_id DESC LIMIT 100")
        ).fetchall()
    return [r[0] for r in rows]


def get_assets_for_run(run_id: str) -> list[dict]:
    if run_id == "__all__":
        query = text("""
            SELECT DISTINCT ON (asset_key)
                run_id, asset_key, asset_code, return_value,
                return_type, upstream_assets, finished_at
            FROM asset_provenance
            ORDER BY asset_key, finished_at DESC
        """)
        params = {}
    else:
        query = text("""
            SELECT run_id, asset_key, asset_code, return_value,
                   return_type, upstream_assets, finished_at
            FROM asset_provenance
            WHERE run_id = :run_id
            ORDER BY finished_at
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
        }
        for r in rows
    ]
