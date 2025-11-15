"""
Management command to warm up dashboard cache and optimize performance
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.db import connection
from django.utils import timezone

from organizations.models import School, District
from submissions.models import Period, Form1SLPRow
from dashboards.performance import DashboardCache, QueryOptimizer


class Command(BaseCommand):
    help = 'Warm up dashboard cache and optimize database performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='Clear existing cache before warming up',
        )
        parser.add_argument(
            '--school-year',
            type=str,
            help='Specific school year to warm up (e.g., 2025)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Verbose output',
        )

    def handle(self, *args, **options):
        if options['clear_cache']:
            self.stdout.write('Clearing existing cache...')
            cache.clear()
            self.stdout.write(self.style.SUCCESS('Cache cleared.'))

        verbose = options['verbose']
        school_year = options['school_year']

        self.stdout.write('Starting cache warmup...')
        
        # Get active periods
        periods_qs = Period.objects.filter(is_active=True)
        if school_year:
            periods_qs = periods_qs.filter(school_year_start=int(school_year))
        
        periods = list(periods_qs.order_by('-school_year_start', 'display_order'))
        
        if not periods:
            self.stdout.write(self.style.WARNING('No active periods found.'))
            return

        if verbose:
            self.stdout.write(f'Found {len(periods)} periods to process')

        # Warm up filter options cache
        self._warm_filter_options(periods, verbose)
        
        # Warm up school data cache
        self._warm_school_data(periods, verbose)
        
        # Warm up KPI data cache
        self._warm_kpi_data(periods, verbose)
        
        # Optimize database
        self._optimize_database(verbose)
        
        self.stdout.write(self.style.SUCCESS('Cache warmup completed successfully!'))

    def _warm_filter_options(self, periods, verbose):
        """Warm up filter options cache"""
        if verbose:
            self.stdout.write('Warming up filter options...')
        
        # Cache subjects
        subjects = Form1SLPRow.objects.filter(
            submission__period__in=periods,
            submission__status__in=['submitted', 'noted', 'draft']
        ).values_list('subject', flat=True).distinct().order_by('subject')
        from submissions.constants import SLP_SUBJECT_LABELS
        subjects = [(s, SLP_SUBJECT_LABELS.get(s, s)) for s in subjects if s]
        
        # Cache grades
        grades = Form1SLPRow.objects.filter(
            submission__period__in=periods,
            submission__status__in=['submitted', 'noted', 'draft']
        ).values_list('grade_label', flat=True).distinct().order_by('grade_label')
        grades = [g for g in grades if g]
        
        # Cache districts
        districts = list(District.objects.all().order_by('name'))
        
        # Store in cache
        DashboardCache.set_cached_filter_options('dashboard_filters', {
            'subjects': subjects,
            'grades': grades,
            'districts': districts,
        })
        
        if verbose:
            self.stdout.write(f'  - Cached {len(subjects)} subjects')
            self.stdout.write(f'  - Cached {len(grades)} grade levels')
            self.stdout.write(f'  - Cached {len(districts)} districts')

    def _warm_school_data(self, periods, verbose):
        """Warm up school data cache"""
        if verbose:
            self.stdout.write('Warming up school data...')
        
        # Get all schools with related data
        schools = School.objects.select_related('district', 'profile').order_by('name')
        
        if verbose:
            self.stdout.write(f'Processing {schools.count()} schools...')
        
        # Pre-fetch SLP data for all schools
        slp_data = Form1SLPRow.objects.filter(
            submission__period__in=periods,
            submission__status__in=['submitted', 'noted', 'draft']
        ).select_related('submission__school', 'submission__period').order_by(
            'submission__school__name', 'subject', 'grade_label'
        )
        
        # Group by school
        slp_by_school = {}
        for row in slp_data:
            school_id = row.submission.school_id
            if school_id not in slp_by_school:
                slp_by_school[school_id] = []
            slp_by_school[school_id].append(row)
        
        if verbose:
            self.stdout.write(f'Found SLP data for {len(slp_by_school)} schools')

    def _warm_kpi_data(self, periods, verbose):
        """Warm up KPI calculation cache"""
        if verbose:
            self.stdout.write('Warming up KPI data...')
        
        from dashboards.kpi_calculators import calculate_school_kpis_simple
        from submissions.models import Period
        
        # Convert list back to QuerySet for the KPI calculation
        period_ids = [p.id for p in periods]
        periods_qs = Period.objects.filter(id__in=period_ids)
        
        schools = School.objects.select_related('district', 'profile')
        total_schools = schools.count()
        processed = 0
        
        for school in schools:
            # Calculate and cache KPIs
            school_kpis = calculate_school_kpis_simple(school, periods_qs, 'smme')
            DashboardCache.set_cached_kpi_data(school.id, periods_qs, 'smme', school_kpis)
            
            processed += 1
            if verbose and processed % 50 == 0:
                self.stdout.write(f'  Processed {processed}/{total_schools} schools')
        
        if verbose:
            self.stdout.write(f'Cached KPI data for {processed} schools')

    def _optimize_database(self, verbose):
        """Run database optimization commands"""
        if verbose:
            self.stdout.write('Optimizing database...')
        
        # For SQLite, run VACUUM and ANALYZE
        with connection.cursor() as cursor:
            if verbose:
                self.stdout.write('  Running VACUUM...')
            cursor.execute('VACUUM;')
            
            if verbose:
                self.stdout.write('  Running ANALYZE...')
            cursor.execute('ANALYZE;')
        
        if verbose:
            self.stdout.write('Database optimization completed')

    def _get_cache_stats(self):
        """Get cache statistics (if available)"""
        try:
            # This is implementation-specific and may not work with all cache backends
            stats = cache._cache.get_stats()
            return stats
        except (AttributeError, NotImplementedError):
            return None