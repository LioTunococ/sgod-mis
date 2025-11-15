from django.core.management.base import BaseCommand
from organizations.models import School
from submissions.models import Submission, Form1SLPRow, Period
from dashboards.kpi_calculators import calculate_school_kpis_simple


class Command(BaseCommand):
    help = 'Debug KPI calculations step by step'

    def handle(self, *args, **options):
        # Get available periods
        periods = Period.objects.all()[:3]  # Test with first 3 periods
        
        self.stdout.write(f"Testing with periods: {[p.label for p in periods]}")
        
        # Get a school with SLP data
        school_with_slp = School.objects.filter(
            submissions__form1_slp_rows__isnull=False
        ).first()
        
        if not school_with_slp:
            self.stdout.write(self.style.ERROR("No school found with SLP data"))
            return
            
        self.stdout.write(f"\n=== DEBUGGING SCHOOL: {school_with_slp.name} ===")
        
        # Step 1: Check submissions for this school
        self.stdout.write("\n1. CHECKING SUBMISSIONS:")
        submissions = Submission.objects.filter(school=school_with_slp)
        self.stdout.write(f"Total submissions: {submissions.count()}")
        
        for submission in submissions[:5]:  # Show first 5
            self.stdout.write(f"  - {submission.form_template.title} | Period: {submission.period} | Status: {submission.status}")
        
        # Step 2: Check SMME section submissions
        smme_submissions = submissions.filter(form_template__section__code__iexact='smme')
        self.stdout.write(f"\nSMME section submissions: {smme_submissions.count()}")
        
        for submission in smme_submissions[:3]:
            self.stdout.write(f"  - {submission.form_template.title} | Status: {submission.status}")
        
        # Step 3: Check SLP data for each period
        self.stdout.write("\n2. CHECKING SLP DATA PER PERIOD:")
        for period in periods:
            period_submissions = smme_submissions.filter(period=period)
            self.stdout.write(f"\nPeriod {period.label}:")
            self.stdout.write(f"  Submissions: {period_submissions.count()}")
            
            if period_submissions.exists():
                slp_rows = Form1SLPRow.objects.filter(
                    submission__in=period_submissions,
                    is_offered=True
                )
                self.stdout.write(f"  SLP rows (offered): {slp_rows.count()}")
                
                if slp_rows.exists():
                    sample_row = slp_rows.first()
                    self.stdout.write(f"  Sample row: Subject={sample_row.subject}, Grade={sample_row.grade_label}")
                    self.stdout.write(f"  Sample data: Enrolment={sample_row.enrolment}, S={sample_row.s}, VS={sample_row.vs}, O={sample_row.o}")
        
        # Step 4: Test the KPI calculation
        self.stdout.write("\n3. TESTING KPI CALCULATION:")
        try:
            kpis = calculate_school_kpis_simple(school_with_slp, periods, 'smme')
            self.stdout.write(f"KPI Results: {kpis}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error calculating KPIs: {e}"))
        
        # Step 5: Test with all periods (not just first 3)
        self.stdout.write("\n4. TESTING WITH ALL PERIODS:")
        all_periods = Period.objects.all()
        self.stdout.write(f"Total periods: {all_periods.count()}")
        
        try:
            all_kpis = calculate_school_kpis_simple(school_with_slp, all_periods, 'smme')
            self.stdout.write(f"All periods KPIs: {all_kpis}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error with all periods: {e}"))
        
        self.stdout.write(self.style.SUCCESS('\nDebugging complete!'))