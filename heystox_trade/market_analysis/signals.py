from django.contrib.auth.models import User
from django.db.models.signals import post_save
from market_analysis.models import UserProfile, BankDetail, Earning
from django.dispatch import receiver
from datetime import datetime
# Code Below

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        user_profile = UserProfile.objects.get_or_create(user=instance)
    except:
        pass

@receiver(post_save, sender=BankDetail)
def create_earning_object(sender, instance, **kwargs):
    if "current_balance" in kwargs["update_fields"]:
        Earning.objects.get_or_create(user=instance.user_profile, date=datetime.now().date(), opening_balance=instance.current_balance)