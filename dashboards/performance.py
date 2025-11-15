"""
Performance optimization utilities for dashboard views
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional
from django.core.cache import cache
from django.db.models import QuerySet, Prefetch
from django.utils import timezone
from datetime import timedelta

from organizations.models import School, District
from submissions.models import Form1SLPRow, Period, Submission


class DashboardCache:
    """Cache manager for dashboard data with intelligent cache invalidation"""
    
    # Cache timeouts in seconds
    CACHE_TIMEOUTS = {
        'kpi_data': 300,  # 5 minutes
        'school_list': 1800,  # 30 minutes
        'period_list': 3600,  # 1 hour
        'subject_list': 1800,  # 30 minutes
        'district_list': 3600,  # 1 hour
    }
    
    @staticmethod
    def generate_cache_key(prefix: str, **kwargs) -> str:
        """Generate a unique cache key based on parameters"""
        # Create a string of all parameters for hashing
        param_string = '|'.join(f"{k}={v}" for k, v in sorted(kwargs.items()) if v is not None)
        param_hash = hashlib.md5(param_string.encode()).hexdigest()[:10]
        return f"dashboard_{prefix}_{param_hash}"
    
    @classmethod
    def get_cached_kpi_data(cls, school_id: int, periods: QuerySet, section_code: str) -> Optional[Dict]:
        """Get cached KPI data for a school"""
        cache_key = cls.generate_cache_key(
            'kpi',
            school_id=school_id,
            periods=str(list(periods.values_list('id', flat=True))),
            section=section_code
        )
        return cache.get(cache_key)
    
    @classmethod
    def set_cached_kpi_data(cls, school_id: int, periods: QuerySet, section_code: str, data: Dict) -> None:
        """Cache KPI data for a school"""
        cache_key = cls.generate_cache_key(
            'kpi',
            school_id=school_id,
            periods=str(list(periods.values_list('id', flat=True))),
            section=section_code
        )
        cache.set(cache_key, data, cls.CACHE_TIMEOUTS['kpi_data'])
    
    @classmethod
    def get_cached_slp_data(cls, **filters) -> Optional[List]:
        """Get cached SLP subject data"""
        cache_key = cls.generate_cache_key('slp_subjects', **filters)
        return cache.get(cache_key)
    
    @classmethod
    def set_cached_slp_data(cls, data: List, **filters) -> None:
        """Cache SLP subject data"""
        cache_key = cls.generate_cache_key('slp_subjects', **filters)
        cache.set(cache_key, data, cls.CACHE_TIMEOUTS['kpi_data'])
    
    @classmethod
    def invalidate_school_cache(cls, school_id: int) -> None:
        """Invalidate all cached data for a specific school"""
        # This is a simple implementation - in production you might want more sophisticated invalidation
        cache.clear()  # Clear all cache for simplicity
    
    @classmethod
    def get_cached_filter_options(cls, filter_type: str) -> Optional[List]:
        """Get cached filter options (subjects, districts, etc.)"""
        cache_key = f"filter_options_{filter_type}"
        return cache.get(cache_key)
    
    @classmethod
    def set_cached_filter_options(cls, filter_type: str, data: List) -> None:
        """Cache filter options"""
        cache_key = f"filter_options_{filter_type}"
        timeout = cls.CACHE_TIMEOUTS.get(f"{filter_type}_list", 1800)
        cache.set(cache_key, data, timeout)


class QueryOptimizer:
    """Database query optimization utilities"""
    
    @staticmethod
    def get_optimized_schools_queryset(filters: Dict[str, Any]) -> QuerySet:
        """Get optimized schools queryset with proper select_related"""
        qs = School.objects.select_related('district', 'profile').order_by('name')
        
        if filters.get('district_id') and filters['district_id'] != 'all':
            qs = qs.filter(district_id=filters['district_id'])
        
        if filters.get('school_id') and filters['school_id'] != 'all':
            qs = qs.filter(id=filters['school_id'])
        
        if filters.get('school_level') and filters['school_level'] != 'all':
            if filters['school_level'] == 'elementary':
                qs = qs.filter(profile__grade_span_end__lte=6)
            elif filters['school_level'] == 'secondary':
                qs = qs.filter(profile__grade_span_start__gte=7)
        
        return qs
    
    @staticmethod
    def get_optimized_slp_queryset(periods: QuerySet, filters: Dict[str, Any]) -> QuerySet:
        """Get optimized SLP rows queryset with proper prefetching"""
        qs = Form1SLPRow.objects.filter(
            submission__period__in=periods,
            # Only include finalized submissions (exclude drafts and returned)
            submission__status__in=['submitted', 'noted'],
            # Exclude rows from inactive form templates
            submission__form_template__is_active=True,
        ).select_related(
            'submission__school',
            'submission__school__district',
            'submission__school__profile',
            'submission__period'
        ).order_by('submission__school__name', 'subject', 'grade_label')
        
        # Apply filters
        if filters.get('subject_filter') and filters['subject_filter'] != 'all':
            qs = qs.filter(subject=filters['subject_filter'])
        
        if filters.get('grade_range') and filters['grade_range'] != 'all':
            grade_ranges = {
                'k-3': ['Kinder', 'Grade 1', 'Grade 2', 'Grade 3'],
                '4-6': ['Grade 4', 'Grade 5', 'Grade 6'],
                '7-9': ['Grade 7', 'Grade 8', 'Grade 9'],
                '10-12': ['Grade 10', 'Grade 11', 'Grade 12'],
            }
            if filters['grade_range'] in grade_ranges:
                qs = qs.filter(grade_label__in=grade_ranges[filters['grade_range']])
        
        if filters.get('min_enrollment'):
            try:
                min_enroll = int(filters['min_enrollment'])
                qs = qs.filter(enrolment__gte=min_enroll)
            except (ValueError, TypeError):
                pass
        
        if filters.get('has_intervention') and filters['has_intervention'] != 'all':
            if filters['has_intervention'] == 'yes':
                qs = qs.exclude(intervention_plan__isnull=True).exclude(intervention_plan__exact='')
            elif filters['has_intervention'] == 'no':
                qs = qs.filter(intervention_plan__isnull=True) | qs.filter(intervention_plan__exact='')
        
        return qs
    
    @staticmethod
    def get_bulk_submissions_for_schools(schools: QuerySet, periods: QuerySet) -> Dict[int, List]:
        """Bulk fetch submissions for multiple schools to reduce N+1 queries"""
        submissions = Submission.objects.filter(
            school__in=schools,
            period__in=periods,
            status__in=['submitted', 'noted', 'draft']
        ).select_related('school', 'period', 'form_template').prefetch_related(
            'form1_slp_rows'
        )
        
        # Group submissions by school
        submissions_by_school = {}
        for submission in submissions:
            school_id = submission.school_id
            if school_id not in submissions_by_school:
                submissions_by_school[school_id] = []
            submissions_by_school[school_id].append(submission)
        
        return submissions_by_school


class PerformanceMonitor:
    """Monitor and log performance metrics"""
    
    @staticmethod
    def log_query_performance(view_name: str, query_count: int, execution_time: float) -> None:
        """Log query performance metrics (in production, you might send this to monitoring service)"""
        if query_count > 50:  # Threshold for too many queries
            print(f"WARNING: {view_name} executed {query_count} queries in {execution_time:.2f}s")
        elif execution_time > 2.0:  # Threshold for slow response
            print(f"WARNING: {view_name} took {execution_time:.2f}s to execute")
    
    @staticmethod
    def profile_view(func):
        """Decorator to profile view performance"""
        def wrapper(request, *args, **kwargs):
            from django.db import connection
            from django.conf import settings
            import time
            
            if not settings.DEBUG:
                return func(request, *args, **kwargs)
            
            start_time = time.time()
            start_queries = len(connection.queries)
            
            result = func(request, *args, **kwargs)
            
            end_time = time.time()
            end_queries = len(connection.queries)
            
            execution_time = end_time - start_time
            query_count = end_queries - start_queries
            
            PerformanceMonitor.log_query_performance(
                func.__name__, query_count, execution_time
            )
            
            return result
        return wrapper


# Utility functions for common optimizations
def get_cached_or_compute(cache_key: str, compute_func, timeout: int = 300):
    """Generic cache-or-compute pattern"""
    cached_value = cache.get(cache_key)
    if cached_value is not None:
        return cached_value
    
    computed_value = compute_func()
    cache.set(cache_key, computed_value, timeout)
    return computed_value


def batch_process_schools(schools: QuerySet, periods: QuerySet, batch_size: int = 50):
    """Process schools in batches to avoid memory issues with large datasets"""
    total_schools = schools.count()
    
    for start in range(0, total_schools, batch_size):
        end = min(start + batch_size, total_schools)
        batch = schools[start:end]
        yield batch