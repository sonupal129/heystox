from rest_framework import serializers
from django.contrib.auth.models import User


# Code Starts Below

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id","first_name", "last_name", "email",)
