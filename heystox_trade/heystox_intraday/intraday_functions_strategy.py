from  market_analysis.models import SortedStocksList, Indicator, StrategyTimestamp, Symbol
from datetime import datetime, timedelta
from heystox_intraday.intraday_fetchdata import get_stock_live_data
# Start code below

def is_stocks_ohl():
    sorted_stocks = SortedStocksList.objects.filter(created_at=datetime.now().date())
    ohl_indicator = Indicator.objects.get(name="OHL")
    for stock in sorted_stocks:
        indi = StrategyTimestamp.objects.filter(indicator__name="OHL", created_at=datetime.now().date(), stock=stock)
        if stock.symbol.is_stock_ohl() == stock.entry_type:
            if indi.count() == 0:
                StrategyTimestamp.objects.create(indicator=ohl_indicator, stock=stock, timestamp=datetime.now())
            elif indi.count() >= 1:
                indi.exclude(pk=indi.order_by("created_at").first().pk).delete()
        else:
            if indi.count() >= 0:
                indi.delete()


def is_stocks_pdhl():
    sorted_stocks = SortedStocksList.objects.filter(created_at=datetime.now().date())
    pdhl_indicator = Indicator.objects.get(name="PDHL")
    for stock in sorted_stocks:
        if stock.symbol.is_stock_pdhl() == stock.entry_type:
            StrategyTimestamp.objects.create(indicator=pdhl_indicator, stock=stock, timestamp=datetime.now())


def entry_for_long_short():
    sorted_stocks = SortedStocksList.objects.filter(created_at=datetime.now().date())
    long_short_entry = Indicator.objects.get(name="LONGSHORT")
    for stock in sorted_stocks:
        if stock.symbol.has_entry_for_long_short() == stock.entry_type:
            StrategyTimestamp.objects.create(indicator=long_short_entry, stock=stock, timestamp=datetime.now())
        else:
            StrategyTimestamp.objects.filter(indicator=long_short_entry, stock=stock, timestamp=datetime.now().date()).delete()

def get_macd_crossover(stock_name:str): # Need to Work more to find final crossover
    """This function find crossover between macd and macd signal and return signal as buy or sell"""
    data = get_stock_live_data(stock_name)
    return ""


def get_stochastic_crossover(stock_name:str): # Find Stochastic crossover signals
    return ""
