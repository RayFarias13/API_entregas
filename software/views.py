from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Case, When, Value, CharField
from django.db.models.functions import TruncMonth, ExtractDay



from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import *
from receptor.models import *
import json
import datetime
from django.utils import timezone
from receptor.models import Customer
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test, permission_required
from django.contrib.auth import logout
from . import views


# Página Kanban - GERAL
@login_required
def board(request):
    # Get all deliveries where cd_mov_ret == 0
    entregas = DadosEntrega.objects.filter(cd_mov_ret=0)

    kanban = {}

    for entrega in entregas:
        # Get the corresponding sale
        try:
            venda = DadosVenda.objects.get(cd_vd=entrega.cd_vd)
        except DadosVenda.DoesNotExist:
            venda = None

        # Get the customer for the f
        cliente = None
        if venda:
            try:
                cliente = Customer.objects.get(code=str(venda.cd_cli))
            except Customer.DoesNotExist:
                cliente = None

        # Determine delivery person
        entregador = f"Motoboy {entrega.cd_fun_entr}" if entrega.cd_fun_entr else "Sem entregador"

        # Add to kanban dictionary
        if entregador not in kanban:
            kanban[entregador] = []

        kanban[entregador].append({
            'cd_entr': entrega.cd_entr,
            'cd_vd': entrega.cd_vd,
            'cd_nf': venda.cd_nf if venda else 'Não cadastrado',
            'cliente': cliente.name if cliente else 'Desconhecido',
            'endereco': cliente.address if cliente else 'Desconhecido',
            'complemento': cliente.address_complement if cliente else '',
            'telefone': cliente.phone_number if cliente else '',
            
        })

    return render(request, 'board.html', {'kanban': kanban})

@login_required
def board_administrativo(request):
    # Get all deliveries where cd_mov_ret == 0
    entregas = DadosEntrega.objects.filter(cd_mov_ret=0)

    kanban = {}

    for entrega in entregas:
        # Get the corresponding sale
        try:
            venda = DadosVenda.objects.get(cd_vd=entrega.cd_vd)
        except DadosVenda.DoesNotExist:
            venda = None

        # Get the customer for the f
        cliente = None
        if venda:
            try:
                cliente = Customer.objects.get(code=str(venda.cd_cli))
            except Customer.DoesNotExist:
                cliente = None

        # Determine delivery person
        entregador = f"Motoboy {entrega.cd_fun_entr}" if entrega.cd_fun_entr else "Sem entregador"

        # Add to kanban dictionary
        if entregador not in kanban:
            kanban[entregador] = []

        kanban[entregador].append({
            'cd_entr': entrega.cd_entr,
            'cd_vd': entrega.cd_vd,
            'cd_nf': venda.cd_nf if venda else 'Não cadastrado',
            'cliente': cliente.name if cliente else 'Desconhecido',
            'endereco': cliente.address if cliente else 'Desconhecido',
            'complemento': cliente.address_complement if cliente else '',
            'telefone': cliente.phone_number if cliente else '',
            
        })

    return render(request, 'boardadministrativo.html', {'kanban': kanban})

#kaban - motoboy
@login_required
def board_motoboy(request):
    try:
        funcionario = request.user.funcionario  # pega o funcionário logado

    except AttributeError:
        return redirect('login')  # se não tiver perfil de funcionário, redireciona para login

    #  Se for entregador, filtra apenas as entregas dele
    if funcionario.funcao == 'ENTREGADOR':
        entregas = DadosEntrega.objects.filter(
            cd_mov_ret=0,
            cd_fun_entr=funcionario.cd_usu
        )
    else:
        # gerente/admin vê tudo
        entregas = DadosEntrega.objects.filter(cd_mov_ret=0)

    kanban = {}

    for entrega in entregas:
        try:
            venda = DadosVenda.objects.get(cd_vd=entrega.cd_vd)
        except DadosVenda.DoesNotExist:
            venda = None

        cliente = None
        if venda:
            try:
                cliente = Customer.objects.get(code=str(venda.cd_cli))
            except Customer.DoesNotExist:
                cliente = None

        entregador = f"Motoboy {entrega.cd_fun_entr}" if entrega.cd_fun_entr else "Sem entregador"

        if entregador not in kanban:
            kanban[entregador] = []

        kanban[entregador].append({
            'cd_entr': entrega.cd_entr,
            'cd_vd': entrega.cd_vd,
            'cd_nf': venda.cd_nf if venda else 'Não cadastrado',
            'cliente': cliente.name if cliente else 'Desconhecido',
            'endereco': cliente.address if cliente else 'Desconhecido',
            'complemento': cliente.address_complement if cliente else '',
            'telefone': cliente.phone_number if cliente else '',
        })

    return render(request, 'motoboy_entregas.html', {'kanban': kanban})



# API para atualizar status
@csrf_exempt
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
            customer = Customer.objects.filter(id=venda.cd_cli).first()

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
    # Lista de clientes e funcionários
    customers = Customer.objects.all()
    funcionarios = Funcionarios_lista.objects.all()  # agora vem do banco

    # Calcular próximo código de entrega e venda
    ultimo = DadosEntrega.objects.order_by('-cd_entr').first()
    proximo_cd_entr = ultimo.cd_entr + 100000 if ultimo else 1100000

    ultimo_vd = DadosEntrega.objects.order_by('-cd_vd').first()
    proximo_cd_vd = ultimo_vd.cd_vd + 100000 if ultimo_vd else 1100000

    if request.method == 'POST':
        cd_fun_entr = request.POST.get('cd_fun_entr')
        customer_id = request.POST.get('customer_id')

        if not cd_fun_entr or not customer_id:
            return render(request, 'entrega_avulsa.html', {
                'erro': 'Funcionário e cliente são obrigatórios',
                'customers': customers,
                'funcionarios': funcionarios,
                'proximo_cd_entr': proximo_cd_entr,
                'proximo_cd_vd': proximo_cd_vd
            })

        DadosEntrega.objects.create(
            cd_entr=proximo_cd_entr,
            cd_vd=proximo_cd_vd,
            cd_fun_entr=cd_fun_entr,
            cd_mov_ret=0
        )

        return redirect('board')

    return render(request, 'entrega_avulsa.html', {
        'customers': customers,
        'funcionarios': funcionarios,
        'proximo_cd_entr': proximo_cd_entr,
        'proximo_cd_vd': proximo_cd_vd
    })




@login_required
def finalizar_entrega(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método inválido.'}, status=405)

    try:
        data = json.loads(request.body)
        cd_entr = data.get('cd_entr')
        cd_vd = data.get('cd_vd')
        status = data.get('status', 'ENTREGUE')
        observacoes = data.get('observacoes')

        # Validar status
        status_validos = dict(EntregaFinalizada.STATUS_CHOICES)
        if status not in status_validos:
            return JsonResponse(
                {'success': False, 'message': 'Status inválido.'},
                status=400
            )

        entrega = DadosEntrega.objects.get(cd_entr=cd_entr, cd_vd=cd_vd)
        venda = DadosVenda.objects.get(cd_vd=cd_vd)

        entrega.cd_mov_ret = 1
        entrega.save()

        cliente = Customer.objects.filter(code=venda.cd_cli).first()

        if entrega.data_entr_ini and entrega.hora_entr_ini:
            data_hora_inicio = timezone.make_aware(
                datetime.datetime.combine(entrega.data_entr_ini, entrega.hora_entr_ini)
            )
        else:
            data_hora_inicio = None

        EntregaFinalizada.objects.create(
            usermotoboy=request.user if request.user.is_authenticated else None,
            entrega=entrega,
            venda=venda,
            funcionario=entrega.cd_fun_entr,
            cupomfiscal=venda.cd_nf,
            cliente=cliente,
            nome_cliente=cliente.name if cliente else None,
            endereco=cliente.address if cliente else None,
            complemento=cliente.address_complement if cliente else None,
            telefone=cliente.phone_number if cliente else None,
            data_hora_inicio=data_hora_inicio,
            entrega_status=status,
            observacoes=observacoes
        )

        return JsonResponse({
            'success': True,
            'message': f'Entrega finalizada como "{status_validos[status]}"!'
        })

    except DadosEntrega.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Entrega não encontrada.'}, status=404)
    except DadosVenda.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Venda não encontrada.'}, status=404)
    except Exception as e:
        print("Erro finalizar_entrega:", str(e))
        return JsonResponse({'success': False, 'message': 'Erro interno.'}, status=500)

@login_required    
def somente_staff(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return JsonResponse({'error': 'Acesso negado'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper



def somente_gerente(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'funcionario') or request.user.funcionario.funcao != 'GERENTE':
            return JsonResponse({'error': 'Acesso negado'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


def somente_operadordecaixa(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'funcionario') or request.user.funcionario.funcao != 'OP. DE CAIXA':
            return JsonResponse({'error': 'Acesso negado'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper

    


def login_view(request):
    try:
        if request.method == 'POST':
            username = request.POST.get('username')
            password = request.POST.get('password')

            user = authenticate(request, username=username, password=password)

            if user is not None:
                if user.funcionario.funcao == 'ENTREGADOR':
                    login(request, user)
                    return redirect('entregas_motoboy')

                elif user.funcionario.funcao == 'OP. DE CAIXA':
                    login(request, user)
                    return redirect('board')
                
                elif user.funcionario.funcao in ['GERENTE', 'ADMINISTRATIVO', 'S. GERENTE']:
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
            return redirect('login') # Ou para uma página de listagem

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
    if request.method == "POST":
        id_motoboy = request.POST.get('motoboy') # ID do usuário selecionado
        km = request.POST.get('km_diario')
        data = request.POST.get('data_apuracao')

        if id_motoboy and km and data:
            # Buscamos a instância do usuário pelo ID
            usuario = User.objects.get(id=id_motoboy)
            #usuario = Funcionarios_lista.objects.get(id=id_motoboy)  # pega o funcionário relacionado ao usuário
            
            dadoskilometragem.objects.create(
                usermotoboy=usuario,
                km_diario=float(km.replace(',', '.')),
                data_apuracao=data
            )
            print(f"KM registrado: {km} para {usuario.username} na data {data}")
            return redirect('registrar_km')

    # Buscamos todos os usuários para o administrador escolher um
    # Dica: se você usa grupos, pode filtrar por: User.objects.filter(groups__name='Motoboys')
    todos_motoboys = User.objects.all().order_by('first_name')
    
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
                        .annotate(mes_base=TruncMonth('data_apuracao'))
                        .annotate(dia = ExtractDay('data_apuracao'))
                        .values('mes_base', 'usermotoboy__first_name', 'km_diario', 'data_apuracao')
                        .order_by('-data_apuracao')[:10]
                        )
    

    total_geral = dadoskilometragem.objects.aggregate(Sum('km_diario'))['km_diario__sum'] or 0

    return render(request, 'lista_km.html', {
        'relatorios': relatorios_quinzenais,
        'total_geral': total_geral,
        'ultimosregistros' : ultimosregistros,  # opcional: últimos 10 registros
        #'ultimos_registros': dadoskilometragem.objects.order_by('-data_apuracao')[:10]  # opcional: últimos 10 registros
    })