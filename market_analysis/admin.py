from django.contrib import admin
from market_analysis.models import *
from market_analysis.csv_import_export import *
# Register your models here.

class SymbolAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = SymbolResource
    list_display = ["symbol", "exchange"]
    list_filter = ["exchange"]
    search_fields = ["symbol", "name"]


class CandleAdmin(admin.ModelAdmin):
    list_display = ["symbol", "exchange", "candle_type"]
    list_filter = ["candle_type", "date"]
    search_fields = ["symbol__symbol"]
    date_hierarchy = 'date'

    def exchange(self, obj):
        return obj.symbol.exchange


class StrategyTimestampInline(admin.TabularInline):
    model = StrategyTimestamp
    fields = ('strategy', 'timestamp', 'entry_price', "created_at")
    readonly_fields = ("entry_price", "created_at", 'strategy')
    extra = 0

class SortedStocksListAdmin(ExportMixin,admin.ModelAdmin):
    resource_class = SortedStocksListResource
    date_hierarchy = 'created_at'
    list_display = ["symbol", "entry_price", "entry_type"]
    readonly_fields = ("created_at",)
    inlines = [StrategyTimestampInline]
    search_fields = ["symbol__symbol"]

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["get_user_email"]
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
    list_display = ["symbol", "sector", "created_at"]
    search_fields = ["symbol__symbol"]

class SortedStockDashboardReportAdmin(ExportMixin ,admin.ModelAdmin):
    resource_class = SortedStockDashboardReportResource
    list_display = ["name", "entry_type", "entry_price", "entry_time"]
    search_fields = ["name"]

class OrderInline(admin.TabularInline):
    model = Order
    fields = ('order_id', 'transaction_type', 'status', 'entry_type', 'entry_time', 'message')
    readonly_fields = ('order_id', 'transaction_type', "transaction_type", "entry_type", "entry_time", "message")
    extra = 0

class OrderBookAdmin(admin.ModelAdmin):
    list_display = ["symbol", "date"]
    inlines = [OrderInline]
    readonly_fields = ["symbol", "strength", "date"]
    date_hierarchy = 'date'


class StrategyAdmin(admin.ModelAdmin):
    list_display = ["view_strategy_name", "strategy_type", "priority_type", "strategy_for"]
    readonly_fields = ["strategy_name", "strategy_location", "priority_type", "strategy_for"]
    actions = ["discover_update_strategies"]

    def view_strategy_name(self, obj):
        return obj.get_strategy_name()

    
    def discover_update_strategies(self, request, queryset):
        from market_analysis.tasks.strategies.strategy_register import strategy_list
        registered_strategy = []
        for strategy in strategy_list:
            registered_strategy.append(strategy.id)
        Strategy.objects.exclude(id__in=registered_strategy).delete()

    def has_add_permission(self, request):
        return False


class DeployedStrategiesAdmin(admin.ModelAdmin):
    list_display = ["symbol", "strategy", "timeframe", "entry_type", "active"]
    search_fields = ["symbol__symbol"]
    list_filter = ["strategy", "timeframe", "entry_type"]
    readonly_fields = ["symbol", "strategy", "timeframe", "entry_type"]

    def has_add_permission(self, request):
        return True

class BacktestReportAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = BacktestReportResource
    list_filter = ["strategy_name"]



admin.site.register(MarketHoliday, MarketHolidayAdmin)
admin.site.register(Candle, CandleAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Symbol, SymbolAdmin)
admin.site.register(MasterContract)
admin.site.register(BankDetail)
admin.site.register(Credentials)
admin.site.register(Earning)
admin.site.register(SortedStocksList, SortedStocksListAdmin)
admin.site.register(PreMarketOrderData, PreMarketOrderDataAdmin)
admin.site.register(SortedStockDashboardReport, SortedStockDashboardReportAdmin)
admin.site.register(OrderBook, OrderBookAdmin)
admin.site.register(Strategy, StrategyAdmin)
admin.site.register(DeployedStrategies, DeployedStrategiesAdmin)
admin.site.register(BacktestReport, BacktestReportAdmin)
# admin.site.register(BacktestLogs)