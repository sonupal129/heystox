from django.contrib import admin
from market_analysis.models import (Candle, UserProfile, 
    MasterContract, Symbol, BankDetail, Credentials, Earning, Indicator, SortedStocksList, StrategyTimestamp)
# Register your models here.

class SymbolAdmin(admin.ModelAdmin):
    list_display = ["symbol", "exchange"]
    list_filter = ["exchange"]
    search_fields = ["symbol", "name"]
    date_hierarchy = 'created_at'


class CandleAdmin(admin.ModelAdmin):
    list_display = ["symbol", "exchange", "candle_type"]
    list_filter = ["candle_type", "date"]
    search_fields = ["symbol__symbol"]
    date_hierarchy = 'date'

    def exchange(self, obj):
        return obj.symbol.exchange


class StrategyTimestampInline(admin.TabularInline):
    model = StrategyTimestamp
    fields = ('indicator', 'timestamp')
    extra = 0

class SortedStocksListAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    inlines = [StrategyTimestampInline]

class UserProfileAdmin(admin.ModelAdmin):
    list_dispaly = ["get_user_email"]
    actions = ["get_upstox_login_url"]

    def get_upstox_login_url(self, request, obj):
        user_obj = obj.first()
        return self.message_user(request, user_obj.get_authentication_url())

admin.site.register(Candle, CandleAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Symbol, SymbolAdmin)
admin.site.register(MasterContract)
admin.site.register(BankDetail)
admin.site.register(Credentials)
admin.site.register(Earning)
admin.site.register(Indicator)
admin.site.register(SortedStocksList, SortedStocksListAdmin)
admin.site.register(StrategyTimestamp)