from django.contrib import admin

from software.models import EscalaFixa, Filial, Funcionarios_lista, dadoskilometragem, EntregaFinalizada, DadosVenda, DadosEntrega
''
# Register your models here.

@admin.register(DadosVenda)
class DadosVendaAdmin(admin.ModelAdmin):
    list_display = ("id", "cd_cli", "cd_nf", "cd_vd")
    search_fields = ("cd_cli", "cd_nf", "cd_vd")
    readonly_fields = ("id",)

@admin.register(DadosEntrega)
class DadosEntregaAdmin(admin.ModelAdmin):
    list_display = ("id", "cd_entr", "cd_vd", "cd_fun_entr", "cd_fun_lib", "cd_mov_ret", "cd_filial", "data_entr_ini", "hora_entr_ini", "data_hora_atribuicao")
    search_fields = ("cd_entr", "cd_vd", "cd_fun_entr", "cd_fun_lib", "cd_mov_ret", "cd_filial")
    list_filter = ("data_entr_ini",)
    readonly_fields = ("id",)


@admin.register(Funcionarios_lista)
class Funcionario_listaAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "cd_usu", "funcao")
    search_fields = ("user__username", "cd_usu", "funcao")
    list_filter = ("funcao",)
    readonly_fields = ("id",)

@admin.register(dadoskilometragem)
class DadoskilometragemAdmin(admin.ModelAdmin):
    list_display = ("id", "usermotoboy", "km_diario", "data_apuracao")
    search_fields = ("usermotoboy__username", "km_diario")
    list_filter = ("data_apuracao",)
    readonly_fields = ("id",)

    
@admin.register(EntregaFinalizada)
class EntregaFinalizadaAdmin(admin.ModelAdmin):
    list_display = ('id','entrega','venda','funcionario','cliente','cupomfiscal','nome_cliente','endereco','entrega_status','data_hora_entrega')
    search_fields = ('id','funcionario','cliente','cupomfiscal','nome_cliente','endereco')
    list_filter = ('entrega_status','cliente',)
    readonly_fields = ('id',)
    
@admin.register(Filial)
class FilialAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome')
    search_fields = ('nome',)
    readonly_fields = ('id',)


@admin.register(EscalaFixa)
class EscalaFixaAdmin(admin.ModelAdmin):
    list_display = ('id', 'funcionario', 'dia_fixo_semana', 'domingo_do_mes', 'tipo_escala', 'data_inicio')
    search_fields = ('funcionario__user__username',)
    list_filter = ('dia_fixo_semana', 'tipo_escala')
    readonly_fields = ('id',)