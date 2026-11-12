from django.contrib import admin
from django.utils import timezone
from .models import Category, Comment, ServiceRequest, WorkOrder


class OverdueFilter(admin.SimpleListFilter):
    title = "due status"
    parameter_name = "overdue"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Overdue (open/assigned past due)"),
            ("no", "Not overdue"),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        active_statuses = [ServiceRequest.Status.OPEN, ServiceRequest.Status.ASSIGNED]
        if self.value() == "yes":
            return queryset.filter(status__in=active_statuses, due_at__lt=now)
        if self.value() == "no":
            return queryset.exclude(status__in=active_statuses, due_at__lt=now)
        return queryset


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "priority",
        "status",
        "due_at",
        "resolved_at",
        "created_at",
    )
    list_filter = ("status", "priority", "category", OverdueFilter)
    search_fields = ("title", "description", "location", "resolution_summary")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ("service_request", "technician", "assigned_at", "completed_at")
    list_filter = ("technician",)
    search_fields = ("service_request__title", "work_notes")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("service_request", "author", "is_internal", "created_at")
    list_filter = ("is_internal",)
    search_fields = ("body",)