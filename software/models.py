from django.db import models
from django.utils import timezone
from receptor.models import Customer 
from django.contrib.auth.models import User


class Funcionarios_lista(models.Model):
    funcionario_funcao_choice = [
        ('DEFINIR', 'Definir'),
        ('ENTREGADOR', 'Entregador'),
        ('OP. DE CAIXA', 'Op. de Caixa'),
        ('GERENTE', 'Gerente'),
        ('ADMINISTRATIVO', 'Administrativo'),
        ('S. GERENTE','S. Gerente')     ]
    

    funcionario_ativo_choice = [
        ('ATIVO', 'Ativo'),
        ('INATIVO', 'Inativo'),
    ]

    user = models.OneToOneField(User,on_delete=models.CASCADE, related_name='funcionario', null=True, blank=True)
    cd_usu = models.IntegerField(unique=True, null=True, blank=True, help_text="Código legado do vetor")
    funcao = models.CharField(max_length=50,choices=funcionario_funcao_choice,default='DEFINIR')
    status = models.CharField(max_length=20, choices=funcionario_ativo_choice, default='ATIVO')
    filial = models.ForeignKey('Filial', on_delete=models.PROTECT, null=True, blank=True)
    
    class Meta:
        db_table = 'glb_usu'

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class DadosVenda(models.Model):
    cd_cli = models.IntegerField()
    cd_nf = models.IntegerField()
    cd_vd = models.IntegerField()

    class Meta:
        db_table = 'dados_venda'
        unique_together = (('cd_nf', 'cd_vd'),)

    def __str__(self):
        return f"Venda {self.cd_nf} - VD {self.cd_vd}"


class DadosEntrega(models.Model):
    cd_entr = models.IntegerField()
    cd_vd = models.IntegerField()
    cd_fun_entr = models.IntegerField(null=True, blank=True)
    cd_fun_lib = models.IntegerField(null=True, blank=True)
    cd_mov_ret = models.IntegerField(null=True, blank=True)
    cd_filial = models.IntegerField(null=True, blank=True)
    data_entr_ini = models.DateField(auto_now_add=True)
    hora_entr_ini = models.TimeField(auto_now_add=True)
    data_hora_atribuicao = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    
    class Meta:
        managed = True
        db_table = 'dados_entrega'
        unique_together = ('cd_entr', 'cd_vd','cd_filial')  # chave composta


    def __str__(self):
        return f"Entrega {self.cd_entr}"





class EntregaFinalizada(models.Model):
    STATUS_CHOICES = [
        ('ENTREGUE', 'Entregue'),
        ('CLIENTE_AUSENTE', 'Cliente ausente'),
        ('ENDERECO_INCORRETO', 'Endereço incorreto'),
        ('CLIENTE_RECUSOU', 'Cliente recusou'),
    ]
    usermotoboy = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='entregas_finalizadas')
    entrega = models.ForeignKey(DadosEntrega, on_delete=models.CASCADE, related_name='entregas_finalizadas')
    venda = models.ForeignKey(DadosVenda, on_delete=models.SET_NULL, null=True, blank=True)
    funcionario = models.IntegerField(null=True, blank=True)
    cliente = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    cupomfiscal = models.IntegerField(null=True, blank=True)
    nome_cliente = models.CharField(max_length=200, null=True, blank=True)
    endereco = models.CharField(max_length=300, null=True, blank=True)
    complemento = models.CharField(max_length=200, null=True, blank=True)
    telefone = models.CharField(max_length=50, null=True, blank=True)
    data_hora_inicio = models.DateTimeField(null=True, blank=True)
    data_hora_entrega = models.DateTimeField(auto_now_add=True)
    entrega_status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='ENTREGUE'
    )
    observacoes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'entrega_finalizada'
        ordering = ['-data_hora_entrega']

    def __str__(self):
        return f'Entrega {self.entrega_id} - Cliente {self.nome_cliente} - Status: {self.entrega_status}'
      # ✅ Método helper (opcional e MUITO útil)
    def iniciar_entrega(self):
        self.data_hora_inicio = timezone.now()
        self.save()



class dadoskilometragem(models.Model):
    usermotoboy = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='pontuacao_motoboy')
    km_diario = models.FloatField(default=0.0)
    data_apuracao= models.DateField(blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    gorjeta = models.FloatField(default=0.0)
    
    class Meta:
        db_table = 'km_diario'

    def __str__(self):
        return f'Motoboy: {self.usermotoboy.get_full_name() if self.usermotoboy else "Desconecido"} - KM: {self.km_diario} - Gorjeta: {self.gorjeta}'
    

class HistoricoLocalizacao(models.Model):
    # Relaciona a localização ao usuário (entregador)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posicoes')
    
    # Coordenadas com precisão decimal (9 casas decimais é o padrão ouro para GPS)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    # Data e hora exata do registro
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Histórico de Entrega"
        ordering = ['-data_criacao']

    def __str__(self):
        return f"{self.usuario.username} - {self.data_criacao.strftime('%d/%m %H:%M')}"
    



class EscalaFixa(models.Model):
    DIAS_SEMANA = [
        (0, 'Segunda-feira'),
        (1, 'Terça-feira'),
        (2, 'Quarta-feira'),
        (3, 'Quinta-feira'),
        (4, 'Sexta-feira'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]
    
    ORDEM_DOMINGO = [
        (1, '1º Domingo do Mês'),
        (2, '2º Domingo do Mês'),
        (3, '3º Domingo do Mês'),
        (4, '4º Domingo do Mês'),
    ]

    TIPO_ESCALA = [
        ('FIXO', 'Folga Fixa'),
        ('SAB_DOM_ALT', 'Sábado e Domingo Alternados'),
        ('DIÁRIA', 'Diária'),
        ('SEMANAL', 'Semanal'),
        ('QUINZENAL', 'Quinzenal'),
        ('MENSAL', 'Mensal'),
    ]


    funcionario = models.OneToOneField('Funcionarios_lista', on_delete=models.CASCADE, related_name='escala_fixa')
    dia_fixo_semana = models.IntegerField(choices=DIAS_SEMANA, help_text="Dia que o funcionário sempre folga")
    domingo_do_mes = models.IntegerField(choices=ORDEM_DOMINGO, null=True, blank=True, help_text="Qual domingo do mês ele folga")
    tipo_escala = models.CharField(max_length=20, choices=TIPO_ESCALA, default='FIXO', help_text="Tipo de escala fixa")
    
    class Meta:
        db_table = 'folgasfixas'

    def __str__(self):
        return f"Escala de {self.funcionario}: {self.get_dia_fixo_semana_display()}"




#forum ou chat

class Forum(models.Model):
    titulo = models.CharField(max_length=200)
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'forum'

    def __str__(self):
        return self.titulo
    


    
class Comentario(models.Model):
    topico = models.ForeignKey(Forum, on_delete=models.CASCADE, related_name='comentarios')
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    texto = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)

    parent = models.ForeignKey('self',null=True, blank=True, on_delete=models.CASCADE,related_name='respostas')

    class Meta:
        db_table = 'comentario'

    def __str__(self):
        return f"{self.autor} - {self.texto[:20]}"
    

class Filial(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome