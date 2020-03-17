from django.urls import path
from market_analysis import views

# Code Starts Below
app_name = 'market_analysis_urls'

urlpatterns = [
    path('heystox/login/', views.upstox_login, name="upstox-login"),
    path('', views.get_access_token_from_upstox, name='login-upstox-done'),
    path('sorted-stocks/', views.SortedStocksDashBoardView.as_view(), name="sorted-dashboard"),
    path('report/', views.SortedStocksDashBoardReportView.as_view(), name="sorted-dashboard-report"),
    path('login/', views.UserLoginRegisterView.as_view(), name="login-register"),
]

