from django.contrib import admin

from .models import FaultReportStatus, ReportMechanic, ReportStatusChange, SparePart, UnitOperator


@admin.register(SparePart)
class SparePartAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "unit_price")
    search_fields = ("name", "description")
    ordering = ("name",)
    # The photo is uploaded from the app, which checks and re-encodes it; the raw upload of
    # the admin panel would skip that
    exclude = ("photo",)


@admin.register(UnitOperator)
class UnitOperatorAdmin(admin.ModelAdmin):
    """
    The model's clean() applies the API rules: one open assignment per unit and per operator,
    no future dates. An assignment is ended (end date), never deleted: it is the unit's history.
    """

    list_display = ("unit", "operator", "start_date", "end_date")
    list_filter = ("end_date",)
    search_fields = ("unit__economic_number", "operator__enrollment_id")
    ordering = ("-start_date",)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ReportMechanic)
class ReportMechanicAdmin(admin.ModelAdmin):
    list_display = ("fault_report", "mechanic", "start_date", "end_date")
    list_filter = ("end_date",)
    search_fields = ("fault_report__unit__economic_number", "mechanic__enrollment_id")
    ordering = ("-start_date",)


@admin.register(FaultReportStatus)
class FaultReportStatusAdmin(admin.ModelAdmin):
    list_display = ("order", "name")
    ordering = ("order",)


@admin.register(ReportStatusChange)
class ReportStatusChangeAdmin(admin.ModelAdmin):
    """The history is written by the system: here it can only be read."""

    list_display = ("fault_report", "status", "changed_at", "changed_by")
    list_filter = ("status",)
    ordering = ("-changed_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
