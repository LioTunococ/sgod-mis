# Directory Tools - Section Assignment Fix Plan

**Date**: October 17, 2025  
**Status**: URGENT - Multi-unit dashboard broken due to missing sections  
**DO NOT DEVIATE FROM THIS PLAN**

---

## PROBLEM SUMMARY

1. **No sections in database** → School portal shows empty (no tabs)
2. **Section assignment broken** → Can't assign section admins to specific sections
3. **Text input error-prone** → Typing "SMME, PCT" causes errors

---

## ROOT CAUSES

### Issue 1: Empty Sections Table
```python
Section.objects.all().count()  # Returns: 0 ❌
```
**Impact**: Multi-unit dashboard has no tabs to show

### Issue 2: Manual Section Input
Current form has text field where users type "SMME, PCT" - prone to typos and errors.

### Issue 3: No Visual Section Selector
Users can't see which sections exist in the system.

---

## SOLUTION (5 STEPS - 45 MINUTES)

### STEP 1: Load Sections Data (5 min) ✅ DO THIS FIRST

**Action**:
```bash
python manage.py loaddata data/sections.seed.json
```

**Verify**:
```python
python manage.py shell -c "from organizations.models import Section; print('Sections:', Section.objects.count())"
# Should print: Sections: 6
```

**Result**: School portal will show 6 tabs (SMME, YFS, HRD, DRRM, SMN, PR)

---

### STEP 2: Update Form - Add Section Checkboxes (10 min)

**File**: `organizations/forms.py`

**Remove**:
```python
section_codes = forms.CharField(...)  # ❌ DELETE THIS
```

**Add**:
```python
assigned_sections = forms.ModelMultipleChoiceField(
    queryset=Section.objects.all().order_by('code'),
    required=False,
    widget=forms.CheckboxSelectMultiple,
    label="Assign to Sections",
    help_text="For Section Admins - select which sections they manage"
)
```

**Update clean() method**:
```python
def clean(self):
    cleaned_data = super().clean()
    if cleaned_data.get('create_user'):
        user_role = cleaned_data.get('user_role')
        assigned_sections = cleaned_data.get('assigned_sections', [])
        
        if user_role == 'section_admin' and not assigned_sections:
            raise forms.ValidationError(
                "Section Admins must be assigned to at least one section."
            )
    return cleaned_data
```

---

### STEP 3: Update View - Save Sections (5 min)

**File**: `organizations/views.py` - `manage_directory()` function

**Replace**:
```python
elif user_role == 'section_admin':
    section_codes_str = school_form.cleaned_data.get('section_codes', '')
    codes = [c.strip().upper() for c in section_codes_str.split(',')]
    profile.section_admin_codes = codes
```

**With**:
```python
elif user_role == 'section_admin':
    assigned_sections = school_form.cleaned_data.get('assigned_sections', [])
    codes = [section.code.upper() for section in assigned_sections]
    profile.section_admin_codes = codes
    role_display = f"Section Admin ({', '.join(codes)})"
```

---

### STEP 4: Update Template - Show Checkboxes (15 min)

**File**: `templates/organizations/manage_directory.html`

**Replace the section codes field**:

Find this:
```html
<div id="section-codes-field" style="display: none;">
  <!-- old text input -->
</div>
```

Replace with:
```html
<div id="section-assignment-field" style="display: none;" class="form-group">
  <label class="form-label">Assign to Sections</label>
  <p class="muted" style="font-size: 0.875rem; margin-bottom: 0.5rem;">
    Select which sections this Section Admin can manage
  </p>
  <div style="display: flex; flex-direction: column; gap: 0.5rem; padding: 0.75rem; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 0.375rem;">
    {% for section in school_form.assigned_sections.field.queryset %}
      <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
        <input 
          type="checkbox" 
          name="assigned_sections" 
          value="{{ section.id }}"
          style="width: 1rem; height: 1rem;">
        <span style="font-weight: 500;">{{ section.code|upper }}</span>
        <span style="color: #6b7280; font-size: 0.875rem;">- {{ section.name }}</span>
      </label>
    {% endfor %}
  </div>
</div>
```

**Update JavaScript**:
```javascript
const sectionAssignmentField = document.getElementById('section-assignment-field');

function updateFieldsVisibility() {
  const role = roleSelect.value;
  sectionAssignmentField.style.display = role === 'section_admin' ? 'block' : 'none';
  psdsDistrictField.style.display = role === 'psds' ? 'block' : 'none';
}
```

---

### STEP 5: Test All Role Types (10 min)

#### Test 1: School Head
```
1. Create user, role = "School Head"
2. Login as that user
3. Expected: See ALL 6 tabs (SMME, YFS, HRD, DRRM, SMN, PR)
```

#### Test 2: Section Admin - SMME Only
```
1. Create user, role = "Section Admin"
2. Check ONLY "SMME" checkbox
3. Login as that user
4. Expected: See ONLY SMME tab
```

#### Test 3: Section Admin - Multiple Sections
```
1. Create user, role = "Section Admin"  
2. Check "SMME" and "HRD" checkboxes
3. Login as that user
4. Expected: See ONLY SMME and HRD tabs
```

---

## EXECUTION CHECKLIST

- [ ] **Step 1**: Load sections fixture
- [ ] **Step 2**: Update forms.py (add assigned_sections field)
- [ ] **Step 3**: Update views.py (save selected sections)
- [ ] **Step 4**: Update template (checkbox UI)
- [ ] **Step 5**: Test all role types

---

## SUCCESS CRITERIA

✅ 6 sections loaded in database  
✅ Checkbox selector for sections (not text)  
✅ School heads see ALL 6 tabs  
✅ Section admins see ONLY assigned tabs  
✅ No typos possible (checkboxes prevent errors)  

---

**START WITH STEP 1 NOW!**
  - Individual `.form-group` containers for each field
  - Explicit `.form-label` with required indicators (`<span class="required">*</span>`)
  - Inline error display (`<span class="form-error">`)
  - `.form-grid` layout for responsive 2-column form
  - Proper `.form-actions` container for buttons
  - Placeholder text for all inputs
  - Input validation feedback

#### Reset Password Form
- Applied same improvements as school form
- Compact 2-column layout with `.form-grid--compact`
- Clear error messaging
- Professional styling

#### Schools Table
- **Added Search Functionality**:
  - Search bar in table header
  - Filters by school name or code
  - "Clear" button when search is active
  - Shows search results count
- **Enhanced Display**:
  - Added ADM column (✓/No indicator)
  - Bold school names
  - Code fields in `<code>` tags
  - Shows "G1-G6" format for grades
  - "Showing X schools" counter
  - Better empty state messaging
- **Improved Data**:
  - Shows 50 most recent schools (was 25)
  - Ordered by newest first (by ID descending)
  - Search returns up to 50 results

#### Users Table
- **Enhanced Display**:
  - Added "Date Joined" column
  - Bold usernames
  - Staff status with visual indicator (✓ Staff / Regular)
  - Formatted dates (e.g., "Oct 17, 2025")
  - "Never" for users who haven't logged in
  - Shows count of displayed users
- **Improved Data**:
  - Ordered by newest first (`-date_joined`)
  - Shows 25 most recent users

### 2. **Form Enhancements** (`organizations/forms.py`)

#### SchoolForm
```python
# Added widget attributes to all fields:
widgets = {
    'code': TextInput(attrs={
        'class': 'form-input', 
        'placeholder': 'e.g., SCHOOL001'
    }),
    'name': TextInput(attrs={
        'class': 'form-input', 
        'placeholder': 'e.g., Sample Elementary School'
    }),
    'division': TextInput(attrs={
        'class': 'form-input', 
        'placeholder': 'e.g., Division I'
    }),
    'school_type': TextInput(attrs={
        'class': 'form-input', 
        'placeholder': 'e.g., Elementary'
    }),
    'min_grade': NumberInput(attrs={
        'class': 'form-input', 
        'placeholder': '1', 
        'min': '0', 
        'max': '12'
    }),
    'max_grade': NumberInput(attrs={
        'class': 'form-input', 
        'placeholder': '6', 
        'min': '0', 
        'max': '12'
    }),
    'implements_adm': CheckboxInput(attrs={
        'class': 'form-checkbox'
    }),
}
```

#### UserPasswordResetForm
```python
# Added widget attributes:
username = forms.CharField(
    widget=TextInput(attrs={
        'class': 'form-input', 
        'placeholder': 'Enter username'
    })
)
new_password = forms.CharField(
    widget=PasswordInput(attrs={
        'class': 'form-input', 
        'placeholder': 'Enter new password'
    })
)
```

### 3. **View Improvements** (`organizations/views.py`)

#### Enhanced Error Handling
```python
# Before: Generic messages
messages.success(request, f"Created school {school.name}.")
messages.error(request, "User not found.")

# After: Clear, actionable messages
messages.success(request, f"✓ Created school: {school.name} ({school.code})")
messages.error(request, "✗ User not found.")
messages.error(request, "Please fix the errors in the form.")
```

#### Added Search Functionality
```python
search_query = request.GET.get("search", "").strip()
if search_query:
    schools = School.objects.select_related("district").filter(
        Q(name__icontains=search_query) | Q(code__icontains=search_query)
    ).order_by("name")[:50]
else:
    schools = School.objects.select_related("district").order_by("-id")[:50]
```

#### Improved Data Queries
- Schools: Changed from `order_by("name")[:25]` to `order_by("-id")[:50]` (newest first, more results)
- Users: Changed from `order_by("username")[:25]` to `order_by("-date_joined")[:25]` (newest first)
- Added `search_query` to template context

## Visual Improvements

### Before
- Basic form rendering with `as_p`
- No placeholders or input hints
- Generic error messages
- Limited to 25 schools
- No search capability
- Basic table layout
- Inconsistent styling

### After
- Professional form layout with design system
- Helpful placeholders on all inputs
- Clear success/error messages with icons (✓/✗)
- Shows 50 schools with search
- Search by name or code
- Enhanced tables with visual indicators
- Consistent Boring Design System styling
- Better mobile responsiveness

## Usage

### Creating a School
1. Fill in required fields (Code, Name) - marked with red asterisk
2. Optional: Add division, district, school type, grades, ADM status
3. Click "Create School"
4. Success message appears: "✓ Created school: [Name] ([Code])"
5. New school appears in the table immediately

### Resetting a Password
1. Enter the username
2. Enter the new password
3. Click "Reset Password"
4. Success message: "✓ Password reset for: [username]"

### Searching Schools
1. Type school name or code in search box
2. Click "Search"
3. View filtered results (up to 50)
4. Click "Clear" to reset

## Technical Details

### CSS Classes Used
- `.form-grid` - Responsive 2-column form layout
- `.form-grid--compact` - Compact 2-column layout
- `.form-group` - Individual field container
- `.form-label` - Field labels
- `.form-input` - Text/number/select inputs
- `.form-checkbox` - Checkbox inputs
- `.form-error` - Inline error messages
- `.form-actions` - Button container
- `.required` - Required field indicator
- `.btn`, `.btn--primary`, `.btn--secondary`, `.btn--outline` - Buttons
- `.card`, `.card--wide` - Card containers
- `.table`, `.table-scroll` - Table layout

### Form Validation
- Client-side: HTML5 validation (required, min/max for numbers)
- Server-side: Django model validation
- Inline error display on submission
- Form data preserved on validation error

### Security
- Protected by `@require_sgod_admin()` decorator
- CSRF token on all forms
- Password field uses `PasswordInput` widget
- User lookup validates existence before reset

## Future Enhancements
- [ ] Bulk school import from CSV
- [ ] User search functionality
- [ ] Edit school inline
- [ ] Delete school with confirmation
- [ ] Pagination for schools/users
- [ ] Export schools to CSV
- [ ] Filter by district/division
- [ ] Sort tables by column
- [ ] View school details modal
- [ ] Activity log (who created what when)

## Related Files
- Template: `templates/organizations/manage_directory.html`
- View: `organizations/views.py` (`manage_directory()`)
- Forms: `organizations/forms.py` (`SchoolForm`, `UserPasswordResetForm`)
- URL: `organizations/urls.py` (`directory/`)
- Tests: `organizations/tests.py` (`DirectoryManagementTests`)
- CSS: `static/css/form-system.css`
