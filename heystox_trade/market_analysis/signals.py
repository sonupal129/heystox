from django.contrib.auth.models import User
from django.db.models.signals import post_save
from market_analysis.models import UserProfile
from django.dispatch import receiver

# Code Below

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        user_profile = UserProfile.objects.get_or_create(user=instance)
    except:
        pass