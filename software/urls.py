from django.urls import path, include
from . import views

urlpatterns = [
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
    path('perfil/', views.perfil_motoboy, name='perfilmotoboy'),
    #path('perfil/entregas/', views.motoboy_entregas_dia,        name='motoboy_entregas_dia'),
    path('perfil/entregas/', views.board_motoboy,        name='motoboy_entregas_dia'),  # função correta
    path('perfil/historico/', views.motoboy_historico_entregas, name='motoboy_historico_entregas'),
    path('perfil/km/',        views.motoboy_historico_km,        name='motoboy_historico_km'),
    path('perfil/pontuacao/', views.motoboy_pontuacao,           name='motoboy_pontuacao'),
    path('cadastro_cliente/', views.cadastro_cliente, name='cadastro_cliente'),


]
