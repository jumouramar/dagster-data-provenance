import os

DAGSTER_HOME = os.getenv("DAGSTER_HOME")
ENVIRONMENT = os.getenv("ENVIRONMENT")

# Postgres (container + Dagster metadata storage)
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT"))
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

# Provenance DB (independent credentials — may differ in other environments)
PROVENANCE_HOST = os.getenv("PROVENANCE_HOST")
PROVENANCE_PORT = int(os.getenv("PROVENANCE_PORT"))
PROVENANCE_DB = os.getenv("PROVENANCE_DB")
PROVENANCE_USER = os.getenv("PROVENANCE_USER")
PROVENANCE_PASSWORD = os.getenv("PROVENANCE_PASSWORD")
