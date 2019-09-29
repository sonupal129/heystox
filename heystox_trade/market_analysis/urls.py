from django.urls import path
from market_analysis import views

# Code Starts Below

urlpatterns = [
    path('heystox/login', views.upstox_login, name="upstox-login"),
    path('', views.get_access_token_from_upstox, name='login-upstox-done')
]

