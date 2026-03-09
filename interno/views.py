import os
import time
import psycopg2
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()

def sincronizar_com_neon():
    tempo_espera = 180  # 3 minutos

    while True:
        pg_conn_local = None
        pg_conn_neon = None
        
        try:
            # 1. Conecta ao Banco Local
            pg_conn_local = psycopg2.connect(
                host=os.getenv("DB_HOST_LOCAL"),
                database=os.getenv("DB_NAME_LOCAL"),
                user=os.getenv("DB_USER_LOCAL"),
                password=os.getenv("DB_PASSWORD_LOCAL"),
                port=os.getenv("DB_PORT_LOCAL")
            )
            pg_cur_local = pg_conn_local.cursor()

            # 2. Busca dados (Status '0' = pendente)
            pg_cur_local.execute("""
                SELECT pdv.cd_entr, pdv.cd_vd, pe.cd_fun_entr, pe.cd_fun_lib, pe.cd_mov_ret 
                FROM public.pdv_vd_ctrl_entr_pdv_vd AS pdv
                INNER JOIN public.pdv_vd_ctrl_entr AS pe ON pdv.cd_entr = pe.cd_entr
                WHERE pe.sts_entr = '0'
            """)
            registros = pg_cur_local.fetchall()

            if registros:
                print(f"Sincronizando {len(registros)} registros...")
                
                # 3. Conecta ao Neon (Uma única vez para todos os registros)
                pg_conn_neon = psycopg2.connect(
                    os.getenv("DATABASE_URL_NEON"), # Recomendo usar a URL completa do Neon
                    sslmode='require'
                )
                pg_cur_neon = pg_conn_neon.cursor()

                for r in registros:
                    # Converte Decimal para Int se necessário
                    dados = [int(x) if isinstance(x, Decimal) else x for x in r]
                    
                    pg_cur_neon.execute("""
                        INSERT INTO dados_entrega (cd_entr, cd_vd, cd_fun_entr, cd_fun_lib, cd_mov_ret)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (cd_entr) DO NOTHING
                    """, dados)

                pg_conn_neon.commit()
                print("Sincronização concluída com sucesso.")
            else:
                print("Nenhum registro novo encontrado.")

        except Exception as e:
            print(f"Erro durante a sincronização: {e}")
        
        finally:
            # 4. Fecha as conexões com segurança
            if pg_conn_local: pg_conn_local.close()
            if pg_conn_neon: pg_conn_neon.close()
            
            print(f"Aguardando {tempo_espera/60} minutos para a próxima carga...")
            time.sleep(tempo_espera)

if __name__ == "__main__":
    sincronizar_com_neon()