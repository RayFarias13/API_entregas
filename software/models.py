from django.db import models
from django.utils import timezone
from receptor.models import Customer 
from django.contrib.auth.models import User


class Funcionarios_lista(models.Model):
    funcionario_funcao_choice = [
        ('ENTREGADOR', 'Entregador'),
        ('OP. DE CAIXA', 'Op. de Caixa'),
        ('GERENTE', 'Gerente'),
        ('ADMINISTRATIVO', 'Administrativo'),
        ('S. GERENTE','S. Gerente')
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='funcionario'
    )
    cd_usu = models.IntegerField(
        unique=True,
        null=True,
        blank=True,
        help_text="Código legado do vetor"
    )
    funcao = models.CharField(
        max_length=50,
        choices=funcionario_funcao_choice,
        default='DEFINIR'
    )

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
    data_entr_ini = models.DateField(auto_now_add=True)
    hora_entr_ini = models.TimeField(auto_now_add=True)

    class Meta:
        db_table = 'dados_entrega'

    def __str__(self):
        return f"Entrega {self.cd_entr}"





class EntregaFinalizada(models.Model):
    STATUS_CHOICES = [
        ('ENTREGUE', 'Entregue'),
        ('CLIENTE_AUSENTE', 'Cliente ausente'),
        ('ENDERECO_INCORRETO', 'Endereço incorreto'),
        ('CLIENTE_RECUSOU', 'Cliente recusou'),
    ]

    entrega = models.ForeignKey(DadosEntrega, on_delete=models.CASCADE, related_name='entregas_finalizadas')
    venda = models.ForeignKey(DadosVenda, on_delete=models.CASCADE, related_name='entregas_finalizadas')
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

    def __str__(self):
        return f'Entrega {self.entrega_id} - Cliente {self.nome_cliente} - Status: {self.entrega_status}'
