from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

from .models import ContactInquiry, FinanceRequestStatus, MemberDeposit, MemberLoan, MemberLoanRepayment, MembershipApplication, MemberProfile


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactInquiry
        fields = ("name", "email", "subject", "message")
        widgets = {
            "message": forms.Textarea(attrs={"rows": 5}),
        }


class MembershipApplicationForm(forms.ModelForm):
    class Meta:
        model = MembershipApplication
        fields = ("full_name", "id_number", "phone_number", "email", "payment_method", "proof_of_payment")
        widgets = {
            "full_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "id_number": forms.TextInput(attrs={"autocomplete": "off"}),
            "phone_number": forms.TelInput(attrs={"autocomplete": "tel"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "payment_method": forms.Select(),
            "proof_of_payment": forms.ClearableFileInput(attrs={"accept": ".pdf,.jpg,.jpeg,.png"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user and not self.is_bound:
            self.fields["email"].initial = user.email
        for field_name in ("full_name", "id_number", "phone_number", "email", "payment_method", "proof_of_payment"):
            self.fields[field_name].required = True

    def clean_proof_of_payment(self):
        uploaded = self.cleaned_data["proof_of_payment"]
        if uploaded.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Choose a file smaller than 5 MB.")
        allowed_types = {"application/pdf", "image/jpeg", "image/png"}
        if uploaded.content_type not in allowed_types:
            raise forms.ValidationError("Upload a PDF, JPG, or PNG proof of payment.")
        header = uploaded.read(8)
        uploaded.seek(0)
        valid_signature = (
            (uploaded.content_type == "application/pdf" and header.startswith(b"%PDF-"))
            or (uploaded.content_type == "image/png" and header.startswith(b"\x89PNG\r\n\x1a\n"))
            or (uploaded.content_type == "image/jpeg" and header.startswith(b"\xff\xd8\xff"))
        )
        if not valid_signature:
            raise forms.ValidationError("The selected file does not look like a valid PDF, JPG, or PNG.")
        return uploaded


class MembershipDecisionForm(forms.Form):
    action = forms.ChoiceField(choices=(
        ("", "Choose a decision"),
        (MembershipApplication.Status.APPROVED, "Approve membership"),
        (MembershipApplication.Status.REJECTED, "Reject application"),
        (MembershipApplication.Status.NEEDS_INFO, "Request more information"),
    ))
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Add a note for the applicant. Required when requesting information or rejecting."}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("action") in (MembershipApplication.Status.REJECTED, MembershipApplication.Status.NEEDS_INFO) and not cleaned.get("note", "").strip():
            self.add_error("note", "Add a short note so the applicant understands the decision or what information is needed.")
        return cleaned


class ApplicantInformationForm(forms.Form):
    response = forms.CharField(label="Your response", widget=forms.Textarea(attrs={"rows": 5, "placeholder": "Provide the information requested by the reviewer."}))


class MemberProfileForm(forms.ModelForm):
    class Meta:
        model = MemberProfile
        fields = ("full_name", "id_number", "phone_number", "email", "role")
        widgets = {
            "full_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "id_number": forms.TextInput(attrs={"autocomplete": "off"}),
            "phone_number": forms.TelInput(attrs={"autocomplete": "tel"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "role": forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True

    def clean_role(self):
        role = self.cleaned_data["role"]
        if role != MemberProfile.Role.USER and not MembershipApplication.objects.filter(
            user=self.instance.user, status=MembershipApplication.Status.APPROVED
        ).exists() and role != self.instance.role:
            raise forms.ValidationError("This account needs an approved membership application before it can hold a member or staff role.")
        return role


class FinanceProofValidationMixin:
    def clean_proof_of_payment(self):
        uploaded = self.cleaned_data.get("proof_of_payment")
        if not uploaded:
            return uploaded
        if uploaded.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Choose a file smaller than 5 MB.")
        allowed_types = {"application/pdf", "image/jpeg", "image/png"}
        if uploaded.content_type not in allowed_types:
            raise forms.ValidationError("Upload a PDF, JPG, or PNG payment proof.")
        header = uploaded.read(8)
        uploaded.seek(0)
        valid_signature = (
            (uploaded.content_type == "application/pdf" and header.startswith(b"%PDF-"))
            or (uploaded.content_type == "image/png" and header.startswith(b"\x89PNG\r\n\x1a\n"))
            or (uploaded.content_type == "image/jpeg" and header.startswith(b"\xff\xd8\xff"))
        )
        if not valid_signature:
            raise forms.ValidationError("The selected file does not look like a valid PDF, JPG, or PNG.")
        return uploaded


class MemberDepositForm(FinanceProofValidationMixin, forms.ModelForm):
    class Meta:
        model = MemberDeposit
        fields = ("share_count", "payment_method", "proof_of_payment")
        labels = {"share_count": "Number of shares for this month"}
        widgets = {
            "share_count": forms.Select(choices=(
                ("", "Choose shares"), (1, "1 share — RWF 6,000 per month"),
                (2, "2 shares — RWF 12,000 per month"),
                (3, "3 shares — RWF 18,000 per month"),
                (4, "4 shares — RWF 24,000 per month"),
            )),
        }

    def __init__(self, *args, **kwargs):
        self.member = kwargs.pop("member")
        self.contribution_month = kwargs.pop("contribution_month")
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        if self.member and self.contribution_month and MemberDeposit.objects.filter(
            member=self.member, contribution_month=self.contribution_month,
            status__in=(FinanceRequestStatus.PENDING, FinanceRequestStatus.APPROVED),
        ).exists():
            raise forms.ValidationError("A contribution for this month has already been submitted and is awaiting or has received approval.")
        return cleaned


class MemberLoanRequestForm(forms.ModelForm):
    class Meta:
        model = MemberLoan
        fields = ("requested_amount", "purpose")
        labels = {"requested_amount": "Requested amount (RWF)", "purpose": "Purpose of the loan"}
        widgets = {
            "requested_amount": forms.NumberInput(attrs={"min": "0.01", "step": "0.01", "placeholder": "Amount in RWF"}),
            "purpose": forms.Textarea(attrs={"rows": 5, "placeholder": "Explain why you are requesting this loan."}),
        }


class MemberLoanRepaymentForm(FinanceProofValidationMixin, forms.ModelForm):
    class Meta:
        model = MemberLoanRepayment
        fields = ("loan", "amount", "payment_method", "proof_of_payment")
        widgets = {"amount": forms.NumberInput(attrs={"min": "0.01", "step": "0.01", "placeholder": "Amount in RWF"})}

    def __init__(self, *args, **kwargs):
        member = kwargs.pop("member")
        super().__init__(*args, **kwargs)
        open_loans = MemberLoan.objects.filter(
            member=member, status="approved", approved_amount__isnull=False,
        ).select_related("member")
        self.fields["loan"].queryset = open_loans

    def clean(self):
        cleaned = super().clean()
        loan = cleaned.get("loan")
        amount = cleaned.get("amount")
        if loan and loan.outstanding_balance <= 0:
            self.add_error("loan", "This loan has already been fully repaid.")
        elif loan and amount and amount > loan.outstanding_balance:
            self.add_error("amount", "The repayment cannot exceed the approved outstanding loan balance.")
        return cleaned


class DepositReviewAdminForm(forms.ModelForm):
    class Meta:
        model = MemberDeposit
        fields = ("status", "review_note")


class LoanReviewAdminForm(forms.ModelForm):
    class Meta:
        model = MemberLoan
        fields = ("approved_amount", "status", "review_note")

    def clean(self):
        cleaned = super().clean()
        approved_amount = cleaned.get("approved_amount")
        if cleaned.get("status") == FinanceRequestStatus.APPROVED:
            approved_amount = approved_amount or self.instance.requested_amount
            if approved_amount > self.instance.requested_amount:
                self.add_error("approved_amount", "The approved amount cannot exceed the amount requested.")
        return cleaned


class RepaymentReviewAdminForm(forms.ModelForm):
    class Meta:
        model = MemberLoanRepayment
        fields = ("status", "review_note")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("status") == FinanceRequestStatus.APPROVED and self.instance.status != FinanceRequestStatus.APPROVED:
            loan = self.instance.loan
            if loan.status != FinanceRequestStatus.APPROVED:
                self.add_error("status", "Only repayments for an approved loan can be approved.")
            elif self.instance.amount > loan.outstanding_balance:
                self.add_error("status", "This repayment exceeds the loan balance remaining after other approved repayments.")
        return cleaned


class FinanceDepositDecisionForm(forms.Form):
    action = forms.ChoiceField(choices=(
        ("", "Choose a decision"),
        (FinanceRequestStatus.APPROVED, "Approve verified payment"),
        (FinanceRequestStatus.REJECTED, "Reject payment proof"),
    ))
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Add a note for the member. Required when rejecting."}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("action") == FinanceRequestStatus.REJECTED and not cleaned.get("note", "").strip():
            self.add_error("note", "Add a short note explaining why this proof was rejected.")
        return cleaned
