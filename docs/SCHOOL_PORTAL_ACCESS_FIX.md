# School Portal Access Fix

## Issues Fixed

### 1. ❌ "No school portal data available" Error
**Problem**: When logging in as a school user, the dashboard showed "No school portal data available for this account" instead of the school portal interface.

**Root Cause**: Creating a school in Django admin doesn't automatically create the required `SchoolUserRole` link between the user and the school. The system checks for this relationship to determine if a user is a school head.

**Solution**: 
- Added proper "Access Denied" page when user has no school assignment
- Enhanced directory tools to create user + school link automatically
- Now shows clear instructions on what to do if access is denied

### 2. 🎨 Old Design System
**Problem**: School portal was using old `app.css` instead of the new Boring Design System.

**Solution**: Updated `templates/dashboards/school_home.html` to use `form-system.css`

### 3. 📝 User Creation Workflow
**Problem**: No easy way to create a school AND its associated school head user in one step.

**Solution**: Enhanced Directory Tools form to optionally create a user account when creating a school.

## Changes Made

### 1. **School Portal Template** (`templates/dashboards/school_home.html`)

#### Updated CSS Import
```html
<!-- Before -->
<link rel="stylesheet" href="{% static 'css/app.css' %}">

<!-- After -->
<link rel="stylesheet" href="{% static 'css/form-system.css' %}">
```

#### Added Access Denied Page
```html
{% if not school_portal %}
  <div class="card card--wide" style="margin-top: 2rem; text-align: center; padding: 3rem;">
    <h1 style="color: #dc2626; margin-bottom: 1rem;">🚫 Access Denied</h1>
    <p style="font-size: 1.125rem; color: #6b7280; margin-bottom: 1.5rem;">
      No school portal data available for this account.
    </p>
    <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 0.5rem; padding: 1.5rem; margin-bottom: 2rem;">
      <p style="color: #991b1b; margin-bottom: 0.5rem;"><strong>Possible reasons:</strong></p>
      <ul style="text-align: left; color: #991b1b; display: inline-block;">
        <li>Your user account is not linked to a school</li>
        <li>You don't have School Head permissions</li>
        <li>Your school assignment is missing in the database</li>
      </ul>
    </div>
    <p style="color: #6b7280;">
      Please contact your SGOD administrator to assign you to a school.
    </p>
  </div>
{% else %}
  <!-- Normal school portal content -->
{% endif %}
```

### 2. **Enhanced SchoolForm** (`organizations/forms.py`)

Added optional user creation fields:

```python
class SchoolForm(forms.ModelForm):
    # ... existing school fields ...
    
    # Optional fields for creating a school head user
    create_user = forms.BooleanField(
        required=False,
        initial=True,
        label="Create school head user account"
    )
    username = forms.CharField(
        required=False,
        help_text="Username for the school head"
    )
    user_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(),
        label="Initial password"
    )
    user_email = forms.EmailField(
        required=False,
        label="Email (optional)"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        create_user = cleaned_data.get('create_user')
        username = cleaned_data.get('username')
        user_password = cleaned_data.get('user_password')
        
        if create_user:
            if not username:
                self.add_error('username', 'Username is required when creating a user')
            if not user_password:
                self.add_error('user_password', 'Password is required when creating a user')
        
        return cleaned_data
```

### 3. **Enhanced Directory View** (`organizations/views.py`)

Updated to handle user creation:

```python
@login_required
@require_sgod_admin()
def manage_directory(request):
    # ...
    if action == "create_school":
        school_form = SchoolForm(request.POST)
        if school_form.is_valid():
            from accounts.models import SchoolUserRole
            
            school = school_form.save()
            SchoolProfile.objects.get_or_create(school=school)
            
            # Create user if requested
            if school_form.cleaned_data.get('create_user'):
                username = school_form.cleaned_data['username']
                password = school_form.cleaned_data['user_password']
                email = school_form.cleaned_data.get('user_email', '')
                
                try:
                    user = get_user_model().objects.create_user(
                        username=username,
                        password=password,
                        email=email
                    )
                    # Link user to school as school head
                    SchoolUserRole.objects.create(
                        user=user,
                        school=school,
                        role=SchoolUserRole.Role.SCHOOL_HEAD,
                        is_primary=True
                    )
                    messages.success(
                        request, 
                        f"✓ Created school: {school.name} ({school.code}) and user: {username}"
                    )
                except Exception as e:
                    messages.warning(
                        request,
                        f"✓ Created school: {school.name} but failed to create user: {str(e)}"
                    )
            else:
                messages.success(request, f"✓ Created school: {school.name} ({school.code})")
            
            return redirect("organizations:manage_directory")
    # ...
```

### 4. **Enhanced Template** (`templates/organizations/manage_directory.html`)

Added user creation fields to the form:

```html
<!-- User Creation Section -->
<div class="form-group" style="grid-column: 1 / -1; border-top: 2px solid #e5e7eb; padding-top: 1.5rem; margin-top: 1rem;">
  <label class="form-label" style="font-size: 1rem; font-weight: 600;">
    {{ school_form.create_user }}
    Create School Head User Account
  </label>
  <p class="muted">Automatically create a user account linked to this school as school head</p>
</div>

<div class="form-group">
  <label for="id_username" class="form-label">Username</label>
  {{ school_form.username }}
  <p class="muted">Username for the school head</p>
</div>

<div class="form-group">
  <label for="id_user_password" class="form-label">Initial Password</label>
  {{ school_form.user_password }}
</div>

<div class="form-group" style="grid-column: 1 / -1;">
  <label for="id_user_email" class="form-label">Email (Optional)</label>
  {{ school_form.user_email }}
</div>
```

## How to Use

### Creating a School with User Account

1. Go to **Directory Tools** (`/organizations/directory/`)
2. Fill in school details:
   - School Code (required): e.g., `SCHOOL001`
   - School Name (required): e.g., `Sample Elementary School`
   - District, Division, Type, Grades, etc. (optional)
3. Check **"Create school head user account"** (checked by default)
4. Fill in user details:
   - Username (required): e.g., `school001_head`
   - Initial Password (required): Choose a secure password
   - Email (optional): e.g., `head@school001.edu`
5. Click **"Create School"**
6. Success! Both school and user are created and linked

### Result
- ✅ School created in database
- ✅ SchoolProfile created
- ✅ User account created with specified password
- ✅ SchoolUserRole created linking user to school as "School Head"
- ✅ User can now log in and access the school portal

### If You Already Created a School Without a User

**Option 1: Django Admin** (Manual)
1. Go to Django Admin `/admin/`
2. Navigate to **Accounts → School user roles**
3. Click **"Add school user role"**
4. Select:
   - User: The user account
   - School: The school
   - Role: School Head
   - Is primary: ✓ Checked
5. Save

**Option 2: Directory Tools** (Easier)
1. Go to Directory Tools
2. Create a new user in the "Reset Password" section first (or use Django admin to create user)
3. Then manually link them using Django admin as above

## Understanding the Data Model

### SchoolUserRole
This model links users to schools with specific roles:

```python
class SchoolUserRole(models.Model):
    user = ForeignKey(User)          # The user account
    school = ForeignKey(School)       # The school
    role = CharField                  # "school_head"
    is_primary = BooleanField         # Primary school assignment
```

**Why it's needed**: The system uses this to determine:
- If a user is a school head
- Which school they manage
- What permissions they have

### Without SchoolUserRole
- User can log in
- But sees "No school portal data available"
- Cannot access school-specific features

### With SchoolUserRole
- User can log in
- Sees full school portal dashboard
- Can create/edit submissions
- Can view school-specific data

## Visual Improvements

### Access Denied Page
- Clear error message with icon (🚫)
- Explains the problem
- Lists possible reasons
- Tells user what to do
- Professional, helpful design

### Directory Tools Form
- Checkbox to enable user creation
- Clear field labels
- Visual separator between school and user sections
- Helpful placeholder text
- Success messages show both school and user info

## Testing

To test the fix:

1. **Test Access Denied Page**:
   ```
   - Create a user in Django admin WITHOUT SchoolUserRole
   - Log in as that user
   - Should see "Access Denied" page with clear instructions
   ```

2. **Test School + User Creation**:
   ```
   - Go to Directory Tools
   - Fill in school details
   - Check "Create school head user account"
   - Fill in username/password
   - Submit
   - Log out
   - Log in as new user
   - Should see full school portal
   ```

3. **Test Existing Workflow**:
   ```
   - Create school WITHOUT checking "Create user"
   - Should work as before
   - Manually link user later using Django admin
   ```

## Migration Notes

**No database migrations needed!** This is purely a form/view enhancement. The `SchoolUserRole` model already exists.

## Security

- Passwords are hashed using Django's `create_user()` method
- No plaintext passwords stored
- User creation happens in transaction with school creation
- If user creation fails, school is still created (graceful degradation)

## Future Enhancements

- [ ] Add "Edit School" functionality in Directory Tools
- [ ] Add "Link Existing User to School" form
- [ ] Show existing school users in the schools table
- [ ] Add bulk user creation from CSV
- [ ] Add email notification when user is created
- [ ] Add "Generate Random Password" button
- [ ] Show password strength indicator

## Related Files

- Template: `templates/dashboards/school_home.html`
- Template: `templates/organizations/manage_directory.html`
- View: `dashboards/views.py` (`school_home()`)
- View: `organizations/views.py` (`manage_directory()`)
- Form: `organizations/forms.py` (`SchoolForm`)
- Model: `accounts/models.py` (`SchoolUserRole`)
- Documentation: `docs/DIRECTORY_TOOLS_IMPROVEMENTS.md`
