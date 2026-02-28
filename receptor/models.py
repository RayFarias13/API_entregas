from django.db import models

class ApiRequest(models.Model):
    """Captura qualquer requisição"""
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=500)
    full_path = models.CharField(max_length=1000)
    headers = models.JSONField()
    query_params = models.JSONField(null=True, blank=True)
    body_raw = models.TextField(null=True, blank=True)
    body_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.method} {self.path} at {self.created_at}"


class Customer(models.Model):
    """Armazena dados do customer"""
    '''Amazerna novos endereços no banco de dados'''
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50)
    code = models.CharField(max_length=50, unique=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    login_email = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    address_complement = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=50, blank=True, null=True)
    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)
    operating_hour_start = models.TimeField(blank=True, null=True)
    operating_hour_end = models.TimeField(blank=True, null=True)
    extraFields = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.code})"




