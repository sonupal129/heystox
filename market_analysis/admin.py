from django.contrib import admin
from market_analysis.models import *
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
    search_fields = ["symbol__symbol"]

class UserProfileAdmin(admin.ModelAdmin):
    list_dispaly = ["get_user_email"]
    actions = ["get_upstox_login_url"]

    def get_upstox_login_url(self, request, obj):
        user_profile = obj.first()
        message = "Login URL for " + user_profile.user.get_full_name() + ": " + user_profile.get_authentication_url()
        return self.message_user(request, message)

class MarketHolidayAdmin(admin.ModelAdmin):
    list_display = ["date", "get_day_from_date"]

    def get_day_from_date(self, obj):
        return obj.date.strftime("%A")


class PreMarketOrderDataAdmin(admin.ModelAdmin):
    list_dispaly = ["symbol__symbol", "sector", "created_at"]
    search_fields = ["symbol__symbol"]

class SortedStockDashboardReportAdmin(admin.ModelAdmin):
    list_dispaly = ["name", "entry_type", "entry_price"]

admin.site.register(MarketHoliday, MarketHolidayAdmin)
admin.site.register(Candle, CandleAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Symbol, SymbolAdmin)
admin.site.register(MasterContract)
admin.site.register(BankDetail)
admin.site.register(Credentials)
admin.site.register(Earning)
admin.site.register(Indicator)
admin.site.register(SortedStocksList, SortedStocksListAdmin)
admin.site.register(PreMarketOrderData, PreMarketOrderDataAdmin)
admin.site.register(SortedStockDashboardReport, SortedStockDashboardReportAdmin)
# TEST


# admin.site.register(StrategyTimestamp)