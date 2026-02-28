import psycopg2
import sqlite3

from dotenv import load_dotenv
import os


load_dotenv()

pg_conn = psycopg2.connect(
    host=os.getenv("DB_HOSTWEB"),
    dbname=os.getenv("DB_NAMEWEB"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORTWEB"),
)
pg_cur = pg_conn.cursor()

# Puxar apenas cd_usu e nm_usu
pg_cur.execute("SELECT cd_usu, nm_usu FROM glb_usu")  # nome da tabela PostgreSQL
dados_postgres = pg_cur.fetchall()


print(f"{len(dados_postgres)} registros encontrados no PostgreSQL")


pg_cur.close()
pg_conn.close()