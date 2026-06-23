DAGSTER_HOME = "/app"
ENVIRONMENT = "development"

POSTGRES_HOST = "postgres"
POSTGRES_PORT = 5432
POSTGRES_DB = "dagster"
POSTGRES_USER = "dagster"
POSTGRES_PASSWORD = "dagster"

POSTGRES_CONN = dict(
    host=POSTGRES_HOST,
    port=POSTGRES_PORT,
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD,
    dbname=POSTGRES_DB,
)
