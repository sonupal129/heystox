from django.urls import path
from market_analysis import views

# Code Starts Below
app_name = 'market_analysis_urls'

urlpatterns = [
    path('heystox/login/', views.UpstoxLogin.as_view(), name="upstox-login"),
    path('', views.UpstoxLoginComplete.as_view(), name='login-upstox-done'),
    path('sorted-stocks/', views.SortedStocksDashBoardView.as_view(), name="sorted-dashboard"),
    path('report/', views.SortedStocksDashBoardReportView.as_view(), name="sorted-dashboard-report"),
    path('login/', views.UserLoginRegisterView.as_view(), name="login-register"),
]

