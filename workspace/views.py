from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import ContactForm, RegistrationForm
from .models import Announcement, Task, TeamMember


def public_home(request):
    return render(request, "workspace/home.html", {"today": timezone.localdate()})


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
        return redirect("dashboard")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("dashboard")
    return render(request, "workspace/register.html", {"form": form})


@login_required
def dashboard(request):
    tasks = Task.objects.select_related("assignee").all()
    announcements = Announcement.objects.select_related("author")[:4]
    context = {
        "tasks": tasks[:6], "announcements": announcements,
        "task_count": tasks.count(), "active_count": tasks.exclude(status=Task.Status.DONE).count(),
        "completed_count": tasks.filter(status=Task.Status.DONE).count(),
        "team_count": request.user.__class__.objects.count(),
        "today": timezone.localdate(),
    }
    return render(request, "workspace/dashboard.html", context)


@login_required
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
            {"src": "/static/workspace/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"}
        ],
    })


def service_worker(request):
    script = """const CACHE = 'safetyfund-shell-v1';
self.addEventListener('install', event => event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(['/static/workspace/app.css','/static/workspace/app.js','/static/workspace/icon.svg']))));
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET' || new URL(event.request.url).origin !== self.location.origin) return;
  if (new URL(event.request.url).pathname.startsWith('/static/')) event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request)));
});
"""
    response = HttpResponse(script, content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    return response
