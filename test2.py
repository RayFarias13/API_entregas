import psycopg2
import sqlite3

from dotenv import load_dotenv
import os


load_dotenv()

pg_conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
pg_cur = pg_conn.cursor()

# Puxar apenas cd_usu e nm_usu
pg_cur.execute("SELECT cd_usu, nm_usu FROM glb_usu")  # nome da tabela PostgreSQL
dados_postgres = pg_cur.fetchall()
pg_cur.close()
pg_conn.close()

print(f"{len(dados_postgres)} registros encontrados no PostgreSQL")

# --- 2) Conectar no SQLite ---
sqlite_conn = sqlite3.connect('db.sqlite3')  # banco do Django
sqlite_cur = sqlite_conn.cursor()

# Criar a tabela SQLite se não existir (com os dois campos extras)
sqlite_cur.execute("""
CREATE TABLE IF NOT EXISTS glb_usu (
    cd_usu INTEGER PRIMARY KEY,
    nm_usu TEXT NOT NULL,
    ds_senha TEXT DEFAULT '123456',
    funcao TEXT DEFAULT 'DEFINIR'
)
""")

# --- 3) Inserir ou atualizar mantendo ds_senha e funcao ---
for cd_usu, nm_usu in dados_postgres:
    # Tenta atualizar nm_usu se o registro já existir
    sqlite_cur.execute("""
        UPDATE glb_usu
        SET nm_usu = ?
        WHERE cd_usu = ?
    """, (nm_usu, cd_usu))

    # Se não existir (nenhuma linha foi atualizada), insere com valores padrão para os campos extras
    if sqlite_cur.rowcount == 0:
        sqlite_cur.execute("""
            INSERT INTO glb_usu (cd_usu, nm_usu, ds_senha, funcao)
            VALUES (?, ?, '123456', 'DEFINIR')
        """, (cd_usu, nm_usu))

sqlite_conn.commit()
sqlite_conn.close()

print("Dados do PostgreSQL atualizados com sucesso no SQLite!")
