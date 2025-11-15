# Directory Tools Refinement Plan

**Date**: October 17, 2025  
**Goal**: Clean up directory tools, add SHN section, enable creating all account types

---

## PROBLEMS IDENTIFIED

1. ❌ **Missing SHN section** - School Health and Nutrition not in database
2. ❌ **Password reset separated** - Should be in same area as user creation
3. ❌ **Template confusing** - Too many sections, hard to navigate
4. ❌ **Can't create PSDS/Section Admin standalone** - Only via school creation

---

## SOLUTION PLAN (3 PHASES)

### PHASE 1: Add SHN Section (2 min)
**Action**: Add School Health and Nutrition section to database

**Command**:
```python
python manage.py shell -c "from organizations.models import Section; Section.objects.get_or_create(code='shn', defaults={'name': 'School Health and Nutrition Section'}); print('Total sections:', Section.objects.count())"
```

**Result**: 7 sections total (SMME, YFS, HRD, DRRM, SMN, PR, **SHN**)

---

### PHASE 2: Reorganize Template (30 min)

**Current Structure (Confusing)**:
```
1. Create School (with optional user creation)
2. Manage Sections
3. Reset Password
4. Recent Schools table
5. Recent Users table
```

**New Structure (Clear)**:
```
┌─────────────────────────────────────┐
│ 📋 TABS (Easy Navigation)           │
├─────────────────────────────────────┤
│ [Schools] [Users] [Sections]        │ ← Tab navigation
└─────────────────────────────────────┘

TAB 1: SCHOOLS
┌─────────────────────────────────────┐
│ ➕ Create New School                │
│   - School details form             │
│   - Optional: Create school head    │
├─────────────────────────────────────┤
│ 📊 Recent Schools (searchable)      │
└─────────────────────────────────────┘

TAB 2: USERS
┌─────────────────────────────────────┐
│ ➕ Create New User                  │
│   - Username, password, email       │
│   - Role selector (4 options)       │
│   - School assignment (for heads)   │
│   - Section assignment (for admins) │
│   - District assignment (for PSDS)  │
├─────────────────────────────────────┤
│ 🔑 Reset Password                   │
│   - Quick password reset            │
├─────────────────────────────────────┤
│ 📊 Recent Users                     │
└─────────────────────────────────────┘

TAB 3: SECTIONS
┌─────────────────────────────────────┐
│ ➕ Create New Section               │
│   - Code, Name                      │
├─────────────────────────────────────┤
│ 📊 All Sections (with form counts)  │
└─────────────────────────────────────┘
```

**Benefits**:
- ✅ Clear separation of concerns
- ✅ Tab navigation reduces scrolling
- ✅ Related actions grouped together
- ✅ Easier to find what you need

---

### PHASE 3: Add Standalone User Creation (45 min)

**New Feature**: "Create New User" form (separate from school creation)

**Form Fields**:
```html
Username: [____________]
Password: [____________]
Email:    [____________] (optional)

Role: [School Head ▼]
      ├─ School Head
      ├─ PSDS (Provincial Supervisor)
      ├─ Section Admin
      └─ SGOD Admin

--- Role-Specific Fields (show/hide based on role) ---

[IF School Head selected]
  School: [Select school ▼]  ← Dropdown of existing schools

[IF PSDS selected]
  District: [Select district ▼]

[IF Section Admin selected]
  Sections: ☐ SMME ☐ YFS ☐ HRD ☐ DRRM ☐ SMN ☐ PR ☐ SHN

[IF SGOD Admin selected]
  (No additional fields - gets superuser status)
```

**View Logic** (`organizations/views.py`):
```python
elif action == "create_user":
    username = request.POST.get("username")
    password = request.POST.get("password")
    email = request.POST.get("email", "")
    user_role = request.POST.get("user_role")
    
    # Validate
    if User.objects.filter(username=username).exists():
        messages.error("Username already exists")
        return
    
    # Create user
    user = User.objects.create_user(username, email, password)
    profile, _ = UserProfile.objects.get_or_create(user=user)
    
    # Assign role
    if user_role == 'school_head':
        school_id = request.POST.get("school_id")
        school = School.objects.get(id=school_id)
        profile.school = school
        SchoolUserRole.objects.create(user=user, school=school, role='school_head')
    
    elif user_role == 'psds':
        district_id = request.POST.get("district_id")
        profile.psds_district_id = district_id
    
    elif user_role == 'section_admin':
        section_ids = request.POST.getlist("section_ids")
        sections = Section.objects.filter(id__in=section_ids)
        codes = [s.code.upper() for s in sections]
        profile.section_admin_codes = codes
    
    elif user_role == 'sgod_admin':
        user.is_staff = True
        user.is_superuser = True
        user.save()
    
    profile.save()
    messages.success(f"Created user: {username}")
```

---

## IMPLEMENTATION STEPS

### Step 1: Add SHN Section ✅
```bash
python manage.py shell -c "from organizations.models import Section; Section.objects.get_or_create(code='shn', defaults={'name': 'School Health and Nutrition Section'})"
```

### Step 2: Create Tabbed Template Structure
**File**: `templates/organizations/manage_directory.html`

**Add at top** (after title):
```html
<!-- Tab Navigation -->
<div class="tab-nav" style="margin: 2rem 0; border-bottom: 2px solid #e5e7eb;">
  <button class="tab-btn active" onclick="showTab('schools')">
    📚 Schools
  </button>
  <button class="tab-btn" onclick="showTab('users')">
    👥 Users
  </button>
  <button class="tab-btn" onclick="showTab('sections')">
    📋 Sections
  </button>
</div>

<style>
.tab-nav {
  display: flex;
  gap: 0.5rem;
}
.tab-btn {
  padding: 0.75rem 1.5rem;
  border: none;
  background: none;
  border-bottom: 3px solid transparent;
  cursor: pointer;
  font-weight: 500;
  color: #6b7280;
  transition: all 0.2s;
}
.tab-btn:hover {
  color: #1f2937;
  background: #f9fafb;
}
.tab-btn.active {
  color: #2563eb;
  border-bottom-color: #2563eb;
  font-weight: 600;
}
.tab-content {
  display: none;
}
.tab-content.active {
  display: block;
}
</style>
```

**Wrap each section**:
```html
<!-- SCHOOLS TAB -->
<div id="tab-schools" class="tab-content active">
  <!-- Create School form -->
  <!-- Recent Schools table -->
</div>

<!-- USERS TAB -->
<div id="tab-users" class="tab-content">
  <!-- Create User form (NEW) -->
  <!-- Reset Password form (MOVED) -->
  <!-- Recent Users table -->
</div>

<!-- SECTIONS TAB -->
<div id="tab-sections" class="tab-content">
  <!-- Create Section form -->
  <!-- Sections table -->
</div>
```

**Add JavaScript**:
```javascript
<script>
function showTab(tabName) {
  // Hide all tabs
  document.querySelectorAll('.tab-content').forEach(tab => {
    tab.classList.remove('active');
  });
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  
  // Show selected tab
  document.getElementById('tab-' + tabName).classList.add('active');
  event.target.classList.add('active');
}
</script>
```

### Step 3: Add Standalone User Creation Form
**Location**: Users tab, before Reset Password

**HTML**:
```html
<section class="card card--wide" style="margin-bottom:1.5rem;">
  <h2>➕ Create New User</h2>
  <p class="muted">Create users with any role (School Head, PSDS, Section Admin, SGOD Admin)</p>
  
  <form method="post" class="form-grid">
    {% csrf_token %}
    <input type="hidden" name="action" value="create_user">
    
    <!-- Username -->
    <div class="form-group">
      <label class="form-label">Username <span class="required">*</span></label>
      <input type="text" name="username" class="form-input" required>
    </div>
    
    <!-- Password -->
    <div class="form-group">
      <label class="form-label">Password <span class="required">*</span></label>
      <input type="password" name="password" class="form-input" required>
    </div>
    
    <!-- Email -->
    <div class="form-group">
      <label class="form-label">Email</label>
      <input type="email" name="email" class="form-input">
    </div>
    
    <!-- Role -->
    <div class="form-group">
      <label class="form-label">Role <span class="required">*</span></label>
      <select name="user_role" id="user_role_select" class="form-input" required>
        <option value="school_head">School Head</option>
        <option value="psds">PSDS (Provincial Supervisor)</option>
        <option value="section_admin">Section Admin</option>
        <option value="sgod_admin">SGOD Admin</option>
      </select>
    </div>
    
    <!-- School (for School Head) -->
    <div class="form-group" id="school-field" style="grid-column: 1 / -1;">
      <label class="form-label">School <span class="required">*</span></label>
      <select name="school_id" class="form-input">
        <option value="">Select a school</option>
        {% for school in all_schools %}
          <option value="{{ school.id }}">{{ school.name }} ({{ school.code }})</option>
        {% endfor %}
      </select>
    </div>
    
    <!-- District (for PSDS) -->
    <div class="form-group" id="district-field" style="grid-column: 1 / -1; display: none;">
      <label class="form-label">District <span class="required">*</span></label>
      <select name="district_id" class="form-input">
        {% for district in districts %}
          <option value="{{ district.id }}">{{ district.name }}</option>
        {% endfor %}
      </select>
    </div>
    
    <!-- Sections (for Section Admin) -->
    <div class="form-group" id="sections-field" style="grid-column: 1 / -1; display: none;">
      <label class="form-label">Sections <span class="required">*</span></label>
      <div style="display: flex; flex-wrap: wrap; gap: 1rem; padding: 0.75rem; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 0.375rem;">
        {% for section in sections %}
          <label style="display: flex; align-items: center; gap: 0.5rem;">
            <input type="checkbox" name="section_ids" value="{{ section.id }}">
            <span>{{ section.code|upper }}</span>
          </label>
        {% endfor %}
      </div>
    </div>
    
    <div class="form-actions" style="grid-column: 1 / -1;">
      <button type="submit" class="btn btn--primary">Create User</button>
    </div>
  </form>
</section>

<script>
document.getElementById('user_role_select').addEventListener('change', function() {
  const role = this.value;
  document.getElementById('school-field').style.display = role === 'school_head' ? 'block' : 'none';
  document.getElementById('district-field').style.display = role === 'psds' ? 'block' : 'none';
  document.getElementById('sections-field').style.display = role === 'section_admin' ? 'block' : 'none';
});
</script>
```

### Step 4: Add View Handler
**File**: `organizations/views.py`

**Add to POST handling**:
```python
elif action == "create_user":
    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "")
    email = request.POST.get("email", "").strip()
    user_role = request.POST.get("user_role")
    
    # Validation
    if not username or not password:
        messages.error(request, "Username and password are required")
        return redirect("organizations:manage_directory")
    
    if get_user_model().objects.filter(username=username).exists():
        messages.error(request, f"Username '{username}' already exists")
        return redirect("organizations:manage_directory")
    
    # Create user
    from accounts.models import SchoolUserRole, UserProfile
    user = get_user_model().objects.create_user(username=username, password=password, email=email)
    profile, _ = UserProfile.objects.get_or_create(user=user)
    
    # Assign role
    if user_role == 'school_head':
        school_id = request.POST.get("school_id")
        if not school_id:
            messages.error(request, "School selection is required for School Head")
            user.delete()
            return redirect("organizations:manage_directory")
        
        school = School.objects.get(id=school_id)
        profile.school = school
        profile.save()
        SchoolUserRole.objects.create(user=user, school=school, role='school_head', is_primary=True)
        role_display = f"School Head at {school.name}"
    
    elif user_role == 'psds':
        district_id = request.POST.get("district_id")
        if not district_id:
            messages.error(request, "District selection is required for PSDS")
            user.delete()
            return redirect("organizations:manage_directory")
        
        district = District.objects.get(id=district_id)
        profile.psds_district = district
        profile.save()
        role_display = f"PSDS for {district.name}"
    
    elif user_role == 'section_admin':
        section_ids = request.POST.getlist("section_ids")
        if not section_ids:
            messages.error(request, "At least one section is required for Section Admin")
            user.delete()
            return redirect("organizations:manage_directory")
        
        sections = Section.objects.filter(id__in=section_ids)
        codes = [s.code.upper() for s in sections]
        profile.section_admin_codes = codes
        profile.save()
        role_display = f"Section Admin ({', '.join(codes)})"
    
    elif user_role == 'sgod_admin':
        user.is_staff = True
        user.is_superuser = True
        user.save()
        role_display = "SGOD Admin (Full Access)"
    
    messages.success(request, f"✓ Created user: {username} as {role_display}")
    return redirect("organizations:manage_directory")
```

### Step 5: Update Context
**Add to context dict**:
```python
return render(request, "organizations/manage_directory.html", {
    "school_form": school_form,
    "reset_form": reset_form,
    "schools": schools,
    "users": users,
    "sections": sections_with_counts,
    "all_schools": School.objects.all().order_by("name"),  # NEW
    "districts": District.objects.all().order_by("name"),   # NEW
    "search_query": search_query,
})
```

---

## TESTING CHECKLIST

### Test 1: SHN Section
- [ ] Verify SHN appears in sections table
- [ ] Verify SHN appears in section checkboxes (user creation)

### Test 2: Tabbed Navigation
- [ ] Click "Schools" tab → Shows schools content
- [ ] Click "Users" tab → Shows users content
- [ ] Click "Sections" tab → Shows sections content
- [ ] Active tab highlighted correctly

### Test 3: Create School Head (standalone)
- [ ] Fill form with School Head role
- [ ] Select a school
- [ ] Submit → User created with school assignment
- [ ] Login as that user → See school portal

### Test 4: Create PSDS (standalone)
- [ ] Fill form with PSDS role
- [ ] Select a district
- [ ] Submit → User created with district assignment
- [ ] Login as that user → Redirect to SMME KPI dashboard

### Test 5: Create Section Admin (standalone)
- [ ] Fill form with Section Admin role
- [ ] Check SMME and SHN
- [ ] Submit → User created with section codes
- [ ] Login as that user → See only SMME and SHN tabs

### Test 6: Create SGOD Admin (standalone)
- [ ] Fill form with SGOD Admin role
- [ ] Submit → User created with superuser status
- [ ] Login as that user → Redirect to division overview

---

## SUCCESS CRITERIA

✅ 7 sections in database (including SHN)  
✅ Clean tabbed navigation  
✅ Can create all 4 user types standalone  
✅ Reset password in Users tab (logical grouping)  
✅ No confusing layout  
✅ All role-specific fields show/hide correctly  

---

## ESTIMATED TIME

- Phase 1 (SHN): 2 minutes
- Phase 2 (Tabs): 30 minutes
- Phase 3 (User creation): 45 minutes

**Total: ~80 minutes (1 hour 20 min)**

---

**READY TO START?** Say "yes" and I'll execute all 3 phases systematically.
