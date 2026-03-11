from django.urls import path, include
from . import views

urlpatterns = [
    path('home/', views.board, name='board'),
    path('home_administrativo/', views.board_administrativo, name='boardadministrativo'),
    path('api/atualizar_status/', views.atualizar_status, name='atualizar-status'),
    path('entrega_avulsa/', views.criar_entrega_avulsa, name='entrega_avulsa'),  # função correta
    path('finalizar_entrega/', views.finalizar_entrega, name='finalizar_entrega'),
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),   
    path('cadastro_funcionario/', views.cadastro_funcionario, name='cadastro_funcionario'),
    path('entregas_motoboy/', views.board_motoboy, name='entregas_motoboy'),
    path('gerenciar_cadastros/', views.gerenciar_funcionarios, name='gerenciar_cadastros'),
    path('km/novo/', views.registrar_km_manual, name='registrar_km'),
    path('km/historico/', views.lista_km, name='lista_km'),
    path('localizacao_motoboy/', views.atualizar_localizacao, name='atualizar_localizacao'),
    path('mapa/', views.mapa_entregadores, name='mapa_entregadores'),
    path('posicoes/', views.dados_entregadores_json, name='dados_json'),
]
