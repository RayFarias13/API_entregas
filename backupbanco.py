import os

Servidorinicial =os.getenv("DATABASE_URL_NEON")
Servidorfinal = os.getenv("DATABASE_URL_RENDER")


def backup_database():
    os.system(f"pg_dump --no-owner --no-privileges {Servidorinicial} >backup.sql")

    #psql Servidorfinal <backup.sql


def restore_database():
    os.system(f"psql {Servidorfinal} <backup.sql")