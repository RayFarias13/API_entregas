from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import *
from receptor.models import *
import json
import datetime
from django.utils import timezone
from receptor.models import Customer


# Página Kanban - GERAL
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


def kanban_view(request):
    motoboys = Funcionarios_lista.objects.all()
    kanban_data = []

    for motoboy in motoboys:
        entregas = DadosEntrega.objects.filter(cd_fun_entr=motoboy.cd_usu)
        entregas_list = []

        for e in entregas:
            venda = DadosVenda.objects.filter(cd_vd=e.cd_vd).first()
            cd_nf = venda.cd_nf if venda else "Não cadastrado"

            entregas_list.append({
                'cd_entr': e.cd_entr,
                'cd_vd': e.cd_vd,
                'cd_nf': cd_nf,
                # Adicione outros campos do cliente se precisar
            })

        kanban_data.append({
            'motoboy': motoboy.nm_usu,
            'entregas': entregas_list
        })

    return render(request, 'kanban.html', {'kanban': kanban_data})


@csrf_exempt
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
    
def somente_staff(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return JsonResponse({'error': 'Acesso negado'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@somente_staff
def criar_funcionario(request):
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)

    data = json.loads(request.body)

    user = User.objects.create_user(
        username=data['username'],
        password=data['password'],
        first_name=data.get('first_name', ''),
        last_name=data.get('last_name', '')
    )

    Funcionarios_lista.objects.create(
        user=user,
        funcao=data.get('funcao', 'DEFINIR')
    )

    return JsonResponse({'success': True, 'message': 'Funcionário criado'})




@csrf_exempt  # remova se for usar CSRF token
def login_funcionario(request):
    if request.method != 'POST':
        return JsonResponse(
            {'success': False, 'message': 'Método inválido'},
            status=405
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {'success': False, 'message': 'JSON inválido'},
            status=400
        )

    user = authenticate(
        request,
        username=data.get('username'),
        password=data.get('password')
    )

    if user is None:
        return JsonResponse(
            {'success': False, 'message': 'Credenciais inválidas'},
            status=401
        )

    # Verifica se possui perfil
    if not hasattr(user, 'funcionario'):
        return JsonResponse(
            {'success': False, 'message': 'Usuário sem perfil de funcionário'},
            status=403
        )

    login(request, user)

    return JsonResponse({
        'success': True,
        'user_id': user.id,
        'username': user.username,
        'nome': user.get_full_name(),
        'funcao': user.funcionario.funcao,
        'cd_usu': user.funcionario.cd_usu
    })




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

@login_required
@somente_staff
@somente_gerente
def autenticacao_moto(request):
    pass

#deletar depois
def autenticacao_funcionario(request):
    if not request.user or not hasattr(request.user, 'funcionario'):
        return JsonResponse({'success': False, 'message': 'Usuário sem perfil de funcionário'}, status=403)
    if User.is_staff:
        return True
    return User.is_authenticated

    


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            login(request, user)  # cria sessão
            return redirect('board')  # redireciona para o kanban
        elif user is not None:
            login(request, user)  # cria sessão
            return redirect('entregas_motoboy')  # redireciona para o histórico do cliente
        elif user is not None and user.funcionario.funcao == 'GERENTE':
            pass
            #login(request, user)  # cria sessão
            #return redirect('board')  # redireciona para o kanban
        else:
            return render(request, 'login.html', {"error": True})

    return render(request, 'login.html')


def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('login')

@login_required
def cadastro_funcionario(request):
    try:
        funcionario = request.user.funcionario  # pega o funcionário logado
        lista = ['GERENTE','ADMINISTRATIVO','S. GERENTE']

        if funcionario.funcao not in lista:
            return redirect('login')  # se não for gerente, redireciona para login


        if request.method == 'POST':
            username = request.POST.get('username')
            password = request.POST.get('password')
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            funcao = request.POST.get('funcao','DEFINIR')
            

            if User.objects.filter(username=username).exists():
                return render(request, 'cadastro_funcionario.html', {"error": "Usuário já existe"})

            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            Funcionarios_lista.objects.create(
                user=user,
                funcao=funcao
            )

            return redirect('login')

        return render(request, 'cadastro_funcionario.html')
    except AttributeError:
        return redirect('login')  # se não tiver perfil de funcionário, redireciona para login
    

@login_required
def gerenciar_funcionarios(request):
    try:
        funcionario = request.user.funcionario  # pega o funcionário logado
        lista = ['GERENTE','ADMINISTRATIVO','S. GERENTE']

        if funcionario.funcao not in lista:
            return redirect('login')  # se não for gerente, redireciona para login

        funcionarios = Funcionarios_lista.objects.all()
        return render(request, 'gerenciar_cadastros.html', {'funcionarios': funcionarios})
    except AttributeError:
        return redirect('login')  # se não tiver perfil de funcionário, redireciona para login
