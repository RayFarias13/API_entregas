import psycopg2
import sqlite3

from dotenv import load_dotenv
import os


load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)

print("Conectado com sucesso!")

print ('-----')

pg_cur = conn.cursor()
#dados
#cur.execute ("""SELECT * FROM public.pdv_vd_ctrl_entr order by dt_hr_lib desc limit 1""")


#rows = cur.fetchall()
#for row in rows:
    #print (row[16])



 #nomedascolunas
pg_cur.execute ("""SELECT column_name FROM information_schema.columns WHERE table_name = 'pdv_vd_ctrl_entr'""")
print(pg_cur.fetchall()   )   

pg_cur.execute ("""SELECT column_name FROM information_schema.columns WHERE table_name = 'pdv_vd_entr'""")
print(pg_cur.fetchall()   )   
pg_cur.execute ("""SELECT column_name FROM information_schema.columns WHERE table_name = 'glb_usu'""")

print(pg_cur.fetchall()   )   
#puxar dados da tabela de usuarios
pg_cur.execute("""SELECT cd_usu, nm_usu from public.glb_usu""")
dados_usuarios = pg_cur.fetchall()
print(f'{len(dados_usuarios)} usuarios encontrados.')


#sqlite

sqlite_conn = sqlite3.connect('monitor_api/db.sqlite3')
sqlite_cur = sqlite_conn.cursor()

sqlite_cur.executemany( "INSERT INTO glb_usu (cd_usu, nm_usu, ds_senha, funcao) VALUES (?, ?, ?, ?)",dados_usuarios)

sqlite_conn.commit()
print(f'{sqlite_cur.rowcount} usuarios inseridos no SQLite.')

pg_cur.close()
conn.close()
sqlite_cur.close()
sqlite_conn.close()

