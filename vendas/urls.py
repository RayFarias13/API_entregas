from django.urls import path, include
from . import views

urlpatterns = [
    path('vendas/lancar/', views.renderizar_formulario_venda, name='vendas_lancar'),
    path('vendas/criar/', views.criar_pedido_view, name='vendas_criar'),
    path('produtos/buscar/<str:codigo>/', views.buscar_produto_view, name='buscar_produto_view'), # Nova rota
    path('produtos/novo/', views.produto_salvar_view, name='produto_criar'),
    path('produtos/editar/<int:pk>/', views.produto_salvar_view, name='produto_editar'),

]
