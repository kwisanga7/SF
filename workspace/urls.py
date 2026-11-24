from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path("", views.public_home, name="home"),
    path("app.css", views.app_stylesheet, name="app_stylesheet"),
    path("brand-logo.jpg", views.brand_logo, name="brand_logo"),
    path("team-photo.jpeg", views.team_photo, name="team_photo"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("announcements/", views.public_announcements, name="announcements"),
    path("team/", views.team, name="team"),
    path("register/", views.register, name="register"),
    path("account/", views.account_home, name="account_home"),
    path("account/apply/", views.apply_membership, name="apply_membership"),
    path("workspace/", views.dashboard, name="dashboard"),
    path("login/", auth_views.LoginView.as_view(template_name="workspace/login.html", redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("tasks/<int:task_id>/status/", views.update_task_status, name="update_task_status"),
    path("manifest.json", views.manifest, name="manifest"),
    path("sw.js", views.service_worker, name="service_worker"),
]
