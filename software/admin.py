from django.contrib import admin

#from software.models import Funcionarios_lista, dadoskilometragem, EntregaFinalizada, dadosvenda, dadosentrega
'''
# Register your models here.

@admin.register(dadosvenda)
class DadosVendaAdmin(admin.ModelAdmin):
    list_display = ("id", "cd_cli", "cd_nf", "cd_vd")
    search_fields = ("cd_cli", "cd_nf", "cd_vd")
    readonly_fields = ("id",)

@admin.register(dadosentrega)
class DadosEntregaAdmin(admin.ModelAdmin):
    list_display = ("id", "cd_entr", "cd_vd", "cd_fun_entr", "cd_fun_lib", "cd_mov_ret", "cd_filial", "data_entr_ini", "hora_entr_ini", "data_hora_atribuicao")
    search_fields = ("cd_entr", "cd_vd", "cd_fun_entr", "cd_fun_lib", "cd_mov_ret", "cd_filial")
    list_filter = ("data_entr_ini",)
    readonly_fields = ("id",)


@admin.register(Funcionarios_lista)
class CustomerAdmin(admin.ModelAdmin):
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
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "usermotoboy", "destinatario", "endereco_destino", "data_entrega")
    search_fields = ("usermotoboy__username", "destinatario", "endereco_destino")
    list_filter = ("data_entrega",)

'''
