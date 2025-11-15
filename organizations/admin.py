from django.contrib import admin

from .models import District, Section, School, SchoolProfile


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "school_count")
    search_fields = ("name", "code")
    ordering = ("name",)
    
    def school_count(self, obj):
        """Show number of schools in this district"""
        count = obj.schools.count()
        return f"{count} schools"
    school_count.short_description = "Schools"


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "form_count")
    search_fields = ("code", "name")
    ordering = ("code",)
    
    def form_count(self, obj):
        """Show number of forms associated with this section"""
        from submissions.models import FormTemplate
        count = FormTemplate.objects.filter(section=obj).count()
        return f"{count} forms"
    form_count.short_description = "Forms"


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "division",
        "district",
        "school_type",
        "grade_span_label",
        "implements_adm",
    )
    list_filter = ("division", "district", "school_type", "implements_adm")
    search_fields = ("name", "code")
    autocomplete_fields = ("district",)


@admin.register(SchoolProfile)
class SchoolProfileAdmin(admin.ModelAdmin):
    list_display = ("school", "head_name", "grade_span_start", "grade_span_end")
    search_fields = ("school__name", "school__code", "head_name")
    autocomplete_fields = ("school",)

