from django.test import TestCase
from .base import BaseViewTest
from market_analysis.views import *

# Code Below

class UpstoxLoginCompleteTest(BaseViewTest, TestCase):
    url_name_space = 'market_analysis_urls:upstox-login'
    url_path = "/heystox/login"
    view = UpstoxLoginComplete

class UpstoxLoginTest(BaseViewTest, TestCase):
    url_name_space = 'market_analysis_urls:login-upstox-done'
    url_path = '/'
    view = UpstoxLogin 
    status_code = 302

class SortedStockDashboardViewTest(BaseViewTest, TestCase):
    url_name_space = 'market_analysis_urls:sorted-dashboard'
    url_path = '/report/'
    view = SortedStocksDashBoardView
    status_code = 302