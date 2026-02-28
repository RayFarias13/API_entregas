from django.urls import path, re_path
from .views import *

urlpatterns = [
    # 1️⃣ Endpoint real de customers (deve vir primeiro!)
    path('debug/customers', customers),

    # 2️⃣ Catch-all para capturar qualquer outra rota
    re_path(r'debug/(?P<path>.*)$', capturar_tudo, name='capturar_tudo'),
]
