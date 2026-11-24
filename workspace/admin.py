from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.urls import path, reverse
from django.utils.html import format_html
from .models import Announcement, ContactInquiry, MembershipApplication, Task, TeamMember


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


@admin.register(MembershipApplication)
class MembershipApplicationAdmin(admin.ModelAdmin):
    list_display = ("full_name", "user", "payment_method", "status", "submitted_at", "reviewed_by", "reviewed_at")
    list_filter = ("status", "submitted_at")
    search_fields = ("full_name", "id_number", "phone_number", "email", "user__username", "motivation")
    exclude = ("proof_of_payment",)
    readonly_fields = ("user", "full_name", "id_number", "phone_number", "email", "motivation", "payment_method", "payment_reference", "proof_download", "submitted_at", "reviewed_by", "reviewed_at")
    fields = ("user", "full_name", "id_number", "phone_number", "email", "motivation", "payment_method", "payment_reference", "proof_download", "submitted_at", "status", "review_note", "reviewed_by", "reviewed_at")

    def get_urls(self):
        custom_urls = [
            path("<int:object_id>/proof/", self.admin_site.admin_view(self.download_proof), name="workspace_membershipapplication_proof"),
        ]
        return custom_urls + super().get_urls()

    @admin.display(description="Proof of payment")
    def proof_download(self, obj):
        if not obj or not obj.proof_of_payment:
            return "No proof uploaded"
        url = reverse("admin:workspace_membershipapplication_proof", args=[obj.pk])
        return format_html('<a href="{}">Download proof securely</a>', url)

    def download_proof(self, request, object_id):
        application = self.get_object(request, object_id)
        if application is None or not application.proof_of_payment:
            raise Http404
        if not self.has_view_permission(request, application):
            raise PermissionDenied
        extension = application.proof_of_payment.name.rsplit(".", 1)[-1].lower()
        response = FileResponse(application.proof_of_payment.open("rb"), content_type="application/octet-stream")
        response["Content-Disposition"] = f'attachment; filename="safetyfund-membership-proof-{application.pk}.{extension}"'
        response["X-Content-Type-Options"] = "nosniff"
        return response

    def save_model(self, request, obj, form, change):
        from django.utils import timezone
        if change and "status" in form.changed_data and obj.status != MembershipApplication.Status.PENDING:
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        elif obj.status == MembershipApplication.Status.PENDING:
            obj.reviewed_by = None
            obj.reviewed_at = None
        super().save_model(request, obj, form, change)
