from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile


# Code Starts Below

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=False, read_only=True)
    class Meta:
        model = UserProfile
        fields = ["mobile", "for_trade", 'subscribed_historical_api', "subscribed_live_api", "user"]
