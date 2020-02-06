"""heystox_trade URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include


admin.site.site_header = 'Heystox Admin'
admin.site.site_title = "Heystox Admin"
admin.site.index_title = "Welcome to Heystox"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include("market_analysis.urls", namespace="market_analysis_urls")),
    path('api/v1/', include("market_analysis.api_urls", namespace="market_analysis_api_urls")),
    path('admin/statuscheck', include("celerybeat_status.urls")),

]