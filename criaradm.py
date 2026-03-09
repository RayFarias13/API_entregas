#comando apenas para criar adm, no banco do neon
import os
import django
from django.contrib.auth import get_user_model

# Configura o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'monitor_api.settings')
django.setup()

User = get_user_model()

# Pega das variáveis do Render ou usa um padrão caso estejam vazias
# O segundo argumento é o "plano B" se a variável não existir
username = os.getenv('USERADMIN')
email = os.getenv('EMAILADMIN')
password = os.getenv('PASSWORDADMIN')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f"Sucesso: Usuário '{username}' criado!")
else:
    print(f"Aviso: Usuário '{username}' já existe no Neon.")