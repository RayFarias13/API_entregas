#comando apenas para criar adm, no banco do neon
import os
import django
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'monitor_api.settings')
django.setup()

User = get_user_model()
USERADMIN = os.getenv('DJANGO_SUPERUSER_USERNAME')
EMAILADMIN = os.getenv('DJANGO_SUPERUSER_EMAIL')
PASSWORDADMIN = os.getenv('DJANGO_SUPERUSER_PASSWORD')

if not User.objects.filter(username=USERADMIN).exists():
    User.objects.create_superuser(USERADMIN, EMAILADMIN, PASSWORDADMIN)
    print(f"Superusuário '{USERADMIN}' criado com sucesso!")
else:
    print(f"Superusuário '{USERADMIN}' já existe.")