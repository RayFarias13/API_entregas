from decimal import Decimal

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Case, When, Value, CharField, OuterRef, Subquery
from django.db.models.functions import ExtractMonth, TruncMonth, ExtractDay
from django.db import transaction

from django.db.models import Q
from collections import OrderedDict

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import *
from receptor.models import *
import json
import datetime
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test, permission_required
from django.contrib.auth import logout
from itertools import groupby
from collections import defaultdict
import logging
logger = logging.getLogger(__name__)





# Página Kanban - GERAL

@login_required
def board_administrativo(request):
    # 1. Busca entregas ativas
    entregas = DadosEntrega.objects.filter(cd_mov_ret=0)

    # 2. Cria o mapa de nomes GARANTINDO chaves inteiras
    # Filtramos cd_usu__isnull=False para evitar erros de conversão
    funcionarios_map = {
        int(f.cd_usu): (f.user.get_full_name() or f.user.username)
        for f in Funcionarios_lista.objects.filter(cd_usu__isnull=False).select_related('user')
    }

    vendas, clientes = montar_dados_entregas(entregas)
    kanban = {}

    for entrega in entregas:
        venda = vendas.get(entrega.cd_vd)
        # O montar_dados_entregas usa strings como chaves para clientes
        cliente = clientes.get(str(venda.cd_cli)) if venda else None

        # 3. Lógica do Entregador com Garantia de Tipo
        entregador = "Sem entregador"
        if entrega.cd_fun_entr is not None:
            try:
                # Forçamos a busca como INT para bater com o mapa acima
                cod_busca = int(entrega.cd_fun_entr)
                entregador = funcionarios_map.get(cod_busca, f"Motoboy {cod_busca}")
            except (ValueError, TypeError):
                entregador = "Código Inválido"

        # 4. Organiza no Kanban
        if entregador not in kanban:
            kanban[entregador] = []

        kanban[entregador].append({
            'cd_entr': entrega.cd_entr,
            'cd_vd': entrega.cd_vd,
            'cd_nf': venda.cd_nf if (venda and venda.cd_nf != 0) else 'AVULSA',
            'cliente': cliente.name if cliente else 'Desconhecido',
            'endereco': cliente.address if cliente else 'Desconhecido',
            'complemento': cliente.address_complement if cliente else '',
            'telefone': cliente.phone_number.replace('+', '') if cliente else '',
            'entregador': entregador,
            'data_entr_ini': entrega.data_entr_ini,
            'hora_entr_ini': entrega.hora_entr_ini,
        
        })

    return render(request, 'boardadministrativo.html', {'kanban': kanban})

#kaban - motoboy
@login_required
def board_motoboy(request):
    try:
        # Pega o objeto do funcionário logado
        funcionario = request.user.funcionario
    except AttributeError:
        return redirect('login')

    if not funcionario.cd_usu:
        entregas = DadosEntrega.objects.none()
    else:
        # 1. REMOVEMOS o str() e o strip(). Usamos o valor inteiro direto.
        # 2. Mantemos o filtro de cd_mov_ret=0 para alinhar com o administrativo
        entregas = DadosEntrega.objects.filter(
            cd_fun_entr=funcionario.cd_usu,
            cd_mov_ret=0
        )

    # DEBUG: Verifique no console se agora o count é maior que 0
    print(f"[DEBUG] Motoboy ID: {funcionario.cd_usu} | Entregas: {entregas.count()}")

    vendas, clientes = montar_dados_entregas(entregas)

    lista_entregas = []
    for entrega in entregas:
        venda = vendas.get(entrega.cd_vd)
        # Buscamos o cliente garantindo que a chave seja uma string limpa
        cd_cli_busca = str(venda.cd_cli).strip() if venda else None
        cliente_obj = clientes.get(cd_cli_busca) if cd_cli_busca else None

        lista_entregas.append({
            'cd_entr': entrega.cd_entr,
            'cd_vd': entrega.cd_vd,
            'cd_nf': venda.cd_nf if (venda and venda.cd_nf != 0) else "AVULSA",
            'cliente': cliente_obj.name if cliente_obj else f"Cliente Cód. {cd_cli_busca or '?'}",
            'endereco': cliente_obj.address if cliente_obj else 'Endereço não informado',
            'complemento': cliente_obj.address_complement if cliente_obj else '',
            'telefone': cliente_obj.phone_number if cliente_obj else '',
        })

    return render(request, 'motoboy_entregas_dia.html', {'entregas': lista_entregas})

def montar_dados_entregas(entregas):
    entregas = list(entregas)
    cds_venda = [e.cd_vd for e in entregas if e.cd_vd]
    
    vendas = {
        v.cd_vd: v 
        for v in DadosVenda.objects.filter(cd_vd__in=cds_venda)
    }

    # Pegamos os códigos de cliente e limpamos (removendo espaços e garantindo string)
    cds_cliente = [str(v.cd_cli).strip() for v in vendas.values() if v.cd_cli]

    # Na busca do Customer, usamos o __in com a lista limpa
    clientes = {
        str(c.code).strip(): c 
        for c in Customer.objects.filter(code__in=cds_cliente)
    }

    return vendas, clientes

@login_required
def atualizar_status(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'erro', 'msg': 'Método não permitido'}, status=405)

    data = json.loads(request.body)
    cd_entr = data.get('cd_entr')
    novo_status = data.get('status')
    cd_fun_entr = data.get('cd_fun_entr')  # opcional

    # Buscar entrega
    entrega = DadosEntrega.objects.filter(cd_entr=cd_entr).first()
    if not entrega:
        return JsonResponse({'status': 'erro', 'msg': 'Entrega não encontrada'}, status=404)

    # Atualizar status
    if novo_status == 'Aguardando Entrega':
        entrega.cd_fun_entr = None
        entrega.cd_mov_ret = 0

    elif novo_status == 'Em Entrega':
        if not cd_fun_entr:
            return JsonResponse({'status': 'erro', 'msg': 'Funcionário obrigatório'}, status=400)
        entrega.cd_fun_entr = cd_fun_entr
        entrega.cd_mov_ret = 0

    elif novo_status == 'Entregue':
        entrega.cd_mov_ret = 1
        entrega.save()  # salva antes de criar histórico

        # Buscar dados do cliente
        venda = DadosVenda.objects.filter(cd_vd=entrega.cd_vd).first()
        customer = None
        if venda:
            customer = Customer.objects.filter(code=str(venda.cd_cli)).first()

        # Criar registro no histórico
        EntregaFinalizada.objects.create(
            cd_entr=entrega.cd_entr,
            cd_vd=entrega.cd_vd,
            cd_fun_entr=entrega.cd_fun_entr,
            cd_cli=customer.code if customer else None,
            nome_cliente=customer.name if customer else '',
            endereco=customer.address if customer else '',
            complemento=customer.address_complement if customer else '',
            telefone=customer.phone_number if customer else '',
            entrega_status='ENTREGUE',  # ou outro status se passar no payload
            observacoes=data.get('observacoes', '')
        )

        return JsonResponse({'status': 'ok'})  # retorna imediatamente após salvar histórico

    # Salvar alterações de status que não sejam "Entregue"
    entrega.save()
    return JsonResponse({'status': 'ok'})

@login_required
def buscar_customer_por_nome(request):
    nome = request.GET.get('nome', '')

    customers = Customer.objects.filter(
        name__icontains=nome
    ).values(
        'id',
        'name',
        'address',
        'address_complement',
        'phone_number'
    )

    return JsonResponse(list(customers), safe=False)

@login_required
def criar_entrega_avulsa(request):
    # 1. Validação de Permissão
    try:
        funcionario_logado = request.user.funcionario
        FUNCS_PERMITIDAS = {'GERENTE', 'ADMINISTRATIVO', 'S. GERENTE', 'OP. DE CAIXA'}
        if funcionario_logado.funcao not in FUNCS_PERMITIDAS:
            return redirect('login')
    except AttributeError:
        return redirect('login')

    # 2. Preparação de Dados para o Template
    customers = Customer.objects.all().order_by('name')
    entregadores = Funcionarios_lista.objects.filter(funcao='ENTREGADOR').select_related('user')

    # Gerar próximos IDs (Garantindo que sejam inteiros e baseados no maior valor)
    ultimo_entr = DadosEntrega.objects.order_by('-cd_entr').first()
    proximo_cd_entr = (ultimo_entr.cd_entr + 1) if ultimo_entr else 1100000

    ultimo_vd = DadosVenda.objects.order_by('-cd_vd').first()
    proximo_cd_vd = (ultimo_vd.cd_vd + 1) if ultimo_vd else 1100000

    # 3. Processamento do POST
    if request.method == 'POST':
        cd_fun_entr = request.POST.get('cd_fun_entr')  # O código (cd_usu) do entregador
        customer_id = request.POST.get('customer_id')  # O ID da tabela Customer

        if not cd_fun_entr or not customer_id:
            return render(request, 'entrega_avulsa.html', {
                'erro': 'Selecione um entregador e um cliente.',
                'customers': customers,
                'funcionarios': entregadores,
                'proximo_cd_entr': proximo_cd_entr,
                'proximo_cd_vd': proximo_cd_vd,
            })

        try:
            # Usamos transação para garantir que ou cria ambos (Venda e Entrega) ou nenhum
            with transaction.atomic():
                cliente = Customer.objects.get(id=customer_id)
                
                # Criar Venda Fictícia (Essencial para o board do motoboy encontrar o cliente)
                # IMPORTANTE: Salvar o cliente.code como string/int conforme o seu banco original
                DadosVenda.objects.create(
                    cd_cli=cliente.code, 
                    cd_nf=0,  # Indica avulsa
                    cd_vd=proximo_cd_vd
                )

                # Criar a Entrega
                DadosEntrega.objects.create(
                    cd_entr=proximo_cd_entr,
                    cd_vd=proximo_cd_vd,
                    cd_fun_entr=int(cd_fun_entr), # ID legado do entregador
                    cd_mov_ret=0,                 # Status de entrega ativa
                    cd_filial=5,                  # Filial padrão (ajuste se necessário)
                    data_hora_atribuicao=timezone.now()
                )

            return redirect('boardadministrativo')

        except Exception as e:
            return render(request, 'entrega_avulsa.html', {
                'erro': f'Erro ao salvar: {str(e)}',
                'customers': customers,
                'funcionarios': entregadores,
                'proximo_cd_entr': proximo_cd_entr,
                'proximo_cd_vd': proximo_cd_vd,
            })

    return render(request, 'entrega_avulsa.html', {
        'customers': customers,
        'funcionarios': entregadores,
        'proximo_cd_entr': proximo_cd_entr,
        'proximo_cd_vd': proximo_cd_vd,
    })




@login_required
def finalizar_entrega(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método inválido.'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'JSON inválido.'}, status=400)

    cd_entr     = data.get('cd_entr')
    cd_vd       = data.get('cd_vd')
    status      = data.get('status', 'ENTREGUE')
    observacoes = data.get('observacoes')

    # 1. Validar campos obrigatórios
    if not cd_entr or not cd_vd:
        return JsonResponse({'success': False, 'message': 'cd_entr e cd_vd são obrigatórios.'}, status=400)

    # 2. Validar status
    STATUS_VALIDOS = [s[0] for s in EntregaFinalizada.STATUS_CHOICES]
    if status not in STATUS_VALIDOS:
        return JsonResponse({'success': False, 'message': f'Status inválido: {status}'}, status=400)

    try:
        # 3. Buscar entrega pela chave composta (cd_entr + cd_vd)
        try:
            entrega = DadosEntrega.objects.get(cd_entr=cd_entr, cd_vd=cd_vd)
        except DadosEntrega.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Entrega não encontrada.'}, status=404)

        # 4. Buscar venda (opcional)
        venda = DadosVenda.objects.filter(cd_vd=cd_vd).first()

        # 5. Buscar cliente (se houver venda)
        cliente = None
        if venda:
            cliente = Customer.objects.filter(code=venda.cd_cli).first()

        # 6. Tratar data/hora de início
        data_hora_inicio = None
        if entrega.data_entr_ini and entrega.hora_entr_ini:
            data_hora_inicio = timezone.make_aware(
                datetime.datetime.combine(entrega.data_entr_ini, entrega.hora_entr_ini)
            )

        # 7. Salvar tudo atomicamente
        with transaction.atomic():
            entrega.cd_mov_ret = 1
            entrega.save()

            EntregaFinalizada.objects.create(
                usermotoboy      = request.user,
                entrega          = entrega,
                venda            = venda,
                funcionario      = entrega.cd_fun_entr,
                cupomfiscal      = venda.cd_nf if venda else 0,
                cliente          = cliente,
                nome_cliente     = cliente.name if cliente else "N/A",
                endereco         = cliente.address if cliente else "N/A",
                complemento      = cliente.address_complement if cliente else None,
                telefone         = cliente.phone_number if cliente else None,
                data_hora_inicio = data_hora_inicio,
                entrega_status   = status,
                observacoes      = observacoes,
            )

        status_labels = dict(EntregaFinalizada.STATUS_CHOICES)
        return JsonResponse({
            'success': True,
            'message': f'Entrega finalizada como "{status_labels.get(status, status)}"!'
        })

    except Exception as e:
        logger.exception("Erro inesperado em finalizar_entrega")
        return JsonResponse({'success': False, 'message': 'Erro interno no servidor.'}, status=500)
    


    


def login_view(request):
    try:
        if request.method == 'POST':
            username = request.POST.get('username').strip().lower()
            password = request.POST.get('password').strip().lower()

            user = authenticate(request, username=username, password=password)

            if user is not None:
                if user.funcionario.funcao == 'ENTREGADOR':
                    login(request, user)
                    return redirect('perfilmotoboy')

                                
                elif user.funcionario.funcao in ['GERENTE', 'ADMINISTRATIVO', 'S. GERENTE', 'OP. DE CAIXA']:
                    login(request, user)
                    return redirect('boardadministrativo')
                
                elif user.is_staff:  # para usuários admin do Django sem perfil de funcionário
                    login(request, user)
                    return redirect('admin:index')
                
               
                
                else:
                    return render(request, 'login.html', {"error": True, "message": "Função não autorizada."})
            
            else:
                return render(request, 'login.html', {"error": True})

        return render(request, 'login.html')

    except Exception as e:
        print("Erro no login_view:", str(e))
        return render(request, 'login.html', {"error": True})
    



def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('login')

@login_required
def cadastro_funcionario(request):
    # 1. Validação de Permissão
    try:
        funcionario_logado = request.user.funcionario
        permissoes_admin = ['GERENTE', 'ADMINISTRATIVO', 'S. GERENTE']
        
        if funcionario_logado.funcao not in permissoes_admin or not request.user.is_staff:
            return redirect('login') 
    except AttributeError:
        return redirect('login')

    if request.method == 'POST':
        # 2. Captura de dados
        username = request.POST.get('username').strip().lower()
        password = request.POST.get('password').strip().lower()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '')
        email = request.POST.get('email', '').strip()
        funcao = request.POST.get('funcao')
        cd_usu = request.POST.get('cd_usu', '').strip()

        # 3. Validações de existência
        if User.objects.filter(username=username).exists():
            return render(request, 'cadastro_funcionario.html', {"error": "Este login já está em uso."})
        
        if cd_usu and Funcionarios_lista.objects.filter(cd_usu=cd_usu).exists():
            return render(request, 'cadastro_funcionario.html', {"error": "Este Código de Funcionário já está cadastrado."})

        try:
            # 4. Criação do User (Senha criptografada)
            novo_usuario = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=email
            )

            # 5. Criação do Perfil de Funcionário
            Funcionarios_lista.objects.create(
                user=novo_usuario,
                funcao=funcao,
                cd_usu=cd_usu if cd_usu else None
            )

            messages.success(request, "Funcionário cadastrado com sucesso!")
            return redirect('gerenciar_cadastros') # Ou para uma página de listagem

        except Exception as e:
            return render(request, 'cadastro_funcionario.html', {"error": f"Erro ao salvar: {e}"})

    return render(request, 'cadastro_funcionario.html')
    

@login_required
def gerenciar_funcionarios(request):
    try:
        funcionario = request.user.funcionario  # pega o funcionário logado
        lista = ['GERENTE','ADMINISTRATIVO','S. GERENTE']

        if funcionario.funcao not in lista:
            print(f"Acesso negado para função")  # Log para depuração
            return redirect('login')  # se não for gerente, redireciona para login

        funcionarios = Funcionarios_lista.objects.all()
        return render(request, 'gerenciar_cadastros.html', {'funcionarios': funcionarios})
    except AttributeError:
        return redirect('login')  # se não tiver perfil de funcionário, redireciona para login



@login_required
def registrar_km_manual(request):
    try:
        funcionario = request.user.funcionario
    except AttributeError:
        return redirect('login')

    FUNCS_PERMITIDAS = {'GERENTE', 'ADMINISTRATIVO', 'S. GERENTE'}
    if funcionario.funcao not in FUNCS_PERMITIDAS:
        return redirect('login')

    if request.method == "POST":
        id_motoboy = request.POST.get('motoboy')
        km = request.POST.get('km_diario')
        data = request.POST.get('data_apuracao')

        if id_motoboy and km and data:
            try:
                usuario = User.objects.get(id=id_motoboy)
            except User.DoesNotExist:
                return redirect('registrar_km')

            dadoskilometragem.objects.create(
                usermotoboy=usuario,
                km_diario=float(km.replace(',', '.')),
                data_apuracao=data
            )
            return redirect('registrar_km')

    todos_motoboys = User.objects.filter(
        funcionario__funcao='ENTREGADOR'
    ).order_by('first_name')

    return render(request, 'registrar_km.html', {'motoboys': todos_motoboys})


@login_required
def lista_km(request):
    relatorios_quinzenais = (
        dadoskilometragem.objects
        # 1. Truncamos o mês para agrupar registros do mesmo mês/ano
        .annotate(mes_base=TruncMonth('data_apuracao'))
        # 2. Extraímos o dia para saber em qual quinzena cai
        .annotate(dia=ExtractDay('data_apuracao'))
        # 3. Criamos a lógica da quinzena
        .annotate(quinzena=Case(
            When(dia__lte=15, then=Value('1ª Quinzena')),
            default=Value('2ª Quinzena'),
            output_field=CharField(),
        ))
        # 4. Agrupamos pelos campos necessários
        .values('mes_base', 'quinzena', 'usermotoboy__first_name')
        # 5. Somamos os KMs do grupo
        .annotate(total_periodo=Sum('km_diario'))
        # 6. Ordenamos por mês e depois pela quinzena
        .order_by('-mes_base', '-quinzena', 'usermotoboy__first_name')
    )

    ultimosregistros = (dadoskilometragem.objects
                        #.annotate(mes_base=TruncMonth('data_apuracao'))
                        .annotate(mes_base = ExtractMonth('data_apuracao'))
                        .annotate(dia = ExtractDay('data_apuracao'))
                        .values('mes_base','dia', 'usermotoboy__first_name', 'km_diario', 'data_apuracao')
                        .order_by('-data_apuracao')[:10]
                        )
    

    total_geral = dadoskilometragem.objects.aggregate(Sum('km_diario'))['km_diario__sum'] or 0

    return render(request, 'lista_km.html', {
        'relatorios': relatorios_quinzenais,
        'total_geral': total_geral,
        'ultimosregistros' : ultimosregistros,  # opcional: últimos 10 registros
        #'ultimos_registros': dadoskilometragem.objects.order_by('-data_apuracao')[:10]  # opcional: últimos 10 registros
    })



@login_required
def atualizar_localizacao(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'erro', 'message': 'Método não permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        lat = data.get('latitude')
        lng = data.get('longitude')
        
        # Validação de campos ausentes
        if lat is None or lng is None:
            return JsonResponse({'status': 'erro', 'message': 'Coordenadas ausentes'}, status=400)
        
        HistoricoLocalizacao.objects.create(
            usuario=request.user,
            latitude=Decimal(str(lat)),
            longitude=Decimal(str(lng))
        )
        
        return JsonResponse({'status': 'sucesso', 'message': 'Posição salva!'})
    
    except (ValueError, TypeError):
        return JsonResponse({'status': 'erro', 'message': 'Dados inválidos'}, status=400)
    
    except Exception:
        # Nunca expor str(e) em produção
        return JsonResponse({'status': 'erro', 'message': 'Erro interno no servidor'}, status=500)
    

@login_required
def mapa_entregadores(request):
    return render(request, 'mapa.html')

@login_required
def dados_entregadores_json(request):
    # Sua lógica de Subquery (Perfeita!)
    ultimas_posicoes_ids = HistoricoLocalizacao.objects.filter(
        usuario=OuterRef('usuario')
    ).order_by('-data_criacao').values('id')[:1]

    posicoes = HistoricoLocalizacao.objects.filter(
        id__in=Subquery(ultimas_posicoes_ids)
    ).select_related('usuario')

    # Transformamos o QuerySet em uma lista para o JSON
    data = [{
        "id": p.usuario.id,
        "username": p.usuario.username,
        "lat": float(p.latitude),
        "lng": float(p.longitude),
        "hora": timezone.localtime(p.data_criacao).strftime('%d/%m/%y às %H:%M')


    } for p in posicoes]

    return JsonResponse(data, safe=False)


@login_required
def perfil_motoboy(request):
    try:
        funcionario = request.user.funcionario
    except AttributeError:
        return redirect('login')

    hoje = timezone.now().date()
    mes_atual = hoje.month
    ano_atual = hoje.year

    # Total de entregas do mês (usa data_hora_entrega pois auto_now_add é garantido)
    total_entregas_mes = EntregaFinalizada.objects.filter(
        usermotoboy=request.user,
        data_hora_entrega__month=mes_atual,
        data_hora_entrega__year=ano_atual
    ).count()

    # Total de KM do mês
    total_km_mes = dadoskilometragem.objects.filter(
        usermotoboy=request.user,
        data_apuracao__month=mes_atual,
        data_apuracao__year=ano_atual
    ).aggregate(Sum('km_diario'))['km_diario__sum'] or 0

    # Últimas 5 entregas finalizadas
    ultimas_entregas = EntregaFinalizada.objects.filter(
        usermotoboy=request.user
    ).order_by('-data_hora_entrega')[:5]

    entregas_formatadas = [{
        'cliente': e.nome_cliente or 'Desconhecido',
        'horario': timezone.localtime(e.data_hora_entrega).strftime('%d/%m %H:%M'),
        'status': 'entregue' if e.entrega_status == 'ENTREGUE' else 'andamento'
    } for e in ultimas_entregas]

    return render(request, 'perfilmotoboy.html', {
        'funcionario': funcionario,
        'total_entregas_mes': total_entregas_mes,
        'total_km_mes': round(total_km_mes, 1),
        'pontuacao': total_entregas_mes,  # ajuste se tiver lógica própria de pontos
        'ultimas_entregas': entregas_formatadas,
    })


# ─────────────────────────────────────────
# ENTREGAS DO DIA - HISTORICO DO DIA
# ─────────────────────────────────────────
@login_required
def motoboy_entregas_dia_historico(request):
    try:
        funcionario = request.user.funcionario
        if funcionario.funcao != 'ENTREGADOR':
            return redirect('boardadministrativo')
    except AttributeError:
        return redirect('login')
 
    hoje = timezone.now().date()
 
    entregas_qs = EntregaFinalizada.objects.filter(
        usermotoboy=request.user,
        data_hora_entrega__date=hoje
    ).order_by('-data_hora_entrega')
 
    status_display = dict(EntregaFinalizada.STATUS_CHOICES)
 
    entregas = [{
        'cd_entr': e.entrega_id,
        'cliente': e.nome_cliente or 'Desconhecido',
        'endereco': e.endereco or '',
        'complemento': e.complemento or '',
        'telefone': e.telefone or '',
        'status': e.entrega_status,
        'status_display': status_display.get(e.entrega_status, e.entrega_status),
        'horario': timezone.localtime(e.data_hora_entrega).strftime('%H:%M'),
    } for e in entregas_qs]
 
    entregues = sum(1 for e in entregas if e['status'] == 'ENTREGUE')
    pendentes = len(entregas) - entregues
 
    return render(request, 'motoboy_entregas_dia.html', {
        'entregas': entregas,
        'total': len(entregas),
        'entregues': entregues,
        'pendentes': pendentes,
        'hoje': hoje.strftime('%d/%m/%Y'),
    })
 
 
# ─────────────────────────────────────────
# HISTÓRICO DE ENTREGAS
# ─────────────────────────────────────────
@login_required
def motoboy_historico_entregas(request):
    try:
        funcionario = request.user.funcionario
        if funcionario.funcao != 'ENTREGADOR':
            return redirect('boardadministrativo')
    except AttributeError:
        return redirect('login')
 
    hoje = timezone.now().date()
 
    # Meses disponíveis (últimos 6 meses)
    meses_disponiveis = []
    for i in range(6):
        d = (hoje.replace(day=1) - datetime.timedelta(days=i * 28)).replace(day=1)
        meses_disponiveis.append({
            'value': d.strftime('%Y-%m'),
            'label': d.strftime('%B/%Y').capitalize(),
        })
 
    mes_selecionado = request.GET.get('mes', hoje.strftime('%Y-%m'))
 
    try:
        ano, mes = map(int, mes_selecionado.split('-'))
    except ValueError:
        ano, mes = hoje.year, hoje.month
 
    entregas_qs = EntregaFinalizada.objects.filter(
        usermotoboy=request.user,
        data_hora_entrega__year=ano,
        data_hora_entrega__month=mes,
    ).order_by('-data_hora_entrega')
 
    status_display = dict(EntregaFinalizada.STATUS_CHOICES)
 
    # Agrupar por data
    grupos_dict = defaultdict(list)
    for e in entregas_qs:
        data_local = timezone.localtime(e.data_hora_entrega)
        chave = data_local.strftime('%d/%m/%Y')
        grupos_dict[chave].append({
            'cliente': e.nome_cliente or 'Desconhecido',
            'endereco': e.endereco or '',
            'status': e.entrega_status,
            'status_display': status_display.get(e.entrega_status, e.entrega_status),
            'hora': data_local.strftime('%H:%M'),
        })
 
    entregas_agrupadas = [
        {'data': data, 'entregas': itens}
        for data, itens in grupos_dict.items()
    ]
 
    total_geral = EntregaFinalizada.objects.filter(usermotoboy=request.user).count()
 
    return render(request, 'motoboy_historico_entregas.html', {
        'entregas_agrupadas': entregas_agrupadas,
        'meses_disponiveis': meses_disponiveis,
        'mes_selecionado': mes_selecionado,
        'total_geral': total_geral,
    })
 
 
# ─────────────────────────────────────────
# HISTÓRICO DE KM
# ─────────────────────────────────────────
@login_required
def motoboy_historico_km(request):
    try:
        funcionario = request.user.funcionario
        if funcionario.funcao != 'ENTREGADOR':
            return redirect('boardadministrativo')
    except AttributeError:
        return redirect('login')
 
    hoje = timezone.now().date()
 
    # Meses disponíveis
    meses_disponiveis = []
    for i in range(6):
        d = (hoje.replace(day=1) - datetime.timedelta(days=i * 28)).replace(day=1)
        meses_disponiveis.append({
            'value': d.strftime('%Y-%m'),
            'label': d.strftime('%B/%Y').capitalize(),
        })
 
    mes_selecionado = request.GET.get('mes', hoje.strftime('%Y-%m'))
 
    try:
        ano, mes = map(int, mes_selecionado.split('-'))
    except ValueError:
        ano, mes = hoje.year, hoje.month
 
    registros_qs = dadoskilometragem.objects.filter(
        usermotoboy=request.user,
        data_apuracao__year=ano,
        data_apuracao__month=mes,
    ).order_by('data_apuracao')
 
    DIAS_SEMANA = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
 
    # Separar em quinzenas
    primeira = []
    segunda  = []
    for r in registros_qs:
        item = {
            'data': r.data_apuracao.strftime('%d/%m/%Y'),
            'dia_semana': DIAS_SEMANA[r.data_apuracao.weekday()],
            'km': round(r.km_diario, 1),
        }
        if r.data_apuracao.day <= 15:
            primeira.append(item)
        else:
            segunda.append(item)
 
    quinzenas = []
    if primeira:
        quinzenas.append({
            'label': '1ª Quinzena',
            'registros': primeira,
            'total': round(sum(r['km'] for r in primeira), 1),
        })
    if segunda:
        quinzenas.append({
            'label': '2ª Quinzena',
            'registros': segunda,
            'total': round(sum(r['km'] for r in segunda), 1),
        })
 
    total_mes = round(
        dadoskilometragem.objects.filter(
            usermotoboy=request.user,
            data_apuracao__year=ano,
            data_apuracao__month=mes,
        ).aggregate(Sum('km_diario'))['km_diario__sum'] or 0, 1
    )
 
    total_geral = round(
        dadoskilometragem.objects.filter(
            usermotoboy=request.user
        ).aggregate(Sum('km_diario'))['km_diario__sum'] or 0, 1
    )
 
    return render(request, 'motoboy_historico_km.html', {
        'quinzenas': quinzenas,
        'meses_disponiveis': meses_disponiveis,
        'mes_selecionado': mes_selecionado,
        'total_mes': total_mes,
        'total_geral': total_geral,
    })
 
 
# ─────────────────────────────────────────
# PONTUAÇÃO
# ─────────────────────────────────────────
@login_required
def motoboy_pontuacao(request):
    try:
        funcionario = request.user.funcionario
        if funcionario.funcao != 'ENTREGADOR':
            return redirect('boardadministrativo')
    except AttributeError:
        return redirect('login')
 
    hoje = timezone.now().date()
    inicio_semana = hoje - datetime.timedelta(days=hoje.weekday())
 
    total_geral  = EntregaFinalizada.objects.filter(usermotoboy=request.user).count()
    total_mes    = EntregaFinalizada.objects.filter(
        usermotoboy=request.user,
        data_hora_entrega__year=hoje.year,
        data_hora_entrega__month=hoje.month,
    ).count()
    total_semana = EntregaFinalizada.objects.filter(
        usermotoboy=request.user,
        data_hora_entrega__date__gte=inicio_semana,
    ).count()
 
    # Histórico por mês (últimos 2 meses)
    por_mes = []
    max_mes = 0
    for i in range(2):
        d = (hoje.replace(day=1) - datetime.timedelta(days=i * 28)).replace(day=1)
        total = EntregaFinalizada.objects.filter(
            usermotoboy=request.user,
            data_hora_entrega__year=d.year,
            data_hora_entrega__month=d.month,
        ).count()
        por_mes.append({
            'label': d.strftime('%B/%Y').capitalize(),
            'total': total,
            'pct': 0,
        })
        if total > max_mes:
            max_mes = total
 
    # Calcula porcentagem para barra de progresso
    for m in por_mes:
        m['pct'] = round((m['total'] / max_mes) * 100) if max_mes > 0 else 0
 
    return render(request, 'motoboy_pontuacao.html', {
        'total_geral': total_geral,
        'total_mes': total_mes,
        'total_semana': total_semana,
        'por_mes': por_mes,
    })



@login_required
def cadastro_cliente(request):
    try:
        funcionario = request.user.funcionario
        FUNCS_PERMITIDAS = {'GERENTE', 'ADMINISTRATIVO', 'S. GERENTE'}
        if funcionario.funcao not in FUNCS_PERMITIDAS:
            return redirect('login')
    except AttributeError:
        return redirect('login')

    if request.method == 'POST':
        name        = request.POST.get('name', '').strip()
        code        = request.POST.get('code', '').strip()
        type_       = request.POST.get('type', '')
        email       = request.POST.get('email', '').strip() or None
        login_email = request.POST.get('login_email', '').strip() or None
        phone       = request.POST.get('phone_number', '').strip() or None
        address     = request.POST.get('address', '').strip() or None
        complement  = request.POST.get('address_complement', '').strip() or None
        lat         = request.POST.get('latitude') or 0.0
        lng         = request.POST.get('longitude') or 0.0
        hour_start  = request.POST.get('operating_hour_start') or None
        hour_end    = request.POST.get('operating_hour_end') or None

        # Validações
        if not name or not code:
            return render(request, 'cadastro_cliente.html', {
                'error': 'Nome e Código são obrigatórios.',
                'form_data': request.POST,
            })

        if Customer.objects.filter(code=code).exists():
            return render(request, 'cadastro_cliente.html', {
                'error': f'Já existe um cliente com o código "{code}".',
                'form_data': request.POST,
            })

        Customer.objects.create(
            name=name,
            code=code,
            type=type_,
            email=email,
            login_email=login_email,
            phone_number=phone,
            address=address,
            address_complement=complement,
            latitude=float(lat),
            longitude=float(lng),
            operating_hour_start=hour_start,
            operating_hour_end=hour_end,
        )

        return render(request, 'entrega_avulsa.html', {
            'success': f'Cliente "{name}" cadastrado com sucesso!',
        })

    return render(request, 'entrega_avulsa.html')



@login_required
def historico_entregas(request):
    # Pega todos os registros inicialmente, ordenando pelos mais recentes
    entregas = EntregaFinalizada.objects.all().order_by('-data_hora_entrega')

    # --- Lógica de Filtros ---
    
    # Filtro por Nome do Cliente ou Endereço (Busca textual)
    q = request.GET.get('q')
    if q:
        entregas = entregas.filter(
            Q(nome_cliente__icontains=q) | 
            Q(endereco__icontains=q) |
            Q(entrega__cd_entr__icontains=q) # Busca por ID da entrega também
        )

    # Filtro por Status
    status = request.GET.get('status')
    if status:
        entregas = entregas.filter(entrega_status=status)

    # Filtro por Motoboy (usando o ID do User do Django)
    motoboy_id = request.GET.get('motoboy')
    if motoboy_id:
        entregas = entregas.filter(usermotoboy_id=motoboy_id)

    # Filtro por Data (Início e Fim)
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    if data_inicio:
        entregas = entregas.filter(data_hora_entrega__date__gte=data_inicio)
    if data_fim:
        entregas = entregas.filter(data_hora_entrega__date__lte=data_fim)

    # Dados para preencher os selects dos filtros no HTML
    motoboys = User.objects.filter(funcionario__funcao='ENTREGADOR')
    status_choices = EntregaFinalizada.STATUS_CHOICES

    context = {
        'entregas': entregas,
        'motoboys': motoboys,
        'status_choices': status_choices,
        'filtros': request.GET, # Para manter os valores nos campos após filtrar
    }

    return render(request, 'historico_entregas.html', context)

@login_required
def historico_geral_entregas(request):
    mes_sel = int(request.GET.get('mes', timezone.now().month))
    motoboy_id = request.GET.get('motoboy') # Aqui recebemos o ID do User para o filtro
    
    # 1. Criamos o mapa de nomes baseados no cd_usu (o que está no campo 'funcionario')
    # Forçamos int() para garantir o "match" perfeito
    funcionarios_map = {
        int(f.cd_usu): (f.user.get_full_name() or f.user.username)
        for f in Funcionarios_lista.objects.filter(cd_usu__isnull=False).select_related('user')
    }

    # 2. Query Base
    query = EntregaFinalizada.objects.filter(
        data_hora_entrega__month=mes_sel,
        data_hora_entrega__year=timezone.now().year
    )
    
    if motoboy_id:
        query = query.filter(usermotoboy_id=motoboy_id)
        
    entregas_list = query.order_by('-data_hora_entrega')

    # 3. Agrupamento por Data
    agrupados = OrderedDict()
    for e in entregas_list:
        data_str = e.data_hora_entrega.strftime('%d/%m/%Y')
        if data_str not in agrupados:
            agrupados[data_str] = []
            
        # LÓGICA DO NOME PELO CAMPO FUNCIONARIO
        nome_exibicao = "Desconhecido"
        if e.funcionario:
            # Busca o nome no mapa usando o código numérico salvo no registro
            nome_exibicao = funcionarios_map.get(int(e.funcionario), f"Cód. {e.funcionario}")

        agrupados[data_str].append({
            'cliente': e.nome_cliente,
            'endereco': e.endereco,
            'hora': e.data_hora_entrega.strftime('%H:%M'),
            'status': e.entrega_status,
            'status_display': e.get_entrega_status_display(),
            'motoboy': nome_exibicao # Agora usa o nome vindo do código legado
        })

    # ... (resto do contexto: totais e meses)
    context = {
        'entregas_agrupadas': [{'data': k, 'entregas': v} for k, v in agrupados.items()],
        'motoboys': User.objects.filter(funcionario__funcao='ENTREGADOR'),
        'mes_selecionado': mes_sel,
        'total_geral': query.count(),
        'total_entregue': query.filter(entrega_status='ENTREGUE').count(),
        'total_problemas': query.exclude(entrega_status='ENTREGUE').count(),
    }
    return render(request, 'historico_entregascopy.html', context)