from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

import requests


from .services.nuvemshop import NuvemshopAPI
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
# TIPO DE ENTREGA
# ============================================================

def obter_tipo_entrega(pedido):
    

    if not isinstance(pedido, dict):
        return "delivery"


    
        
    fulfillments = pedido.get("same_billing_and_shipping_address") or []

    if not isinstance(fulfillments, list):
        return "delivery"

    if fulfillments == True:
        retirar = "delivery"
    else:
        retirar ='retirar'

    return retirar


# ============================================================
# LISTAR PEDIDOS
# ============================================================

@login_required
def lista_pedidos(request):

    status = request.GET.get(
        "status",
        ""
    )

    api = NuvemshopAPI()

    try:

        pedidos = api.listar_pedidos(
            status
        )

    except Exception as exc:

        messages.error(
            request,
            f"Erro ao consultar Nuvemshop: {exc}",
        )

        pedidos = []

    # --------------------------------------------------------
    # Adicionar informações de entrega
    # --------------------------------------------------------

    for pedido in pedidos:

        tipo_entrega = obter_tipo_entrega(
            pedido
        )

        pedido["tipo_entrega"] = (
            tipo_entrega
        )

        pedido["retirar"] = (
            tipo_entrega == "retirada"
        )

    return render(
        request,
        "lista.html",
        {
            "pedidos": pedidos,
            "status_atual": status,
        },
    )


# ============================================================
# CONFERIR PEDIDO
# ============================================================

@login_required
def conferir_pedido(
    request,
    pedido_id
):

    api = NuvemshopAPI()

    # --------------------------------------------------------
    # BUSCAR PEDIDO
    # --------------------------------------------------------

    try:

        pedido = api.buscar_pedido(
            pedido_id
        )

    except Exception as exc:

        messages.error(
            request,
            f"Erro ao buscar pedido: {exc}",
        )

        return redirect(
            "lista_pedidos"
        )

    # --------------------------------------------------------
    # VALIDAR PEDIDO
    # --------------------------------------------------------

    if not isinstance(
        pedido,
        dict
    ):

        messages.error(
            request,
            "Resposta inválida da Nuvemshop.",
        )

        return redirect(
            "lista_pedidos"
        )

    # --------------------------------------------------------
    # CANCELADO
    # --------------------------------------------------------

    if pedido.get("status") == "cancelled":

        messages.error(
            request,
            "Pedido cancelado não pode ser conferido.",
        )

        return redirect(
            "lista_pedidos"
        )

    # --------------------------------------------------------
    # TIPO DE ENTREGA
    # --------------------------------------------------------

    # tipo_entrega = obter_tipo_entrega(
    #     pedido
    # )
    
    tipo_entrega = pedido.get("same_billing_and_shipping_address")

    if tipo_entrega == True:
        retirar = "delivery"
    else:
        retirar ='retirar'

    # retirar = (tipo_entrega == "retirada")

    # pedidoentrega = pedido.get("same_billing_and_shipping_address")
    pedidoentrega = pedido
    print(f'test - {pedidoentrega}')

    # --------------------------------------------------------
    # PRODUTOS
    # --------------------------------------------------------

    produtos = pedido.get(
        "products"
    ) or []

    if not isinstance(
        produtos,
        list
    ):

        produtos = []

    itens = []

    for produto in produtos:

        if not isinstance(
            produto,
            dict
        ):
            continue

        sku = str(
            produto.get("sku") or ""
        ).strip()

        barcode = str(
            produto.get("barcode") or ""
        ).strip()

        try:

            quantidade = int(
                float(
                    produto.get(
                        "quantity"
                    ) or 0
                )
            )

        except (
            ValueError,
            TypeError
        ):

            quantidade = 0

        itens.append(
            {
                "product_id":
                    produto.get(
                        "product_id"
                    ),

                "name":
                    produto.get(
                        "name",
                        ""
                    ),

                "sku":
                    sku,

                "barcode":
                    barcode,

                "quantity":
                    quantidade,
            }
        )

    # --------------------------------------------------------
    # SESSÃO DA CONFERÊNCIA
    # --------------------------------------------------------

    session_key = (
        f"conferencia_{pedido_id}"
    )

    conferencia = request.session.get(
        session_key
    )

    # --------------------------------------------------------
    # INICIALIZAR CONFERÊNCIA
    # --------------------------------------------------------

    if not isinstance(
        conferencia,
        dict
    ):

        conferencia = {
            "pedido_id":
                str(pedido_id),

            "itens":
                {},

            "finalizado":
                False,
        }

        for item in itens:

            product_id = str(
                item.get(
                    "product_id"
                )
            )

            conferencia[
                "itens"
            ][product_id] = {
                "conferido": 0
            }

        request.session[
            session_key
        ] = conferencia

        request.session.modified = True

    # --------------------------------------------------------
    # GARANTIR ESTRUTURA
    # --------------------------------------------------------

    itens_conferencia = (
        conferencia.setdefault(
            "itens",
            {}
        )
    )

    if not isinstance(
        itens_conferencia,
        dict
    ):

        itens_conferencia = {}

        conferencia[
            "itens"
        ] = itens_conferencia

    # --------------------------------------------------------
    # ADICIONAR QUANTIDADE CONFERIDA
    # --------------------------------------------------------

    for item in itens:

        product_id = str(
            item.get(
                "product_id"
            )
        )

        dados_item = (
            conferencia
            .get("itens", {})
            .get(product_id, {})
        )

        if not isinstance(
            dados_item,
            dict
        ):

            dados_item = {
                "conferido": 0
            }

        try:

            conferido = int(
                dados_item.get(
                    "conferido",
                    0
                )
                or 0
            )

        except (
            ValueError,
            TypeError
        ):

            conferido = 0

        item["conferido"] = (
            conferido
        )

        item["completo"] = (
            conferido
            >= item["quantity"]
        )

    # --------------------------------------------------------
    # TOTAIS
    # --------------------------------------------------------

    total_itens = sum(
        item["quantity"]
        for item in itens
    )

    total_conferido = sum(
        item["conferido"]
        for item in itens
    )

    conferencia_completa = (
        total_itens > 0
        and total_conferido >= total_itens
    )

    # --------------------------------------------------------
    # SALVAR SESSÃO
    # --------------------------------------------------------

    request.session[
        session_key
    ] = conferencia

    request.session.modified = True

    # --------------------------------------------------------
    # DEBUG
    # --------------------------------------------------------

    print("=" * 80)
    print(
        f"PEDIDO #{pedido.get('number')}"
    )
    print(
        f"TIPO ENTREGA: {tipo_entrega}"
    )
    print(
        f"RETIRAR: {retirar}"
    )
    print("=" * 80)

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render(
        request,
        "conferir_pedido.html",
        {
            "pedido":
                pedido,

            "itens":
                itens,

            "total_itens":
                total_itens,

            "total_conferido":
                total_conferido,

            "conferencia_completa":
                conferencia_completa,

            "retirar":
                retirar,

            "tipo_entrega":
                tipo_entrega,
        },
    )


# ============================================================
# BIPAR PRODUTO
# ============================================================

@login_required
@require_POST
def bipar_produto(
    request,
    pedido_id
):

    codigo = str(
        request.POST.get(
            "codigo"
        ) or ""
    ).strip()

    # --------------------------------------------------------
    # CÓDIGO VAZIO
    # --------------------------------------------------------

    if not codigo:

        return JsonResponse(
            {
                "ok":
                    False,

                "mensagem":
                    "Código de barras vazio.",
            },
            status=400,
        )

    api = NuvemshopAPI()

    # --------------------------------------------------------
    # BUSCAR PEDIDO
    # --------------------------------------------------------

    try:

        pedido = api.buscar_pedido(
            pedido_id
        )

    except Exception as exc:

        return JsonResponse(
            {
                "ok":
                    False,

                "mensagem":
                    (
                        "Erro ao consultar "
                        f"Nuvemshop: {exc}"
                    ),
            },
            status=500,
        )

    if not isinstance(
        pedido,
        dict
    ):

        return JsonResponse(
            {
                "ok":
                    False,

                "mensagem":
                    "Pedido inválido.",
            },
            status=500,
        )

    # --------------------------------------------------------
    # CONFERÊNCIA
    # --------------------------------------------------------

    session_key = (
        f"conferencia_{pedido_id}"
    )

    conferencia = request.session.get(
        session_key
    )

    if not isinstance(
        conferencia,
        dict
    ):

        return JsonResponse(
            {
                "ok":
                    False,

                "mensagem":
                    (
                        "Conferência não encontrada. "
                        "Volte para a lista e abra "
                        "o pedido novamente."
                    ),
            },
            status=400,
        )

    # --------------------------------------------------------
    # NÃO PERMITIR BIPAR FINALIZADO
    # --------------------------------------------------------

    if conferencia.get(
        "finalizado"
    ):

        return JsonResponse(
            {
                "ok":
                    False,

                "mensagem":
                    (
                        "Este pedido já foi finalizado "
                        "e enviado para a Zetti."
                    ),
            },
            status=400,
        )

    # --------------------------------------------------------
    # PROCURAR PRODUTO
    # --------------------------------------------------------

    produto_encontrado = None

    produtos = pedido.get(
        "products"
    ) or []

    for produto in produtos:

        if not isinstance(
            produto,
            dict
        ):
            continue

        sku = str(
            produto.get("sku") or ""
        ).strip()

        barcode = str(
            produto.get("barcode") or ""
        ).strip()

        if (
            codigo == sku
            or codigo == barcode
        ):

            produto_encontrado = produto

            break

    # --------------------------------------------------------
    # NÃO ENCONTRADO
    # --------------------------------------------------------

    if not produto_encontrado:

        return JsonResponse(
            {
                "ok":
                    False,

                "tipo":
                    "produto_incorreto",

                "mensagem":
                    (
                        f"O código {codigo} "
                        "não pertence a este pedido."
                    ),
            },
            status=400,
        )

    # --------------------------------------------------------
    # PRODUCT ID
    # --------------------------------------------------------

    product_id = str(
        produto_encontrado.get(
            "product_id"
        )
    )

    # --------------------------------------------------------
    # QUANTIDADE ESPERADA
    # --------------------------------------------------------

    try:

        quantidade_esperada = int(
            float(
                produto_encontrado.get(
                    "quantity"
                ) or 0
            )
        )

    except (
        ValueError,
        TypeError
    ):

        quantidade_esperada = 0

    # --------------------------------------------------------
    # ITENS DA CONFERÊNCIA
    # --------------------------------------------------------

    itens_conferencia = (
        conferencia.setdefault(
            "itens",
            {}
        )
    )

    if not isinstance(
        itens_conferencia,
        dict
    ):

        itens_conferencia = {}

        conferencia[
            "itens"
        ] = itens_conferencia

    item_conferencia = (
        itens_conferencia.setdefault(
            product_id,
            {
                "conferido": 0
            }
        )
    )

    if not isinstance(
        item_conferencia,
        dict
    ):

        item_conferencia = {
            "conferido": 0
        }

        itens_conferencia[
            product_id
        ] = item_conferencia

    try:

        conferido = int(
            item_conferencia.get(
                "conferido",
                0
            )
            or 0
        )

    except (
        ValueError,
        TypeError
    ):

        conferido = 0

    # --------------------------------------------------------
    # QUANTIDADE EXCEDIDA
    # --------------------------------------------------------

    if conferido >= quantidade_esperada:

        return JsonResponse(
            {
                "ok":
                    False,

                "tipo":
                    "quantidade_excedida",

                "mensagem":
                    (
                        f"{produto_encontrado.get('name', '')} "
                        "já foi totalmente conferido."
                    ),

                "produto":
                    produto_encontrado.get(
                        "name",
                        ""
                    ),

                "esperado":
                    quantidade_esperada,

                "conferido":
                    conferido,
            },
            status=400,
        )

    # --------------------------------------------------------
    # REGISTRAR BIP
    # --------------------------------------------------------

    conferido += 1

    item_conferencia[
        "conferido"
    ] = conferido

    itens_conferencia[
        product_id
    ] = item_conferencia

    conferencia[
        "itens"
    ] = itens_conferencia

    request.session[
        session_key
    ] = conferencia

    request.session.modified = True

    # --------------------------------------------------------
    # CALCULAR PROGRESSO
    # --------------------------------------------------------

    total_esperado = 0
    total_conferido = 0

    for produto in produtos:

        if not isinstance(
            produto,
            dict
        ):
            continue

        pid = str(
            produto.get(
                "product_id"
            )
        )

        try:

            esperado = int(
                float(
                    produto.get(
                        "quantity"
                    ) or 0
                )
            )

        except (
            ValueError,
            TypeError
        ):

            esperado = 0

        dados = (
            conferencia
            .get("itens", {})
            .get(pid, {})
        )

        if not isinstance(
            dados,
            dict
        ):

            dados = {}

        try:

            atual = int(
                dados.get(
                    "conferido",
                    0
                )
                or 0
            )

        except (
            ValueError,
            TypeError
        ):

            atual = 0

        total_esperado += esperado
        total_conferido += atual

    completa = (
        total_esperado > 0
        and total_conferido >= total_esperado
    )

    # --------------------------------------------------------
    # RESPOSTA
    # --------------------------------------------------------

    return JsonResponse(
        {
            "ok":
                True,

            "produto":
                produto_encontrado.get(
                    "name",
                    ""
                ),

            "product_id":
                product_id,

            "sku":
                str(
                    produto_encontrado.get(
                        "sku"
                    ) or ""
                ),

            "barcode":
                str(
                    produto_encontrado.get(
                        "barcode"
                    ) or ""
                ),

            "conferido":
                conferido,

            "esperado":
                quantidade_esperada,

            "total_conferido":
                total_conferido,

            "total_esperado":
                total_esperado,

            "completa":
                completa,
        }
    )


# ============================================================
# FINALIZAR CONFERÊNCIA
# ============================================================

@login_required
@require_POST
def finalizar_conferencia(
    request,
    pedido_id
):

    session_key = (
        f"conferencia_{pedido_id}"
    )

    conferencia = request.session.get(
        session_key
    )

    if not isinstance(
        conferencia,
        dict
    ):

        messages.error(
            request,
            "Conferência não encontrada.",
        )

        return redirect(
            "lista_pedidos"
        )

    # --------------------------------------------------------
    # NÃO DUPLICAR ENVIO
    # --------------------------------------------------------

    if conferencia.get(
        "finalizado"
    ):

        messages.warning(
            request,
            "Este pedido já foi enviado para a Zetti.",
        )

        return redirect(
            "lista_pedidos"
        )

    api = NuvemshopAPI()

    # --------------------------------------------------------
    # BUSCAR PEDIDO
    # --------------------------------------------------------

    try:

        pedido = api.buscar_pedido(
            pedido_id
        )

    except Exception as exc:

        messages.error(
            request,
            f"Erro ao buscar pedido: {exc}",
        )

        return redirect(
            "lista_pedidos"
        )

    if not isinstance(
        pedido,
        dict
    ):

        messages.error(
            request,
            "Pedido inválido.",
        )

        return redirect(
            "lista_pedidos"
        )

    # --------------------------------------------------------
    # CANCELADO
    # --------------------------------------------------------

    if pedido.get(
        "status"
    ) == "cancelled":

        messages.error(
            request,
            "Pedido cancelado não pode ser enviado para a Zetti.",
        )

        return redirect(
            "lista_pedidos"
        )

    # --------------------------------------------------------
    # VALIDAR TODOS OS PRODUTOS
    # --------------------------------------------------------

    faltando = []

    produtos = (
        pedido.get(
            "products"
        )
        or []
    )

    for produto in produtos:

        if not isinstance(
            produto,
            dict
        ):
            continue

        product_id = str(
            produto.get(
                "product_id"
            )
        )

        try:

            esperado = int(
                float(
                    produto.get(
                        "quantity"
                    ) or 0
                )
            )

        except (
            ValueError,
            TypeError
        ):

            esperado = 0

        dados_item = (
            conferencia
            .get("itens", {})
            .get(product_id, {})
        )

        if not isinstance(
            dados_item,
            dict
        ):

            dados_item = {}

        try:

            conferido = int(
                dados_item.get(
                    "conferido",
                    0
                )
                or 0
            )

        except (
            ValueError,
            TypeError
        ):

            conferido = 0

        if conferido < esperado:

            faltando.append(
                (
                    produto.get(
                        "name",
                        ""
                    ),

                    esperado - conferido,
                )
            )

    # --------------------------------------------------------
    # TEM PRODUTO FALTANDO
    # --------------------------------------------------------

    if faltando:

        mensagens_faltando = ", ".join(
            f"{nome} ({qtd})"
            for nome, qtd in faltando
        )

        messages.error(
            request,
            (
                "Pedido ainda não foi totalmente "
                "conferido. "
                f"Faltando: {mensagens_faltando}"
            ),
        )

        return redirect(
            "conferir_pedido",
            pedido_id=pedido_id,
        )

    # --------------------------------------------------------
    # TIPO DE ENTREGA
    # --------------------------------------------------------

    # tipo_entrega = obter_tipo_entrega(
    #     pedido
    # )
    tipo_entrega = obter_tipo_entrega (pedido)

    retirar = (
        tipo_entrega == "retirada"
    )

    print("=" * 80)
    print("FINALIZANDO CONFERÊNCIA")
    print(
        "PEDIDO:",
        pedido.get("number")
    )
    print(
        "TIPO:",
        tipo_entrega
    )
    print(
        "RETIRAR:",
        retirar
    )
    print("=" * 80)

    # --------------------------------------------------------
    # ENVIAR PARA ZETTI
    # --------------------------------------------------------

    try:

        resultado = enviar_pedido_zetti(
            pedido
        )

    except Exception as exc:

        messages.error(
            request,
            f"Erro ao enviar para Zetti: {exc}",
        )

        return redirect(
            "conferir_pedido",
            pedido_id=pedido_id,
        )

    # --------------------------------------------------------
    # MARCAR COMO FINALIZADO
    # --------------------------------------------------------

    conferencia[
        "finalizado"
    ] = True

    conferencia[
        "resultado_zetti"
    ] = resultado

    conferencia[
        "tipo_entrega"
    ] = tipo_entrega

    conferencia[
        "retirar"
    ] = retirar

    request.session[
        session_key
    ] = conferencia

    request.session.modified = True

    # --------------------------------------------------------
    # RESULTADO ZETTI
    # --------------------------------------------------------

    dados = (
        resultado.get(
            "data"
        )
        or {}
    )

    if not isinstance(
        dados,
        dict
    ):

        dados = {}

    cd_orcamento = dados.get(
        "cdOrcamento"
    )

    messages.success(
        request,
        (
            f"Pedido #{pedido.get('number')} "
            f"conferido e enviado para a Zetti. "
            
            f"Orçamento: {cd_orcamento}"
        ),
    )

    return redirect(
        "lista_pedidos"
    )


# ============================================================
# BUSCAR PEDIDOS DIRETAMENTE NA NUVEMSHOP
# ============================================================

def buscar_pedidos_nuvemshop(
    status_atual=""
):

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
        "Authorization":
            f"Bearer {access_token}",

        "User-Agent":
            "Sistema de Entregas",

        "Content-Type":
            "application/json",
    }

    params = {
        "per_page": 100,
    }

    if status_atual:

        params[
            "status"
        ] = status_atual

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    pedidos = response.json()

    if not isinstance(
        pedidos,
        list
    ):

        return []

    return pedidos


# ============================================================
# PREPARAR STATUS
# ============================================================

def preparar_status(
    pedidos
):

    if not isinstance(
        pedidos,
        list
    ):

        return []

    for pedido in pedidos:

        if not isinstance(
            pedido,
            dict
        ):
            continue

        # ----------------------------------------------------
        # PEDIDO
        # ----------------------------------------------------

        codigo = pedido.get(
            "status"
        )

        pedido[
            "status_pedido_texto"
        ] = STATUS_PEDIDO.get(
            codigo,
            codigo or "-"
        )

        # ----------------------------------------------------
        # PAGAMENTO
        # ----------------------------------------------------

        codigo = pedido.get(
            "payment_status"
        )

        pedido[
            "status_pagamento_texto"
        ] = STATUS_PAGAMENTO.get(
            codigo,
            codigo or "-"
        )

        # ----------------------------------------------------
        # ENVIO
        # ----------------------------------------------------

        codigo = pedido.get(
            "shipping_status"
        )

        pedido[
            "status_envio_texto"
        ] = STATUS_ENVIO.get(
            codigo,
            codigo or "-"
        )

        # ----------------------------------------------------
        # TIPO ENTREGA
        # ----------------------------------------------------

        tipo_entrega = obter_tipo_entrega(
            pedido
        )

        pedido[
            "tipo_entrega"
        ] = tipo_entrega

        pedido[
            "retirar"
        ] = (
            tipo_entrega == "retirada"
        )

    return pedidos


# ============================================================
# MONTAR CLIENTE ZETTI
# ============================================================

def montar_cliente_zetti(
    pedido
):

    endereco = (
        pedido.get(
            "shipping_address"
        )
        or {}
    )

    if not isinstance(
        endereco,
        dict
    ):

        endereco = {}

    cliente = (
        pedido.get(
            "customer"
        )
        or {}
    )

    if not isinstance(
        cliente,
        dict
    ):

        cliente = {}

    nome = (
        pedido.get(
            "contact_name"
        )

        or cliente.get(
            "name"
        )

        or endereco.get(
            "name"
        )

        or "CLIENTE"
    )

    cpf = (
        pedido.get(
            "contact_identification"
        )

        or cliente.get(
            "identification"
        )

        or ""
    )

    telefone = (
        pedido.get(
            "contact_phone"
        )

        or cliente.get(
            "phone"
        )

        or endereco.get(
            "phone"
        )

        or ""
    )

    email = (
        pedido.get(
            "contact_email"
        )

        or cliente.get(
            "email"
        )

        or ""
    )

    numero = (
        endereco.get(
            "number"
        )
        or "SN"
    )

    return {

        "nome":
            nome,

        "cpfCgc":
            cpf,

        "telefone":
            telefone,

        "endereco":
            endereco.get(
                "address",
                ""
            ),

        "numero":
            numero,

        "complemento":
            endereco.get(
                "floor",
                ""
            ),

        "cep":
            endereco.get(
                "zipcode",
                ""
            ),

        "bairro":
            endereco.get(
                "locality",
                ""
            ),

        "cidade":
            endereco.get(
                "city",
                ""
            ),

        "uf":
            obter_uf(
                endereco
            ),

        "referencia":
            (
                endereco.get(
                    "customs"
                )
                or ""
            ),

        "email":
            email,
    }


# ============================================================
# MONTAR ITENS ZETTI
# ============================================================

def montar_itens_zetti(
    pedido
):

    itens = []

    produtos = (
        pedido.get(
            "products"
        )
        or []
    )

    if not isinstance(
        produtos,
        list
    ):

        produtos = []

    for produto in produtos:

        if not isinstance(
            produto,
            dict
        ):

            continue

        sku = (
            produto.get(
                "sku"
            )
        )

        # ----------------------------------------------------
        # SKU OBRIGATÓRIO
        # ----------------------------------------------------

        if not sku:

            raise Exception(
                (
                    f"O produto "
                    f"'{produto.get('name', '-')}' "
                    "não possui SKU. "
                    "Não é possível enviar para o PDV."
                )
            )

        # ----------------------------------------------------
        # SKU NUMÉRICO
        # ----------------------------------------------------

        try:

            cd_produto = int(
                str(sku).strip()
            )

        except (
            ValueError,
            TypeError
        ):

            raise Exception(
                (
                    f"O SKU '{sku}' "
                    f"do produto "
                    f"'{produto.get('name', '-')}' "
                    "não é numérico."
                )
            )

        # ----------------------------------------------------
        # QUANTIDADE
        # ----------------------------------------------------

        try:

            quantidade = float(
                produto.get(
                    "quantity",
                    0
                )
                or 0
            )

        except (
            ValueError,
            TypeError
        ):

            quantidade = 0

        # ----------------------------------------------------
        # PREÇO
        # ----------------------------------------------------

        try:

            preco = float(
                produto.get(
                    "price",
                    0
                )
                or 0
            )

        except (
            ValueError,
            TypeError
        ):

            preco = 0

        total = (
            quantidade
            * preco
        )

        # ----------------------------------------------------
        # ITEM
        # ----------------------------------------------------

        itens.append(
            {
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
                            "barcode"
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
            }
        )

    # --------------------------------------------------------
    # SEM PRODUTOS
    # --------------------------------------------------------

    if not itens:

        raise Exception(
            "O pedido não possui produtos."
        )

    return itens


# ============================================================
# MONTAR PAGAMENTOS ZETTI
# ============================================================

def montar_pagamentos_zetti(
    pedido
):

    payment_status = pedido.get(
        "payment_status"
    )

    # --------------------------------------------------------
    # NÃO PAGO
    # --------------------------------------------------------

    if payment_status != "paid":

        return []

    payment_details = (
        pedido.get(
            "payment_details"
        )
        or {}
    )

    if not isinstance(
        payment_details,
        dict
    ):

        payment_details = {}

    metodo = payment_details.get(
        "method"
    )

    # --------------------------------------------------------
    # VALOR
    # --------------------------------------------------------

    try:

        valor = float(
            pedido.get(
                "total",
                0
            )
            or 0
        )

    except (
        ValueError,
        TypeError
    ):

        valor = 0

    # --------------------------------------------------------
    # MAPA PAGAMENTOS
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

    forma_pagamento = (
        mapa_pagamentos.get(
            metodo
        )
    )

    if not forma_pagamento:

        raise Exception(
            (
                f"Método de pagamento "
                f"'{metodo}' não possui "
                "mapeamento para a Zetti."
            )
        )

    # --------------------------------------------------------
    # PARCELAS
    # --------------------------------------------------------

    try:

        parcelas = int(
            payment_details.get(
                "installments",
                1
            )
            or 1
        )

    except (
        ValueError,
        TypeError
    ):

        parcelas = 1

    # --------------------------------------------------------
    # PAGAMENTO
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
            parcelas,
    }

    return [
        pagamento
    ]


# ============================================================
# MONTAR PEDIDO ZETTI
# ============================================================

def montar_pedido_zetti(
    pedido
):

    # --------------------------------------------------------
    # CLIENTE
    # --------------------------------------------------------

    cliente = montar_cliente_zetti(
        pedido
    )

    # --------------------------------------------------------
    # ITENS
    # --------------------------------------------------------

    itens = montar_itens_zetti(
        pedido
    )

    # --------------------------------------------------------
    # VALORES
    # --------------------------------------------------------

    try:

        total = float(
            pedido.get(
                "total",
                0
            )
            or 0
        )

    except (
        ValueError,
        TypeError
    ):

        total = 0

    try:

        subtotal = float(
            pedido.get(
                "subtotal",
                0
            )
            or 0
        )

    except (
        ValueError,
        TypeError
    ):

        subtotal = 0

    try:

        desconto = float(
            pedido.get(
                "discount",
                0
            )
            or 0
        )

    except (
        ValueError,
        TypeError
    ):

        desconto = 0

    # --------------------------------------------------------
    # FRETE
    # --------------------------------------------------------

    frete = (
        total
        - subtotal
        + desconto
    )

    if frete < 0:

        frete = 0

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    payment_status = pedido.get(
        "payment_status"
    )

    if payment_status == "paid":

        status_zetti = "Pago"

    else:

        status_zetti = (
            "PagamentoNaEntrega"
        )

    # --------------------------------------------------------
    # RETIRADA / DELIVERY
    # --------------------------------------------------------

    tipo_entrega = obter_tipo_entrega(
        pedido
    )

    retirar = (
        tipo_entrega == "retirada"
    )

    # --------------------------------------------------------
    # PAGAMENTOS
    # --------------------------------------------------------

    pagamentos = (
        montar_pagamentos_zetti(
            pedido
        )
    )

    # --------------------------------------------------------
    # FILIAL
    # --------------------------------------------------------

    try:

        cd_filial = int(
            getattr(
                settings,
                "ZETTI_CD_FILIAL",
                1
            )
        )

    except (
        ValueError,
        TypeError
    ):

        cd_filial = 1

    # --------------------------------------------------------
    # PAYLOAD
    # --------------------------------------------------------

    payload = {

        "cdFilial":
            cd_filial,

        "nrPedido":
            str(
                f"bob_1{pedido.get('number')}"
            ),

        "cdVendedor":
            202,

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
        # IMPORTANTE
        #
        # True  = RETIRADA
        # False = DELIVERY
        # ----------------------------------------------------

        "retirar":
            retirar,

        "itens":
            itens,

        "statusPedido":
            status_zetti,

        "pagamentos":
            pagamentos,
    }

    # --------------------------------------------------------
    # DEBUG
    # --------------------------------------------------------

    print("=" * 80)
    print("MONTANDO PEDIDO ZETTI")
    print(
        "PEDIDO:",
        pedido.get("number")
    )
    print(
        "TIPO ENTREGA:",
        tipo_entrega
    )
    print(
        "RETIRAR:",
        retirar
    )
    print(
        "FULFILLMENTS:",
        pedido.get("fulfillments")
    )
    print("=" * 80)

    return payload


# ============================================================
# ENVIAR PEDIDO PARA ZETTI
# ============================================================

def enviar_pedido_zetti(
    pedido
):

    token = getattr(
        settings,
        "ZETTI_API_TOKEN",
        ""
    )

    if not token:

        raise Exception(
            "ZETTI_API_TOKEN não configurado."
        )

    # --------------------------------------------------------
    # MONTAR PAYLOAD
    # --------------------------------------------------------

    payload = montar_pedido_zetti(
        pedido
    )

    # --------------------------------------------------------
    # DEBUG
    # --------------------------------------------------------

    print("=" * 80)
    print("PAYLOAD ENVIADO PARA ZETTI")
    print("=" * 80)

    print(payload)

    print("=" * 80)

    # --------------------------------------------------------
    # HEADERS
    # --------------------------------------------------------

    headers = {

        "Authorization":
            f"ApiKey {token}",

        "Content-Type":
            "application/json",
    }

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    response = requests.post(

        f"{ZETTI_URL}/pedidos",

        headers=headers,

        json=payload,

        timeout=30,
    )

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    try:

        resultado = response.json()

    except ValueError:

        resultado = {}

    # --------------------------------------------------------
    # GARANTIR DICT
    # --------------------------------------------------------

    if not isinstance(
        resultado,
        dict
    ):

        resultado = {}

    # --------------------------------------------------------
    # ERRO HTTP
    # --------------------------------------------------------

    if not response.ok:

        mensagem = (

            resultado.get(
                "msg"
            )

            or resultado.get(
                "mensagem"
            )

            or response.text

            or "Erro desconhecido."
        )

        raise Exception(
            (
                f"Zetti HTTP "
                f"{response.status_code}: "
                f"{mensagem}"
            )
        )

    # --------------------------------------------------------
    # ERRO API
    # --------------------------------------------------------

    if resultado.get(
        "status"
    ) != 200:

        raise Exception(

            resultado.get(
                "msg"
            )

            or resultado.get(
                "mensagem"
            )

            or "A Zetti recusou o pedido."
        )

    return resultado


# ============================================================
# ENVIAR PARA PDV
# ============================================================

@login_required
@require_POST
def enviar_para_pdv(
    request,
    pedido_id
):

    # --------------------------------------------------------
    # BUSCAR PEDIDOS
    # --------------------------------------------------------

    try:

        pedidos = buscar_pedidos_nuvemshop()

    except Exception as exc:

        messages.error(
            request,
            f"Erro ao consultar pedido: {exc}"
        )

        return redirect(
            "lista_pedidos"
        )

    # --------------------------------------------------------
    # LOCALIZAR
    # --------------------------------------------------------

    pedido = None

    for item in pedidos:

        if not isinstance(
            item,
            dict
        ):
            continue

        if str(
            item.get("id")
        ) == str(pedido_id):

            pedido = item

            break

    # --------------------------------------------------------
    # NÃO ENCONTRADO
    # --------------------------------------------------------

    if not pedido:

        messages.error(
            request,
            "Pedido não encontrado."
        )

        return redirect(
            "lista_pedidos"
        )

    # --------------------------------------------------------
    # CANCELADO
    # --------------------------------------------------------

    if pedido.get(
        "status"
    ) == "cancelled":

        messages.error(
            request,
            "Pedido cancelado não pode ser enviado ao PDV."
        )

        return redirect(
            "lista_pedidos"
        )

    # --------------------------------------------------------
    # TIPO DE ENTREGA
    # --------------------------------------------------------

    tipo_entrega = obter_tipo_entrega(
        pedido
    )

    retirar = (
        tipo_entrega == "retirada"
    )

    # --------------------------------------------------------
    # DEBUG
    # --------------------------------------------------------

    print("=" * 80)
    print("ENVIO MANUAL PARA PDV")
    print(
        "PEDIDO:",
        pedido.get("number")
    )
    print(
        "TIPO:",
        tipo_entrega
    )
    print(
        "RETIRAR:",
        retirar
    )
    print("=" * 80)

    # --------------------------------------------------------
    # ENVIAR
    # --------------------------------------------------------

    try:

        resultado = enviar_pedido_zetti(
            pedido
        )

        dados = (
            resultado.get(
                "data"
            )
            or {}
        )

        if not isinstance(
            dados,
            dict
        ):

            dados = {}

        cd_orcamento = dados.get(
            "cdOrcamento"
        )

        situacao = dados.get(
            "situacao"
        )

        mensagem = (

            dados.get(
                "mensagem"
            )

            or resultado.get(
                "msg"
            )

            or "Pedido enviado com sucesso."
        )

        # ----------------------------------------------------
        # GUARDAR SESSÃO
        # ----------------------------------------------------

        pedidos_zetti = (
            request.session.get(
                "pedidos_zetti",
                {}
            )
        )

        if not isinstance(
            pedidos_zetti,
            dict
        ):

            pedidos_zetti = {}

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

            "tipo_entrega":
                tipo_entrega,
        }

        request.session[
            "pedidos_zetti"
        ] = pedidos_zetti

        request.session.modified = True

        # ----------------------------------------------------
        # SUCESSO
        # ----------------------------------------------------

        messages.success(
            request,
            (
                f"Pedido #{pedido.get('number')} "
                "enviado para o PDV. "
                f"Tipo: {tipo_entrega}. "
                f"Orçamento Zetti: "
                f"{cd_orcamento}"
            )
        )

    except Exception as exc:

        messages.error(
            request,
            f"Erro ao enviar para o PDV: {exc}"
        )

    return redirect(
        "lista_pedidos"
    )


# ============================================================
# OBTER UF
# ============================================================

def obter_uf(
    endereco
):

    if not isinstance(
        endereco,
        dict
    ):

        return ""

    uf = endereco.get(
        "province",
        ""
    )

    if not uf:

        return ""

    uf = str(
        uf
    ).strip()

    # --------------------------------------------------------
    # JÁ É SIGLA
    # --------------------------------------------------------

    if len(uf) == 2:

        return uf.upper()

    # --------------------------------------------------------
    # MAPA
    # --------------------------------------------------------

    mapa_ufs = {

        "Acre":
            "AC",

        "Alagoas":
            "AL",

        "Amapá":
            "AP",

        "Amazonas":
            "AM",

        "Bahia":
            "BA",

        "Ceará":
            "CE",

        "Distrito Federal":
            "DF",

        "Espírito Santo":
            "ES",

        "Goiás":
            "GO",

        "Maranhão":
            "MA",

        "Mato Grosso":
            "MT",

        "Mato Grosso do Sul":
            "MS",

        "Minas Gerais":
            "MG",

        "Pará":
            "PA",

        "Paraíba":
            "PB",

        "Paraná":
            "PR",

        "Pernambuco":
            "PE",

        "Piauí":
            "PI",

        "Rio de Janeiro":
            "RJ",

        "Rio Grande do Norte":
            "RN",

        "Rio Grande do Sul":
            "RS",

        "Rondônia":
            "RO",

        "Roraima":
            "RR",

        "Santa Catarina":
            "SC",

        "São Paulo":
            "SP",

        "Sergipe":
            "SE",

        "Tocantins":
            "TO",
    }

    return mapa_ufs.get(
        uf,
        ""
    )