from django.db import models

class Atendimento(models.Model):
    cpf = models.CharField(max_length=14, blank=True, null=True, db_index=True)
    nome = models.CharField(max_length=255)
    idade = models.PositiveIntegerField(null=True, blank=True)
    genero = models.CharField(max_length=50, blank=True)
    telefone = models.CharField(max_length=50, blank=True)
    bairro = models.CharField(max_length=150, blank=True)
    cliente = models.CharField(max_length=50, blank=True)
    
    # Serviços (você pode salvar como texto ou booleanos)
    servicos = models.TextField(blank=True) 
    
    faz_uso_continuo = models.CharField(max_length=10, blank=True)
    quais_medicamentos = models.TextField(blank=True)
    acompanhamento_medico = models.CharField(max_length=10, blank=True)
    receber_orientacoes = models.CharField(max_length=50, blank=True)
    deseja_promocoes = models.CharField(max_length=10, blank=True)
    observacoes = models.TextField(blank=True)
    
    # Resultados
    pa = models.CharField(max_length=50, blank=True)
    glicemia = models.CharField(max_length=50, blank=True)
    temperatura = models.CharField(max_length=50, blank=True)
    outro_resultado = models.CharField(max_length=100, blank=True)
    
    data_atendimento = models.DateField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Atendimento de {self.nome} - {self.data_atendimento}"