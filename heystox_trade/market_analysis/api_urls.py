from django.urls import path
from market_analysis import api_views
from rest_framework.authtoken import views

# Code Below
app_name = 'market_analysis_api_urls'


urlpatterns = [
    path('users', api_views.UsersListView.as_view(), name="users"),
]


#  Token Authentication

urlpatterns += [
    path("api-auth-token", views.obtain_auth_token),
]