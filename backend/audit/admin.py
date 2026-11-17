from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """The trail can only be read, here and everywhere else."""

    list_display = ("timestamp", "user_enrollment_id", "user_role", "action", "table_name", "record")
    list_filter = ("action", "table_name", "user_role")
    search_fields = ("user_enrollment_id", "user_name", "record")
    date_hierarchy = "timestamp"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
