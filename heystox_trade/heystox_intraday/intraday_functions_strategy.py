from market_analysis.models import SortedStocksList, Indicator, StrategyTimestamp, Symbol
from datetime import datetime, timedelta
from heystox_intraday.trading_indicator import get_macd_data, get_stochastic_data
# Start code below

def is_stocks_ohl():
    sorted_stocks = SortedStocksList.objects.filter(created_at__date=datetime.now().date())
    ohl_indicator = Indicator.objects.get(name="OHL")
    for stock in sorted_stocks:
        indi = StrategyTimestamp.objects.filter(indicator__name="OHL", timestamp__date=datetime.now().date(), stock=stock)
        if stock.symbol.is_stock_ohl() == stock.entry_type:
            if indi.count() == 0:
                StrategyTimestamp.objects.create(indicator=ohl_indicator, stock=stock, timestamp=datetime.now())
            elif indi.count() >= 1:
                indi.exclude(pk=indi.order_by("timestamp").first().pk).delete() 
        else:
            if indi.count() >= 0:
                indi.delete()


def is_stocks_pdhl(obj_id):
    stock = SortedStocksList.objects.get(created_at__date=datetime.now().date(), id=obj_id)
    pdhl_indicator = Indicator.objects.get(name="PDHL")
    if stock.symbol.is_stock_pdhl() == stock.entry_type:
        pdhl, is_created = StrategyTimestamp.objects.get_or_create(indicator=pdhl_indicator, stock=stock)
        pdhl.timestamp = datetime.now()
        pdhl.save()


def entry_for_long_short(obj_id):
    stock = SortedStocksList.objects.get(created_at__date=datetime.now().date(), id=obj_id)
    long_short_entry = Indicator.objects.get(name="LONGSHORT")
    if stock.symbol.has_entry_for_long_short() == stock.entry_type:
        long_short, is_created = StrategyTimestamp.objects.get_or_create(indicator=long_short_entry, stock=stock)
        long_short.timestamp = datetime.now()
        long_short.save()
    else:
        StrategyTimestamp.objects.filter(indicator=long_short_entry, stock=stock, timestamp__date=datetime.now().date()).delete()


def get_macd_crossover(sorted_stock): # Macd Crossover Strategy
    """This function find crossover between macd and macd signal and return signal as buy or sell"""
    macd_indicator = Indicator.objects.get(name="MACD")
    df = get_macd_data(sorted_stock.symbol)
    df.loc[(df["signal"] != df["signal"].shift()) & (df["signal"] == "BUY"), "signal"] = "BUY_CROSSOVER"
    df.loc[(df["signal"] != df["signal"].shift()) & (df["signal"] == "SELL"), "signal"] = "SELL_CROSSOVER"
    last_crossover = df[df.signal.str.endswith("CROSSOVER")].iloc[-1]
    if last_crossover.signal == "SELL_CROSSOVER" and sorted_stock.entry_type == "SELL" and df.iloc[-1].macd_diff >= -0.070 or df.iloc[-2].macd_diff >= -0.070:
        stamp, is_created = StrategyTimestamp.objects.update_or_create(stock=sorted_stock, indicator=macd_indicator, defaults={"timestamp": df.iloc[-1].date, "diff":df.iloc[-1].macd_diff})
    elif last_crossover.signal == "BUY_CROSSOVER" and sorted_stock.entry_type == "BUY" and df.iloc[-1].macd_diff >= 0.070 or df.iloc[-2].macd_diff >= 0.070:
        stamp, is_created = StrategyTimestamp.objects.update_or_create(stock=sorted_stock, indicator=macd_indicator, defaults={"timestamp": df.iloc[-1].date, "diff":df.iloc[-1].macd_diff})


def get_stochastic_crossover(sorted_stock): # Stochastic crossover strategy
    stoch_indicator = Indicator.objects.get(name="STOCHASTIC")
    df = get_stochastic_data(sorted_stock.symbol)
    df.loc[(df["signal"] != df["signal"].shift()) & (df["signal"] == "BUY"), "signal"] = "BUY_CROSSOVER"
    df.loc[(df["signal"] != df["signal"].shift()) & (df["signal"] == "SELL"), "signal"] = "SELL_CROSSOVER"
    last_crossover = df[df.signal.str.endswith("CROSSOVER")].iloc[-1]
    if last_crossover.signal == "SELL_CROSSOVER" and sorted_stock.entry_type == "SELL" and df.iloc[-1].percentage >= -22.70 or df.iloc[-2].percentage >= -22.70:
        stamp, is_created = StrategyTimestamp.objects.update_or_create(stock=sorted_stock, indicator=stoch_indicator, defaults={"timestamp": df.iloc[-1].date, "diff":df.iloc[-1].percentage})
    elif last_crossover.signal == "BUY_CROSSOVER" and sorted_stock.entry_type == "BUY" and df.iloc[-1].percentage >= 22.80 or df.iloc[-2].percentage >= 22.80:
        stamp, is_created = StrategyTimestamp.objects.update_or_create(stock=sorted_stock, indicator=stoch_indicator, defaults={"timestamp": df.iloc[-1].date, "diff":df.iloc[-1].percentage})
