from django.urls import path
from market_analysis import api_views
from market_analysis.api_views import CustomTokenAuthentication
# Code Below
app_name = 'market_analysis_api_urls'


urlpatterns = [
    path('users/', api_views.UsersListView.as_view(), name="users"),
    path('sorted-stocks/', api_views.SortedStocksListView.as_view(), name="sorted-stocks"),
    path('sorted-stocks/<str:symbol>/', api_views.SortedStocksListView.as_view(), name="sorted-stock"),
    # path('dashboard/<str:symbol_name>/', api_views.LiveStockDataView.as_view(), name="live-data"),
]

# API LOGIN URLS

urlpatterns += [
    path("login/", CustomTokenAuthentication.as_view(), name="customer-authentication"),
]



