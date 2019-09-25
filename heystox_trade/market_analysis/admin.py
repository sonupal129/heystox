from django.contrib import admin
from market_analysis.models import (Candle, UserProfile, MasterContract, Symbol)
# Register your models here.

class SymbolAdmin(admin.ModelAdmin):
      list_display = ["symbol", "exchange"]
      list_filter = ["exchange"]
      search_fields = ["symbol", "name"]

class CandleAdmin(admin.ModelAdmin):
      list_display = ["symbol", "exchange", "candle_type"]
      list_filter = ["candle_type"]
      search_fields = ["symbol__symbol"]

      def exchange(self, obj):
            return obj.symbol.exchange

admin.site.register(Candle, CandleAdmin)
admin.site.register(UserProfile)
admin.site.register(Symbol, SymbolAdmin)
admin.site.register(MasterContract)