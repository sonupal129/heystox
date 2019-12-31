import django_filters
from market_analysis.models import SortedStocksList
# Code Starts

class SymbolFilters(django_filters.FilterSet):
    last_day_closing_price__lt = django_filters.NumberFilter(field_name='last_day_closing_price', lookup_expr='lt')
    last_day_opening_price__gt = django_filters.NumberFilter(field_name='last_day_opening_price', lookup_expr='gt')
    symbol__name = django_filters.CharFilter(field_name="symbol", lookup_expr='icontains')

class SortedStocksFilter(django_filters.FilterSet):
    created_at__date = django_filters.DateFilter(field_name="created_at", lookup_expr="date")
