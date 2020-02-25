from django.urls import path
from market_analysis import views

# Code Starts Below
app_name = 'market_analysis_urls'

urlpatterns = [
    path('heystox/login/', views.upstox_login, name="upstox-login"),
    path('', views.get_access_token_from_upstox, name='login-upstox-done'),
    path('dashboard/', views.StockDashboardView.as_view(), name="dashboard"),
    path('dashboard/sorted-stocks/', views.SortedStocksDashBoardView.as_view(), name="sorted-dashboard"),
    path('login/', views.UserLoginRegisterView.as_view(), name="login-register"),
]

