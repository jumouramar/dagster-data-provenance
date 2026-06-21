import json

from dagster import get_dagster_logger
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

logger = get_dagster_logger()


class PostgresClient:
    def __init__(self, host: str, port: int, dbname: str, user: str, password: str):
        self.engine: Engine = create_engine(
            f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}",
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
        )

    def execute_query(self, query: str, params: dict = None):
        try:
            with self.engine.begin() as conn:
                result = conn.execute(text(query), params or {})
                if result.returns_rows:
                    rows = result.fetchall()
                    logger.info(f"Rows returned: {len(rows)}")
                    return rows
                logger.info(f"Rows affected: {result.rowcount}")
                return result.rowcount
        except SQLAlchemyError as e:
            logger.error(f"SQLAlchemy error: {e}")
            raise ValueError(f"Database error: {e}")

    def insert_batch(
        self, schema: str, table: str, records: list[dict], returning: str = None
    ) -> list:
        if not records:
            logger.warning(f"No records to insert into {schema}.{table}.")
            return []

        clean = [
            {k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in r.items()}
            for r in records
        ]

        columns = list(clean[0].keys())
        col_names = ", ".join(columns)
        placeholders = ", ".join([f":{col}" for col in columns])
        returning_clause = f" RETURNING {returning}" if returning else ""
        query = text(
            f"INSERT INTO {schema}.{table} ({col_names}) VALUES ({placeholders}){returning_clause}"
        )

        try:
            with self.engine.begin() as conn:
                result = conn.execute(query, clean)
                if returning:
                    values = [row[0] for row in result.fetchall()]
                    logger.info(f"Inserted {len(clean)} records into {schema}.{table}, returning {values}")
                    return values
            logger.info(f"Inserted {len(clean)} records into {schema}.{table}")
            return []
        except SQLAlchemyError as e:
            logger.error(f"insert_batch error in {schema}.{table}: {e}")
            raise ValueError(f"Database error on insert: {e}")

    def upsert_batch(
        self,
        schema: str,
        table: str,
        records: list[dict],
        conflict_columns: list[str],
        returning: str = None,
    ) -> list:
        if not records:
            logger.warning(f"No records to upsert into {schema}.{table}.")
            return []

        clean = [
            {k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in r.items()}
            for r in records
        ]
        columns = list(clean[0].keys())
        col_names = ", ".join(columns)
        placeholders = ", ".join([f":{col}" for col in columns])
        update_cols = [c for c in columns if c not in conflict_columns]
        set_clause = ", ".join([f"{c} = EXCLUDED.{c}" for c in update_cols])
        returning_clause = f" RETURNING {returning}" if returning else ""
        query = text(
            f"INSERT INTO {schema}.{table} ({col_names}) VALUES ({placeholders})"
            f" ON CONFLICT ({', '.join(conflict_columns)}) DO UPDATE SET {set_clause}"
            f"{returning_clause}"
        )
        try:
            with self.engine.begin() as conn:
                result = conn.execute(query, clean)
                if returning:
                    values = [row[0] for row in result.fetchall()]
                    logger.info(f"Upserted {len(clean)} records into {schema}.{table}, returning {values}")
                    return values
            logger.info(f"Upserted {len(clean)} records into {schema}.{table}")
            return []
        except SQLAlchemyError as e:
            logger.error(f"upsert_batch error in {schema}.{table}: {e}")
            raise ValueError(f"Database error on upsert: {e}")

    def upsert_batch(
        self,
        schema: str,
        table: str,
        records: list[dict],
        conflict_columns: list[str],
        returning: str = None,
    ) -> list:
        if not records:
            logger.warning(f"No records to upsert into {schema}.{table}.")
            return []

        clean = [
            {k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in r.items()}
            for r in records
        ]

        columns = list(clean[0].keys())
        col_names = ", ".join(columns)
        placeholders = ", ".join([f":{col}" for col in columns])
        update_cols = [c for c in columns if c not in conflict_columns]
        set_clause = ", ".join([f"{c} = EXCLUDED.{c}" for c in update_cols])
        returning_clause = f" RETURNING {returning}" if returning else ""
        query = text(
            f"INSERT INTO {schema}.{table} ({col_names}) VALUES ({placeholders})"
            f" ON CONFLICT ({', '.join(conflict_columns)}) DO UPDATE SET {set_clause}"
            f"{returning_clause}"
        )

        try:
            with self.engine.begin() as conn:
                result = conn.execute(query, clean)
                if returning:
                    values = [row[0] for row in result.fetchall()]
                    logger.info(f"Upserted {len(clean)} records into {schema}.{table}, returning {values}")
                    return values
            logger.info(f"Upserted {len(clean)} records into {schema}.{table}")
            return []
        except SQLAlchemyError as e:
            logger.error(f"upsert_batch error in {schema}.{table}: {e}")
            raise ValueError(f"Database error on upsert: {e}")
