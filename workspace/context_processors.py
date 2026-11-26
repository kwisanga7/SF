from .models import FinanceNotification


def finance_notification_count(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"finance_notification_count": 0}
    return {
        "finance_notification_count": FinanceNotification.objects.filter(
            recipient=user, read_at__isnull=True,
        ).count(),
    }
