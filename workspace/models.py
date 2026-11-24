from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.validators import FileExtensionValidator
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
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    class PaymentMethod(models.TextChoices):
        MOBILE_MONEY = "mobile_money", "Mobile money"
        BANK_TRANSFER = "bank_transfer", "Bank transfer"

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
