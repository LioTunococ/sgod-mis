#!/usr/bin/env python3
"""
Simple test to check SMME dashboard URL accessibility
"""

import os
import sys
import django
import requests
from urllib.parse import urljoin

# Add the project directory to Python path
project_dir = r'c:\Users\Leinster C. Denna\Desktop\SGOD_Project'
sys.path.append(project_dir)

# Set the DJANGO_SETTINGS_MODULE environment variable
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgod_mis.settings.dev')

# Setup Django
django.setup()

def test_dashboard_url():
    """Smoke check: reverse URL patterns without requiring a running server"""
    base_url = "http://127.0.0.1:8000"
    
    # Try to find the correct URL pattern
    try:
        from django.urls import reverse
        from dashboards.urls import urlpatterns
        
        print("Dashboard URL patterns:")
        for pattern in urlpatterns:
            print(f"  - {pattern.pattern}")
            
    except Exception as e:
        print(f"Could not get URL patterns: {e}")
    
    # Assert URL reversing works; no network dependency
    from django.urls import reverse, NoReverseMatch
    candidate_names = [
        'smme_kpi_dashboard',
        'district_submission_gaps',
        'division_overview',
        'school_home',
    ]
    reversed_any = False
    for name in candidate_names:
        try:
            url = reverse(name)
            assert isinstance(url, str) and url.startswith('/')
            reversed_any = True
            break
        except Exception:
            continue
    assert reversed_any, "No dashboard URL name could be reversed"

if __name__ == "__main__":
    print("SMME Dashboard URL Test")
    print("=" * 40)
    
    success = test_dashboard_url()
    
    print("\n" + "=" * 40)
    if success:
        print("✅ Dashboard URL test successful!")
    else:
        print("⚠ Dashboard URL needs verification")
        print("Check the URL patterns and ensure the server is running")
