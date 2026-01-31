from django.urls import path
from . import views

urlpatterns = [
    path('board/', views.board, name='board'),
    path('api/atualizar_status/', views.atualizar_status, name='atualizar-status'),
    path('entrega_avulsa/', views.criar_entrega_avulsa, name='entrega_avulsa'),  # função correta
    path('finalizar_entrega/', views.finalizar_entrega, name='finalizar_entrega'),

]
