from django.contrib import admin
from .models import ApiRequest, Customer

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "type", "email", "phone_number")
    search_fields = ("name", "code", "email", "phone_number")
    list_filter = ("type",)
    readonly_fields = ("id",)

@admin.register(ApiRequest)
class ApiRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "method", "path", "full_path", "created_at")
    search_fields = ("path", "full_path", "headers", "body_raw")
    readonly_fields = ("id", "method", "path", "full_path", "headers", "query_params", "body_raw", "body_json", "created_at")
    list_filter = ("method",)
    ordering = ("-created_at",)
