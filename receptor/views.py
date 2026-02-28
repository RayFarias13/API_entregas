import json
from datetime import datetime

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import ApiRequest, Customer
from software.models import DadosEntrega, DadosVenda
#from bancoexterno.views import dados_entrega
import os
import sqlite3
from decimal import Decimal
import psycopg2
from dotenv import load_dotenv
load_dotenv()


SENSITIVE_HEADERS = ["authorization", "x-api-key", "api-key"]

@csrf_exempt
def capturar_tudo(request, path=""):
    """Captura qualquer rota e salva no banco"""
    method = request.method
    full_path = request.get_full_path()
    headers = dict(request.headers)
    query_params = dict(request.GET)

    # Mascarar headers sensíveis
    for key in list(headers.keys()):
        if key.lower() in SENSITIVE_HEADERS:
            headers[key] = "****MASKED****"

    body_raw = request.body.decode("utf-8") if request.body else ""
    try:
        body_json = json.loads(body_raw) if body_raw else None
    except:
        body_json = None

    ApiRequest.objects.create(
        method=method,
        path=path,
        full_path=full_path,
        headers=headers,
        query_params=query_params,
        body_raw=body_raw,
        body_json=body_json
    )

    return JsonResponse({
        "status": "capturado",
        "path": path,
        "method": method
    }, status=200)


@csrf_exempt
def customers(request):
    capturar_tudo(request, path="")

    # Executa SEM quebrar a API
    try:
        dados_banco_externo()
    except Exception as e:
        print("Erro ao executar dados_entrega:", e)

    method = request.method

    if method == "GET":
        code = request.GET.get('filter[0][value]')
        if code:
            try:
                customer = Customer.objects.get(code=code)
                data = [{
                    "name": customer.name,
                    "type": customer.type,
                    "code": customer.code,
                    "email": customer.email,
                    "login_email": customer.login_email,
                    "address": customer.address,
                    "address_complement": customer.address_complement,
                    "phone_number": customer.phone_number,
                    "latitude": customer.latitude,
                    "longitude": customer.longitude,
                    "operating_hour_start": str(customer.operating_hour_start) if customer.operating_hour_start else None,
                    "operating_hour_end": str(customer.operating_hour_end) if customer.operating_hour_end else None,
                    "extraFields": customer.extraFields
                }]
                return JsonResponse({"data": data, "total": 1}, status=200)
            except Customer.DoesNotExist:
                return JsonResponse({"data": [], "total": 0}, status=200)

        all_customers = Customer.objects.all()
        data = [{
            "name": c.name,
            "type": c.type,
            "code": c.code,
            "email": c.email,
            "login_email": c.login_email,
            "address": c.address,
            "address_complement": c.address_complement,
            "phone_number": c.phone_number,
            "latitude": c.latitude,
            "longitude": c.longitude,
            "operating_hour_start": str(c.operating_hour_start) if c.operating_hour_start else None,
            "operating_hour_end": str(c.operating_hour_end) if c.operating_hour_end else None,
            "extraFields": c.extraFields
        } for c in all_customers]

        return JsonResponse({"data": data, "total": len(data)}, status=200)

    elif method == "POST":
        try:
            body = json.loads(request.body)
        except:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        code = body.get("code")
        if not code:
            return JsonResponse({"error": "Code is required"}, status=400)

        customer, created = Customer.objects.get_or_create(
            code=code,
            defaults={
                "name": body.get("name", ""),
                "type": body.get("type", ""),
                "email": body.get("email"),
                "login_email": body.get("login_email"),
                "address": body.get("address"),
                "address_complement": body.get("address_complement"),
                "phone_number": body.get("phone_number"),
                "latitude": body.get("latitude", 0.0),
                "longitude": body.get("longitude", 0.0),
                "operating_hour_start": body.get("operating_hour_start"),
                "operating_hour_end": body.get("operating_hour_end"),
                "extraFields": body.get("extraFields"),
            }
        )

        return JsonResponse({
            "id": customer.id,
            "name": customer.name,
            "code": customer.code,
            "created": created,
            "Responsavel": "Farias"
        }, status=201 if created else 200)

    return JsonResponse({"error": "Method not allowed"}, status=405)



def dados_banco_externo():
    # --- Conexão PostgreSQL ---
    pg_conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )
    pg_cur = pg_conn.cursor()

    # --- Buscar registros no Postgres ---
    pg_cur.execute("""
        SELECT 
            pdv.cd_entr,
            pdv.cd_vd,
            pe.cd_fun_entr,
            pe.cd_fun_lib,
            pe.cd_mov_ret
        FROM public.pdv_vd_ctrl_entr_pdv_vd AS pdv
        INNER JOIN public.pdv_vd_ctrl_entr AS pe
            ON pdv.cd_entr = pe.cd_entr
        WHERE pe.sts_entr = '0'
    """)
    registros_venda = pg_cur.fetchall()
    print(f'Quantidade de registros no Postgres: {len(registros_venda)}')

    if not registros_venda:
        print("Nenhum registro para processar.")
        pg_cur.close()
        pg_conn.close()
        return

    # --- Inserir dados em DadosEntrega usando ORM ---
    registros_inseridos = 0
    for r in registros_venda:
        cd_entr, cd_vd, cd_fun_entr, cd_fun_lib, cd_mov_ret = [
            int(x) if isinstance(x, Decimal) else x for x in r
        ]
        obj, created = DadosEntrega.objects.get_or_create(
            cd_entr=cd_entr,
            cd_vd=cd_vd,
            defaults={
                'cd_fun_entr': cd_fun_entr,
                'cd_fun_lib': cd_fun_lib,
                'cd_mov_ret': cd_mov_ret
                # data_entr_ini e hora_entr_ini são preenchidos automaticamente
            }
        )
        if created:
            registros_inseridos += 1

    print(f"Registros inseridos em dados_entrega: {registros_inseridos}")

    # --- Só inserir dados_venda se realmente inseriu algo em DadosEntrega ---
    if registros_inseridos > 0:
        cd_vds = [int(r[1]) if isinstance(r[1], Decimal) else r[1] for r in registros_venda]
        pg_cur.execute("""
            SELECT cd_cli, cd_nf, cd_vd
            FROM public.pdv_vd
            WHERE cd_vd = ANY(%s)
        """, (cd_vds,))
        dados = pg_cur.fetchall()
        print(f"Registros adicionais encontrados no Postgres: {len(dados)}")

        for r in dados:
            cd_cli, cd_nf, cd_vd = [int(x) if isinstance(x, Decimal) else x for x in r]
            DadosVenda.objects.get_or_create(
                cd_cli=cd_cli,
                cd_nf=cd_nf,
                cd_vd=cd_vd
            )

    # --- Fechar conexão PostgreSQL ---
    pg_cur.close()
    pg_conn.close()

