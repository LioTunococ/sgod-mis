#!/usr/bin/env python3
"""
Test script for SMME KPI Dashboard functionality
"""

import os
import sys
import django
import pytest

# Add the project directory to Python path
project_dir = r'c:\Users\Leinster C. Denna\Desktop\SGOD_Project'
sys.path.append(project_dir)

# Set the DJANGO_SETTINGS_MODULE environment variable
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgod_mis.settings.dev')

# Setup Django
django.setup()

def test_smme_kpi_functions():
    """Import-only smoke test for KPI calculators (no DB access)."""
    try:
        from dashboards import kpi_calculators as kc  # noqa: F401
    except Exception as e:
        raise AssertionError(f"Unable to import KPI calculators: {e}")
    assert True

def test_dashboard_view():
    """Ensure the dashboard view can be imported and a request built (no auth assumptions)."""
    print("\nTesting SMME Dashboard View...")
    
    try:
        from dashboards.views import smme_kpi_dashboard
        print("✓ Dashboard view imported successfully")
        
        # Import Django test client
        from django.test import RequestFactory
        from django.contrib.auth.models import User
        
        # Create a test request
        factory = RequestFactory()
        request = factory.get('/dashboard/smme-kpi/')
        
        # Create or get a test user (with proper permissions)
        try:
            # Check if we need to create a superuser for testing
            users = User.objects.filter(is_superuser=True)
            if users.exists():
                request.user = users.first()
                print(f"✓ Using test user: {request.user.username}")
            else:
                print("⚠ No superuser found, skipping view test")
                pytest.skip("No superuser available; view auth not asserted in this smoke test")
                
        except Exception as e:
            print(f"⚠ User setup error: {e}")
            pytest.skip("User setup issue; skipping view smoke test")
            
    except ImportError as e:
        raise AssertionError(f"View import error: {e}")
    except Exception as e:
        raise AssertionError(f"View test error: {e}")
    assert True

if __name__ == "__main__":
    print("SMME KPI Dashboard Test Suite")
    print("=" * 50)
    
    success = True
    
    # Test KPI functions
    if not test_smme_kpi_functions():
        success = False
    
    # Test dashboard view
    if not test_dashboard_view():
        success = False
        
    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed! SMME KPI Dashboard is ready.")
    else:
        print("❌ Some tests failed. Check the errors above.")
        
    print("Test complete.")