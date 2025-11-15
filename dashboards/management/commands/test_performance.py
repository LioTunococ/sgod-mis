"""
Performance test script for the optimized dashboard
"""
import time
import requests
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Test dashboard performance with and without optimizations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            type=str,
            default='http://localhost:8000/dashboards/smme-kpi/',
            help='Dashboard URL to test',
        )
        parser.add_argument(
            '--iterations',
            type=int,
            default=5,
            help='Number of test iterations',
        )

    def handle(self, *args, **options):
        url = options['url']
        iterations = options['iterations']
        
        self.stdout.write(f'Testing dashboard performance: {url}')
        self.stdout.write(f'Running {iterations} iterations...\n')
        
        times = []
        
        for i in range(iterations):
            self.stdout.write(f'Iteration {i + 1}...', ending='')
            
            start_time = time.time()
            try:
                response = requests.get(url, timeout=30)
                end_time = time.time()
                
                if response.status_code == 200:
                    duration = end_time - start_time
                    times.append(duration)
                    
                    # Get performance headers if available
                    perf_time = response.headers.get('X-Performance-Time', 'N/A')
                    perf_queries = response.headers.get('X-Performance-Queries', 'N/A')
                    
                    self.stdout.write(f' {duration:.3f}s (Server: {perf_time}s, Queries: {perf_queries})')
                else:
                    self.stdout.write(f' ERROR: HTTP {response.status_code}')
                    
            except requests.RequestException as e:
                self.stdout.write(f' ERROR: {e}')
        
        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            self.stdout.write(f'\nPerformance Summary:')
            self.stdout.write(f'  Average: {avg_time:.3f}s')
            self.stdout.write(f'  Minimum: {min_time:.3f}s')
            self.stdout.write(f'  Maximum: {max_time:.3f}s')
            
            if avg_time < 1.0:
                self.stdout.write(self.style.SUCCESS('✓ Excellent performance (<1s)'))
            elif avg_time < 2.0:
                self.stdout.write(self.style.SUCCESS('✓ Good performance (<2s)'))
            elif avg_time < 5.0:
                self.stdout.write(self.style.WARNING('⚠ Acceptable performance (<5s)'))
            else:
                self.stdout.write(self.style.ERROR('✗ Poor performance (>5s)'))
        else:
            self.stdout.write(self.style.ERROR('No successful requests completed'))