from __future__ import annotations

from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.forms import modelformset_factory, inlineformset_factory
from django.forms.models import BaseInlineFormSet

# --- Custom Formset to Allow Deletion of Invalid Forms ---

# Improved: skip validation for forms marked for deletion by setting empty_permitted
class DeletionFriendlyBaseInlineFormSet(BaseInlineFormSet):
    def is_valid(self):
        # Before validation, forcibly mark forms with DELETE checked as empty_permitted
        if self.can_delete:
            for form in self.forms:
                delete_val = None
                # Try to get DELETE from raw data (works even if form is invalid)
                if hasattr(form, 'data'):
                    delete_val = form.data.get(form.add_prefix('DELETE'))
                if delete_val in ('on', '1', 'true', 'yes', 'checked'):
                    form.empty_permitted = True
        return super().is_valid()

    def _should_delete_form(self, form):
        # Allow deletion if DELETE is checked, regardless of validity or emptiness
        return form.cleaned_data.get('DELETE', False) or (
            hasattr(form, 'data') and form.data.get(form.add_prefix('DELETE')) in ('on', '1', 'true', 'yes', 'checked')
        )

    def clean(self):
        # Mark forms for deletion as empty_permitted before validation
        if self.can_delete:
            for form in self.forms:
                if self._should_delete_form(form):
                    form.empty_permitted = True
        super().clean()

from django.utils.text import slugify

from .models import (
    Form1SLPRow,
    Form1SLPLLCEntry,
    Form1SLPAnalysis,
)

# ---- SLP (School Learning Progress) Forms ----

class SLPProficiencyForm(forms.ModelForm):
    """Form for handling proficiency data entry for each grade level"""
    class Meta:
        model = Form1SLPRow
        fields = ['enrolment', 'dnme', 'fs', 's', 'vs', 'o']
        widgets = {
            'enrolment': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'dnme': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'fs': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            's': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'vs': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'o': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'})
        }

    def clean(self):
        cleaned_data = super().clean()
        enrolment = cleaned_data.get('enrolment') or 0
        total = sum(cleaned_data.get(f, 0) for f in ['dnme', 'fs', 's', 'vs', 'o'])
        if total > enrolment:
            raise forms.ValidationError("Total of proficiency levels cannot exceed enrollment")
        return cleaned_data

class SLPLLCEntryForm(forms.ModelForm):
    """Form for handling Least Learned Competency entries"""
    class Meta:
        model = Form1SLPLLCEntry
        fields = ['llc_description', 'intervention']
        widgets = {
            'llc_description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Describe the Least Learned Competency'
            }),
            'intervention': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Describe the intervention plan'
            })
        }

class SLPAnalysisForm(forms.ModelForm):
    """Form for handling SLP analysis data per learning area"""
    class Meta:
        model = Form1SLPAnalysis
        fields = ['dnme_factors', 'fs_factors', 's_practices',
                 'vs_practices', 'o_practices', 'overall_strategy']
        widgets = {
            'dnme_factors': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 4,
                'placeholder': 'Describe hindering factors for DNME learners'
            }),
            'fs_factors': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 4,
                'placeholder': 'Describe hindering factors for FS learners'
            }),
            's_practices': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 4,
                'placeholder': 'Describe best practices for Satisfactory learners'
            }),
            'vs_practices': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 4,
                'placeholder': 'Describe best practices for Very Satisfactory learners'
            }),
            'o_practices': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 4,
                'placeholder': 'Describe best practices for Outstanding learners'
            }),
            'overall_strategy': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 4,
                'placeholder': 'Describe overall strategy for DNME learners'
            })
        }

# Form sets
SLPLLCEntryFormSet = forms.modelformset_factory(
    Form1SLPLLCEntry,
    form=SLPLLCEntryForm,
    extra=3,
    max_num=3,
    min_num=3,
    validate_min=True,
    can_delete=False
)



from . import constants as smea_constants
from . import constants as smea_constants
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
    SMEAActivityRow,
    SMEAProject,
    Submission,
    SubmissionAttachment,
    # New Reading Assessment Models
    ReadingAssessmentCRLA,
    ReadingAssessmentPHILIRI,
    ReadingInterventionNew,
)





class SMEAProjectForm(forms.ModelForm):
    AREA_CHOICES = [
        ('', '-- Select Area of Concern --'),
        ('Access', 'Access'),
        ('Quality', 'Quality'),
        ('Equity', 'Equity'),
        ('Enabling Mechanisms', 'Enabling Mechanisms'),
    ]
    
    area_of_concern = forms.ChoiceField(
        choices=AREA_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'project-field'})
    )
    
    class Meta:
        model = SMEAProject
        fields = ["project_title", "area_of_concern", "conference_date"]
        widgets = {
            "project_title": forms.TextInput(attrs={"class": "project-field"}),
            "conference_date": forms.DateInput(attrs={"type": "date", "class": "project-field"}),
        }


class SMEAActivityRowForm(forms.ModelForm):
    class Meta:
        model = SMEAActivityRow
        fields = [
            "activity",
            "output_target",
            "output_actual",
            "timeframe_target",
            "timeframe_actual",
            "budget_target",
            "budget_actual",
            "interpretation",
            "issues_unaddressed",
            "facilitating_factors",
            "agreements",
        ]
        widgets = {
            "activity": forms.Textarea(attrs={"rows": 3, "class": "activity-field table-input table-textarea"}),
            "output_target": forms.TextInput(attrs={"class": "activity-field table-input numeric-input"}),
            "output_actual": forms.TextInput(attrs={"class": "activity-field table-input numeric-input"}),
            "timeframe_target": forms.TextInput(attrs={"class": "activity-field table-input", "placeholder": "e.g., Jan-Mar"}),
            "timeframe_actual": forms.TextInput(attrs={"class": "activity-field table-input", "placeholder": "e.g., Jan-Feb"}),
            "budget_target": forms.TextInput(attrs={"class": "activity-field table-input numeric-input"}),
            "budget_actual": forms.TextInput(attrs={"class": "activity-field table-input numeric-input"}),
            "interpretation": forms.Textarea(attrs={"rows": 3, "class": "activity-field table-input table-textarea"}),
            "issues_unaddressed": forms.Textarea(attrs={"rows": 3, "class": "activity-field table-input table-textarea"}),
            "facilitating_factors": forms.Textarea(attrs={"rows": 3, "class": "activity-field table-input table-textarea"}),
            "agreements": forms.Textarea(attrs={"rows": 3, "class": "activity-field table-input table-textarea"}),
        }





class SubmissionAttachmentForm(forms.ModelForm):

    file = forms.FileField(label="Upload supporting file")



    class Meta:

        model = SubmissionAttachment

        fields = ["file"]



    def save(self, submission, commit: bool = True):

        attachment = super().save(commit=False)

        attachment.submission = submission

        attachment.original_name = self.cleaned_data["file"].name

        if commit:

            attachment.save()

        return attachment





class SubmissionReviewForm(forms.Form):

    ACTION_RETURN = "return"

    ACTION_NOTE = "note"

    ACTION_CHOICES = (

        (ACTION_NOTE, "Note"),

        (ACTION_RETURN, "Return with remarks"),

    )



    action = forms.ChoiceField(choices=ACTION_CHOICES)

    remarks = forms.CharField(widget=forms.Textarea, required=False)



    def clean(self):

        cleaned = super().clean()

        action = cleaned.get("action")

        remarks = cleaned.get("remarks", "").strip()

        if action == self.ACTION_RETURN and not remarks:

            self.add_error("remarks", "Remarks are required when returning a submission.")

        cleaned["remarks"] = remarks

        return cleaned





class Form1PctRowForm(forms.ModelForm):

    class Meta:

        model = Form1PctRow

        fields = ["area", "percent", "action_points"]

        widgets = {

            "action_points": forms.Textarea(attrs={"rows": 3}),

            "percent": forms.NumberInput(attrs={"min": 0, "max": 100}),

        }



    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["area"].disabled = True

        self.fields["area"].widget = forms.HiddenInput()

        self.fields["percent"].widget.attrs.setdefault("title", "Percent implementation for this area (0-100).")

        self.fields["action_points"].widget.attrs.setdefault("placeholder", "Key actions or follow-up plans")



    def clean_percent(self):

        percent = self.cleaned_data.get("percent")

        if percent is None:

            return percent

        if percent < 0 or percent > 100:

            raise ValidationError("Percent must be between 0 and 100.")

        return percent





class Form1SLPRowForm(forms.ModelForm):
    REASON_CHOICES = [
        ("a", "Pre-requisite skills were not mastered"),
        ("b", "The identified LLC are difficult to teach"),
        ("c", "The identified LLC were not covered or taught during the quarter"),
        ("d", "Learners under DNME or FS have special education needs"),
        ("e", "Reading proficiency DNME/FS: low/high emerging (G1-G3) or non-reader/frustration (G4-G10)"),
        ("f", "Other observable reasons (specify)")
    ]

    # Present reasons as multi-select checkboxes, but store as CSV in the model field
    reasons = forms.MultipleChoiceField(
        choices=REASON_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple
    )
    reason_other = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "If Other (f), please specify 2-5 sentences."})
    )

    class Meta:
        model = Form1SLPRow
        fields = [
            "grade_label",
            "subject",
            "enrolment",
            "dnme",
            "fs",
            "s",
            "vs",
            "o",
            "is_offered",
            "top_three_llc",
            # New storage fields (bound via custom clean/save)
            "non_mastery_reasons",
            "non_mastery_other",
            "intervention_plan",
        ]
        widgets = {
            "top_three_llc": forms.Textarea(attrs={"rows": 2}),
            "intervention_plan": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["grade_label"].disabled = True
        self.fields["grade_label"].widget = forms.HiddenInput()
        self.fields["subject"].disabled = True
        self.fields["subject"].widget = forms.HiddenInput()

        numeric_fields = ["enrolment", "dnme", "fs", "s", "vs", "o"]
        for field in numeric_fields:
            if field in self.fields:
                self.fields[field].widget.attrs.setdefault("min", 0)
                classes = self.fields[field].widget.attrs.get("class", "")
                classes = f"{classes} slp-input".strip()
                self.fields[field].widget.attrs["class"] = classes
                self.fields[field].required = False

        field_hints = {
            "enrolment": "Total learners enrolled for this subject.",
            "dnme": "Learners who did not meet expectations.",
            "fs": "Fairly satisfactory learners.",
            "s": "Satisfactory learners.",
            "vs": "Very satisfactory learners.",
            "o": "Outstanding learners.",
            "is_offered": "Uncheck if this subject is not offered for the grade.",
        }
        for field, hint in field_hints.items():
            if field in self.fields:
                self.fields[field].widget.attrs.setdefault("title", hint)

        if "is_offered" in self.fields:
            self.fields["is_offered"].label = "Subject offered"

        if "top_three_llc" in self.fields:
            self.fields["top_three_llc"].widget.attrs.update({
                "placeholder": "List the 3 least learned competencies, one per line",
                "rows": 6
            })
            self.fields["top_three_llc"].label = ""
            self.fields["top_three_llc"].required = False
        if "intervention_plan" in self.fields:
            self.fields["intervention_plan"].widget.attrs.update({
                "placeholder": "List the interventions for each competency, one per line",
                "rows": 6
            })
            self.fields["intervention_plan"].label = ""
            self.fields["intervention_plan"].required = False

        # Initialize the virtual reasons fields from model storage
        if self.instance and getattr(self.instance, "non_mastery_reasons", None) is not None:
            stored = (self.instance.non_mastery_reasons or "").split(",") if self.instance.non_mastery_reasons else []
            self.initial.setdefault("reasons", [s.strip() for s in stored if s.strip()])
        if self.instance and getattr(self.instance, "non_mastery_other", None) is not None:
            self.initial.setdefault("reason_other", self.instance.non_mastery_other)

    def clean(self):
        cleaned = super().clean()
        for field in ["enrolment", "dnme", "fs", "s", "vs", "o"]:
            cleaned[field] = cleaned.get(field) or 0
        if not cleaned.get("is_offered", True):
            for field in ["enrolment", "dnme", "fs", "s", "vs", "o"]:
                cleaned[field] = 0
            return cleaned
        enrolment = cleaned.get("enrolment") or 0
        detail_sum = sum([
            cleaned.get("dnme") or 0,
            cleaned.get("fs") or 0,
            cleaned.get("s") or 0,
            cleaned.get("vs") or 0,
            cleaned.get("o") or 0,
        ])
        if detail_sum > enrolment:
            grade_value = getattr(self.instance, "grade_label", None) or cleaned.get("grade_label") or "this grade"
            subject_code = cleaned.get("subject") or getattr(self.instance, "subject", None)
            if hasattr(self.instance, "get_subject_display"):
                subject_label = self.instance.get_subject_display()
            else:
                subject_label = smea_constants.SLP_SUBJECT_LABELS.get(subject_code, subject_code or "subject")
            raise ValidationError(f"Totals for {grade_value} ({subject_label}) cannot exceed enrolment.")

        # Validate reasons: if 'f' selected, require reason_other 2-5 sentences
        reasons = cleaned.get("reasons") or []
        other_text = (cleaned.get("reason_other") or "").strip()
        if "f" in reasons:
            # Naive sentence count by period/question mark/exclamation
            sent_count = len([s for s in other_text.replace("!", ".").replace("?", ".").split(".") if s.strip()])
            if sent_count < 2:
                self.add_error("reason_other", "Please provide 2-5 sentences explaining the other reasons.")
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        # Serialize reasons virtual fields back to storage
        reasons_list = self.cleaned_data.get("reasons") or []
        obj.non_mastery_reasons = ",".join(reasons_list)
        obj.non_mastery_other = (self.cleaned_data.get("reason_other") or "").strip()
        if commit:
            obj.save()
        return obj
        return cleaned




class Form1SLPAnalysisForm(forms.ModelForm):
    """Form for SLP Analysis questions per learning area"""

    class Meta:
        model = Form1SLPAnalysis

        fields = [
            "dnme_factors",
            "fs_factors",
            "s_practices",
            "vs_practices",
            "o_practices",
            "overall_strategy",
        ]

        widgets = {
            "dnme_factors": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Describe the root causes why learners did not meet expectations in this learning area...",
                "class": "form-control"
            }),
            "fs_factors": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Describe the root causes why learners are fairly satisfactory in this learning area...",
                "class": "form-control"
            }),
            "s_practices": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Describe what facilitating factors helped satisfactory learners...",
                "class": "form-control"
            }),
            "vs_practices": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Describe what facilitating factors helped very satisfactory learners...",
                "class": "form-control"
            }),
            "o_practices": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Describe what facilitating factors helped outstanding learners...",
                "class": "form-control"
            }),
            "overall_strategy": forms.Textarea(attrs={
                "rows": 5,
                "placeholder": "Describe your specific strategy or intervention to address DNME learners in this learning area...",
                "class": "form-control"
            }),
        }





class Form1SLPTopDNMEForm(forms.ModelForm):

    class Meta:

        model = Form1SLPTopDNME

        fields = ["position", "grade_label", "count"]



    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["position"].disabled = True

        self.fields["position"].widget = forms.HiddenInput()





class Form1SLPTopOutstandingForm(forms.ModelForm):

    class Meta:

        model = Form1SLPTopOutstanding

        fields = ["position", "grade_label", "count"]



    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["position"].disabled = True

        self.fields["position"].widget = forms.HiddenInput()





class Form1ReadingCRLAForm(forms.ModelForm):

    class Meta:

        model = Form1ReadingCRLA

        fields = ["level", "timing", "subject", "band", "count"]

        widgets = {

            "count": forms.NumberInput(attrs={"min": 0}),

        }





class Form1ReadingPHILIRIForm(forms.ModelForm):

    class Meta:

        model = Form1ReadingPHILIRI

        fields = [

            "level",

            "timing",

            "language",

            "band_4_7",

            "band_5_8",

            "band_6_9",

            "band_10",

        ]

        widgets = {

            "band_4_7": forms.NumberInput(attrs={"min": 0}),

            "band_5_8": forms.NumberInput(attrs={"min": 0}),

            "band_6_9": forms.NumberInput(attrs={"min": 0}),

            "band_10": forms.NumberInput(attrs={"min": 0}),

        }





class Form1ReadingInterventionForm(forms.ModelForm):

    class Meta:

        model = Form1ReadingIntervention

        fields = ["order", "description"]

        widgets = {

            "description": forms.Textarea(attrs={"rows": 2}),

        }



    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["order"].disabled = True

        self.fields["order"].widget = forms.HiddenInput()





class Form1RMARowForm(forms.ModelForm):

    class Meta:
        model = Form1RMARow
        fields = [
            "grade_label",
            "enrolment",
            "emerging_not_proficient",
            "emerging_low_proficient",
            "developing_nearly_proficient",
            "transitioning_proficient",
            "at_grade_level",
        ]
        widgets = {
            "enrolment": forms.NumberInput(attrs={"min": 0}),
            "emerging_not_proficient": forms.NumberInput(attrs={"min": 0}),
            "emerging_low_proficient": forms.NumberInput(attrs={"min": 0}),
            "developing_nearly_proficient": forms.NumberInput(attrs={"min": 0}),
            "transitioning_proficient": forms.NumberInput(attrs={"min": 0}),
            "at_grade_level": forms.NumberInput(attrs={"min": 0}),
        }
        labels = {
            "emerging_not_proficient": "Emerging - Not Proficient",
            "emerging_low_proficient": "Emerging - Low Proficient",
            "developing_nearly_proficient": "Developing - Nearly Proficient",
            "transitioning_proficient": "Transitioning - Proficient",
            "at_grade_level": "At Grade Level",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["grade_label"].disabled = True
        self.fields["grade_label"].widget = forms.HiddenInput()

        proficiency_fields = [
            "enrolment",
            "emerging_not_proficient",
            "emerging_low_proficient",
            "developing_nearly_proficient",
            "transitioning_proficient",
            "at_grade_level"
        ]
        for field in proficiency_fields:
            if field in self.fields:
                self.fields[field].widget.attrs.setdefault("min", 0)
                # Make fields flexible (allow blank during draft)
                self.fields[field].required = False

        proficiency_hints = {
            "emerging_not_proficient": "Learners below 25% proficiency - Not Proficient",
            "emerging_low_proficient": "Learners 25%-49% proficiency - Low Proficient",
            "developing_nearly_proficient": "Learners 50%-74% proficiency - Nearly Proficient",
            "transitioning_proficient": "Learners 75%-84% proficiency - Proficient",
            "at_grade_level": "Learners above 85% proficiency - At Grade Level",
        }
        for field, hint in proficiency_hints.items():
            if field in self.fields:
                self.fields[field].widget.attrs.setdefault("title", hint)

    def clean(self):
        cleaned = super().clean()
        enrolment = cleaned.get("enrolment") or 0
        total = sum([
            cleaned.get("emerging_not_proficient") or 0,
            cleaned.get("emerging_low_proficient") or 0,
            cleaned.get("developing_nearly_proficient") or 0,
            cleaned.get("transitioning_proficient") or 0,
            cleaned.get("at_grade_level") or 0,
        ])
        # Only enforce constraint when enrolment is provided (> 0). Allow partial drafts.
        if enrolment and total > enrolment:
            grade_value = None
            display_getter = getattr(self.instance, "get_grade_label_display", None)
            if callable(display_getter):
                grade_value = display_getter()
            if not grade_value:
                grade_value = getattr(self.instance, "grade_label", None) or cleaned.get("grade_label") or "this grade"
            raise ValidationError(f"RMA proficiency totals for {grade_value} cannot exceed enrolment.")
        return cleaned


class Form1RMAInterventionForm(forms.ModelForm):

    class Meta:

        model = Form1RMAIntervention

        fields = ["order", "description"]

        widgets = {

            "description": forms.Textarea(attrs={"rows": 2}),

        }



    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["order"].disabled = True

        self.fields["order"].widget = forms.HiddenInput()
        # Make description optional to allow flexible saving
        if "description" in self.fields:
            self.fields["description"].required = False





class Form1SupervisionRowForm(forms.ModelForm):


    class Meta:
        model = Form1SupervisionRow
        fields = [
            "grade_label",
            "total_teachers",
            "teachers_supervised_observed_ta",
            "intervention_support_provided",
            "result",
        ]
        widgets = {
            "grade_label": forms.TextInput(),
            "total_teachers": forms.NumberInput(attrs={"min": 0, "placeholder": "Total teachers"}),
            "teachers_supervised_observed_ta": forms.NumberInput(attrs={"min": 0, "placeholder": "Supervised/Observed/TA"}),
            "intervention_support_provided": forms.Textarea(attrs={"rows": 2}),
            "result": forms.Textarea(attrs={"rows": 2}),
        }




    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["grade_label"].widget.attrs.setdefault("placeholder", "Grade / Teacher")
        self.fields["total_teachers"].widget.attrs.setdefault("min", 0)
        self.fields["total_teachers"].widget.attrs.setdefault("title", "Total number of teachers in this grade/area.")
        self.fields["teachers_supervised_observed_ta"].widget.attrs.setdefault("min", 0)
        self.fields["teachers_supervised_observed_ta"].widget.attrs.setdefault("title", "Number of teachers supervised, observed, or given TA.")
        self.fields["intervention_support_provided"].widget.attrs.setdefault("placeholder", "Coaching or support provided")
        self.fields["result"].widget.attrs.setdefault("placeholder", "Resulting change or next steps")




    def clean(self):
        cleaned_data = super().clean()
        total_teachers = cleaned_data.get("total_teachers")
        supervised = cleaned_data.get("teachers_supervised_observed_ta")
        if total_teachers is not None and supervised is not None:
            if supervised > total_teachers:
                self.add_error("teachers_supervised_observed_ta", "Cannot exceed total number of teachers.")
        return cleaned_data





class Form1ADMHeaderForm(forms.ModelForm):
    """Form for ADM header to indicate if school offers ADM"""
    
    class Meta:
        model = Form1ADMHeader
        fields = ["is_offered"]
        widgets = {
            "is_offered": forms.CheckboxInput(attrs={
                "class": "adm-offered-checkbox",
                "onchange": "toggleADMFields(this.checked)"
            })
        }
        labels = {
            "is_offered": "Our school implements ADM (Alternative Delivery Mode) programs"
        }
        help_texts = {
            "is_offered": "Uncheck this if your school does not implement ADM"
        }


class Form1ADMRowForm(forms.ModelForm):

    class Meta:

        model = Form1ADMRow

        fields = [

            "ppas_conducted",

            "ppas_physical_target",

            "ppas_physical_actual",

            "ppas_physical_percent",

            "funds_downloaded",

            "funds_obligated",

            "funds_unobligated",

            "funds_percent_obligated",

            "funds_percent_burn_rate",

            "q1_response",

            "q2_response",

            "q3_response",

            "q4_response",

            "q5_response",

        ]

        widgets = {

            "ppas_conducted": forms.Textarea(attrs={"rows": 2, "class": "adm-field"}),

            "ppas_physical_percent": forms.NumberInput(attrs={"min": 0, "max": 100, "step": "0.01", "class": "adm-field"}),

            "funds_downloaded": forms.NumberInput(attrs={"min": 0, "step": "0.01", "class": "adm-field"}),

            "funds_obligated": forms.NumberInput(attrs={"min": 0, "step": "0.01", "class": "adm-field"}),

            "funds_unobligated": forms.NumberInput(attrs={"min": 0, "step": "0.01", "class": "adm-field"}),

            "funds_percent_obligated": forms.NumberInput(attrs={"min": 0, "max": 100, "step": "0.01", "class": "adm-field"}),

            "funds_percent_burn_rate": forms.NumberInput(attrs={"min": 0, "max": 100, "step": "0.01", "class": "adm-field"}),

            "q1_response": forms.Textarea(attrs={"rows": 3, "class": "adm-field"}),

            "q2_response": forms.Textarea(attrs={"rows": 3, "class": "adm-field"}),

            "q3_response": forms.Textarea(attrs={"rows": 3, "class": "adm-field"}),

            "q4_response": forms.Textarea(attrs={"rows": 3, "class": "adm-field"}),

            "q5_response": forms.Textarea(attrs={"rows": 3, "class": "adm-field"}),

        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add class to all number input fields for targeting
        for field_name in ["ppas_physical_target", "ppas_physical_actual"]:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs["class"] = "adm-field"
        numeric_fields = [
            "ppas_physical_target",
            "ppas_physical_actual",
            "ppas_physical_percent",
            "funds_downloaded",
            "funds_obligated",
            "funds_unobligated",
            "funds_percent_obligated",
            "funds_percent_burn_rate",
        ]
        for field_name in numeric_fields:
            if field_name in self.fields:
                self.fields[field_name].required = False



    def clean(self):

        cleaned = super().clean()
        integer_fields = ["ppas_physical_target", "ppas_physical_actual"]
        decimal_fields = [
            "ppas_physical_percent",
            "funds_downloaded",
            "funds_obligated",
            "funds_unobligated",
            "funds_percent_obligated",
            "funds_percent_burn_rate",
        ]
        for field in integer_fields:
            if cleaned.get(field) in (None, ""):
                cleaned[field] = 0
        for field in decimal_fields:
            if cleaned.get(field) in (None, ""):
                cleaned[field] = Decimal("0")

        percent_fields = [

            ("ppas_physical_percent", "Physical %"),

            ("funds_percent_obligated", "% obligated"),

            ("funds_percent_burn_rate", "Burn rate %"),

        ]

        for field, label in percent_fields:
            value = cleaned.get(field)

            if value < 0 or value > 100:

                self.add_error(field, f"{label} must be between 0 and 100.")

        non_negative_fields = [

            "ppas_physical_target",

            "ppas_physical_actual",

            "funds_downloaded",

            "funds_obligated",

            "funds_unobligated",

        ]

        for field in non_negative_fields:
            value = cleaned.get(field)

            if value < 0:

                self.add_error(field, "Value cannot be negative.")

        target = cleaned.get("ppas_physical_target")

        actual = cleaned.get("ppas_physical_actual")

        if target is not None and actual is not None and actual > target:

            self.add_error("ppas_physical_actual", "Physical actual cannot exceed the target.")

        downloaded = cleaned.get("funds_downloaded")

        obligated = cleaned.get("funds_obligated")

        unobligated = cleaned.get("funds_unobligated")

        if downloaded is not None and obligated is not None and obligated > downloaded:

            self.add_error("funds_obligated", "Funds obligated cannot exceed funds downloaded.")

        if downloaded is not None and unobligated is not None and unobligated > downloaded:

            self.add_error("funds_unobligated", "Funds unobligated cannot exceed funds downloaded.")

        return cleaned





class Form1SignatoriesForm(forms.ModelForm):

    class Meta:

        model = Form1Signatories

        fields = ["prepared_by", "submitted_to"]

        widgets = {

            "prepared_by": forms.TextInput(attrs={"placeholder": "Name / Position"}),

            "submitted_to": forms.TextInput(attrs={"placeholder": "Name / Position"}),

        }





class SubmissionActionForm(forms.Form):

    ACTION_SAVE = "save"

    ACTION_SUBMIT = "submit"

    ACTION_CHOICES = (

        (ACTION_SAVE, "Save Draft"),

        (ACTION_SUBMIT, "Submit"),

    )



    action = forms.ChoiceField(choices=ACTION_CHOICES)



    def clean_action(self):

        return self.cleaned_data["action"]


class FormTemplateCreateForm(forms.ModelForm):

    # Add period selection fields
    school_year = forms.ChoiceField(
        required=False,
        help_text="Select school year for this form (optional)"
    )
    
    quarter = forms.ChoiceField(
        required=False,
        choices=[('', 'All Quarters')] + [(q, q) for q in ['Q1', 'Q2', 'Q3', 'Q4']],
        help_text="Select quarter for filtering (optional)"
    )
    reading_timing_override = forms.ChoiceField(
        required=False,
        choices=[('', 'Auto (Quarter Mapping)'), ('bosy', 'BOSY'), ('mosy', 'MOSY'), ('eosy', 'EOSY')],
        label="Reading Timing Override",
        help_text="Override automatic Q→Reading period mapping for the Reading tab."
    )

    # SMEA Form 1 quick setup
    use_smea_form1 = forms.BooleanField(
        required=False,
        label="Use SMEA Form 1 (fixed title)",
        help_text="When checked, the title is fixed to 'SMEA Form 1' and the form code can be auto-generated."
    )

    ENABLED_TABS_CHOICES = (
        ("projects", "Projects & Activities"),
        ("pct", "% Implementation"),
        ("slp", "SLP"),
        ("reading", "III. Reading (CRLA/PHILIRI)"),
        ("rma", "RMA"),
        ("supervision", "Instructional Supervision & TA"),
        ("adm", "ADM One-Stop-Shop & EiE"),
    )
    enabled_tabs = forms.MultipleChoiceField(
        required=False,
        choices=ENABLED_TABS_CHOICES,
        initial=[c[0] for c in ENABLED_TABS_CHOICES],
        widget=forms.CheckboxSelectMultiple,
        label="Tabs to include"
    )

    def __init__(self, *args, section_queryset=None, **kwargs):

        self.section_queryset = section_queryset

        super().__init__(*args, **kwargs)

        # If SMEA fixed mode is selected in POST, relax title/code requirements
        try:
            use_smea_flag = False
            if hasattr(self, 'data') and self.data:
                val = self.data.get('use_smea_form1')
                use_smea_flag = str(val).lower() in {"1", "true", "on", "yes"} or bool(val)
            if use_smea_flag:
                if 'title' in self.fields:
                    self.fields['title'].required = False
                if 'code' in self.fields:
                    self.fields['code'].required = False
                    # Hint for auto-generation
                    self.fields['code'].help_text = (self.fields['code'].help_text or '') + \
                        (" Leave blank to auto-generate (SMEA Form 1)." if (self.fields['code'].help_text or '') == '' else "")
        except Exception:
            pass

        if section_queryset is not None:

            self.fields["section"].queryset = section_queryset

        date_attrs = {"type": "date"}

        self.fields["open_at"].widget = forms.DateInput(attrs=date_attrs)

        self.fields["close_at"].widget = forms.DateInput(attrs=date_attrs)
        
        # Populate school year choices from Period model
        from .models import Period
        years = Period.objects.values_list('school_year_start', flat=True).distinct().order_by('-school_year_start')
        year_choices = [('', 'Not specified')] + [(str(y), f'SY {y}-{y+1}') for y in years]
        self.fields['school_year'].choices = year_choices

    class Meta:

        model = FormTemplate

        fields = [

            "section",

            "code",

            "title",

            "period_type",

            "open_at",

            "close_at",

            "is_active",

            "reading_timing_override",
        ]

    def clean_section(self):

        section = self.cleaned_data.get("section")

        if section and self.section_queryset is not None:

            if not self.section_queryset.filter(pk=section.pk).exists():

                raise ValidationError("You cannot manage this section.")

        return section

    def clean(self):

        cleaned = super().clean()

        # If SMEA fixed mode, enforce title programmatically and allow blank code
        try:
            use_smea = cleaned.get('use_smea_form1')
            if use_smea is None and hasattr(self, 'data'):
                val = self.data.get('use_smea_form1')
                use_smea = str(val).lower() in {"1", "true", "on", "yes"} or bool(val)
            if use_smea:
                cleaned['title'] = "SMEA Form 1"
        except Exception:
            pass

        open_at = cleaned.get("open_at")

        close_at = cleaned.get("close_at")

        if open_at and close_at and close_at < open_at:

            raise ValidationError("Close date cannot be earlier than open date.")

        return cleaned
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Save school_year and quarter_filter from the form fields
        school_year = self.cleaned_data.get('school_year')
        quarter = self.cleaned_data.get('quarter')
        use_smea_form1 = self.cleaned_data.get('use_smea_form1')
        enabled_tabs = self.cleaned_data.get('enabled_tabs') or []
        
        if school_year:
            instance.school_year = int(school_year)
        if quarter:
            instance.quarter_filter = quarter
        # Persist override (blank becomes '')
        rto = (self.cleaned_data.get('reading_timing_override') or '').lower()
        if rto in {'bosy', 'mosy', 'eosy'}:
            instance.reading_timing_override = rto
        else:
            instance.reading_timing_override = ''

        # When SMEA Form 1 mode is selected, fix the title and optionally auto-generate code
        if use_smea_form1:
            instance.title = "SMEA Form 1"
            # Auto-generate code if empty or clearly default/placeholder
            base_parts = ["smea1"]
            try:
                section_code = (instance.section.code or "").lower()
                if section_code:
                    base_parts.append(section_code)
            except Exception:
                pass
            if instance.school_year:
                base_parts.append(f"sy{instance.school_year}")
            if instance.quarter_filter:
                base_parts.append(instance.quarter_filter.lower())
            base_code = slugify("-".join(base_parts)) or "smea1"

            # Generate unique code when not explicitly provided
            if not (instance.code and instance.code.strip()):
                from .models import FormTemplate
                candidate = base_code
                suffix = 2
                while FormTemplate.objects.filter(code__iexact=candidate).exists():
                    candidate = f"{base_code}-{suffix}"
                    suffix += 1
                instance.code = candidate

            # Persist configuration to schema_descriptor
            schema = dict(instance.schema_descriptor or {})
            schema["form_type"] = "smea_form_1"
            schema["enabled_tabs"] = enabled_tabs
            if instance.school_year:
                schema["school_year"] = instance.school_year
            if instance.quarter_filter:
                schema["quarter"] = instance.quarter_filter
            instance.schema_descriptor = schema
        
        if commit:
            instance.save()
        return instance


class FormTemplateScheduleForm(forms.ModelForm):

    class Meta:

        model = FormTemplate

        fields = [

            "open_at",

            "close_at",

            "is_active",

        ]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        date_attrs = {"type": "date"}

        self.fields["open_at"].widget = forms.DateInput(attrs=date_attrs)

        self.fields["close_at"].widget = forms.DateInput(attrs=date_attrs)

    def clean(self):

        cleaned = super().clean()

        open_at = cleaned.get("open_at")

        close_at = cleaned.get("close_at")

        if open_at and close_at and close_at < open_at:

            raise ValidationError("Close date cannot be earlier than open date.")

        return cleaned





Form1PctRowFormSet = modelformset_factory(

    Form1PctRow,

    form=Form1PctRowForm,

    extra=0,

    can_delete=False,

)



Form1SLPRowFormSet = modelformset_factory(

    Form1SLPRow,

    form=Form1SLPRowForm,

    extra=0,

    can_delete=False,

)



Form1SLPTopDNMEFormSet = modelformset_factory(

    Form1SLPTopDNME,

    form=Form1SLPTopDNMEForm,

    extra=0,

    can_delete=False,

)



Form1SLPTopOutstandingFormSet = modelformset_factory(

    Form1SLPTopOutstanding,

    form=Form1SLPTopOutstandingForm,

    extra=0,

    can_delete=False,

)



Form1ReadingCRLAFormSet = modelformset_factory(

    Form1ReadingCRLA,

    form=Form1ReadingCRLAForm,

    extra=1,

    can_delete=True,

)



Form1ReadingPHILIRIFormSet = modelformset_factory(

    Form1ReadingPHILIRI,

    form=Form1ReadingPHILIRIForm,

    extra=1,

    can_delete=True,

)



Form1ReadingInterventionFormSet = modelformset_factory(

    Form1ReadingIntervention,

    form=Form1ReadingInterventionForm,

    extra=0,

    can_delete=False,

    max_num=5,

)



Form1RMARowFormSet = modelformset_factory(

    Form1RMARow,

    form=Form1RMARowForm,

    extra=0,

    can_delete=False,

)



Form1RMAInterventionFormSet = modelformset_factory(

    Form1RMAIntervention,

    form=Form1RMAInterventionForm,

    extra=0,

    can_delete=False,

    max_num=5,

)



Form1SupervisionRowFormSet = modelformset_factory(
    Form1SupervisionRow,
    form=Form1SupervisionRowForm,
    extra=3,
    can_delete=True,
    max_num=3,
)



Form1ADMRowFormSet = modelformset_factory(
    Form1ADMRow,
    form=Form1ADMRowForm,
    extra=3,
    can_delete=True,
    max_num=20,
)


# New Reading Assessment Forms (Matrix-Based 2025-26)
class ReadingAssessmentCRLAForm(forms.ModelForm):
    """
    Form for CRLA Assessment - Matrix layout with all grades/subjects for one period/level
    """
    class Meta:
        model = ReadingAssessmentCRLA
        fields = [
            'period', 'level',
            'mt_grade_1', 'mt_grade_2', 'mt_grade_3',
            'fil_grade_2', 'fil_grade_3',
            'eng_grade_3'
        ]
        widgets = {
            'period': forms.HiddenInput(),
            'level': forms.HiddenInput(),
            'mt_grade_1': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'mt_grade_2': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'mt_grade_3': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'fil_grade_2': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'fil_grade_3': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'eng_grade_3': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in {'period', 'level'}:
                continue
            field.required = False

    def clean(self):
        cleaned = super().clean()
        for name in list(self.fields.keys()):
            if name in {'period', 'level'}:
                continue
            cleaned[name] = cleaned.get(name) or 0
        return cleaned


class ReadingAssessmentPHILIRIForm(forms.ModelForm):
    """
    Form for PHILIRI Assessment - Separate fields for each individual grade level
    """
    class Meta:
        model = ReadingAssessmentPHILIRI
        fields = [
            'period', 'level',
            'eng_grade_4', 'eng_grade_5', 'eng_grade_6', 'eng_grade_7', 'eng_grade_8', 'eng_grade_9', 'eng_grade_10',
            'fil_grade_4', 'fil_grade_5', 'fil_grade_6', 'fil_grade_7', 'fil_grade_8', 'fil_grade_9', 'fil_grade_10'
        ]
        widgets = {
            'period': forms.HiddenInput(),
            'level': forms.HiddenInput(),
            'eng_grade_4': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'eng_grade_5': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'eng_grade_6': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'eng_grade_7': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'eng_grade_8': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'eng_grade_9': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'eng_grade_10': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'fil_grade_4': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'fil_grade_5': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'fil_grade_6': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'fil_grade_7': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'fil_grade_8': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'fil_grade_9': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'fil_grade_10': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in {'period', 'level'}:
                continue
            field.required = False

    def clean(self):
        cleaned = super().clean()
        for name in list(self.fields.keys()):
            if name in {'period', 'level'}:
                continue
            cleaned[name] = cleaned.get(name) or 0
        return cleaned


class ReadingInterventionNewForm(forms.ModelForm):
    """
    Form for Reading Interventions - Maximum 5 interventions
    """
    class Meta:
        model = ReadingInterventionNew
        fields = ['order', 'description']
        widgets = {
            'order': forms.HiddenInput(),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-input', 'placeholder': 'Describe the intervention strategy...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make description optional (flexible: allow blank entries)
        if 'description' in self.fields:
            self.fields['description'].required = False

    def clean(self):
        cleaned = super().clean()
        # Normalize empty descriptions to empty string
        desc = cleaned.get('description')
        if not desc:
            cleaned['description'] = ''
        return cleaned


# Formset Factories for New Reading Assessments
ReadingAssessmentCRLAFormSet = modelformset_factory(
    ReadingAssessmentCRLA,
    form=ReadingAssessmentCRLAForm,
    extra=0,
    can_delete=False,
)

ReadingAssessmentPHILIRIFormSet = modelformset_factory(
    ReadingAssessmentPHILIRI,
    form=ReadingAssessmentPHILIRIForm,
    extra=0,
    can_delete=False,
)

ReadingInterventionNewFormSet = modelformset_factory(
    ReadingInterventionNew,
    form=ReadingInterventionNewForm,
    extra=0,
    can_delete=False,
)

# Projects & Activities Formsets

# Use the custom formset base class to allow deletion of invalid forms
SMEAProjectFormSet = inlineformset_factory(
    Submission,
    SMEAProject,
    form=SMEAProjectForm,
    extra=0,
    can_delete=True,
    fields=['project_title', 'area_of_concern', 'conference_date'],
    formset=DeletionFriendlyBaseInlineFormSet,
)

SMEAActivityRowFormSet = inlineformset_factory(
    SMEAProject,
    SMEAActivityRow,
    form=SMEAActivityRowForm,
    extra=0,
    can_delete=True,
    fields=['activity', 'output_target', 'output_actual', 'timeframe_target', 'timeframe_actual',
            'budget_target', 'budget_actual', 'interpretation', 'issues_unaddressed',
            'facilitating_factors', 'agreements'],
    formset=DeletionFriendlyBaseInlineFormSet,
)














