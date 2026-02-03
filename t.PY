import os
import psycopg2
import sqlite3

from dotenv import load_dotenv
load_dotenv()

pg_conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
pg_cur = pg_conn.cursor()

# 
pg_cur.execute('select * from est_orc_cpl where cd_orc = 626842')
dados_postgres = pg_cur.fetchall()
print(dados_postgres)
pg_cur.close()
pg_conn.close() 
