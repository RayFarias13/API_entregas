import psycopg2
import sqlite3

from dotenv import load_dotenv
import os


load_dotenv()

pg_conn = psycopg2.connect(
    host='wdbsp001.vetor.cloud',
    dbname='DF_DRG_DROGACINTIA_VTF_PRD',
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port='55003',
)
pg_cur = pg_conn.cursor()

# Puxar apenas cd_usu e nm_usu
pg_cur.execute("SELECT cd_usu, nm_usu FROM glb_usu")  # nome da tabela PostgreSQL
dados_postgres = pg_cur.fetchall()


print(f"{len(dados_postgres)} registros encontrados no PostgreSQL")


pg_cur.close()
pg_conn.close()