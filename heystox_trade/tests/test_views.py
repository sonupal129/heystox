from django.test import TestCase
from .base import BaseViewTest
from market_analysis.views import *

# Code Below

class StockDashboardViewTest(BaseViewTest, TestCase):
    url_name_space = 'market_analysis_urls:dashboard'
    url_path = '/dashboard/'
    view = StockDashboardView

class UpstoxLoginTest(BaseViewTest, TestCase):
    url_name_space = 'market_analysis_urls:upstox-login'
    url_path = "/heystox/login"
    view = upstox_login

class UpstoxLoginTest(BaseViewTest, TestCase):
    url_name_space = 'market_analysis_urls:login-upstox-done'
    url_path = '/'
    view = get_access_token_from_upstox
    status_code = 302

class SortedStockDashboardViewTest(BaseViewTest, TestCase):
    url_name_space = 'market_analysis_urls:sorted-dashboard'
    url_path = '/dashboard/sorted-stocks/'
    view = SortedStocksDashBoardView