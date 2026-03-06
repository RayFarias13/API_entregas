from django.contrib import admin

from software.models import Funcionarios_lista, dadoskilometragem

# Register your models here.
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
