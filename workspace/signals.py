from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import MemberProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_safetyfund_profile(sender, instance, created, **kwargs):
    if created:
        role = MemberProfile.Role.ADMIN if instance.is_staff or instance.is_superuser else MemberProfile.Role.USER
        MemberProfile.objects.get_or_create(
            user=instance,
            defaults={"email": instance.email or "", "role": role},
        )
