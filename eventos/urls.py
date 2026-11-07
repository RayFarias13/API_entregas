from django.urls import path
from . import views

urlpatterns = [
    path('atendimento/',views.atedimento_pagina,name='atendimento'),
    path('buscar-cliente/', views.buscar_cliente, name='buscar_cliente'),
    path('salvar-atendimento/', views.salvar_atendimento, name='salvar_atendimento'),
]