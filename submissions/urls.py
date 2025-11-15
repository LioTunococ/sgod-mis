from django.urls import path

from . import views

urlpatterns = [
    path("manage/forms/", views.manage_section_forms, name="manage_section_forms"),
    path("forms/<slug:section_code>/", views.open_forms_list, name="open_forms_list"),
    path(
        "submission/start/<slug:form_code>/<int:period_id>/",
        views.start_submission,
        name="start_submission",
    ),
    path("submission/<int:submission_id>/", views.edit_submission, name="edit_submission"),
    path(
        "submission/<int:submission_id>/add-project/",
        views.add_project,
        name="add_project",
    ),
    path(
        "submission/<int:submission_id>/attachments/<int:attachment_id>/delete/",
        views.delete_attachment,
        name="delete_attachment",
    ),
    path("project/<int:project_id>/add-activity/", views.add_activity, name="add_activity"),
    path("review/<slug:section_code>/queue/", views.review_queue, name="review_queue"),
    path("review/<int:submission_id>/tabs/", views.review_submission_tabs, name="review_submission_tabs"),
    path("review/<int:submission_id>/export/<str:file_format>/", views.review_submission_export, name="review_submission_export"),
    path("review/<int:submission_id>/", views.review_detail, name="review_detail"),
    
    # SLP form wizard
    path("submission/<int:submission_id>/slp/", views.slp_wizard, name="slp_wizard"),
]
