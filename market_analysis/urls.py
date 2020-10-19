from django.urls import path
from market_analysis import views

# Code Starts Below
app_name = 'market_analysis_urls'

urlpatterns = [
    path('', views.HomeView.as_view(), name="home-page"),
    path('heystox/login/', views.UpstoxLogin.as_view(), name="upstox-login"),
    path('heystox/login/complete/', views.UpstoxLoginComplete.as_view(), name='login-upstox-done'),
    path('heystox/logout/', views.UpstoxLogoutView.as_view(), name='logout-upstox'),
    path('report/', views.SortedStocksDashBoardReportView.as_view(), name="sorted-dashboard-report"),
    path('backtest-stocks/', views.BacktestSortedStocksView.as_view(), name="backtest-sorted-stocks"),
    path('backtest-stocks/<force>/', views.BacktestSortedStocksView.as_view(), name="backtest-sorted-stocks"),
    path('login/', views.UserLoginRegisterView.as_view(), name="login-register"),
]

