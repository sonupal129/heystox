from django.urls import path
from market_analysis import api_views


# Code Below
app_name = 'market_analysis_api_urls'

urlpatterns = [
    path('users', api_views.UsersListView.as_view(), name="users"),
]