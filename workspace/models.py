from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils.deconstruct import deconstructible
from pathlib import Path
from uuid import uuid4


@deconstructible
class PrivateProofStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(location=settings.PRIVATE_MEDIA_ROOT, base_url="/private-membership-proof/")


private_proof_storage = PrivateProofStorage()


def membership_proof_path(instance, filename):
    extension = Path(filename).suffix.lower()
    return f"membership-proofs/{uuid4().hex}{extension}"


def finance_proof_path(instance, filename):
    extension = Path(filename).suffix.lower()
    return f"finance-proofs/{uuid4().hex}{extension}"


class FinancePaymentMethod(models.TextChoices):
    MOBILE_MONEY = "mobile_money", "MoMoPay — 050456"
    BANK_TRANSFER = "bank_transfer", "Equity Bank — 4004201431267"


class FinanceRequestStatus(models.TextChoices):
    PENDING = "pending", "Pending review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class MemberDeposit(models.Model):
    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="safetyfund_deposits")
    amount = models.DecimalField("Amount (RWF)", max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    share_count = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(4)])
    contribution_month = models.DateField(null=True, blank=True, help_text="First day of the contribution month.")
    share_price = models.DecimalField("Share value per share (RWF)", max_digits=10, decimal_places=2, default=5000)
    management_fee_per_share = models.DecimalField("Management and development fee per share (RWF)", max_digits=10, decimal_places=2, default=1000)
    payment_method = models.CharField(max_length=20, choices=FinancePaymentMethod.choices)
    proof_of_payment = models.FileField(upload_to=finance_proof_path, storage=private_proof_storage)
    status = models.CharField(max_length=12, choices=FinanceRequestStatus.choices, default=FinanceRequestStatus.PENDING)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_safetyfund_deposits")
    review_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-submitted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["member", "contribution_month"],
                condition=Q(contribution_month__isnull=False, status__in=["pending", "approved"]),
                name="one_active_monthly_share_contribution_per_member",
            ),
            models.CheckConstraint(
                condition=Q(share_count__isnull=True) | Q(share_count__gte=1, share_count__lte=4),
                name="share_contribution_quantity_between_1_and_4",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.share_count is not None:
            self.amount = self.share_count * (self.share_price + self.management_fee_per_share)
            if kwargs.get("update_fields") is not None:
                kwargs["update_fields"] = set(kwargs["update_fields"]) | {"amount"}
        super().save(*args, **kwargs)

    @property
    def share_capital(self):
        if self.share_count is None:
            return 0
        return self.share_count * self.share_price

    @property
    def management_fee_total(self):
        if self.share_count is None:
            return 0
        return self.share_count * self.management_fee_per_share

    def __str__(self):
        return f"Deposit {self.amount} — {self.member} ({self.get_status_display()})"


class MemberLoan(models.Model):
    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="safetyfund_loans")
    requested_amount = models.DecimalField("Requested amount (RWF)", max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    approved_amount = models.DecimalField("Approved amount (RWF)", max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0.01)])
    purpose = models.TextField(max_length=1200)
    status = models.CharField(max_length=12, choices=FinanceRequestStatus.choices, default=FinanceRequestStatus.PENDING)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_safetyfund_loans")
    review_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"Loan request {self.requested_amount} — {self.member} ({self.get_status_display()})"

    @property
    def outstanding_balance(self):
        if self.status != FinanceRequestStatus.APPROVED or self.approved_amount is None:
            return 0
        repaid = self.repayments.filter(status=FinanceRequestStatus.APPROVED).aggregate(total=models.Sum("amount"))["total"] or 0
        return max(self.approved_amount - repaid, 0)


class MemberLoanRepayment(models.Model):
    loan = models.ForeignKey(MemberLoan, on_delete=models.CASCADE, related_name="repayments")
    amount = models.DecimalField("Amount (RWF)", max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    payment_method = models.CharField(max_length=20, choices=FinancePaymentMethod.choices)
    proof_of_payment = models.FileField(upload_to=finance_proof_path, storage=private_proof_storage)
    status = models.CharField(max_length=12, choices=FinanceRequestStatus.choices, default=FinanceRequestStatus.PENDING)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_safetyfund_repayments")
    review_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"Repayment {self.amount} — loan #{self.loan_id} ({self.get_status_display()})"


class FinanceNotification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="safetyfund_finance_notifications")
    deposit = models.ForeignKey(MemberDeposit, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications")
    title = models.CharField(max_length=180)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} — {self.recipient}"


class Task(models.Model):
    class Status(models.TextChoices):
        TODO = "todo", "To do"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"

    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    due_date = models.DateField(null=True, blank=True)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="safetyfund_tasks")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_safetyfund_tasks")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_date", "-created_at"]

    def __str__(self):
        return self.title


class Announcement(models.Model):
    title = models.CharField(max_length=180)
    body = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    published_at = models.DateTimeField(auto_now_add=True)
    is_public = models.BooleanField(default=False, help_text="Show this update on the public announcements page.")

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return self.title


class TeamMember(models.Model):
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=120)
    bio = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return f"{self.name} — {self.role}"


class ContactInquiry(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    subject = models.CharField(max_length=180)
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.subject} — {self.name}"


class MembershipApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        NEEDS_INFO = "needs_info", "Additional information requested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        REVOKED = "revoked", "Membership revoked"

    class PaymentMethod(models.TextChoices):
        MOBILE_MONEY = "mobile_money", "MoMoPay — 050456"
        BANK_TRANSFER = "bank_transfer", "Equity Bank — 4004201431267"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="membership_applications")
    full_name = models.CharField(max_length=180, blank=True, default="")
    id_number = models.CharField(max_length=64, blank=True, default="")
    phone_number = models.CharField(max_length=40, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    motivation = models.TextField(help_text="Why would you like to become a SafetyFund member?")
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, blank=True, default="")
    payment_reference = models.CharField(max_length=120, blank=True)
    proof_of_payment = models.FileField(
        upload_to=membership_proof_path,
        storage=private_proof_storage,
        validators=[FileExtensionValidator(["pdf", "jpg", "jpeg", "png"])],
        blank=True,
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_membership_applications")
    review_note = models.TextField(blank=True, help_text="Optional note visible to the applicant.")

    class Meta:
        ordering = ["-submitted_at"]
        constraints = [
            models.UniqueConstraint(fields=["user"], condition=Q(status="pending"), name="one_pending_membership_application_per_user"),
        ]

    def __str__(self):
        return f"{self.user} — {self.get_status_display()}"


class MembershipApplicationHistory(models.Model):
    class Action(models.TextChoices):
        SUBMITTED = "submitted", "Application submitted"
        APPROVED = "approved", "Application approved"
        REJECTED = "rejected", "Application rejected"
        INFO_REQUESTED = "info_requested", "Additional information requested"
        INFO_PROVIDED = "info_provided", "Applicant provided information"
        ROLE_CHANGED = "role_changed", "Member role changed"
        PROFILE_UPDATED = "profile_updated", "Member information updated"
        REVOKED = "revoked", "Membership revoked"

    application = models.ForeignKey(MembershipApplication, on_delete=models.CASCADE, related_name="history")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=Action.choices)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]
        verbose_name_plural = "membership application history"

    def __str__(self):
        return f"{self.application_id}: {self.get_action_display()}"


class MemberProfile(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User (not a member)"
        MEMBER = "member", "Member"
        FINANCE = "finance", "Finance"
        SECRETARY = "secretary", "Secretary"
        DEVELOPER = "developer", "Developer"
        MARKETING = "marketing", "Marketing"
        ADMIN = "admin", "Admin"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="safetyfund_profile")
    full_name = models.CharField(max_length=180, blank=True)
    id_number = models.CharField(max_length=64, blank=True)
    phone_number = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="updated_safetyfund_profiles")

    class Meta:
        ordering = ["full_name", "user__username"]

    def __str__(self):
        return self.full_name or self.user.get_username()
