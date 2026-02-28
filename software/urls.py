from django.urls import path, include
from . import views

urlpatterns = [
    path('board/', views.board, name='board'),
    path('api/atualizar_status/', views.atualizar_status, name='atualizar-status'),
    path('entrega_avulsa/', views.criar_entrega_avulsa, name='entrega_avulsa'),  # função correta
    path('finalizar_entrega/', views.finalizar_entrega, name='finalizar_entrega'),
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),   
    path('cadastro_funcionario/', views.cadastro_funcionario, name='cadastro_funcionario'),
    path('entregas_motoboy/', views.board_motoboy, name='entregas_motoboy'),
    path('gerenciar_cadastros/', views.gerenciar_funcionarios, name='gerenciar_cadastros'),
]
