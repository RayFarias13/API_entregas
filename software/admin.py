from django.contrib import admin

from software.models import Funcionarios_lista

# Register your models here.
@admin.register(Funcionarios_lista)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "cd_usu", "funcao")
    search_fields = ("user__username", "cd_usu", "funcao")
    list_filter = ("funcao",)
    readonly_fields = ("id",)