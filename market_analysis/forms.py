from django import forms
from market_analysis.models import Symbol, User
from market_analysis.imports import *
# Code Starts

class UserLoginRegisterForm(forms.Form):
    email = forms.EmailField(required=False, widget=forms.TextInput(attrs={"placeholder":"Your Email *"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Your Password *"}), required=True, initial="Your Password *")

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_user(self):
        email = self.data["email"]
        password = self.data["password"]
        user = authenticate(username=email, password=password)
        if user is not None:
            return user
        