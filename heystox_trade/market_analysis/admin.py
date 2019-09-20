from django.contrib import admin
from market_analysis.models import (Candle, UserProfile)
# Register your models here.

admin.site.register(Candle)
admin.site.register(UserProfile)