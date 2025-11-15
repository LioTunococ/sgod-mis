from django.core.management.base import BaseCommand
from organizations.models import School
from submissions.models import Submission, Form1SLPRow, Period
from dashboards.kpi_calculators import calculate_school_kpis_simple

class Command(BaseCommand):
    help = 'Debug SMME KPI Dashboard data issues'
    
    def handle(self, *args, **options):
        self.stdout.write("🔍 SMME Dashboard Data Debug")
        self.stdout.write("=" * 40)
        
        # Check schools
        schools = School.objects.all()[:3]
        for school in schools:
            self.stdout.write(f"\n📊 {school.name}")
            
            # Check submissions
            total_subs = Submission.objects.filter(school=school).count()
            active_subs = Submission.objects.filter(
                school=school,
                status__in=['submitted', 'noted', 'approved']
            ).count()
            
            self.stdout.write(f"   Submissions: {total_subs} total, {active_subs} active")
            
            # Check SLP data
            slp_total = Form1SLPRow.objects.filter(submission__school=school).count()
            slp_offered = Form1SLPRow.objects.filter(
                submission__school=school,
                is_offered=True
            ).count()
            
            self.stdout.write(f"   SLP rows: {slp_total} total, {slp_offered} offered")
            
            # Test KPI calculation
            periods = Period.objects.filter(is_active=True)
            kpis = calculate_school_kpis_simple(school, periods, 'smme')
            self.stdout.write(f"   SLP KPI: {kpis['slp']:.1f}% (has_data: {kpis['has_data']})")
        
        # Check periods
        self.stdout.write(f"\n📅 Periods:")
        periods = Period.objects.filter(is_active=True)
        for p in periods[:3]:
            self.stdout.write(f"   {p.label} - {p.school_year_start}")