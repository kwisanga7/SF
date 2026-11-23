from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path("", views.public_home, name="home"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("announcements/", views.public_announcements, name="announcements"),
    path("team/", views.team, name="team"),
    path("register/", views.register, name="register"),
    path("workspace/", views.dashboard, name="dashboard"),
    path("login/", auth_views.LoginView.as_view(template_name="workspace/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("tasks/<int:task_id>/status/", views.update_task_status, name="update_task_status"),
    path("manifest.json", views.manifest, name="manifest"),
    path("sw.js", views.service_worker, name="service_worker"),
]
