from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from pathlib import Path

from .decorators import member_required
from .forms import ContactForm, MembershipApplicationForm, RegistrationForm
from .models import Announcement, MembershipApplication, Task, TeamMember


def public_home(request):
    return render(request, "workspace/home.html", {"today": timezone.localdate()})


def app_stylesheet(request):
    css_file = Path(__file__).parent / "static" / "workspace" / "app.css"
    response = FileResponse(css_file.open("rb"), content_type="text/css; charset=utf-8")
    response["Cache-Control"] = "no-store"
    return response


def brand_logo(request):
    image = Path(__file__).parent / "static" / "workspace" / "safetyfund-logo.jpg"
    return FileResponse(image.open("rb"), content_type="image/jpeg")


def team_photo(request):
    image = Path(__file__).parent / "static" / "workspace" / "team-photo.jpeg"
    return FileResponse(image.open("rb"), content_type="image/jpeg")


def about(request):
    return render(request, "workspace/about.html")


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Thanks for reaching out. Your message has been received.")
        return redirect("contact")
    return render(request, "workspace/contact.html", {"form": form})


def public_announcements(request):
    announcements = Announcement.objects.filter(is_public=True).select_related("author")
    return render(request, "workspace/announcements.html", {"announcements": announcements})


def team(request):
    members = TeamMember.objects.filter(is_published=True)
    return render(request, "workspace/team.html", {"members": members})


def register(request):
    if request.user.is_authenticated:
        return redirect("account_home")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("account_home")
    return render(request, "workspace/register.html", {"form": form})


@login_required
def account_home(request):
    latest_application = request.user.membership_applications.first()
    is_member = request.user.is_staff or MembershipApplication.objects.filter(
        user=request.user, status=MembershipApplication.Status.APPROVED
    ).exists()
    can_apply = not request.user.is_staff and not is_member and (
        latest_application is None or latest_application.status == MembershipApplication.Status.REJECTED
    )
    return render(request, "workspace/account.html", {
        "application": latest_application, "is_member": is_member, "can_apply": can_apply,
    })


@login_required
def apply_membership(request):
    if request.user.is_staff or MembershipApplication.objects.filter(
        user=request.user, status=MembershipApplication.Status.APPROVED
    ).exists():
        messages.info(request, "Your account already has member access.")
        return redirect("account_home")
    if MembershipApplication.objects.filter(user=request.user, status=MembershipApplication.Status.PENDING).exists():
        messages.info(request, "Your membership application is already awaiting review.")
        return redirect("account_home")
    form = MembershipApplicationForm(request.POST or None, request.FILES or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        application = form.save(commit=False)
        application.user = request.user
        application.save()
        messages.success(request, "Your application has been sent for admin review.")
        return redirect("account_home")
    return render(request, "workspace/apply.html", {"form": form})


@member_required
def dashboard(request):
    tasks = Task.objects.select_related("assignee").all()
    announcements = Announcement.objects.select_related("author")[:4]
    context = {
        "tasks": tasks[:6], "announcements": announcements,
        "task_count": tasks.count(), "active_count": tasks.exclude(status=Task.Status.DONE).count(),
        "completed_count": tasks.filter(status=Task.Status.DONE).count(),
        "team_count": MembershipApplication.objects.filter(
            status=MembershipApplication.Status.APPROVED
        ).values("user_id").distinct().count(),
        "today": timezone.localdate(),
    }
    return render(request, "workspace/dashboard.html", context)


@member_required
def update_task_status(request, task_id):
    if request.method != "POST":
        return redirect("dashboard")
    task = get_object_or_404(Task, pk=task_id)
    if task.status == Task.Status.DONE:
        task.status = Task.Status.TODO
    else:
        task.status = Task.Status.DONE
    task.save(update_fields=["status"])
    messages.success(request, f'“{task.title}” marked {task.get_status_display().lower()}.')
    return redirect("dashboard")


def manifest(request):
    return JsonResponse({
        "name": "SafetyFund Workspace", "short_name": "SafetyFund", "start_url": "/",
        "scope": "/", "display": "standalone", "background_color": "#f6f7f5",
        "theme_color": "#173f35", "icons": [
            {"src": "/brand-logo.jpg", "sizes": "640x640", "type": "image/jpeg", "purpose": "any"}
        ],
    })


def service_worker(request):
    script = """const CACHE = 'safetyfund-shell-v4';
self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(caches.open(CACHE).then(cache => Promise.allSettled([
    '/app.css', '/brand-logo.jpg', '/static/workspace/app.js', '/static/workspace/icon.svg'
  ].map(asset => cache.add(asset)))));
});
self.addEventListener('activate', event => event.waitUntil(
  caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('safetyfund-shell-') && key !== CACHE).map(key => caches.delete(key))))
    .then(() => self.clients.claim())
));
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET' || new URL(event.request.url).origin !== self.location.origin) return;
  const path = new URL(event.request.url).pathname;
  if (path === '/app.css' || path === '/brand-logo.jpg' || path.startsWith('/static/')) event.respondWith(
    fetch(event.request).then(response => {
      if (response.ok) caches.open(CACHE).then(cache => cache.put(event.request, response.clone()));
      return response;
    }).catch(() => caches.match(event.request, {ignoreSearch: true}))
  );
});
"""
    response = HttpResponse(script, content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    return response
