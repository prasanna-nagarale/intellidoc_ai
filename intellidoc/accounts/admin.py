# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ( "first_name", "last_name", "avatar", "bio", "phone")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "last_active", "created_at")}),
        ("Subscription", {"fields": ("plan", "documents_uploaded", "queries_made", "storage_used")}),
    )
    list_display = ("email", "first_name", "last_name", "is_staff", "plan")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
