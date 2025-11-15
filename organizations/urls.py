from django.urls import path

from . import views

app_name = "organizations"

urlpatterns = [
    path("school-profiles/", views.school_profile_list, name="school_profile_list"),
    path("school-profiles/<int:pk>/", views.edit_school_profile, name="edit_school_profile"),
    path("school-profile/edit/", views.edit_my_school_profile, name="edit_my_school_profile"),
    path("directory/", views.manage_directory, name="manage_directory"),
]
