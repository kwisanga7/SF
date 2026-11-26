from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import FileResponse, Http404
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from .forms import DepositReviewAdminForm, LoanReviewAdminForm, RepaymentReviewAdminForm
from .models import Announcement, ContactInquiry, FinanceRequestStatus, MemberDeposit, MemberLoan, MemberLoanRepayment, MembershipApplication, MembershipApplicationHistory, Task, TeamMember


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
    change_list_template = "admin/workspace/membershipapplication/change_list.html"
    list_display = ("full_name", "user", "payment_method", "status", "submitted_at", "reviewed_by", "reviewed_at", "dashboard_review")
    list_filter = ("status", "submitted_at")
    search_fields = ("full_name", "id_number", "phone_number", "email", "user__username", "motivation")
    exclude = ("proof_of_payment",)
    readonly_fields = ("user", "full_name", "id_number", "phone_number", "email", "motivation", "payment_method", "payment_reference", "proof_download", "submitted_at", "status", "review_note", "reviewed_by", "reviewed_at", "dashboard_review")
    fields = ("dashboard_review", "user", "full_name", "id_number", "phone_number", "email", "motivation", "payment_method", "payment_reference", "proof_download", "submitted_at", "status", "review_note", "reviewed_by", "reviewed_at")

    class HistoryInline(admin.TabularInline):
        model = MembershipApplicationHistory
        extra = 0
        can_delete = False
        fields = ("created_at", "actor", "action", "note")
        readonly_fields = fields

    inlines = (HistoryInline,)

    @admin.display(description="Review in SafetyFund dashboard")
    def dashboard_review(self, obj):
        if not obj:
            return "Save the application before opening the review dashboard."
        url = reverse("management_review_application", args=[obj.pk])
        return format_html('<a href="{}">Open application review</a>', url)

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
        old_status = form.initial.get("status") if change else None
        status_changed = change and old_status != obj.status
        if status_changed and obj.status != MembershipApplication.Status.PENDING:
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        elif obj.status == MembershipApplication.Status.PENDING:
            obj.reviewed_by = None
            obj.reviewed_at = None
        super().save_model(request, obj, form, change)
        if not change:
            MembershipApplicationHistory.objects.create(
                application=obj, actor=request.user, action=MembershipApplicationHistory.Action.SUBMITTED,
            )
        elif status_changed:
            history_action = {
                MembershipApplication.Status.APPROVED: MembershipApplicationHistory.Action.APPROVED,
                MembershipApplication.Status.REJECTED: MembershipApplicationHistory.Action.REJECTED,
                MembershipApplication.Status.NEEDS_INFO: MembershipApplicationHistory.Action.INFO_REQUESTED,
            }.get(obj.status)
            if history_action:
                MembershipApplicationHistory.objects.create(
                    application=obj, actor=request.user, action=history_action, note=obj.review_note,
                )


@admin.register(MembershipApplicationHistory)
class MembershipApplicationHistoryAdmin(admin.ModelAdmin):
    list_display = ("application", "action", "actor", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("application__full_name", "application__user__username", "note")
    readonly_fields = ("application", "actor", "action", "note", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class FinanceProofAdminMixin:
    proof_field = "proof_of_payment"

    def get_urls(self):
        custom_urls = [
            path("<path:object_id>/proof/", self.admin_site.admin_view(self.download_finance_proof), name=f"{self.opts.app_label}_{self.opts.model_name}_proof"),
        ]
        return custom_urls + super().get_urls()

    @admin.display(description="Payment proof")
    def proof_download(self, obj):
        if not obj or not getattr(obj, self.proof_field):
            return "No proof uploaded"
        url = reverse(f"admin:{self.opts.app_label}_{self.opts.model_name}_proof", args=[obj.pk])
        return format_html('<a href="{}">Download proof securely</a>', url)

    def download_finance_proof(self, request, object_id):
        record = self.get_object(request, object_id)
        proof = getattr(record, self.proof_field, None) if record else None
        if not record or not proof:
            raise Http404
        if not self.has_view_permission(request, record):
            raise PermissionDenied
        extension = proof.name.rsplit(".", 1)[-1].lower()
        response = FileResponse(proof.open("rb"), content_type="application/octet-stream")
        response["Content-Disposition"] = f'attachment; filename="safetyfund-{self.opts.model_name}-{record.pk}-proof.{extension}"'
        response["X-Content-Type-Options"] = "nosniff"
        return response

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def record_review(self, request, obj, form, change):
        old_status = form.initial.get("status") if change else None
        if change and old_status != obj.status:
            if old_status != FinanceRequestStatus.PENDING:
                from django.core.exceptions import ValidationError
                raise ValidationError("A reviewed finance request cannot be reopened or changed to another decision.")
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        elif obj.status == FinanceRequestStatus.PENDING:
            obj.reviewed_by = None
            obj.reviewed_at = None
        super().save_model(request, obj, form, change)


@admin.register(MemberDeposit)
class MemberDepositAdmin(FinanceProofAdminMixin, admin.ModelAdmin):
    form = DepositReviewAdminForm
    list_display = ("member", "contribution_month", "share_count", "amount", "payment_method", "status", "submitted_at", "finance_review_link", "reviewed_by", "reviewed_at")
    list_filter = ("status", "payment_method", "submitted_at")
    search_fields = ("member__username", "member__email", "member__safetyfund_profile__full_name")
    fields = ("finance_review_link", "member", "contribution_month", "share_count", "share_price", "management_fee_per_share", "amount", "payment_method", "proof_download", "submitted_at", "status", "review_note", "reviewed_by", "reviewed_at")
    readonly_fields = ("finance_review_link", "member", "contribution_month", "share_count", "share_price", "management_fee_per_share", "amount", "payment_method", "proof_download", "submitted_at", "status", "review_note", "reviewed_by", "reviewed_at")

    @admin.display(description="Review in workspace")
    def finance_review_link(self, obj):
        if not obj:
            return "Save the deposit before opening its review page."
        return format_html('<a href="{}">Open payment verification</a>', reverse("finance_review_deposit", args=[obj.pk]))

@admin.register(MemberLoan)
class MemberLoanAdmin(admin.ModelAdmin):
    form = LoanReviewAdminForm
    list_display = ("member", "requested_amount", "approved_amount", "status", "submitted_at", "reviewed_by", "reviewed_at")
    list_filter = ("status", "submitted_at")
    search_fields = ("member__username", "member__email", "member__safetyfund_profile__full_name", "purpose")
    fields = ("member", "requested_amount", "approved_amount", "purpose", "submitted_at", "status", "review_note", "reviewed_by", "reviewed_at")
    readonly_fields = ("member", "requested_amount", "purpose", "submitted_at", "reviewed_by", "reviewed_at")

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.status != FinanceRequestStatus.PENDING:
            fields.extend(("status", "approved_amount"))
        return fields

    def save_model(self, request, obj, form, change):
        old_status = form.initial.get("status") if change else None
        if change and old_status != obj.status and old_status != FinanceRequestStatus.PENDING:
            from django.core.exceptions import ValidationError
            raise ValidationError("A reviewed loan request cannot be reopened or changed to another decision.")
        if obj.status == FinanceRequestStatus.APPROVED and obj.approved_amount is None:
            obj.approved_amount = obj.requested_amount
        if change and old_status != obj.status:
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        elif obj.status == FinanceRequestStatus.PENDING:
            obj.reviewed_by = None
            obj.reviewed_at = None
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False


@admin.register(MemberLoanRepayment)
class MemberLoanRepaymentAdmin(FinanceProofAdminMixin, admin.ModelAdmin):
    form = RepaymentReviewAdminForm
    list_display = ("loan", "member_name", "amount", "payment_method", "status", "submitted_at", "reviewed_by", "reviewed_at")
    list_filter = ("status", "payment_method", "submitted_at")
    search_fields = ("loan__member__username", "loan__member__email", "loan__member__safetyfund_profile__full_name")
    fields = ("loan", "amount", "payment_method", "proof_download", "submitted_at", "status", "review_note", "reviewed_by", "reviewed_at")
    readonly_fields = ("loan", "amount", "payment_method", "proof_download", "submitted_at", "reviewed_by", "reviewed_at")

    @admin.display(description="Member")
    def member_name(self, obj):
        profile = getattr(obj.loan.member, "safetyfund_profile", None)
        return (profile.full_name if profile else "") or obj.loan.member.get_username()

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.status != FinanceRequestStatus.PENDING:
            fields.append("status")
        return fields

    def save_model(self, request, obj, form, change):
        old_status = form.initial.get("status") if change else None
        if change and old_status == FinanceRequestStatus.PENDING and obj.status == FinanceRequestStatus.APPROVED:
            from django.core.exceptions import ValidationError
            with transaction.atomic():
                loan = MemberLoan.objects.select_for_update().get(pk=obj.loan_id)
                if loan.status != FinanceRequestStatus.APPROVED or obj.amount > loan.outstanding_balance:
                    raise ValidationError("This repayment is greater than the currently outstanding approved loan balance.")
                self.record_review(request, obj, form, change)
            return
        self.record_review(request, obj, form, change)
