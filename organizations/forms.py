from __future__ import annotations

import json

from django import forms
from django.contrib.auth import get_user_model

from .models import District, School, SchoolProfile, Section
from submissions import constants as smea_constants


class SchoolProfileForm(forms.ModelForm):
    # Structured SHS strand selection (checkboxes)
    shs_strands = forms.MultipleChoiceField(
        required=False,
        choices=[(label, label) for (_code, label, _prefix) in smea_constants.SHS_STRANDS],
        widget=forms.CheckboxSelectMultiple,
        label="SHS Strands Offered",
        help_text="Check the SHS strands your school offers. This pre-configures SLP specialized subjects."
    )
    # Free-form for other programs (SPED, ALS, etc.) or custom notes
    strands = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))

    class Meta:
        model = SchoolProfile
        fields = [
            "head_name",
            "head_contact",
            "grade_span_start",
            "grade_span_end",
            "strands",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = getattr(self, "instance", None)
        if instance and getattr(instance, "strands", None) and not self.data:
            # Pre-populate SHS checkboxes for known strands
            known_labels = {label for (_c, label, _p) in smea_constants.SHS_STRANDS}
            selected_shs = [s for s in (instance.strands or []) if isinstance(s, str) and s in known_labels]
            self.fields["shs_strands"].initial = selected_shs
            # Pre-populate free-form textarea with any remaining items
            others = [s for s in (instance.strands or []) if isinstance(s, str) and s not in known_labels]
            if others:
                self.fields["strands"].initial = ", ".join(others)

    def clean_strands(self):
        value = self.cleaned_data.get("strands")
        if isinstance(value, list):
            return value
        if not value:
            return []
        if isinstance(value, str):
            stripped = value.strip()
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return []

    def clean(self):
        cleaned = super().clean()
        # Combine structured SHS selections with any free-form entries
        shs = cleaned.get("shs_strands") or []
        others = cleaned.get("strands") or []
        combined = []
        seen = set()
        for s in list(shs) + list(others):
            if isinstance(s, str):
                s2 = s.strip()
                if s2 and s2 not in seen:
                    combined.append(s2)
                    seen.add(s2)
        cleaned["strands"] = combined
        return cleaned


class SchoolForm(forms.ModelForm):
    district = forms.ModelChoiceField(
        queryset=District.objects.order_by("name"), 
        required=False,
        widget=forms.Select(attrs={'class': 'form-input'})
    )
    
    # Optional fields for creating a school head user
    create_user = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        label="Create school head user account"
    )
    username = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-input', 
            'placeholder': 'e.g., school001_head'
        }),
        help_text="Username for the school head"
    )
    user_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Password for school head'
        }),
        label="Initial password"
    )
    user_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'email@example.com'
        }),
        label="Email (optional)"
    )
    
    # Role selection
    USER_ROLE_CHOICES = [
        ('school_head', 'School Head'),
        ('psds', 'PSDS (Provincial Supervisor)'),
        ('section_admin', 'Section Admin (SMME, PCT, SLP, etc.)'),
        ('sgod_admin', 'SGOD Admin (Full System Access)'),
    ]
    user_role = forms.ChoiceField(
        choices=USER_ROLE_CHOICES,
        initial='school_head',
        required=False,
        widget=forms.Select(attrs={'class': 'form-input'}),
        help_text="Role to assign to the user"
    )
    
    # For section admins - select multiple sections via checkboxes
    assigned_sections = forms.ModelMultipleChoiceField(
        queryset=Section.objects.all().order_by('code'),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Assign to Sections",
        help_text="For Section Admins: select which sections they can manage"
    )
    
    # For PSDS - district assignment
    psds_district = forms.ModelChoiceField(
        queryset=District.objects.order_by("name"),
        required=False,
        widget=forms.Select(attrs={'class': 'form-input'}),
        label="PSDS District",
        help_text="For PSDS: assign to district"
    )

    class Meta:
        model = School
        fields = [
            "code",
            "name",
            "division",
            "district",
            "school_type",
            "min_grade",
            "max_grade",
            "implements_adm",
        ]
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g., SCHOOL001'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g., Sample Elementary School'}),
            'division': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g., Division I'}),
            'school_type': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g., Elementary'}),
            'min_grade': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '1', 'min': '0', 'max': '12'}),
            'max_grade': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '6', 'min': '0', 'max': '12'}),
            'implements_adm': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        create_user = cleaned_data.get('create_user')
        username = cleaned_data.get('username')
        user_password = cleaned_data.get('user_password')
        user_role = cleaned_data.get('user_role')
        assigned_sections = cleaned_data.get('assigned_sections', [])
        psds_district = cleaned_data.get('psds_district')
        
        if create_user:
            if not username:
                self.add_error('username', 'Username is required when creating a user')
            if not user_password:
                self.add_error('user_password', 'Password is required when creating a user')
            
            # Validate sections for section admins
            if user_role == 'section_admin' and not assigned_sections:
                self.add_error('assigned_sections', 'Section Admins must be assigned to at least one section')
            
            # Validate district for PSDS
            if user_role == 'psds' and not psds_district:
                self.add_error('psds_district', 'District is required for PSDS role')
        
        return cleaned_data


User = get_user_model()


class UserPasswordResetForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Enter username'})
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Enter new password'})
    )

    def save(self):
        username = self.cleaned_data["username"]
        new_password = self.cleaned_data["new_password"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise forms.ValidationError("User not found.")
        user.set_password(new_password)
        user.save(update_fields=["password"])
        return user
