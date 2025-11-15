"""
Performance monitoring middleware for dashboard views
"""
import time
from django.db import connection
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """Middleware to monitor dashboard performance"""
    
    def process_request(self, request):
        """Start timing the request"""
        request._performance_start_time = time.time()
        request._performance_start_queries = len(connection.queries) if settings.DEBUG else 0
        return None
    
    def process_response(self, request, response):
        """Log performance metrics for dashboard views"""
        # Only monitor dashboard views
        if not request.path.startswith('/dashboards/'):
            return response
        
        if hasattr(request, '_performance_start_time'):
            end_time = time.time()
            execution_time = end_time - request._performance_start_time
            
            query_count = 0
            if settings.DEBUG and hasattr(request, '_performance_start_queries'):
                query_count = len(connection.queries) - request._performance_start_queries
            
            # Log performance warnings
            if execution_time > 2.0:
                print(f"SLOW REQUEST: {request.path} took {execution_time:.2f}s")
            
            if query_count > 50:
                print(f"HIGH QUERY COUNT: {request.path} executed {query_count} queries")
            
            # Add performance headers for debugging
            if settings.DEBUG:
                response['X-Performance-Time'] = f"{execution_time:.3f}"
                response['X-Performance-Queries'] = str(query_count)
        
        return response


class CacheHeaderMiddleware(MiddlewareMixin):
    """Add cache-related headers for dashboard optimization"""
    
    def process_response(self, request, response):
        """Add cache headers for dashboard responses"""
        if request.path.startswith('/dashboards/'):
            # Add cache control headers for dashboard static content
            if request.path.endswith('.js') or request.path.endswith('.css'):
                response['Cache-Control'] = 'public, max-age=86400'  # 24 hours
            elif request.path.startswith('/dashboards/api/'):
                response['Cache-Control'] = 'public, max-age=300'  # 5 minutes for API
            else:
                response['Cache-Control'] = 'public, max-age=60'  # 1 minute for dashboard pages
        
        return response


class DatabaseConnectionPoolMiddleware(MiddlewareMixin):
    """Optimize database connections for dashboard views"""
    
    def process_request(self, request):
        """Optimize database settings for dashboard requests"""
        if request.path.startswith('/dashboards/'):
            # For dashboard requests, we can be more aggressive with connection reuse
            from django.db import connections
            
            for conn in connections.all():
                # Enable query caching if available
                if hasattr(conn, 'use_debug_cursor'):
                    conn.use_debug_cursor = False  # Disable debug cursor for better performance
        
        return None