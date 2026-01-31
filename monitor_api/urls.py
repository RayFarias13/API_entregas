from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter # router que gera rotas para ViewSets



urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("receptor.urls")),
    path('api/token/',obtain_auth_token, name='api_token_auth'),  # endpoint para obter o token
    path("soft/", include("software.urls")),
]

