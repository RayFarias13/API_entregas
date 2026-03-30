import os
import psycopg2
import json
import io
from psycopg2 import extras
from dotenv import load_dotenv

# 1. Carregar variáveis de ambiente
load_dotenv()

URL_ORIGEM = os.getenv('DATABASE_URL_NEON')
URL_DESTINO = os.getenv('DATABASE_URL_RENDER')

def clonar_tudo():
    conn_ori = None
    conn_des = None
    try:
        print("--- Iniciando Conexão com os Bancos ---")
        if not URL_ORIGEM or not URL_DESTINO:
            raise Exception("URLs não encontradas no arquivo .env!")

        # Conectar à Origem (Neon) e Destino (Render)
        conn_ori = psycopg2.connect(URL_ORIGEM)
        conn_des = psycopg2.connect(URL_DESTINO)
        
        # Permitir comandos de limpeza (TRUNCATE)
        conn_des.autocommit = True
        
        # Usar DictCursor para mapear nomes de colunas automaticamente
        cur_ori = conn_ori.cursor(cursor_factory=extras.DictCursor)
        cur_des = conn_des.cursor()

        # 2. Buscar todas as tabelas do banco
        cur_ori.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            AND table_name NOT IN ('spatial_ref_sys')
        """)
        todas_tabelas = [row[0] for row in cur_ori.fetchall()]

        # 3. Definir Ordem de Prioridade (Pai antes de Filho) para evitar erros de FK
        # Adicionamos 'receptor_customer' e 'dadosclientes' no topo
        prioridade = [
            'django_migrations', 'django_content_type', 'auth_permission', 
            'auth_user', 'receptor_customer', 'dadosclientes', 
            'dados_entrega', 'dados_venda'
        ]
        
        # Reorganiza a lista: primeiro os prioritários, depois o resto
        tabelas_ordenadas = [t for t in prioridade if t in todas_tabelas]
        tabelas_ordenadas += [t for t in todas_tabelas if t not in tabelas_ordenadas]

        print(f"Total de tabelas localizadas: {len(tabelas_ordenadas)}")

        # 4. Loop de Sincronização
        for tabela in tabelas_ordenadas:
            try:
                print(f"Sincronizando: {tabela}...", end=" ")
                
                # Puxar dados da Origem
                cur_ori.execute(f'SELECT * FROM "{tabela}"')
                rows = cur_ori.fetchall()
                
                if not rows:
                    print(" (Vazia, pulando)")
                    continue

                # Limpar tabela no Destino (CASCADE remove dependências temporariamente)
                cur_des.execute(f'TRUNCATE TABLE "{tabela}" CASCADE')

                # Preparar colunas e dados
                colunas = list(rows[0].keys())
                lista_dados = []

                for row in rows:
                    linha_processada = []
                    for valor in row:
                        # CORREÇÃO PARA JSON/DICT: Converte dicionários para string JSON
                        if isinstance(valor, (dict, list)):
                            linha_processada.append(json.dumps(valor))
                        else:
                            linha_processada.append(valor)
                    lista_dados.append(tuple(linha_processada))

                # Montar e executar INSERT em lote
                colunas_sql = ", ".join([f'"{c}"' for c in colunas])
                placeholders = ", ".join(["%s"] * len(colunas))
                query = f'INSERT INTO "{tabela}" ({colunas_sql}) VALUES ({placeholders})'
                
                extras.execute_batch(cur_des, query, lista_dados)
                print(f"✓ {len(lista_dados)} registros.")

            except Exception as e:
                if "does not exist" in str(e):
                    print(f"× Erro: Tabela não existe no Render. Rode 'python manage.py migrate' no servidor.")
                else:
                    print(f"× Erro: {e}")

        # 5. Sincronizar Sequências (Resetar contadores de ID)
        print("\n--- Atualizando Contadores de ID (Sequences) ---")
        cur_ori.execute("""
            SELECT 'SELECT setval(' || quote_literal(quote_ident(s.relname)) || 
            ', (SELECT MAX(' || quote_ident(c.attname) || ') FROM ' || 
            quote_ident(t.relname) || '));'
            FROM pg_class s
            JOIN pg_depend d ON d.objid = s.oid
            JOIN pg_class t ON t.oid = d.refobjid
            JOIN pg_attribute c ON (c.attrelid, c.attnum) = (d.refobjid, d.refobjsubid)
            WHERE s.relkind = 'S' AND t.relkind = 'r';
        """)
        
        for sync_sql in cur_ori.fetchall():
            try:
                cur_des.execute(sync_sql[0])
            except:
                continue

        print("\n==========================================")
        print("   SINCRONIZAÇÃO CONCLUÍDA COM SUCESSO!   ")
        print("==========================================")

    except Exception as e:
        print(f"\nERRO CRÍTICO: {e}")
    finally:
        if conn_ori: conn_ori.close()
        if conn_des: conn_des.close()

if __name__ == "__main__":
    clonar_tudo()