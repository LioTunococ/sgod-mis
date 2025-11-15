# ACTION PLAN

## Current Focus: Multi-Unit School Dashboard Implementation ✅

**Status**: Week 1 Complete - Ready for Testing  
**Date**: October 17, 2025

### Just Completed
- ✅ Implemented tabbed interface for all 6 government units (SMME, YFS, HRD, DRRM, SMN, PR)
- ✅ Added per-section quarter statistics (Q1, Q2, Q3, Q4)
- ✅ Implemented tab switching without page reload
- ✅ Added school year filtering (global across all tabs)
- ✅ Created custom template filter for dictionary access
- ✅ Updated view logic to support multi-section filtering
- ✅ Maintained backwards compatibility with existing data

### Testing Required
- [ ] Test all 6 section tabs render correctly
- [ ] Verify tab switching works smoothly
- [ ] Validate quarter filtering per section
- [ ] Test school year dropdown updates all sections
- [ ] Check "In Progress" and "Available Forms" display
- [ ] Test with real school accounts (Flora NHS, Luna NHS, Pudtol VHS)
- [ ] Verify empty states show correctly
- [ ] Test on mobile/tablet devices

**Testing URL**: http://127.0.0.1:8000/ (log in as school user)

---

## Previous Work

## URGENT: Fix School Portal Design

### Problem
School portal template (`templates/dashboards/school_home.html`) was accidentally broken during cleanup. The original design used `app.css` with `.portal-layout` and `.portal-sidebar` classes, but these were replaced with classes that don't fully exist in `form-system.css`.

### Solution Options

**Option 1: Restore Original Design** (RECOMMENDED)
- Use `app.css` instead of `form-system.css`
- Restore `.portal-layout` and `.portal-sidebar` structure
- This was the working design that matched the rest of the system

**Option 2: Complete Form-System Migration**
- Finish implementing all missing CSS classes in `form-system.css`
- Add `.portal-layout`, `.portal-sidebar`, etc.
- More work but cleaner long-term

### Files to Fix
- `templates/dashboards/school_home.html` - Restore original structure
- OR `static/css/form-system.css` - Add missing portal classes from app.css

---

## Directory Tools Enhancement: Create Users with Roles

### Current State
Directory tools can only create schools with basic school_head users.

### Goal
Allow creating users with different roles:
- **School Head** - Access to school portal
- **PSDS** - Access to SMME KPI dashboard  
- **Section Admin** (SMME, etc.) - Access to review queues for specific sections
- **SGOD Admin** - Full system access to division overview

### Implementation Plan

#### 1. Update `organizations/forms.py` - SchoolForm

```python
from accounts.models import UserProfile

class SchoolForm(forms.ModelForm):
    # Existing fields
    create_user = forms.BooleanField(...)
    username = forms.CharField(...)
    user_password = forms.CharField(...)
    user_email = forms.EmailField(...)
    
    # NEW: Role selection
    USER_ROLE_CHOICES = [
        ('school_head', 'School Head'),
        ('psds', 'PSDS (Provincial Supervisor)'),
        ('section_admin', 'Section Admin'),
        ('sgod_admin', 'SGOD Admin'),
    ]
    user_role = forms.ChoiceField(
        choices=USER_ROLE_CHOICES,
        initial='school_head',
        required=False,
        help_text="Role to assign to the user"
    )
    
    # NEW: For section admins
    section_codes = forms.CharField(
        required=False,
        help_text="For Section Admins: comma-separated section codes (e.g., SMME, PCT, SLP)"
    )
    
    # NEW: For PSDS
    district = forms.ModelChoiceField(
        queryset=District.objects.all(),
        required=False,
        help_text="For PSDS: assign to district"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        create_user = cleaned_data.get('create_user')
        user_role = cleaned_data.get('user_role')
        section_codes = cleaned_data.get('section_codes')
        
        if create_user:
            if not cleaned_data.get('username'):
                raise forms.ValidationError("Username required if creating user")
            if not cleaned_data.get('user_password'):
                raise forms.ValidationError("Password required if creating user")
                
            # Validate section codes for section admins
            if user_role == 'section_admin' and not section_codes:
                raise forms.ValidationError("Section codes required for Section Admin role")
                
        return cleaned_data
```

#### 2. Update `organizations/views.py` - manage_directory()

```python
from accounts.models import UserProfile

def manage_directory(request):
    # ... existing code ...
    
    if school_form.is_valid():
        school = school_form.save()
        # ... create SchoolProfile ...
        
        if school_form.cleaned_data.get('create_user'):
            username = school_form.cleaned_data['username']
            password = school_form.cleaned_data['user_password']
            email = school_form.cleaned_data.get('user_email', '')
            user_role = school_form.cleaned_data.get('user_role', 'school_head')
            section_codes_str = school_form.cleaned_data.get('section_codes', '')
            district = school_form.cleaned_data.get('district')
            
            # Create user
            user = get_user_model().objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            # Create UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=user)
            
            # Assign role-specific permissions
            if user_role == 'school_head':
                # Set school assignment
                profile.school = school
                profile.save()
                
                # Create SchoolUserRole
                SchoolUserRole.objects.create(
                    user=user,
                    school=school,
                    role='school_head',
                    is_primary=True
                )
                
            elif user_role == 'psds':
                # PSDS gets district assignment
                profile.psds_district = district
                profile.save()
                
            elif user_role == 'section_admin':
                # Section admin gets section codes
                codes = [c.strip().upper() for c in section_codes_str.split(',')]
                profile.section_admin_codes = codes
                profile.save()
                
            elif user_role == 'sgod_admin':
                # SGOD admin gets superuser status
                user.is_staff = True
                user.is_superuser = True
                user.save()
            
            messages.success(request, f"School '{school.name}' created with user '{username}' ({user_role})")
```

#### 3. Update `templates/organizations/manage_directory.html`

```html
<!-- In the user creation section -->
<div class="user-creation-section">
  <h3>Create User Account</h3>
  
  <label>
    <input type="checkbox" name="create_user" checked>
    Create user for this school
  </label>
  
  <div id="user-fields">
    {{ form.username.label_tag }}
    {{ form.username }}
    
    {{ form.user_password.label_tag }}
    {{ form.user_password }}
    
    {{ form.user_email.label_tag }}
    {{ form.user_email }}
    
    <!-- NEW: Role selection -->
    <div class="form-field">
      {{ form.user_role.label_tag }}
      {{ form.user_role }}
      <span class="help-text">{{ form.user_role.help_text }}</span>
    </div>
    
    <!-- NEW: Section codes (show only for section_admin) -->
    <div class="form-field" id="section-codes-field" style="display: none;">
      {{ form.section_codes.label_tag }}
      {{ form.section_codes }}
      <span class="help-text">{{ form.section_codes.help_text }}</span>
    </div>
    
    <!-- NEW: District (show only for PSDS) -->
    <div class="form-field" id="district-field" style="display: none;">
      {{ form.district.label_tag }}
      {{ form.district }}
      <span class="help-text">{{ form.district.help_text }}</span>
    </div>
  </div>
</div>

<script>
// Show/hide fields based on role selection
document.querySelector('[name="user_role"]').addEventListener('change', function() {
  const role = this.value;
  document.getElementById('section-codes-field').style.display = 
    role === 'section_admin' ? 'block' : 'none';
  document.getElementById('district-field').style.display = 
    role === 'psds' ? 'block' : 'none';
});
</script>
```

#### 4. Documentation

Create `docs/USER_ROLES_GUIDE.md` explaining:
- What each role can do
- How to create users with each role
- Examples of common setups

---

## Priority Order

1. **URGENT**: Fix school portal design (Option 1: restore app.css)
2. **HIGH**: Implement role selection in directory tools
3. **MEDIUM**: Test all role types work correctly
4. **LOW**: Documentation and cleanup

---

## Testing Checklist

### School Portal Design
- [ ] School portal loads without errors
- [ ] Stats cards display correctly
- [ ] Quarter navigation works
- [ ] Section cards show properly
- [ ] Matches design of other dashboards

### User Roles in Directory
- [ ] Can create school_head user
- [ ] Can create PSDS user with district
- [ ] Can create section_admin user with codes
- [ ] Can create SGOD admin user
- [ ] Each role redirects to correct dashboard
- [ ] Permissions work correctly

---

## Files to Modify

### For School Portal Fix
- `templates/dashboards/school_home.html`
- `static/css/form-system.css` (if adding portal classes)

### For User Roles Feature
- `organizations/forms.py`
- `organizations/views.py`  
- `templates/organizations/manage_directory.html`
- `docs/USER_ROLES_GUIDE.md` (new)

---

## Notes

- The original school portal design used `.portal-layout` from `app.css`
- Current template uses classes that don't fully exist in `form-system.css`
- User creation currently only supports school_head role
- Need to handle all 4 role types: school_head, psds, section_admin, sgod_admin
