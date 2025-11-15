from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.decorators import require_school_head, require_sgod_admin

from django.contrib.auth import get_user_model

from .forms import SchoolForm, SchoolProfileForm, UserPasswordResetForm
from .models import District, School, SchoolProfile, Section


@login_required
@require_sgod_admin()
def school_profile_list(request):
    base_qs = SchoolProfile.objects.select_related("school", "school__district")

    search_query = request.GET.get("q", "").strip()
    district_id = request.GET.get("district", "").strip()
    strand = request.GET.get("strand", "").strip()

    profiles_qs = base_qs
    if search_query:
        profiles_qs = profiles_qs.filter(
            Q(school__name__icontains=search_query)
            | Q(school__code__icontains=search_query)
            | Q(head_name__icontains=search_query)
            | Q(head_contact__icontains=search_query)
        )
    if district_id:
        profiles_qs = profiles_qs.filter(school__district_id=district_id)

    profiles_qs = profiles_qs.order_by("school__name")
    profiles = list(profiles_qs)
    if strand:
        lowered = strand.lower()
        profiles = [
            profile
            for profile in profiles
            if any(isinstance(item, str) and item.lower() == lowered for item in (profile.strands or []))
        ]

    districts = District.objects.order_by("name")
    strand_options = sorted(
        {
            s
            for profile in base_qs
            for s in (profile.strands or [])
            if isinstance(s, str) and s
        }
    )

    return render(
        request,
        "organizations/school_profile_list.html",
        {
            "profiles": profiles,
            "search_query": search_query,
            "selected_district": district_id,
            "selected_strand": strand,
            "districts": districts,
            "strand_options": strand_options,
        },
    )


@login_required
@require_sgod_admin()
def edit_school_profile(request, pk):
    profile = get_object_or_404(
        SchoolProfile.objects.select_related("school", "school__district"),
        pk=pk,
    )
    form = SchoolProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "School profile updated.")
        return redirect("organizations:school_profile_list")

    return render(
        request,
        "organizations/school_profile_form.html",
        {
            "form": form,
            "profile": profile,
            "list_url": reverse("organizations:school_profile_list"),
        },
    )


@login_required
@require_school_head()
def edit_my_school_profile(request):
    user_profile = getattr(request.user, "profile", None)
    school = getattr(user_profile, "school", None)
    if not school:
        messages.error(request, "No school is associated with your account.")
        return redirect("school_home")

    profile, _ = SchoolProfile.objects.get_or_create(school=school)
    form = SchoolProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        updated_profile = form.save(commit=False)
        updated_profile.school = school
        updated_profile.save()
        messages.success(request, "School profile updated.")
        return redirect("organizations:edit_my_school_profile")

    return render(
        request,
        "organizations/school_profile_self_edit.html",
        {
            "form": form,
            "school": school,
            "profile": profile,
            "back_url": reverse("school_home"),
        },
    )


@login_required
@require_sgod_admin()
def manage_directory(request):
    school_form = SchoolForm()
    reset_form = UserPasswordResetForm()

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create_school":
            school_form = SchoolForm(request.POST)
            if school_form.is_valid():
                from accounts.models import SchoolUserRole
                
                school = school_form.save()
                SchoolProfile.objects.get_or_create(school=school)
                
                # Create user if requested
                if school_form.cleaned_data.get('create_user'):
                    username = school_form.cleaned_data.get('username', '').strip()
                    password = school_form.cleaned_data.get('user_password', '')
                    email = school_form.cleaned_data.get('user_email', '').strip()
                    user_role = school_form.cleaned_data.get('user_role', 'school_head')
                    assigned_sections = school_form.cleaned_data.get('assigned_sections', [])
                    psds_district = school_form.cleaned_data.get('psds_district')
                    
                    if username and password:
                        try:
                            # Check if user already exists
                            if get_user_model().objects.filter(username=username).exists():
                                messages.error(request, f"✗ Username '{username}' already exists. Please choose a different username.")
                                school_form = SchoolForm(request.POST)
                            else:
                                from accounts.models import SchoolUserRole, UserProfile
                                
                                # Create user
                                user = get_user_model().objects.create_user(
                                    username=username,
                                    password=password,
                                    email=email
                                )
                                
                                # Create UserProfile
                                profile, _ = UserProfile.objects.get_or_create(user=user)
                                
                                # Assign role-specific permissions
                                if user_role == 'school_head':
                                    # School Head: Set school assignment
                                    profile.school = school
                                    profile.save()
                                    
                                    # Link user to school as school head
                                    SchoolUserRole.objects.create(
                                        user=user,
                                        school=school,
                                        role=SchoolUserRole.Role.SCHOOL_HEAD,
                                        is_primary=True
                                    )
                                    role_display = "School Head"
                                    
                                elif user_role == 'psds':
                                    # PSDS: Set district assignment
                                    profile.psds_district = psds_district
                                    profile.save()
                                    role_display = f"PSDS for {psds_district.name}"
                                    
                                elif user_role == 'section_admin':
                                    # Section Admin: Set section codes from selected sections
                                    codes = [section.code.upper() for section in assigned_sections]
                                    profile.section_admin_codes = codes
                                    profile.save()
                                    role_display = f"Section Admin ({', '.join(codes)})"
                                    
                                elif user_role == 'sgod_admin':
                                    # SGOD Admin: Set superuser status
                                    user.is_staff = True
                                    user.is_superuser = True
                                    user.save()
                                    role_display = "SGOD Admin (Full Access)"
                                
                                messages.success(
                                    request, 
                                    f"✓ Created school: {school.name} ({school.code}) and linked user: {username} as {role_display}"
                                )
                                return redirect("organizations:manage_directory")
                        except Exception as e:
                            messages.error(
                                request,
                                f"✗ Created school: {school.name} but failed to create user: {str(e)}"
                            )
                    else:
                        messages.warning(
                            request,
                            f"✓ Created school: {school.name} ({school.code}) without user account (username or password missing)"
                        )
                else:
                    messages.success(request, f"✓ Created school: {school.name} ({school.code}) without user account")
                
                return redirect("organizations:manage_directory")
            else:
                messages.error(request, "Please fix the errors in the form.")
        elif action == "reset_password":
            reset_form = UserPasswordResetForm(request.POST)
            if reset_form.is_valid():
                try:
                    user = reset_form.save()
                    messages.success(request, f"✓ Password reset for: {user.username}")
                    return redirect("organizations:manage_directory")
                except forms.ValidationError:
                    messages.error(request, "✗ User not found.")
            else:
                messages.error(request, "Please fix the errors in the form.")
        
        elif action == "create_section":
            section_code = request.POST.get("section_code", "").strip().lower()
            section_name = request.POST.get("section_name", "").strip()
            
            if not section_code or not section_name:
                messages.error(request, "✗ Both section code and name are required.")
            elif Section.objects.filter(code=section_code).exists():
                messages.error(request, f"✗ Section with code '{section_code}' already exists.")
            else:
                Section.objects.create(code=section_code, name=section_name)
                messages.success(request, f"✓ Created section: {section_code.upper()} - {section_name}")
                return redirect("organizations:manage_directory")
        
        elif action == "delete_section":
            section_id = request.POST.get("section_id")
            try:
                section = Section.objects.get(id=section_id)
                section_code = section.code
                section.delete()
                messages.success(request, f"✓ Deleted section: {section_code.upper()}")
                return redirect("organizations:manage_directory")
            except Section.DoesNotExist:
                messages.error(request, "✗ Section not found.")
            except Exception as e:
                messages.error(request, f"✗ Cannot delete section: {str(e)}")
        
        elif action == "create_school_year":
            from submissions.models import Period
            from datetime import datetime
            
            sy_start_str = request.POST.get("sy_start")
            
            try:
                sy_start = int(sy_start_str)
                sy_end = sy_start + 1
                
                # Check if school year already exists
                if Period.objects.filter(school_year_start=sy_start).exists():
                    messages.error(request, f"✗ School year {sy_start}-{sy_end} already exists")
                    return redirect("organizations:manage_directory")
                
                # Create 4 quarters with flexible fields
                quarters_data = [
                    {"tag": "Q1", "label": "Q1 Report", "order": 1},
                    {"tag": "Q2", "label": "Q2 Report", "order": 2},
                    {"tag": "Q3", "label": "Q3 Report", "order": 3},
                    {"tag": "Q4", "label": "Q4 Report", "order": 4},
                ]
                
                created_periods = []
                
                for q in quarters_data:
                    # Get optional dates from form
                    q_lower = q['tag'].lower()
                    open_date_str = request.POST.get(f"{q_lower}_open")
                    close_date_str = request.POST.get(f"{q_lower}_close")
                    
                    # Parse dates
                    open_date = None
                    close_date = None
                    
                    if open_date_str:
                        try:
                            open_date = datetime.strptime(open_date_str, "%Y-%m-%d").date()
                        except ValueError:
                            pass
                    
                    if close_date_str:
                        try:
                            close_date = datetime.strptime(close_date_str, "%Y-%m-%d").date()
                        except ValueError:
                            pass
                    
                    # Create period with new flexible fields
                    period = Period.objects.create(
                        school_year_start=sy_start,
                        label=q['label'],
                        quarter_tag=q['tag'],
                        display_order=q['order'],
                        open_date=open_date,
                        close_date=close_date,
                        is_active=True,
                        # Keep old fields for backward compatibility (remove the quarter field since it doesn't exist)
                        starts_on=open_date,
                        ends_on=close_date
                    )
                    created_periods.append(period.label)
                
                messages.success(
                    request, 
                    f"✓ Created school year {sy_start}-{sy_end} with 4 quarters: {', '.join(created_periods)}"
                )
                return redirect("organizations:manage_directory")
                
            except ValueError:
                messages.error(request, "✗ Invalid school year value. Please enter a valid number.")
            except Exception as e:
                messages.error(request, f"✗ Error creating school year: {str(e)}")
        
        elif action == "delete_period":
            from submissions.models import Period
            
            period_id = request.POST.get("period_id")
            try:
                period = Period.objects.get(id=period_id)
                period_label = period.label
                period.delete()
                messages.success(request, f"✓ Deleted period: {period_label}")
                return redirect("organizations:manage_directory")
            except Period.DoesNotExist:
                messages.error(request, "✗ Period not found.")
            except Exception as e:
                messages.error(request, f"✗ Cannot delete period: {str(e)}")
        
        elif action == "create_period":
            from submissions.models import Period
            from datetime import datetime
            
            sy_start_str = request.POST.get("sy_start")
            label = request.POST.get("label", "").strip()
            quarter_tag = request.POST.get("quarter_tag", "").strip()
            display_order_str = request.POST.get("display_order", "0")
            open_date_str = request.POST.get("open_date")
            close_date_str = request.POST.get("close_date")
            
            try:
                sy_start = int(sy_start_str)
                display_order = int(display_order_str)
            except (ValueError, TypeError):
                messages.error(request, "✗ Invalid input values")
                return redirect("organizations:manage_directory")
            
            # Validation
            if not label:
                messages.error(request, "✗ Period label is required")
                return redirect("organizations:manage_directory")
            
            # Check for duplicate label in same school year
            if Period.objects.filter(school_year_start=sy_start, label=label).exists():
                messages.error(request, f"✗ Period '{label}' already exists for SY {sy_start}-{sy_start+1}")
                return redirect("organizations:manage_directory")
            
            # Parse dates
            open_date = None
            close_date = None
            
            if open_date_str:
                try:
                    open_date = datetime.strptime(open_date_str, "%Y-%m-%d").date()
                except ValueError:
                    messages.error(request, "✗ Invalid open date format")
                    return redirect("organizations:manage_directory")
            
            if close_date_str:
                try:
                    close_date = datetime.strptime(close_date_str, "%Y-%m-%d").date()
                except ValueError:
                    messages.error(request, "✗ Invalid close date format")
                    return redirect("organizations:manage_directory")
            
            try:
                # Create period
                period = Period.objects.create(
                    school_year_start=sy_start,
                    label=label,
                    quarter_tag=quarter_tag,
                    display_order=display_order,
                    open_date=open_date,
                    close_date=close_date,
                    is_active=True
                )
                
                messages.success(request, f"✓ Created period: {period}")
                return redirect("organizations:manage_directory")
            except Exception as e:
                messages.error(request, f"✗ Error creating period: {str(e)}")
        
        elif action == "create_user":
            username = request.POST.get("username", "").strip()
            password = request.POST.get("password", "")
            email = request.POST.get("email", "").strip()
            user_role = request.POST.get("user_role")
            
            # Validation
            if not username or not password:
                messages.error(request, "✗ Username and password are required")
                return redirect("organizations:manage_directory")
            
            if get_user_model().objects.filter(username=username).exists():
                messages.error(request, f"✗ Username '{username}' already exists")
                return redirect("organizations:manage_directory")
            
            # Create user
            from accounts.models import SchoolUserRole, UserProfile
            user = get_user_model().objects.create_user(username=username, password=password, email=email)
            profile, _ = UserProfile.objects.get_or_create(user=user)
            
            # Assign role
            if user_role == 'school_head':
                school_id = request.POST.get("school_id")
                if not school_id:
                    messages.error(request, "✗ School selection is required for School Head")
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
                    messages.error(request, "✗ District selection is required for PSDS")
                    user.delete()
                    return redirect("organizations:manage_directory")
                
                district = District.objects.get(id=district_id)
                profile.psds_district = district
                profile.save()
                role_display = f"PSDS for {district.name}"
            
            elif user_role == 'section_admin':
                section_ids = request.POST.getlist("section_ids")
                if not section_ids:
                    messages.error(request, "✗ At least one section is required for Section Admin")
                    user.delete()
                    return redirect("organizations:manage_directory")
                
                sections_selected = Section.objects.filter(id__in=section_ids)
                codes = [s.code.upper() for s in sections_selected]
                profile.section_admin_codes = codes
                profile.save()
                role_display = f"Section Admin ({', '.join(codes)})"
            
            elif user_role == 'sgod_admin':
                user.is_staff = True
                user.is_superuser = True
                user.save()
                role_display = "SGOD Admin (Full Access)"
            else:
                messages.error(request, "✗ Invalid role selected")
                user.delete()
                return redirect("organizations:manage_directory")
            
            messages.success(request, f"✓ Created user: {username} as {role_display}")
            return redirect("organizations:manage_directory")


    # Search functionality
    search_query = request.GET.get("search", "").strip()
    if search_query:
        schools = School.objects.select_related("district").filter(
            Q(name__icontains=search_query) | Q(code__icontains=search_query)
        ).order_by("name")[:50]
    else:
        schools = School.objects.select_related("district").order_by("-id")[:50]
    
    users = get_user_model().objects.order_by("-date_joined")[:25]
    
    # Get all sections with form counts
    from submissions.models import FormTemplate
    sections = Section.objects.all().order_by("code")
    sections_with_counts = []
    for section in sections:
        form_count = FormTemplate.objects.filter(section=section).count()
        sections_with_counts.append({
            'id': section.id,
            'code': section.code,
            'name': section.name,
            'form_count': form_count
        })

    # Get all periods
    from submissions.models import Period
    periods = Period.objects.all().order_by("-school_year_start", "quarter_tag")
    
    return render(
        request,
        "organizations/manage_directory.html",
        {
            "school_form": school_form,
            "reset_form": reset_form,
            "schools": schools,
            "users": users,
            "sections": sections_with_counts,
            "periods": periods,
            "all_schools": School.objects.all().order_by("name"),
            "districts": District.objects.all().order_by("name"),
            "search_query": search_query,
        },
    )
