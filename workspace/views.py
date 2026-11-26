from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Exists, OuterRef, Q
from django.db.models import Sum
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from pathlib import Path
from decimal import Decimal

from .decorators import finance_reviewer_required, member_required
from .forms import ApplicantInformationForm, ContactForm, FinanceDepositDecisionForm, MemberDepositForm, MemberLoanRepaymentForm, MemberLoanRequestForm, MemberProfileForm, MembershipApplicationForm, MembershipDecisionForm, RegistrationForm
from .models import Announcement, ContactInquiry, FinanceNotification, FinanceRequestStatus, MemberDeposit, MemberLoan, MemberLoanRepayment, MembershipApplication, MembershipApplicationHistory, MemberProfile, Task, TeamMember


def public_home(request):
    return render(request, "workspace/index.html", {"today": timezone.localdate()})


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
    if MembershipApplication.objects.filter(
        user=request.user,
        status__in=(MembershipApplication.Status.PENDING, MembershipApplication.Status.NEEDS_INFO),
    ).exists():
        messages.info(request, "Your membership application is already being reviewed.")
        return redirect("account_home")
    form = MembershipApplicationForm(request.POST or None, request.FILES or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        application = form.save(commit=False)
        application.user = request.user
        application.save()
        profile, _ = MemberProfile.objects.get_or_create(
            user=request.user, defaults={"email": request.user.email or ""},
        )
        profile.full_name = application.full_name
        profile.id_number = application.id_number
        profile.phone_number = application.phone_number
        profile.email = application.email
        profile.save(update_fields=["full_name", "id_number", "phone_number", "email", "updated_at"])
        MembershipApplicationHistory.objects.create(
            application=application,
            actor=request.user,
            action=MembershipApplicationHistory.Action.SUBMITTED,
        )
        messages.success(request, "Your application has been sent for admin review.")
        return redirect("account_home")
    return render(request, "workspace/apply.html", {"form": form})


@login_required
def provide_application_information(request, application_id):
    application = get_object_or_404(MembershipApplication, pk=application_id, user=request.user)
    if application.status != MembershipApplication.Status.NEEDS_INFO:
        messages.info(request, "This application is not waiting for additional information.")
        return redirect("account_home")
    form = ApplicantInformationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        response_text = form.cleaned_data["response"]
        MembershipApplicationHistory.objects.create(
            application=application,
            actor=request.user,
            action=MembershipApplicationHistory.Action.INFO_PROVIDED,
            note=response_text,
        )
        application.status = MembershipApplication.Status.PENDING
        application.save(update_fields=["status"])
        messages.success(request, "Your additional information has been sent to the reviewer.")
        return redirect("account_home")
    return render(request, "workspace/application_response.html", {"application": application, "form": form})


def safetyfund_admin_group():
    safetyfund_admin_group, _created = Group.objects.get_or_create(name="SafetyFund Administrators")
    workspace_permissions = Permission.objects.filter(
        content_type__app_label="workspace",
    ).filter(
        Q(codename__startswith="view_")
        | Q(codename__startswith="add_")
        | Q(codename__startswith="change_"),
    )
    permission_ids = set(workspace_permissions.values_list("pk", flat=True))
    if permission_ids != set(safetyfund_admin_group.permissions.values_list("pk", flat=True)):
        safetyfund_admin_group.permissions.set(permission_ids)
    return safetyfund_admin_group


@staff_member_required(login_url="login")
def management_dashboard(request):
    safetyfund_admins = safetyfund_admin_group()
    for admin_profile in MemberProfile.objects.filter(
        role=MemberProfile.Role.ADMIN, user__is_staff=True, user__is_superuser=False,
    ).select_related("user"):
        admin_profile.user.groups.add(safetyfund_admins)
    today = timezone.localdate()
    this_month = today.replace(day=1)
    approved_member_ids = MembershipApplication.objects.filter(
        status=MembershipApplication.Status.APPROVED,
    ).values("user_id").distinct()
    approved_member_count = MembershipApplication.objects.filter(
        status=MembershipApplication.Status.APPROVED,
    ).values("user_id").distinct().count()
    approved_monthly = MemberDeposit.objects.filter(
        contribution_month=this_month, status=FinanceRequestStatus.APPROVED,
    ).values("member_id").distinct().count()
    pending_monthly = MemberDeposit.objects.filter(
        contribution_month=this_month, status=FinanceRequestStatus.PENDING,
    ).values("member_id").distinct().count()
    submitted_member_ids = MemberDeposit.objects.filter(
        contribution_month=this_month,
        status__in=(FinanceRequestStatus.APPROVED, FinanceRequestStatus.PENDING),
    ).values("member_id").distinct()
    missing_contribution_profiles = MemberProfile.objects.filter(
        user_id__in=approved_member_ids,
    ).exclude(user_id__in=submitted_member_ids).select_related("user")[:6]
    overdue_tasks = Task.objects.filter(
        due_date__lt=today,
    ).exclude(status=Task.Status.DONE).select_related("assignee").order_by("due_date")[:6]

    approved_share_rows = MemberDeposit.objects.filter(
        status=FinanceRequestStatus.APPROVED, share_count__isnull=False,
    ).values_list("share_count", "share_price", "management_fee_per_share")
    share_capital_total = sum(
        (Decimal(shares) * price for shares, price, _fee in approved_share_rows), Decimal("0.00"),
    )
    management_fees_total = sum(
        (Decimal(shares) * fee for shares, _price, fee in approved_share_rows), Decimal("0.00"),
    )
    approved_loan_total = MemberLoan.objects.filter(
        status=FinanceRequestStatus.APPROVED,
    ).aggregate(total=Sum("approved_amount"))["total"] or Decimal("0.00")
    approved_repayment_total = MemberLoanRepayment.objects.filter(
        status=FinanceRequestStatus.APPROVED,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    counts = {
        "pending_applications": MembershipApplication.objects.filter(status=MembershipApplication.Status.PENDING).count(),
        "needs_info_applications": MembershipApplication.objects.filter(status=MembershipApplication.Status.NEEDS_INFO).count(),
        "pending_deposits": MemberDeposit.objects.filter(status=FinanceRequestStatus.PENDING).count(),
        "pending_loans": MemberLoan.objects.filter(status=FinanceRequestStatus.PENDING).count(),
        "pending_repayments": MemberLoanRepayment.objects.filter(status=FinanceRequestStatus.PENDING).count(),
        "active_members": approved_member_count,
        "monthly_paid": approved_monthly,
        "monthly_pending": pending_monthly,
        "monthly_missing": max(approved_member_count - approved_monthly - pending_monthly, 0),
        "unread_messages": ContactInquiry.objects.filter(is_read=False).count(),
        "announcements": Announcement.objects.count(),
        "team_profiles": TeamMember.objects.count(),
        "tasks": Task.objects.count(),
        "overdue_tasks": Task.objects.filter(due_date__lt=today).exclude(status=Task.Status.DONE).count(),
    }
    recent_activity = []
    for application in MembershipApplication.objects.select_related("user").order_by("-submitted_at")[:4]:
        recent_activity.append({
            "when": application.submitted_at, "category": "Membership",
            "title": application.full_name or application.user.get_username(),
            "status": application.get_status_display(),
            "href": reverse("management_review_application", args=[application.pk]),
        })
    for deposit in MemberDeposit.objects.select_related("member").order_by("-submitted_at")[:4]:
        profile = MemberProfile.objects.filter(user=deposit.member).only("full_name").first()
        recent_activity.append({
            "when": deposit.submitted_at, "category": "Share deposit",
            "title": f"{profile.full_name if profile and profile.full_name else deposit.member.get_username()} · RWF {deposit.amount:,.0f}",
            "status": deposit.get_status_display(),
            "href": reverse("finance_review_deposit", args=[deposit.pk]),
        })
    for loan in MemberLoan.objects.select_related("member").order_by("-submitted_at")[:3]:
        recent_activity.append({
            "when": loan.submitted_at, "category": "Loan request",
            "title": f"{loan.member.get_username()} · RWF {loan.requested_amount:,.0f}",
            "status": loan.get_status_display(),
            "href": reverse("admin:workspace_memberloan_change", args=[loan.pk]),
        })
    for repayment in MemberLoanRepayment.objects.select_related("loan__member").order_by("-submitted_at")[:3]:
        recent_activity.append({
            "when": repayment.submitted_at, "category": "Loan repayment",
            "title": f"{repayment.loan.member.get_username()} · RWF {repayment.amount:,.0f}",
            "status": repayment.get_status_display(),
            "href": reverse("admin:workspace_memberloanrepayment_change", args=[repayment.pk]),
        })
    for inquiry in ContactInquiry.objects.order_by("-submitted_at")[:3]:
        recent_activity.append({
            "when": inquiry.submitted_at, "category": "Contact message",
            "title": inquiry.subject, "status": "Unread" if not inquiry.is_read else "Read",
            "href": reverse("admin:workspace_contactinquiry_change", args=[inquiry.pk]),
        })
    recent_activity.sort(key=lambda activity: activity["when"], reverse=True)
    return render(request, "workspace/management_dashboard.html", {
        "counts": counts, "today": today, "this_month": this_month,
        "share_capital_total": share_capital_total,
        "management_fees_total": management_fees_total,
        "loan_balance_total": max(approved_loan_total - approved_repayment_total, Decimal("0.00")),
        "missing_contribution_profiles": missing_contribution_profiles,
        "overdue_tasks": overdue_tasks,
        "recent_activity": recent_activity[:8],
    })


@staff_member_required(login_url="login")
def management_applications(request):
    applications = MembershipApplication.objects.select_related("user", "reviewed_by").all()
    status_filter = request.GET.get("status", "")
    if status_filter in MembershipApplication.Status.values:
        applications = applications.filter(status=status_filter)
    search = request.GET.get("q", "").strip()
    if search:
        applications = applications.filter(
            Q(full_name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone_number__icontains=search)
            | Q(user__username__icontains=search)
        )
    counts = {
        status: MembershipApplication.objects.filter(status=status).count()
        for status, _label in MembershipApplication.Status.choices
    }
    return render(request, "workspace/management_applications.html", {
        "applications": applications, "counts": counts,
        "status_filter": status_filter, "search": search,
        "statuses": MembershipApplication.Status.choices,
        "active_nav": "dashboard",
    })


@staff_member_required(login_url="login")
def review_application(request, application_id):
    application = get_object_or_404(
        MembershipApplication.objects.select_related("user", "reviewed_by").prefetch_related("history__actor"),
        pk=application_id,
    )
    form = MembershipDecisionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        action = form.cleaned_data["action"]
        note = form.cleaned_data["note"].strip()
        application.status = action
        application.review_note = note
        application.reviewed_by = request.user
        application.reviewed_at = timezone.now()
        application.save(update_fields=["status", "review_note", "reviewed_by", "reviewed_at"])
        if action == MembershipApplication.Status.APPROVED:
            profile, _ = MemberProfile.objects.get_or_create(
                user=application.user, defaults={"email": application.user.email or ""},
            )
            if profile.role == MemberProfile.Role.USER:
                profile.role = MemberProfile.Role.MEMBER
                profile.updated_by = request.user
                profile.save(update_fields=["role", "updated_by", "updated_at"])
        elif action == MembershipApplication.Status.REJECTED:
            profile, _ = MemberProfile.objects.get_or_create(
                user=application.user, defaults={"email": application.user.email or ""},
            )
            if profile.role != MemberProfile.Role.USER and not application.user.is_superuser:
                old_role = profile.get_role_display()
                profile.role = MemberProfile.Role.USER
                profile.updated_by = request.user
                profile.save(update_fields=["role", "updated_by", "updated_at"])
                if not application.user.is_superuser:
                    application.user.is_staff = False
                    application.user.save(update_fields=["is_staff"])
                    safetyfund_admin_group = Group.objects.filter(name="SafetyFund Administrators").first()
                    if safetyfund_admin_group:
                        application.user.groups.remove(safetyfund_admin_group)
                MembershipApplicationHistory.objects.create(
                    application=application, actor=request.user,
                    action=MembershipApplicationHistory.Action.ROLE_CHANGED,
                    note=f"Role changed from {old_role} to User after the application was rejected.",
                )
        history_action = {
            MembershipApplication.Status.APPROVED: MembershipApplicationHistory.Action.APPROVED,
            MembershipApplication.Status.REJECTED: MembershipApplicationHistory.Action.REJECTED,
            MembershipApplication.Status.NEEDS_INFO: MembershipApplicationHistory.Action.INFO_REQUESTED,
        }[action]
        MembershipApplicationHistory.objects.create(
            application=application, actor=request.user, action=history_action, note=note,
        )
        messages.success(request, f"Application marked {application.get_status_display().lower()}.")
        return redirect("management_review_application", application_id=application.pk)
    return render(request, "workspace/management_review.html", {"application": application, "form": form, "active_nav": "dashboard"})


@staff_member_required(login_url="login")
def management_members(request):
    approved_application = MembershipApplication.objects.filter(
        user_id=OuterRef("user_id"), status=MembershipApplication.Status.APPROVED,
    )
    profiles = MemberProfile.objects.select_related("user", "updated_by").annotate(
        has_approved_membership=Exists(approved_application),
    )
    role_filter = request.GET.get("role", "")
    if role_filter in MemberProfile.Role.values:
        profiles = profiles.filter(role=role_filter)
    search = request.GET.get("q", "").strip()
    if search:
        profiles = profiles.filter(
            Q(full_name__icontains=search)
            | Q(id_number__icontains=search)
            | Q(phone_number__icontains=search)
            | Q(email__icontains=search)
            | Q(user__username__icontains=search)
        )
    counts = {role: MemberProfile.objects.filter(role=role).count() for role, _label in MemberProfile.Role.choices}
    return render(request, "workspace/management_members.html", {
        "profiles": profiles, "role_filter": role_filter, "search": search,
        "roles": MemberProfile.Role.choices, "counts": counts, "active_nav": "dashboard",
    })


@staff_member_required(login_url="login")
def management_edit_member(request, user_id):
    profile = get_object_or_404(MemberProfile.objects.select_related("user"), user_id=user_id)
    if profile.user.is_superuser:
        raise PermissionDenied("Superuser accounts cannot be changed from member management.")
    old_values = {field: getattr(profile, field) for field in ("full_name", "id_number", "phone_number", "email", "role")}
    form = MemberProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            updated = form.save(commit=False)
            updated.updated_by = request.user
            updated.save()
            account = updated.user
            account.email = updated.email
            role_changed = old_values["role"] != updated.role
            if updated.role == MemberProfile.Role.ADMIN:
                account.is_staff = True
            elif old_values["role"] == MemberProfile.Role.ADMIN:
                account.is_staff = False
            account.save(update_fields=["email", "is_staff"])
            if updated.role == MemberProfile.Role.ADMIN and not account.is_superuser:
                account.groups.add(safetyfund_admin_group())
            elif old_values["role"] == MemberProfile.Role.ADMIN:
                existing_admin_group = Group.objects.filter(name="SafetyFund Administrators").first()
                if existing_admin_group:
                    account.groups.remove(existing_admin_group)

            latest_application = MembershipApplication.objects.filter(user=account).first()
            if role_changed and updated.role == MemberProfile.Role.USER:
                active_application = MembershipApplication.objects.filter(
                    user=account, status=MembershipApplication.Status.APPROVED
                ).first()
                if active_application:
                    active_application.status = MembershipApplication.Status.REVOKED
                    active_application.reviewed_by = request.user
                    active_application.reviewed_at = timezone.now()
                    active_application.review_note = "Membership access was revoked by an administrator; this account is now a user."
                    active_application.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_note"])
                    MembershipApplicationHistory.objects.create(
                        application=active_application, actor=request.user,
                        action=MembershipApplicationHistory.Action.REVOKED,
                        note=active_application.review_note,
                    )
            if latest_application and role_changed and updated.role != MemberProfile.Role.USER:
                MembershipApplicationHistory.objects.create(
                    application=latest_application, actor=request.user,
                    action=MembershipApplicationHistory.Action.ROLE_CHANGED,
                    note=f"Role changed from {MemberProfile.Role(old_values['role']).label} to {updated.get_role_display()}.",
                )
            if latest_application and any(old_values[field] != getattr(updated, field) for field in ("full_name", "id_number", "phone_number", "email")):
                MembershipApplicationHistory.objects.create(
                    application=latest_application, actor=request.user,
                    action=MembershipApplicationHistory.Action.PROFILE_UPDATED,
                    note="Member contact or identity information was updated by an administrator.",
                )
        messages.success(request, f"Saved changes for {updated.full_name or account.username}.")
        return redirect("management_edit_member", user_id=account.pk)
    application = MembershipApplication.objects.filter(user=profile.user).first()
    return render(request, "workspace/management_edit_member.html", {"profile": profile, "form": form, "application": application, "active_nav": "dashboard"})


@staff_member_required(login_url="login")
def management_proof(request, application_id):
    application = get_object_or_404(MembershipApplication, pk=application_id)
    if not application.proof_of_payment:
        from django.http import Http404
        raise Http404
    extension = application.proof_of_payment.name.rsplit(".", 1)[-1].lower()
    response = FileResponse(application.proof_of_payment.open("rb"), content_type="application/octet-stream")
    response["Content-Disposition"] = f'attachment; filename="safetyfund-membership-proof-{application.pk}.{extension}"'
    response["X-Content-Type-Options"] = "nosniff"
    return response


@member_required
def dashboard(request):
    tasks = Task.objects.select_related("assignee").all()
    announcements = Announcement.objects.select_related("author")[:4]
    context = {
        "tasks": tasks[:6], "announcements": announcements,
        "active_nav": "dashboard",
        "task_count": tasks.count(), "active_count": tasks.exclude(status=Task.Status.DONE).count(),
        "completed_count": tasks.filter(status=Task.Status.DONE).count(),
        "team_count": MembershipApplication.objects.filter(
            status=MembershipApplication.Status.APPROVED
        ).values("user_id").distinct().count(),
        "today": timezone.localdate(),
    }
    approved_contributions = list(MemberDeposit.objects.filter(
        member=request.user, status=FinanceRequestStatus.APPROVED,
    ))
    month_start = timezone.localdate().replace(day=1)
    this_month_contribution = MemberDeposit.objects.filter(
        member=request.user, contribution_month=month_start,
        status__in=(FinanceRequestStatus.PENDING, FinanceRequestStatus.APPROVED),
    ).first()
    was_rejected_this_month = MemberDeposit.objects.filter(
        member=request.user, contribution_month=month_start, status=FinanceRequestStatus.REJECTED,
    ).exists()
    if this_month_contribution and this_month_contribution.status == FinanceRequestStatus.APPROVED:
        monthly_contribution_status = "Paid and approved"
    elif this_month_contribution:
        monthly_contribution_status = "Awaiting admin review"
    elif was_rejected_this_month:
        monthly_contribution_status = "Rejected — resubmission needed"
    else:
        monthly_contribution_status = "Not submitted"
    context["finance"] = {
        "share_capital_total": sum((deposit.share_capital for deposit in approved_contributions), Decimal("0.00")),
        "management_fee_total": sum((deposit.management_fee_total for deposit in approved_contributions), Decimal("0.00")),
        "this_month": this_month_contribution,
        "month_start": month_start,
        "monthly_status": monthly_contribution_status,
        "monthly_due": this_month_contribution.amount if this_month_contribution else None,
        "loans_total": MemberLoan.objects.filter(
            member=request.user, status=FinanceRequestStatus.APPROVED,
        ).aggregate(total=Sum("approved_amount"))["total"] or Decimal("0.00"),
        "repayments_total": MemberLoanRepayment.objects.filter(
            loan__member=request.user, status=FinanceRequestStatus.APPROVED,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00"),
        "pending_count": (
            MemberDeposit.objects.filter(member=request.user, status=FinanceRequestStatus.PENDING).count()
            + MemberLoan.objects.filter(member=request.user, status=FinanceRequestStatus.PENDING).count()
            + MemberLoanRepayment.objects.filter(loan__member=request.user, status=FinanceRequestStatus.PENDING).count()
        ),
        "deposits": MemberDeposit.objects.filter(member=request.user).select_related("reviewed_by")[:5],
        "loans": MemberLoan.objects.filter(member=request.user).prefetch_related("repayments")[:5],
        "repayments": MemberLoanRepayment.objects.filter(loan__member=request.user).select_related("loan")[:5],
    }
    context["finance"]["loan_balance"] = sum(
        (loan.outstanding_balance for loan in MemberLoan.objects.filter(
            member=request.user, status=FinanceRequestStatus.APPROVED,
        ).prefetch_related("repayments")),
        Decimal("0.00"),
    )
    return render(request, "workspace/dashboard.html", context)


@member_required
def finance_deposit(request):
    contribution_month = timezone.localdate().replace(day=1)
    if MemberDeposit.objects.filter(
        member=request.user, contribution_month=contribution_month,
        status__in=(FinanceRequestStatus.PENDING, FinanceRequestStatus.APPROVED),
    ).exists():
        messages.info(request, "Your share contribution for this month is already submitted or approved.")
        return redirect("dashboard")
    form = MemberDepositForm(
        request.POST or None, request.FILES or None,
        member=request.user, contribution_month=contribution_month,
    )
    if request.method == "POST" and form.is_valid():
        deposit = form.save(commit=False)
        deposit.member = request.user
        deposit.contribution_month = contribution_month
        deposit.save()
        reviewers = get_user_model().objects.filter(
            Q(is_staff=True) | Q(safetyfund_profile__role=MemberProfile.Role.FINANCE),
        ).exclude(pk=request.user.pk).distinct()
        member_profile = MemberProfile.objects.filter(user=request.user).first()
        member_name = (member_profile.full_name if member_profile else "") or request.user.get_username()
        FinanceNotification.objects.bulk_create([
            FinanceNotification(
                recipient=reviewer,
                deposit=deposit,
                title="Monthly share deposit needs verification",
                message=f"{member_name} submitted {deposit.share_count} share(s), totaling RWF {deposit.amount:,.2f}, for {contribution_month:%B %Y}. Verify the attached proof and approve or reject it.",
            )
            for reviewer in reviewers
        ])
        messages.success(request, "Your deposit proof was submitted. It will appear in your balance after admin approval.")
        return redirect("dashboard")
    return render(request, "workspace/finance_form.html", {
        "form": form, "active_nav": "dashboard", "page_title": "Make a deposit",
        "today": timezone.localdate(), "form_title": "Record a deposit",
        "form_intro": "Send your contribution to SafetyFund and upload its payment proof for review.",
        "submit_label": "Submit deposit", "finance_form_type": "deposit",
        "contribution_month": contribution_month,
    })


@member_required
def finance_loan_request(request):
    form = MemberLoanRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        loan = form.save(commit=False)
        loan.member = request.user
        loan.save()
        messages.success(request, "Your loan request was submitted for admin review.")
        return redirect("dashboard")
    return render(request, "workspace/finance_form.html", {
        "form": form, "active_nav": "dashboard", "page_title": "Request a loan",
        "today": timezone.localdate(), "form_title": "Request a loan",
        "form_intro": "Tell us the amount you need and its purpose. An admin will review your request.",
        "submit_label": "Submit loan request", "finance_form_type": "loan",
    })


@member_required
def finance_loan_repayment(request):
    form = MemberLoanRepaymentForm(request.POST or None, request.FILES or None, member=request.user)
    if request.method == "POST" and form.is_valid():
        repayment = form.save()
        messages.success(request, "Your repayment proof was submitted. Your loan balance will update after admin approval.")
        return redirect("dashboard")
    loans = MemberLoan.objects.filter(
        member=request.user, status=FinanceRequestStatus.APPROVED,
    ).prefetch_related("repayments")
    open_loans = [loan for loan in loans if loan.outstanding_balance > 0]
    return render(request, "workspace/finance_form.html", {
        "form": form, "active_nav": "dashboard", "page_title": "Repay a loan",
        "today": timezone.localdate(), "form_title": "Record a loan repayment",
        "form_intro": "Choose an approved loan, enter the amount paid, and upload proof of payment.",
        "submit_label": "Submit repayment", "finance_form_type": "repayment", "open_loans": open_loans,
    })


@finance_reviewer_required
def finance_review_deposit(request, deposit_id):
    deposit = get_object_or_404(
        MemberDeposit.objects.select_related("member", "reviewed_by"), pk=deposit_id,
    )
    if deposit.member_id == request.user.pk:
        raise PermissionDenied("You cannot review your own deposit.")
    FinanceNotification.objects.filter(
        recipient=request.user, deposit=deposit, read_at__isnull=True,
    ).update(read_at=timezone.now())
    form = FinanceDepositDecisionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            deposit = get_object_or_404(MemberDeposit.objects.select_for_update(), pk=deposit_id)
            if deposit.status != FinanceRequestStatus.PENDING:
                messages.info(request, "This deposit has already been reviewed.")
                return redirect("finance_review_deposit", deposit_id=deposit.pk)
            decision = form.cleaned_data["action"]
            note = form.cleaned_data["note"].strip()
            deposit.status = decision
            deposit.review_note = note
            deposit.reviewed_by = request.user
            deposit.reviewed_at = timezone.now()
            deposit.save(update_fields=["status", "review_note", "reviewed_by", "reviewed_at"])
            FinanceNotification.objects.filter(
                recipient=request.user, deposit=deposit, read_at__isnull=True,
            ).update(read_at=timezone.now())
            member_message = note or f"Your proof for {deposit.contribution_month:%B %Y} was verified and approved."
            FinanceNotification.objects.create(
                recipient=deposit.member,
                deposit=deposit,
                title=f"Your share payment was {deposit.get_status_display().lower()}",
                message=member_message,
            )
        messages.success(request, f"The share payment was {deposit.get_status_display().lower()}.")
        return redirect("finance_review_deposit", deposit_id=deposit.pk)
    return render(request, "workspace/finance_review_deposit.html", {
        "deposit": deposit, "form": form, "active_nav": "notifications",
        "page_title": "Review share payment", "today": timezone.localdate(),
    })


@finance_reviewer_required
def finance_deposit_proof(request, deposit_id):
    deposit = get_object_or_404(MemberDeposit, pk=deposit_id)
    if deposit.member_id == request.user.pk:
        raise PermissionDenied("You cannot review your own deposit.")
    if not deposit.proof_of_payment:
        from django.http import Http404
        raise Http404
    extension = deposit.proof_of_payment.name.rsplit(".", 1)[-1].lower()
    response = FileResponse(deposit.proof_of_payment.open("rb"), content_type="application/octet-stream")
    response["Content-Disposition"] = f'attachment; filename="safetyfund-share-deposit-{deposit.pk}-proof.{extension}"'
    response["X-Content-Type-Options"] = "nosniff"
    return response


@member_required
def workspace_home(request):
    profile, _created = MemberProfile.objects.get_or_create(
        user=request.user, defaults={"email": request.user.email or ""},
    )
    announcements = Announcement.objects.select_related("author")
    return render(request, "workspace/workspace_home.html", {
        "active_nav": "home", "page_title": "Home", "today": timezone.localdate(),
        "profile": profile, "announcement_count": announcements.count(),
        "announcements": announcements[:3],
    })


@member_required
def workspace_notifications(request):
    FinanceNotification.objects.filter(
        recipient=request.user, read_at__isnull=True,
    ).update(read_at=timezone.now())
    finance_notifications = FinanceNotification.objects.filter(
        recipient=request.user,
    ).select_related("deposit", "deposit__member", "deposit__reviewed_by")
    is_finance_reviewer = request.user.is_staff or MemberProfile.objects.filter(
        user=request.user, role=MemberProfile.Role.FINANCE,
    ).exists()
    return render(request, "workspace/workspace_notifications.html", {
        "active_nav": "notifications", "page_title": "Notifications",
        "today": timezone.localdate(),
        "announcements": Announcement.objects.select_related("author").all(),
        "finance_notifications": finance_notifications,
        "is_finance_reviewer": is_finance_reviewer,
    })


@member_required
def workspace_messages(request):
    form = ContactForm(request.POST or None, initial={
        "name": request.user.get_full_name() or request.user.username,
        "email": request.user.email,
    })
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your message has been sent to the SafetyFund team.")
        return redirect("workspace_messages")
    return render(request, "workspace/workspace_messages.html", {
        "active_nav": "messages", "page_title": "Messages",
        "today": timezone.localdate(), "form": form,
    })


@member_required
def workspace_profile(request):
    profile, _created = MemberProfile.objects.get_or_create(
        user=request.user, defaults={"email": request.user.email or ""},
    )
    return render(request, "workspace/workspace_profile.html", {
        "active_nav": "profile", "page_title": "Profile",
        "today": timezone.localdate(), "profile": profile,
    })


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
    script = """const CACHE = 'safetyfund-shell-v19';
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
