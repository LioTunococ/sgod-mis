from django.contrib import admin

from .models import (
    Form1ADMHeader,
    Form1ADMRow,
    Form1PctHeader,
    Form1PctRow,
    Form1ReadingCRLA,
    Form1ReadingIntervention,
    Form1ReadingPHILIRI,
    Form1RMAIntervention,
    Form1RMARow,
    Form1SLPAnalysis,
    Form1SLPRow,
    Form1SLPTopDNME,
    Form1SLPTopOutstanding,
    Form1Signatories,
    Form1SupervisionRow,
    FormTemplate,
    Period,
    SMEAActivityRow,
    SMEAProject,
    Submission,
    SubmissionAttachment,
)


class ReadOnlyInlineMixin:
    readonly_fields: tuple[str, ...] = ()

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    list_display = ("label", "school_year_start", "quarter_tag", "display_order", "is_active")
    list_filter = ("school_year_start", "quarter_tag", "is_active")
    search_fields = ("label",)
    ordering = ("-school_year_start", "display_order")
    
    actions = ['create_school_year_quarters']
    
    change_list_template = "admin/period_changelist.html"
    
    @admin.action(description="Auto-create Q1-Q4 for school year(s)")
    def create_school_year_quarters(self, request, queryset):
        """Admin action to create 4 quarters for selected school years"""
        from django.contrib import messages
        
        # Get unique school years from selection
        school_years = queryset.values_list('school_year_start', flat=True).distinct()
        
        created_count = 0
        for year in school_years:
            quarters = ['Q1', 'Q2', 'Q3', 'Q4']
            for index, quarter_tag in enumerate(quarters, start=1):
                _, created = Period.objects.get_or_create(
                    school_year_start=year,
                    quarter_tag=quarter_tag,
                    defaults={
                        'label': f'{quarter_tag}',
                        'display_order': index,
                        'is_active': True
                    }
                )
                if created:
                    created_count += 1
        
        messages.success(request, f'Created {created_count} quarters for {len(school_years)} school year(s).')
    
    def changelist_view(self, request, extra_context=None):
        """Add form for quick school year creation"""
        extra_context = extra_context or {}
        
        if request.method == 'POST' and 'create_school_year' in request.POST:
            from django.contrib import messages
            year_start = request.POST.get('year_start')
            
            try:
                year_start = int(year_start)
                created_count = 0
                quarters = ['Q1', 'Q2', 'Q3', 'Q4']
                
                for index, quarter_tag in enumerate(quarters, start=1):
                    _, created = Period.objects.get_or_create(
                        school_year_start=year_start,
                        quarter_tag=quarter_tag,
                        defaults={
                            'label': f'{quarter_tag}',
                            'display_order': index,
                            'is_active': True
                        }
                    )
                    if created:
                        created_count += 1
                
                if created_count > 0:
                    messages.success(request, f'Created SY {year_start}-{year_start+1} with {created_count} quarters.')
                else:
                    messages.warning(request, f'SY {year_start}-{year_start+1} already exists.')
            except (ValueError, TypeError):
                messages.error(request, 'Invalid year value.')
        
        # Get list of existing school years
        existing_years = Period.objects.values_list('school_year_start', flat=True).distinct().order_by('-school_year_start')
        extra_context['existing_school_years'] = list(existing_years)
        
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(FormTemplate)
class FormTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "code",
        "section",
        "school_year",
        "quarter_filter",
        "period_type",
        "open_at",
        "close_at",
        "is_active",
    )
    list_filter = ("section", "school_year", "quarter_filter", "period_type", "is_active")
    search_fields = ("title", "code")
    autocomplete_fields = ("section",)


class SubmissionAttachmentInline(ReadOnlyInlineMixin, admin.TabularInline):
    model = SubmissionAttachment
    extra = 0
    readonly_fields = ("original_name", "file", "size", "uploaded_at")


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("school", "form_template", "period", "status", "updated_at")
    list_filter = (
        "status",
        "form_template__section",
        "period__school_year_start",
        "period__quarter_tag",
    )
    search_fields = ("school__name", "form_template__title", "form_template__code")
    autocomplete_fields = ("school", "form_template", "period")
    readonly_fields = (
        "created_at",
        "updated_at",
        "submitted_at",
        "returned_at",
        "noted_at",
    )
    inlines = [SubmissionAttachmentInline]


class SMEAActivityInline(admin.TabularInline):
    model = SMEAActivityRow
    extra = 0


@admin.register(SMEAProject)
class SMEAProjectAdmin(admin.ModelAdmin):
    list_display = ("project_title", "area_of_concern", "submission")
    inlines = [SMEAActivityInline]


class Form1PctRowInline(ReadOnlyInlineMixin, admin.TabularInline):
    model = Form1PctRow
    extra = 0
    readonly_fields = ("area", "percent", "action_points")


@admin.register(Form1PctHeader)
class Form1PctHeaderAdmin(admin.ModelAdmin):
    list_display = ("submission",)
    inlines = [Form1PctRowInline]


@admin.register(Form1SLPRow)
class Form1SLPRowAdmin(admin.ModelAdmin):
    list_display = ("submission", "grade_label", "subject", "is_offered", "enrolment", "dnme", "fs", "s", "vs", "o")
    list_filter = ("grade_label", "subject", "is_offered")
    search_fields = ("submission__school__name", "grade_label", "subject")


@admin.register(Form1SLPAnalysis)
class Form1SLPAnalysisAdmin(admin.ModelAdmin):
    list_display = ("slp_row", "created_at", "updated_at")
    readonly_fields = ("slp_row", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("slp_row__grade_label", "slp_row__subject")


@admin.register(Form1SLPTopDNME)
class Form1SLPTopDNMEAdmin(admin.ModelAdmin):
    list_display = ("submission", "position", "grade_label", "count")
    list_filter = ("position",)


@admin.register(Form1SLPTopOutstanding)
class Form1SLPTopOutstandingAdmin(admin.ModelAdmin):
    list_display = ("submission", "position", "grade_label", "count")
    list_filter = ("position",)


@admin.register(Form1ReadingCRLA)
class Form1ReadingCRLAAdmin(admin.ModelAdmin):
    list_display = ("submission", "level", "timing", "subject", "band", "count")
    list_filter = ("level", "timing", "subject", "band")


@admin.register(Form1ReadingPHILIRI)
class Form1ReadingPHILIRIAdmin(admin.ModelAdmin):
    list_display = (
        "submission",
        "level",
        "timing",
        "language",
        "band_4_7",
        "band_5_8",
        "band_6_9",
        "band_10",
    )
    list_filter = ("level", "timing", "language")


@admin.register(Form1ReadingIntervention)
class Form1ReadingInterventionAdmin(admin.ModelAdmin):
    list_display = ("submission", "order", "description")


@admin.register(Form1RMARow)
class Form1RMARowAdmin(admin.ModelAdmin):
    list_display = (
        "submission",
        "grade_label",
        "enrolment",
        "emerging_not_proficient",
        "emerging_low_proficient",
        "developing_nearly_proficient",
        "transitioning_proficient",
        "at_grade_level",
    )
    list_filter = ("grade_label",)


@admin.register(Form1RMAIntervention)
class Form1RMAInterventionAdmin(admin.ModelAdmin):
    list_display = ("submission", "order", "description")


@admin.register(Form1SupervisionRow)
class Form1SupervisionRowAdmin(admin.ModelAdmin):
    list_display = (
        "submission",
        "grade_label",
        "total_teachers",
        "teachers_supervised_observed_ta",
    )
    list_filter = ("grade_label",)


@admin.register(Form1ADMHeader)
class Form1ADMHeaderAdmin(admin.ModelAdmin):
    list_display = ("submission", "is_offered")
    list_filter = ("is_offered",)


@admin.register(Form1ADMRow)
class Form1ADMRowAdmin(admin.ModelAdmin):
    list_display = (
        "submission",
        "ppas_physical_target",
        "ppas_physical_actual",
        "ppas_physical_percent",
        "funds_downloaded",
        "funds_obligated",
        "funds_percent_obligated",
    )



@admin.register(Form1Signatories)
class Form1SignatoriesAdmin(admin.ModelAdmin):
    list_display = ("submission", "prepared_by", "submitted_to")



