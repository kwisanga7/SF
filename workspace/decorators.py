from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .models import MembershipApplication


def member_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if request.user.is_staff or MembershipApplication.objects.filter(
            user=request.user, status=MembershipApplication.Status.APPROVED
        ).exists():
            return view_func(request, *args, **kwargs)
        messages.info(request, "The management workspace is available to approved members. You can apply from your account page.")
        return redirect("account_home")
    return wrapped
