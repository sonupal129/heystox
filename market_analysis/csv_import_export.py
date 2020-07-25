from market_analysis.imports import *
from market_analysis.models import SortedStockDashboardReport, Symbol, SortedStocksList, BacktestReport

#  Code Below

class SortedStockDashboardReportResource(resources.ModelResource):

    class Meta:
        model = SortedStockDashboardReport
        

class SymbolResource(resources.ModelResource):

    class Meta:
        model = Symbol

class SortedStocksListResource(resources.ModelResource):

    class Meta:
        model = SortedStocksList
        fields = ["created_at", "symbol__symbol", "added", "entry_type"]


class BacktestReportResource(resources.ModelResource):

    class Meta:
        model = BacktestReport