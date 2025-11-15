from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from accounts import services as account_services, roles
from organizations.models import Section


@login_required
def post_login_redirect(request):
    user = request.user

    if account_services.user_is_sgod_admin(user):
        return redirect('division_overview')

    if account_services.user_is_psds(user):
        return redirect('smme_kpi_dashboard')

    section_codes = account_services.get_section_codes(user)
    if section_codes:
        return redirect('review_queue', section_code=section_codes[0])

    first_section = Section.objects.order_by('code').values_list('code', flat=True).first()
    if first_section and (account_services.user_is_section_admin(user, first_section) or roles.is_sgod_admin(user)):
        return redirect('review_queue', section_code=first_section)

    if account_services.user_is_school_head(user):
        return redirect('school_home')

    if first_section:
        return redirect('review_queue', section_code=first_section)

    return redirect('school_home')
