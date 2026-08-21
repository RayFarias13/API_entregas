from django.shortcuts import render
from django.db import transaction

from software.models import PagamentoPedido, Pedido, ProdutoCadastrado, ItemPedido
import os
import json
import requests

from decimal import Decimal
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from .services.nuvemshop import NuvemshopAPI
from .utils import (
    STATUS_PEDIDO,
    STATUS_PAGAMENTO,
    STATUS_ENVIO,
)## ─────────────────────────────────────────
#envio de vendas para o pdv


def renderizar_formulario_venda(request):
    return render(request, 'vendas_lancar.html')


@csrf_exempt
def criar_pedido_view(request):
    if request.method != 'POST':
        return JsonResponse({"erro": "Método não permitido"}, status=405)

    try:
        dados = json.loads(request.body)
        cliente_data = dados.get('cliente', {})

        # Usamos transaction.atomic para garantir que tudo seja salvo ou nada seja (rollback automático em caso de erro)
        with transaction.atomic():
            # 1. Salva o Pedido principal
            pedido = Pedido.objects.create(
                cd_filial=dados.get('cdFilial', 1),
                cgc_filial=dados.get('cgcFilial', "02.010.627/001-59"),
                cd_vendedor=dados.get('cdVendedor'),
                cliente_codigo=cliente_data.get('codigo', ''),
                cliente_nome=cliente_data.get('nome'),
                cliente_cpf_cgc=cliente_data.get('cpfCgc'),
                cliente_telefone=cliente_data.get('telefone'),
                cliente_sexo=cliente_data.get('sexo'),
                cliente_endereco=cliente_data.get('endereco'),
                cliente_numero=cliente_data.get('numero'),
                cliente_complemento=cliente_data.get('complemento'),
                cliente_cep=cliente_data.get('cep'),
                cliente_bairro=cliente_data.get('bairro'),
                cliente_cidade=cliente_data.get('cidade'),
                cliente_uf=cliente_data.get('uf'),
                vlr_produtos=dados.get('vlrProdutos'),
                vlr_descontos=dados.get('vlrDescontos', 0),
                vlr_total=dados.get('vlrTotal'),
                vlr_troco_para=dados.get('vlrTrocoPara', 0),
                observacao=dados.get('observacao', ''),
                retirar=dados.get('retirar', False),
                status_pedido=dados.get('statusPedido', 'Pago')
            )

            # 2. Gera o nrPedido único baseado no ID
            pedido.nr_pedido = f"lol_{pedido.id}"
            pedido.save(update_fields=['nr_pedido'])

            # 3. Salva os Itens em lote ou individualmente com validação de preço
            itens_para_criar = []
            for item_data in dados.get('itens', []):
                cd_produto_reduzido = item_data.get('cdProduto')
                
                try:
                    produto_db = ProdutoCadastrado.objects.get(codigo_reduzido=cd_produto_reduzido)
                    preco_unitario = produto_db.preco_unitario
                except ProdutoCadastrado.DoesNotExist:
                    preco_unitario = item_data.get('vlrUnitario')

                qtd = Decimal(str(item_data.get('quantidade', 1)))
                vlr_unit = Decimal(str(preco_unitario))

                itens_para_criar.append(
                    ItemPedido(
                        pedido=pedido,
                        cd_produto=cd_produto_reduzido,
                        quantidade=qtd,
                        vlr_unitario=vlr_unit,
                        vlr_desconto=item_data.get('vlrDesconto', 0),
                        vlr_total=vlr_unit * qtd,
                        cd_vendedor=item_data.get('cdVendedor', pedido.cd_vendedor),
                        info_diversas=item_data.get('infoDiversas', ''),
                        origemVenda=item_data.get('origemVenda', '')
                    )
                )
            ItemPedido.objects.bulk_create(itens_para_criar)

            # 4. Salva os Pagamentos
            pagamentos_para_criar = []
            for pag in dados.get('pagamentos', []):
                pagamentos_para_criar.append(
                    PagamentoPedido(
                        pedido=pedido,
                        forma_pagamento=pag.get('formaPagamento'),
                        valor=pag.get('valor'),
                        nr_autorizacao=pag.get('nrAutorizacao', ''),
                        nsu=pag.get('nsu', ''),
                        bandeira_cartao=pag.get('bandeiraCartao', ''),
                        adquirente=pag.get('adquirente', ''),
                        data_captura=pag.get('dataCaptura') or None,
                        qtd_parcelas=pag.get('qtdParcelas', 1),
                        cd_convenio=pag.get('cdConvenio', 0),
                        identificador=pag.get('identificador', '')
                    )
                )
            PagamentoPedido.objects.bulk_create(pagamentos_para_criar)

        # 5. Monta o payload para a API externa (fora da transação de banco)
        payload_api = {
            "cdFilial": pedido.cd_filial,
            "cgcFilial": pedido.cgc_filial,
            "nrPedido": pedido.nr_pedido,
            "cdVendedor": pedido.cd_vendedor,
            "dtEmissao": pedido.dt_emissao.isoformat(),
            "cliente": {
                "codigo": pedido.cliente_codigo,
                "nome": pedido.cliente_nome,
                "cpfCgc": pedido.cliente_cpf_cgc,
                "telefone": pedido.cliente_telefone,
                "sexo": pedido.cliente_sexo,
                "endereco": pedido.cliente_endereco,
                "numero": pedido.cliente_numero,
                "complemento": pedido.cliente_complemento,
                "cep": pedido.cliente_cep,
                "bairro": pedido.cliente_bairro,
                "cidade": pedido.cliente_cidade,
                "uf": pedido.cliente_uf
            },
            "vlrProdutos": str(pedido.vlr_produtos),
            "vlrDescontos": str(pedido.vlr_descontos),
            "vlrTotal": str(pedido.vlr_total),
            "vlrTrocoPara": str(pedido.vlr_troco_para),
            "observacao": pedido.observacao,
            "retirar": pedido.retirar,
            "itens": [
                {
                    "cdProduto": item.cd_produto,
                    "quantidade": float(item.quantidade),
                    "vlrUnitario": str(item.vlr_unitario),
                    "vlrDesconto": str(item.vlr_desconto),
                    "vlrTotal": str(item.vlr_total),
                    "cdVendedor": item.cd_vendedor,
                    "infoDiversas": item.info_diversas
                } for item in pedido.itens.all()
            ],
            "statusPedido": pedido.status_pedido,
            "pagamentos": [
                {
                    "formaPagamento": pag.forma_pagamento,
                    "valor": str(pag.valor),
                    "nrAutorizacao": pag.nr_autorizacao or "",
                    "nsu": pag.nsu or "",
                    "bandeiraCartao": pag.bandeira_cartao or "",
                    "adquirente": pag.adquirente or "",
                    "dataCaptura": pag.data_captura.isoformat() if pag.data_captura else "",
                    "qtdParcelas": pag.qtd_parcelas,
                    "cdConvenio": pag.cd_convenio,
                    "identificador": pag.identificador or ""
                } for pag in pedido.pagamentos.all()
            ]
        }

        # 6. Dispara o POST para a API externa
        url_api_externa = os.getenv("PDV_HOST_API_URL")
        headers = {
            "Content-Type": "application/json",
            "Authorization": os.getenv("PDV_HOST_CHAVE")
        }

        # Dica: Reduza o timeout se necessário para não travar o cliente, ou considere usar Celery/Background Tasks no futuro.
        resposta_api = requests.post(url_api_externa, json=payload_api, headers=headers, timeout=30)

        return JsonResponse({
            "status": "sucesso",
            "nrPedido": pedido.nr_pedido,
            "respostaApiExternaStatus": resposta_api.status_code
        }, status=201)

    except Exception as e:
        return JsonResponse({"status": "erro", "detalhes": str(e)}, status=400)
    
    
    
def buscar_produto_view(request, codigo):
    try:
        produto = ProdutoCadastrado.objects.get(codigo_reduzido=codigo)
        return JsonResponse({
            "status": "sucesso",
            "descricao": produto.descricao,
            "preco_unitario": str(produto.preco_unitario)
        }, status=200)
    except ProdutoCadastrado.DoesNotExist:
        return JsonResponse({"status": "erro", "detalhes": "Produto não cadastrado"}, status=404)


def produto_salvar_view(request, pk=None):
    produto = None
    if pk:
        produto = get_object_or_404(ProdutoCadastrado, pk=pk)

    if request.method == 'POST':
        codigo_reduzido = request.POST.get('codigo_reduzido')
        descricao = request.POST.get('descricao')
        ean = request.POST.get('ean')
        preco_unitario = request.POST.get('preco_unitario')

        if produto:
            # Editando o produto existente
            produto.codigo_reduzido = codigo_reduzido
            produto.descricao = descricao
            produto.ean = ean
            produto.preco_unitario = preco_unitario
            produto.save()
        else:
            # Criando um novo produto
            ProdutoCadastrado.objects.create(
                codigo_reduzido=codigo_reduzido,
                descricao=descricao,
                ean=ean,
                preco_unitario=preco_unitario
            )
        
        return redirect('produto_listar') # Redireciona após salvar (ajuste o nome da rota se necessário)

    return render(request, 'produto_form.html', {'produto': produto})


# ____________________________________________________________________________________ #
# #______________________ NUVEM SHOP ________________________________________________#

import requests

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect

from .utils import (
    STATUS_PEDIDO,
    STATUS_PAGAMENTO,
    STATUS_ENVIO,
)


# ============================================================
# CONFIGURAÇÕES
# ============================================================

NUVEMSHOP_URL = (
    "https://api.nuvemshop.com.br/2025-03"
)

ZETTI_URL = (
    "https://integracao.zetti.dev/api/ecommerce"
)


# ============================================================
# BUSCAR PEDIDOS NA NUVEMSHOP
# ============================================================

def buscar_pedidos_nuvemshop(status_atual=""):

    store_id = getattr(
        settings,
        "NUVEMSHOP_STORE_ID",
        ""
    )

    access_token = getattr(
        settings,
        "NUVEMSHOP_ACCESS_TOKEN",
        ""
    )

    if not store_id:
        raise Exception(
            "NUVEMSHOP_STORE_ID não configurado."
        )

    if not access_token:
        raise Exception(
            "NUVEMSHOP_ACCESS_TOKEN não configurado."
        )

    url = (
        f"{NUVEMSHOP_URL}/"
        f"{store_id}/orders"
    )

    headers = {
        "Authorization": f"Bearer {access_token}",

        "User-Agent": "Sistema de Entregas",

        "Content-Type": "application/json",
    }

    params = {
        "per_page": 100,
    }

    if status_atual:
        params["status"] = status_atual

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    pedidos = response.json()

    for ped in pedidos:
        print(ped)
        print("-" * 70)

    if not isinstance(pedidos, list):
        return []

    return pedidos


# ============================================================
# PREPARAR STATUS
# ============================================================

def preparar_status(pedidos):

    for pedido in pedidos:

        # ----------------------------------------------------
        # PEDIDO
        # ----------------------------------------------------

        codigo = pedido.get("status")

        pedido["status_pedido_texto"] = STATUS_PEDIDO.get(
            codigo,
            codigo or "-"
        )

        # ----------------------------------------------------
        # PAGAMENTO
        # ----------------------------------------------------

        codigo = pedido.get("payment_status")

        pedido["status_pagamento_texto"] = STATUS_PAGAMENTO.get(
            codigo,
            codigo or "-"
        )

        # ----------------------------------------------------
        # ENVIO
        # ----------------------------------------------------

        codigo = pedido.get("shipping_status")

        pedido["status_envio_texto"] = STATUS_ENVIO.get(
            codigo,
            codigo or "-"
        )

    return pedidos


# ============================================================
# LISTA DE PEDIDOS
# ============================================================

def lista_pedidos(request):

    status_atual = request.GET.get(
        "status",
        ""
    )

    pedidos = []

    erro = None

    try:

        pedidos = buscar_pedidos_nuvemshop(
            status_atual
        )

        pedidos = preparar_status(
            pedidos
        )

    except requests.exceptions.RequestException as e:

        erro = (
            f"Erro ao consultar a Nuvemshop: {e}"
        )

    except Exception as e:

        erro = str(e)

    return render(
        request,
        "lista.html",
        {
            "pedidos": pedidos,

            "status_atual": status_atual,

            "erro": erro,
        }
    )


# ============================================================
# MONTAR CLIENTE PARA ZETTI
# ============================================================

def montar_cliente_zetti(pedido):

    endereco = (
        pedido.get("shipping_address")
        or {}
    )

    cliente = (
        pedido.get("customer")
        or {}
    )

    nome = (
        pedido.get("contact_name")

        or cliente.get("name")

        or endereco.get("name")

        or "CLIENTE"
    )

    cpf = (
        pedido.get("contact_identification")
        or cliente.get("identification")
        or ""
    )

    telefone = (
        pedido.get("contact_phone")
        or cliente.get("phone")
        or endereco.get("phone")
        or ""
    )

    email = (
        pedido.get("contact_email")
        or cliente.get("email")
        or ""
    )

    return {

        "nome": nome,

        "cpfCgc": cpf,

        "telefone": telefone,

        "endereco": endereco.get(
            "address",
            ""
        ),

        "numero": endereco.get(
            "number",
            "SN"
        ),

        "complemento": endereco.get(
            "floor",
            ""
        ),

        "cep": endereco.get(
            "zipcode",
            ""
        ),

        "bairro": endereco.get(
            "locality",
            ""
        ),

        "cidade": endereco.get(
            "city",
            ""
        ),

        "uf": obter_uf(endereco,) or "",

        "referencia": (
            endereco.get("customs")
            or ""
        ),

        "email": email,
    }


# ============================================================
# IDENTIFICAR SE É RETIRADA
# ============================================================

def pedido_e_retirada(pedido):

    fulfillments = (
        pedido.get("fulfillments")
        or []
    )

    for fulfillment in fulfillments:

        shipping = (
            fulfillment.get("shipping")
            or {}
        )

        tipo = shipping.get("type")

        # ----------------------------------------------------
        # NUVEMSHOP
        #
        # pickup = retirada no local
        # ship   = entrega
        # ----------------------------------------------------

        if tipo == "pickup":

            return True

        if tipo == "ship":

            return False

    # --------------------------------------------------------
    # Caso não exista fulfillment
    # --------------------------------------------------------

    return False


# ============================================================
# MONTAR ITENS PARA ZETTI
# ============================================================

def montar_itens_zetti(pedido):

    itens = []

    produtos = (
        pedido.get("products")
        or []
    )

    for produto in produtos:

        sku = produto.get("sku")

        # ----------------------------------------------------
        # SKU É O CDPRODUTO
        # ----------------------------------------------------

        if not sku:

            raise Exception(
                (
                    f"O produto "
                    f"'{produto.get('name', '-')}' "
                    f"não possui SKU. "
                    f"Não é possível enviar para o PDV."
                )
            )

        try:

            cd_produto = int(
                str(sku).strip()
            )

        except ValueError:

            raise Exception(
                (
                    f"O SKU '{sku}' "
                    f"do produto "
                    f"'{produto.get('name', '-')}' "
                    f"não é numérico."
                )
            )

        quantidade = float(
            produto.get(
                "quantity",
                0
            )
        )

        preco = float(
            produto.get(
                "price",
                0
            )
        )

        total = (
            quantidade * preco
        )

        itens.append({

            "cdProduto":
                cd_produto,

            "cdProdutoEcommerce":
                str(
                    produto.get(
                        "product_id",
                        ""
                    )
                ),

            "cdBarrasProduto":
                str(
                    produto.get(
                        "barcode",
                        ""
                    )
                    or ""
                ),

            "nomeProduto":
                produto.get(
                    "name",
                    ""
                ),

            "quantidade":
                quantidade,

            "vlrUnitario":
                preco,

            "vlrDesconto":
                0,

            "vlrTotal":
                total,
        })

    if not itens:

        raise Exception(
            "O pedido não possui produtos."
        )

    return itens


# ============================================================
# MONTAR PEDIDO ZETTI
# ============================================================

def montar_pedido_zetti(pedido):

    cliente = montar_cliente_zetti(
        pedido
    )

    itens = montar_itens_zetti(
        pedido
    )

    total = float(
        pedido.get(
            "total",
            0
        )
    )

    subtotal = float(
        pedido.get(
            "subtotal",
            0
        )
    )

    desconto = float(
        pedido.get(
            "discount",
            0
        )
        or 0
    )

    # --------------------------------------------------------
    # CALCULAR FRETE
    # --------------------------------------------------------

    frete = (
        total
        - subtotal
        + desconto
    )

    if frete < 0:

        frete = 0

    # --------------------------------------------------------
    # STATUS DO PEDIDO NA ZETTI
    # --------------------------------------------------------

    payment_status = pedido.get(
        "payment_status"
    )

    if payment_status == "paid":

        status_zetti = "Pago"

    else:

        status_zetti = "PagamentoNaEntrega"

    # --------------------------------------------------------
    # RETIRADA OU ENTREGA
    # --------------------------------------------------------

    retirar = pedido_e_retirada(
        pedido
    )
    pagamentos = montar_pagamentos_zetti(
    pedido
)
    # --------------------------------------------------------
    # PAYLOAD
    # --------------------------------------------------------

    payload = {

        # "cdOrigem":
        #     0,

        "cdFilial":
            int(
                getattr(
                    settings,
                    "ZETTI_CD_FILIAL",
                    1
                )
            ),

        "nrPedido":
            str(
                f"bob_1{pedido.get('number')}"
            ),
            "cdVendedor":202,

        "dtEmissao":
            pedido.get(
                "created_at"
            ),

        "cliente":
            cliente,

        "vlrProdutos":
            subtotal,

        "vlrDescontos":
            desconto,

        "vlrFrete":
            frete,

        "vlrTotal":
            total,

        "observacao":
            (
                "Pedido Nuvemshop "
                f"#{pedido.get('number')}"
            ),

        # ----------------------------------------------------
        # TRUE  = retirada
        # FALSE = entrega
        # ----------------------------------------------------

        "retirar":
            retirar,

        "itens":
            itens,

        "statusPedido":
            status_zetti,

        "pagamentos": pagamentos,
    }

    return payload


# ============================================================
# ENVIAR PEDIDO PARA ZETTI
# ============================================================

def enviar_pedido_zetti(pedido):

    token = getattr(
        settings,
        "ZETTI_API_TOKEN",
        ""
    )

    if not token:

        raise Exception(
            "ZETTI_API_TOKEN não configurado."
        )

    payload = montar_pedido_zetti(
        pedido
    )

    # --------------------------------------------------------
    # MOSTRAR PAYLOAD NO TERMINAL
    # --------------------------------------------------------

    print("=" * 80)
    print("PAYLOAD ENVIADO PARA ZETTI")
    print(payload)
    print("=" * 80)

    headers = {

        "Authorization":
            f"ApiKey {token}",

        "Content-Type":
            "application/json",
    }

    response = requests.post(

        f"{ZETTI_URL}/pedidos",

        headers=headers,

        json=payload,

        timeout=30,
    )

    # --------------------------------------------------------
    # TENTAR LER JSON
    # --------------------------------------------------------

    try:

        resultado = response.json()

    except ValueError:

        resultado = {}

    # --------------------------------------------------------
    # ERRO HTTP
    # --------------------------------------------------------

    if not response.ok:

        mensagem = (

            resultado.get("msg")

            or resultado.get("mensagem")

            or response.text

            or "Erro desconhecido."
        )

        raise Exception(
            f"Zetti HTTP {response.status_code}: "
            f"{mensagem}"
        )

    # --------------------------------------------------------
    # ERRO DA API
    # --------------------------------------------------------

    if resultado.get("status") != 200:

        raise Exception(

            resultado.get("msg")

            or "A Zetti recusou o pedido."
        )

    return resultado


# ============================================================
# ENVIAR PARA O PDV
# ============================================================

def enviar_para_pdv(
    request,
    pedido_id
):

    if request.method != "POST":

        return redirect(
            "lista_pedidos"
        )

    # --------------------------------------------------------
    # BUSCAR PEDIDOS NA NUVEMSHOP
    # --------------------------------------------------------

    try:

        pedidos = buscar_pedidos_nuvemshop()

    except Exception as e:

        messages.error(
            request,
            f"Erro ao consultar pedido: {e}"
        )

        return redirect(
            "lista_pedidos"
        )

    # --------------------------------------------------------
    # LOCALIZAR PEDIDO
    # --------------------------------------------------------

    pedido = None

    for item in pedidos:

        if str(
            item.get("id")
        ) == str(pedido_id):

            pedido = item

            break

    if not pedido:

        messages.error(
            request,
            "Pedido não encontrado."
        )

        return redirect(
            "lista_pedidos"
        )

    # --------------------------------------------------------
    # EVITAR PEDIDO CANCELADO
    # --------------------------------------------------------

    if pedido.get("status") == "cancelled":

        messages.error(
            request,
            "Pedido cancelado não pode ser enviado ao PDV."
        )

        return redirect(
            "lista_pedidos"
        )

    # --------------------------------------------------------
    # EVITAR PEDIDO JÁ ENTREGUE
    # --------------------------------------------------------

    if pedido.get("status") == "delivered":

        messages.error(
            request,
            "Pedido já entregue não pode ser enviado ao PDV."
        )

        return redirect(
            "lista_pedidos"
        )

    # --------------------------------------------------------
    # IDENTIFICAR TIPO DE ENTREGA
    # --------------------------------------------------------

    retirar = pedido_e_retirada(
        pedido
    )

    if retirar:

        print(
            f"Pedido #{pedido.get('number')} "
            f"é RETIRADA NO LOCAL."
        )

    else:

        print(
            f"Pedido #{pedido.get('number')} "
            f"é DELIVERY/ENTREGA."
        )

    # --------------------------------------------------------
    # ENVIAR
    # --------------------------------------------------------

    try:

        resultado = enviar_pedido_zetti(
            pedido
        )

        dados = (
            resultado.get("data")
            or {}
        )

        cd_orcamento = dados.get(
            "cdOrcamento"
        )

        situacao = dados.get(
            "situacao"
        )

        mensagem = (

            dados.get("mensagem")

            or resultado.get("msg")

            or "Pedido enviado com sucesso."
        )

        # ----------------------------------------------------
        # GUARDAR NA SESSÃO
        # ----------------------------------------------------

        pedidos_zetti = request.session.get(
            "pedidos_zetti",
            {}
        )

        pedidos_zetti[
            str(pedido_id)
        ] = {

            "cdOrcamento":
                cd_orcamento,

            "situacao":
                situacao,

            "mensagem":
                mensagem,

            "retirar":
                retirar,
        }

        request.session[
            "pedidos_zetti"
        ] = pedidos_zetti

        # ----------------------------------------------------
        # MENSAGEM DE SUCESSO
        # ----------------------------------------------------

        tipo_pedido = (
            "Retirada no local"
            if retirar
            else "Delivery"
        )

        messages.success(
            request,
            (
                f"Pedido #{pedido.get('number')} "
                f"enviado para o PDV. "
                f"Tipo: {tipo_pedido}. "
                f"Orçamento Zetti: "
                f"{cd_orcamento}"
            )
        )

    except Exception as e:

        messages.error(
            request,
            f"Erro ao enviar para o PDV: {e}"
        )

    return redirect(
        "lista_pedidos"
    )





def obter_uf(endereco):

    uf = endereco.get("province", "")

    if not uf:
        return ""

    mapa_ufs = {

        "Acre": "AC",
        "Alagoas": "AL",
        "Amapá": "AP",
        "Amazonas": "AM",
        "Bahia": "BA",
        "Ceará": "CE",
        "Distrito Federal": "DF",
        "Espírito Santo": "ES",
        "Goiás": "GO",
        "Maranhão": "MA",
        "Mato Grosso": "MT",
        "Mato Grosso do Sul": "MS",
        "Minas Gerais": "MG",
        "Pará": "PA",
        "Paraíba": "PB",
        "Paraná": "PR",
        "Pernambuco": "PE",
        "Piauí": "PI",
        "Rio de Janeiro": "RJ",
        "Rio Grande do Norte": "RN",
        "Rio Grande do Sul": "RS",
        "Rondônia": "RO",
        "Roraima": "RR",
        "Santa Catarina": "SC",
        "São Paulo": "SP",
        "Sergipe": "SE",
        "Tocantins": "TO",

    }

    # Se já vier como DF, SP, GO etc.
    if len(uf) == 2:
        return uf.upper()

    return mapa_ufs.get(
        uf,
        ""
    )

def montar_pagamentos_zetti(pedido):

    payment_status = pedido.get(
        "payment_status"
    )

    # --------------------------------------------------------
    # SE NÃO ESTÁ PAGO
    # --------------------------------------------------------

    if payment_status != "paid":

        return []

    payment_details = (
        pedido.get("payment_details")
        or {}
    )

    metodo = payment_details.get(
        "method"
    )

    valor = float(
        pedido.get(
            "total",
            0
        )
        or 0
    )

    # --------------------------------------------------------
    # CONVERTER MÉTODO NUVEMSHOP → ZETTI
    # --------------------------------------------------------

    mapa_pagamentos = {

        "credit_card":
            "CartaoCredito",

        "debit_card":
            "CartaoDebito",

        "pix":
            "Pix",

        "boleto":
            "BoletoBancario",

    }

    forma_pagamento = mapa_pagamentos.get(
        metodo
    )

    if not forma_pagamento:

        raise Exception(
            (
                f"Método de pagamento "
                f"'{metodo}' não possui "
                f"mapeamento para a Zetti."
            )
        )

    # --------------------------------------------------------
    # MONTAR PAGAMENTO
    # --------------------------------------------------------

    pagamento = {

        "formaPagamento":
            forma_pagamento,

        "valor":
            valor,

        "nrAutorizacao":
            str(
                pedido.get(
                    "gateway_id",
                    ""
                )
                or ""
            ),

        "qtdParcelas":
            int(
                payment_details.get(
                    "installments",
                    1
                )
                or 1
            ),

    }

    return [
        pagamento
    ]
