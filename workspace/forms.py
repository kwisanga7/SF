from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

from .models import ContactInquiry, MembershipApplication


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
        fields = ("full_name", "id_number", "phone_number", "email", "motivation", "payment_method", "payment_reference", "proof_of_payment")
        widgets = {
            "full_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "id_number": forms.TextInput(attrs={"autocomplete": "off"}),
            "phone_number": forms.TelInput(attrs={"autocomplete": "tel"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "motivation": forms.Textarea(attrs={"rows": 5, "placeholder": "Tell us a little about your interest in becoming a member."}),
            "payment_method": forms.Select(),
            "payment_reference": forms.TextInput(attrs={"placeholder": "Optional transaction reference"}),
            "proof_of_payment": forms.ClearableFileInput(attrs={"accept": ".pdf,.jpg,.jpeg,.png"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user and not self.is_bound:
            self.fields["email"].initial = user.email
        for field_name in ("full_name", "id_number", "phone_number", "email", "motivation", "payment_method", "proof_of_payment"):
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
