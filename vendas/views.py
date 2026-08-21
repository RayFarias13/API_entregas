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
## ─────────────────────────────────────────
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
                retirar=dados.get('retirar', True),
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