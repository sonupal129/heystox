from django.urls import path
from market_analysis import api_views


# Code Below
app_name = 'market_analysis_api_urls'

urlpatterns = [
    path('users', api_views.users_view, name="users"),
    path('classusers', api_views.UsersListView.as_view(), name="class-users"),
    path('users/<int:pk>/', api_views.user_detail_view, name="user" ),
]