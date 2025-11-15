from django.contrib import admin

from .models import SchoolUserRole, SectionUserRole, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "school", "is_sgod_admin", "section_admin_codes", "created_at")
    search_fields = ("user__username", "user__first_name", "user__last_name", "school__name", "school__code")
    list_filter = ("is_sgod_admin", "districts")
    autocomplete_fields = ("user", "school", "districts")
    filter_horizontal = ("districts",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(SchoolUserRole)
class SchoolUserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "school", "role", "is_primary", "created_at")
    list_filter = ("role", "is_primary", "school__division", "school__district")
    search_fields = ("user__username", "user__first_name", "user__last_name", "school__name", "school__code")
    autocomplete_fields = ("user", "school")
    readonly_fields = ("created_at",)


@admin.register(SectionUserRole)
class SectionUserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "section", "role", "created_at")
    list_filter = ("role", "section__code")
    search_fields = ("user__username", "user__first_name", "user__last_name", "section__name", "section__code")
    autocomplete_fields = ("user", "section")
    readonly_fields = ("created_at",)
