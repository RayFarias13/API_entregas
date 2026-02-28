#!/bin/bash

echo "===== Iniciando deploy do Django no Render ====="

# Ativar virtualenv
#source .venv/bin/activate

# Instalar dependências (caso necessário)
pip install -r Requirements.txt

# Migrar banco de dados
echo "Aplicando migrações..."
python manage.py makemigrations
python manage.py migrate

# Coletar arquivos estáticos
echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

#

# Inicia o Gunicorn
echo "Iniciando Gunicorn..."
gunicorn monitor_api.wsgi:application --bind 0.0.0.0:$PORT