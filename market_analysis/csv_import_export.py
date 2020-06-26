from market_analysis.imports import *
from market_analysis.models import SortedStockDashboardReport, Symbol

#  Code Below

class SortedStockDashboardReportResource(resources.ModelResource):

    class Meta:
        model = SortedStockDashboardReport
        

class SymbolResource(resources.ModelResource):

    class Meta:
        model = Symbol