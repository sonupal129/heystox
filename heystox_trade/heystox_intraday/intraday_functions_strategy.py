from  market_analysis.models import SortedStocksList, Indicator, StrategyTimestamp, Symbol
from datetime import datetime, timedelta
from heystox_intraday.intraday_fetchdata import get_stock_live_data
from ta.trend import macd, macd_diff, macd_signal, ema, ema_indicator
from ta.momentum import stoch, stoch_signal
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
                indi.exclude(pk=indi.order_by("created_at").first().pk).delete()
        else:
            if indi.count() >= 0:
                indi.delete()


def is_stocks_pdhl():
    sorted_stocks = SortedStocksList.objects.filter(created_at__date=datetime.now().date())
    pdhl_indicator = Indicator.objects.get(name="PDHL")
    for stock in sorted_stocks:
        if stock.symbol.is_stock_pdhl() == stock.entry_type:
            pdhl, is_created = StrategyTimestamp.objects.get_or_create(indicator=pdhl_indicator, stock=stock)
            pdhl.timestamp = datetime.now()
            pdhl.save()


def entry_for_long_short():
    sorted_stocks = SortedStocksList.objects.filter(created_at__date=datetime.now().date())
    long_short_entry = Indicator.objects.get(name="LONGSHORT")
    for stock in sorted_stocks:
        if stock.symbol.has_entry_for_long_short() == stock.entry_type:
            long_short, is_created = StrategyTimestamp.objects.get_or_create(indicator=long_short_entry, stock=stock)
            long_short.timestamp = datetime.now()
            long_short.save()
        else:
            StrategyTimestamp.objects.filter(indicator=long_short_entry, stock=stock, timestamp__date=datetime.now().date()).delete()


def get_macd_crossover(sorted_stock): # Need to Work more to find final crossover
    """This function find crossover between macd and macd signal and return signal as buy or sell"""
    macd_indicator = Indicator.objects.get(name="MACD")
    df = get_stock_live_data(sorted_stock.symbol.symbol)
    df["macd"] = macd(df.close_price)
    df["macd_signal"] = macd_signal(df.close_price)
    df["macd_diff"] = macd_diff(df.close_price)
    df["percentage"] = df.macd * df.macd_diff /100
    df["signal"] = np.where(df.macd < df.macd_signal, "SELL", "BUY")
    df.loc[(df["signal"] != df["signal"].shift()) & (df["signal"] == "BUY"), "signal"] = "BUY_CROSSOVER"
    df.loc[(df["signal"] != df["signal"].shift()) & (df["signal"] == "SELL"), "signal"] = "SELL_CROSSOVER"
    last_crossover = df[df.signal.str.endswith("CROSSOVER")].iloc[-1]
    if last_crossover.signal == "SELL_CROSSOVER" and sorted_stock.entry_type == "SELL" and df.iloc[-1].percentage <= -0.0032 and last_crossover.date.date() == datetime.now().date():
        stamp, is_created = StrategyTimestamp.objects.update_or_create(stock=sorted_stock, indicator=macd_indicator, defaults={"timestamp": df.iloc[-1].date, "diff":df.iloc[-1].macd_diff})
    elif last_crossover.signal == "BUY_CROSSOVER" and sorted_stock.entry_type == "BUY" and df.iloc[-1].percentage >= 0.0032 and last_crossover.date.date() == datetime.now().date():
        stamp, is_created = StrategyTimestamp.objects.update_or_create(stock=sorted_stock, indicator=macd_indicator, defaults={"timestamp": df.iloc[-1].date, "diff":df.iloc[-1].macd_diff})


def get_stochastic_crossover(sorted_stock): # Find Stochastic crossover signals
    stoch_indicator = Indicator.objects.get(name="STOCHASTIC")
    df = get_stock_live_data(sorted_stock.symbol.symbol)
    df["stoch"] = stoch(high=df.high_price, close=df.close_price, low=df.low_price)
    df["stoch_signal"] = stoch_signal(high=df.high_price, close=df.close_price, low=df.low_price)
    df["percentage"] = df.stoch * (df.stoch - df.stoch_signal) /100
    df["signal"] = np.where(df.stoch < df.stoch_signal, "SELL", "BUY")
    df.loc[(df["signal"] != df["signal"].shift()) & (df["signal"] == "BUY"), "signal"] = "BUY_CROSSOVER"
    df.loc[(df["signal"] != df["signal"].shift()) & (df["signal"] == "SELL"), "signal"] = "SELL_CROSSOVER"
    last_crossover = df[df.signal.str.endswith("CROSSOVER")].iloc[-1]
    if last_crossover.signal == "SELL_CROSSOVER" and sorted_stock.entry_type == "SELL" and df.iloc[-1].percentage <= -22.70 and last_crossover.date.date() == datetime.now().date():
        stamp, is_created = StrategyTimestamp.objects.update_or_create(stock=sorted_stock, indicator=stoch_indicator, defaults={"timestamp": df.iloc[-1].date, "diff":df.iloc[-1].percentage})
    elif last_crossover.signal == "BUY_CROSSOVER" and sorted_stock.entry_type == "BUY" and df.iloc[-1].percentage >= 22.80 and last_crossover.date.date() == datetime.now().date():
        stamp, is_created = StrategyTimestamp.objects.update_or_create(stock=sorted_stock, indicator=stoch_indicator, defaults={"timestamp": df.iloc[-1].date, "diff":df.iloc[-1].percentage})
