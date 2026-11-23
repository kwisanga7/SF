from django.contrib import admin
from .models import Announcement, ContactInquiry, Task, TeamMember


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "assignee", "due_date")
    list_filter = ("status", "due_date")
    search_fields = ("title", "description")


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "published_at", "is_public")
    list_filter = ("is_public",)
    search_fields = ("title", "body")


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "sort_order", "is_published")
    list_filter = ("is_published",)
    search_fields = ("name", "role", "bio")


@admin.register(ContactInquiry)
class ContactInquiryAdmin(admin.ModelAdmin):
    list_display = ("subject", "name", "email", "submitted_at", "is_read")
    list_filter = ("is_read", "submitted_at")
    search_fields = ("name", "email", "subject", "message")
    readonly_fields = ("name", "email", "subject", "message", "submitted_at")
