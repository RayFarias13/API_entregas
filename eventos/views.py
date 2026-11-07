from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Atendimento
from django.shortcuts import get_object_or_404, render, redirect


@csrf_exempt # Use apenas se for enviar via fetch/AJAX sem token CSRF configurado no front
def salvar_atendimento(request):
    if request.method == 'POST':
        try:
            # Se você enviar via JSON a partir do JavaScript:
            data = json.loads(request.body)
            
            Atendimento.objects.create(
                cpf=data.get('cpf', ''),
                nome=data.get('nome', ''),
                idade=data.get('idade') or None,
                genero=data.get('genero', ''),
                telefone=data.get('telefone', ''),
                bairro=data.get('bairro', ''),
                cliente=data.get('cliente', ''),
                servicos=data.get('servicos', ''),
                faz_uso_continuo=data.get('medicamento', ''),
                quais_medicamentos=data.get('quais_medicamentos', ''),
                acompanhamento_medico=data.get('medico', ''),
                receber_orientacoes=data.get('orientacao', ''),
                deseja_promocoes=data.get('promocoes', ''),
                observacoes=data.get('observacoes', ''),
                pa=data.get('pa', ''),
                glicemia=data.get('glicemia', ''),
                temperatura=data.get('temperatura', ''),
                outro_resultado=data.get('outro_resultado', ''),
                data_atendimento=data.get('data') or None
            )
            return JsonResponse({'status': 'sucesso', 'mensagem': 'Atendimento salvo com sucesso!'})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=400)
            
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido'}, status=400)


def atedimento_pagina(request):
    return render(request,'atendimento.html')

from django.http import JsonResponse
from .models import Atendimento

def buscar_cliente(request):
    cpf = request.GET.get('cpf', '').strip()
    if cpf:
        # Pega o atendimento mais recente deste CPF
        anterior = Atendimento.objects.filter(cpf=cpf).order_by('-criado_em').first()
        if anterior:
            return JsonResponse({
                'encontrado': True,
                'nome': anterior.nome,
                'idade': anterior.idade,
                'genero': anterior.genero,
                'telefone': anterior.telefone,
                'bairro': anterior.bairro,
                'medicamento': anterior.faz_uso_continuo, # ajuste se o nome do campo no model for diferente
                'quais_medicamentos': anterior.quais_medicamentos,
            })
    return JsonResponse({'encontrado': False})