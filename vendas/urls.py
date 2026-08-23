from django.urls import path, include
from . import views

urlpatterns = [
    # path('vendas/lancar/', views.renderizar_formulario_venda, name='vendas_lancar'),
    # path('vendas/criar/', views.criar_pedido_view, name='vendas_criar'),
    # path('produtos/buscar/<str:codigo>/', views.buscar_produto_view, name='buscar_produto_view'), # Nova rota
    # path('produtos/novo/', views.produto_salvar_view, name='produto_criar'),
    # path('produtos/editar/<int:pk>/', views.produto_salvar_view, name='produto_editar'),


     path("painel/", views.lista_pedidos, name="lista_pedidos"),
     path("painel/enviar-pdv/<int:pedido_id>/",views.enviar_para_pdv,name="enviar_para_pdv"),


    path("pedidos/<int:pedido_id>/",views.conferir_pedido,name="conferir_pedido",),

    path("pedidos/<int:pedido_id>/bipar/",views.bipar_produto,name="bipar_produto",),

    path("pedidos/<int:pedido_id>/finalizar/",views.finalizar_conferencia,name="finalizar_conferencia",),

]
