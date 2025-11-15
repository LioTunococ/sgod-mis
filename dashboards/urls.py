from django.urls import path

from . import views

urlpatterns = [
    # Core dashboard views
    path("", views.school_home, name="school_home"),
    path("dashboards/district-submissions/", views.district_submission_gaps, name="district_submission_gaps"),
    path("dashboards/smme-kpi/", views.smme_kpi_dashboard, name="smme_kpi_dashboard"),
    path("dashboards/smme-kpi/data/", views.smme_kpi_dashboard_data, name="smme_kpi_dashboard_data"),
    path("dashboards/smme-kpi/api/", views.smme_kpi_api, name="smme_kpi_api"),
    path("dashboards/smme-kpi/comparison/", views.smme_kpi_comparison, name="smme_kpi_comparison"),
    path("dashboards/smme-kpi/export/", views.smme_kpi_export_csv, name="smme_kpi_export"),
    path("dashboards/division-overview/", views.division_overview, name="division_overview"),
]
