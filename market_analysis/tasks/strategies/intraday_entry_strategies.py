from market_analysis.models import SortedStocksList, StrategyTimestamp, Symbol, Strategy
from market_analysis.imports import *
from market_analysis.tasks.notification_tasks import slack_message_sender
from market_analysis.tasks.orders import *
from .base_strategy import BaseEntryStrategy
# Start code below
# STRATEGY GUIDELINES
# 1. Strategy works on three Strategy type Primary, Secondary or Support Strategy
# 2. Primary Strategy mean if supporting indicator and secondary are with primary indicator then well n good else take entry basis or primary indicator only
# 3. Secondary Strategy can only take entry if there is 2 or more supporting indicators available with it
# 4. Please do not make any change backtest function unless it is required
# 5. There is a way to write strategy, So please understand previouse strategy function parameter then implement new strategy
# Strategies

class StochasticBollingerCrossover(BaseEntryStrategy):
    name = "find_stochastic_bollingerband_crossover"
    strategy_type = "Entry"
    queue = "strategy"

    def find_stochastic_bollingerband_crossover(self, stock_id, entry_type, backtest, backtesting_candles_cache_key, **kwargs):
        """Find Bollinger crossover with adx and stochastic crossover, Supporting Strategy"""
        stock = Symbol.objects.get(id=stock_id)
        today_date = get_local_time().date()
        df = self.create_dataframe(backtesting_candles_cache_key, backtest, **{"symbol": stock, "with_live_candle": False, "candle_type": kwargs.get("candle_type"), "head_count": kwargs.get("head_count")})        
        df["medium_band"] = bollinger_mavg(df.close_price)
        df["adx"] = adx(df.high_price, df.low_price, df.close_price)
        df["medium_band"] = df.medium_band.apply(roundup)
        df["bollinger_signal"] = np.where(df.close_price < df.medium_band, "SELL", "BUY")
        if not backtest:
            df = df.loc[df["date"] > str(today_date)]
        df.loc[(df["bollinger_signal"] != df["bollinger_signal"].shift()) & (df["bollinger_signal"] == "BUY"), "bollinger_signal"] = "BUY_CROSSOVER"
        df.loc[(df["bollinger_signal"] != df["bollinger_signal"].shift()) & (df["bollinger_signal"] == "SELL"), "bollinger_signal"] = "SELL_CROSSOVER"
        bollinger_df = df.copy(deep=True).drop(df.head(1).index)
            
        try:
            if entry_type == "SELL":
                bollinger_crossover = bollinger_df[bollinger_df.bollinger_signal.str.endswith("SELL_CROSSOVER")].iloc[-1]
            elif entry_type == "BUY":
                bollinger_crossover = bollinger_df[bollinger_df.bollinger_signal.str.endswith("BUY_CROSSOVER")].iloc[-1]
        except:
            bollinger_crossover = pd.Series()
            
        if not bollinger_crossover.empty:
            try:
                candle_before_crossover = bollinger_df.loc[bollinger_df["date"] < bollinger_crossover.date].iloc[-1]
                candle_after_crossover = bollinger_df.loc[bollinger_df["date"] > bollinger_crossover.date].iloc[0]
            except:
                return "Candle Before and After Could not be Created"

            bollinger_signal = pd.Series()
            
            if entry_type == "BUY":
                if (candle_before_crossover.open_price <= bollinger_crossover.medium_band and candle_before_crossover.close_price <= bollinger_crossover.medium_band) and \
                    (candle_after_crossover.open_price > bollinger_crossover.medium_band or candle_after_crossover.close_price > bollinger_crossover.medium_band):
                    bollinger_signal = candle_after_crossover

            elif entry_type == "SELL":
                if (candle_before_crossover.open_price >= bollinger_crossover.medium_band and candle_before_crossover.close_price >= bollinger_crossover.medium_band) and \
                    (candle_after_crossover.open_price < bollinger_crossover.medium_band or candle_after_crossover.close_price < bollinger_crossover.medium_band):
                    bollinger_signal = candle_after_crossover

            if not bollinger_signal.empty:
                #Stochastic Indicator 
                df["stoch"] = stoch(high=df.high_price, close=df.close_price, low=df.low_price)
                df["stoch_signal"] = stoch_signal(high=df.high_price, close=df.close_price, low=df.low_price)
                df["stochastic_signal"] = np.where(df.stoch < df.stoch_signal, "SELL", "BUY")
                df.loc[(df["stochastic_signal"].shift() == "BUY") & (df["stochastic_signal"] == "SELL") & (df["stochastic_signal"].shift(-1) == "BUY"), "stochastic_signal"] = "BUY"
                df.loc[(df["stochastic_signal"].shift() == "SELL") & (df["stochastic_signal"] == "BUY") & (df["stochastic_signal"].shift(-1) == "SELL"), "stochastic_signal"] = "SELL"
                df.loc[(df["stochastic_signal"] != df["stochastic_signal"].shift()) & (df["stochastic_signal"] == "BUY"), "stochastic_signal"] = "BUY_CROSSOVER"
                df.loc[(df["stochastic_signal"] != df["stochastic_signal"].shift()) & (df["stochastic_signal"] == "SELL"), "stochastic_signal"] = "SELL_CROSSOVER"
                stoch_df = df.loc[df["date"]  <= bollinger_crossover.date]

                try:
                    if entry_type == "SELL":
                        stochastic_crossover = stoch_df[stoch_df.stochastic_signal.str.endswith("SELL_CROSSOVER")].iloc[-1]
                    elif entry_type == "BUY":
                        stochastic_crossover = stoch_df[stoch_df.stochastic_signal.str.endswith("BUY_CROSSOVER")].iloc[-1]
                except:
                    stochastic_crossover = pd.Series()
                
                if not stochastic_crossover.empty:
                    time_diff = bollinger_signal.date - stochastic_crossover.date
                    if time_diff <= timedelta(minutes=25) and bollinger_signal.adx <= 23:
                        response = self.make_response(stock, entry_type, float(bollinger_signal.close_price), bollinger_signal.date, backtest, 20, **kwargs)
                        return response
                return "Stochastic Crossover Not Found"
            return "Bollinger Signal Not Found"
        return "Bollinger Crossover Not Found"


celery_app.tasks.register(StochasticBollingerCrossover)


class StochasticMacdCrossover(BaseEntryStrategy):
    name = "find_stochastic_macd_crossover"
    queue = "strategy"
    strategy_type = "Entry"

    def find_stochastic_macd_crossover(self, stock_id, entry_type, backtest=False, backtesting_candles_cache_key=None, **kwargs):
        """(Custom Macd Crossover) This function find crossover between macd and macd signal and return signal as buy or sell"""
        stock = Symbol.objects.get(id=stock_id)
        today_date = get_local_time().date()
        df = self.create_dataframe(backtesting_candles_cache_key, backtest, **{"symbol": stock, "with_live_candle": False, "candle_type": kwargs.get("candle_type"), "head_count": kwargs.get("head_count")})        
        df["macd"] = macd(df.close_price)
        df["macd_signal"] = macd_signal(df.close_price)
        df["macd_diff"] = macd_diff(df.close_price)
        df["percentage"] = round(df.macd * df.macd_diff /100, 6)
        df["macd_crossover"] = np.where(df.macd < df.macd_signal, "SELL", "BUY")
        df.loc[(df["macd_crossover"] != df["macd_crossover"].shift()) & (df["macd_crossover"] == "BUY"), "macd_crossover"] = "BUY_CROSSOVER"
        df.loc[(df["macd_crossover"] != df["macd_crossover"].shift()) & (df["macd_crossover"] == "SELL"), "macd_crossover"] = "SELL_CROSSOVER"
        df["stoch"] = stoch(high=df.high_price, close=df.close_price, low=df.low_price)
        df["stoch_signal"] = stoch_signal(high=df.high_price, close=df.close_price, low=df.low_price)
        df["stoch_diff"] = df.stoch - df.stoch_signal
        df["percentage"] = round(df.stoch * (df.stoch - df.stoch_signal) /100, 6)
        df["stochastic_crossover"] = np.where(df.stoch < df.stoch_signal, "SELL", "BUY")
        df.loc[(df["stochastic_crossover"].shift() == "BUY") & (df["stochastic_crossover"] == "SELL") & (df["stochastic_crossover"].shift(-1) == "BUY"), "stochastic_crossover"] = "BUY"
        df.loc[(df["stochastic_crossover"].shift() == "SELL") & (df["stochastic_crossover"] == "BUY") & (df["stochastic_crossover"].shift(-1) == "SELL"), "stochastic_crossover"] = "SELL"
        df.loc[(df["stochastic_crossover"] != df["stochastic_crossover"].shift()) & (df["stochastic_crossover"] == "BUY"), "stochastic_crossover"] = "BUY_CROSSOVER"
        df.loc[(df["stochastic_crossover"] != df["stochastic_crossover"].shift()) & (df["stochastic_crossover"] == "SELL"), "stochastic_crossover"] = "SELL_CROSSOVER"
        
        if not backtest:
            df = df.loc[df["date"] > str(today_date)]
        
        new_df = df.copy(deep=True).drop(df.tail(1).index)
        
        try:
            if entry_type == "SELL":
                macd_crossover = new_df[new_df.macd_crossover.str.endswith("SELL_CROSSOVER")].iloc[-1]
            elif entry_type == "BUY":
                macd_crossover = new_df[new_df.macd_crossover.str.endswith("BUY_CROSSOVER")].iloc[-1]
        except:
            macd_crossover = pd.Series()


        if not macd_crossover.empty:
            df_after_last_crossover = df.loc[df["date"] > macd_crossover.date]
            try:
                if macd_crossover.macd_crossover == "SELL_CROSSOVER":
                    macd_crossover_signal = df_after_last_crossover.loc[(df_after_last_crossover.macd_diff <= -0.070)].iloc[0]
                elif macd_crossover.macd_crossover == "BUY_CROSSOVER":
                    macd_crossover_signal = df_after_last_crossover.loc[(df_after_last_crossover.macd_diff >= 0.070)].iloc[0]
            except:
                macd_crossover_signal = pd.Series()
            

            if not macd_crossover_signal.empty:
                df = df.loc[df["date"] < macd_crossover.date]
                try:
                    if entry_type == "SELL":
                        stochastic_crossover = df[df.stochastic_crossover.str.endswith("SELL_CROSSOVER")].iloc[-1]
                    elif entry_type == "BUY":
                        stochastic_crossover = df[df.stochastic_crossover.str.endswith("BUY_CROSSOVER")].iloc[-1]
                except:
                    stochastic_crossover = pd.Series()
                    
                if not stochastic_crossover.empty:
                    df_after_last_crossover = df.loc[df["date"] >= stochastic_crossover.date]
                    try:
                        if stochastic_crossover.stochastic_crossover == "SELL_CROSSOVER":
                            stochastic_crossover_signal = df_after_last_crossover.loc[(df_after_last_crossover.stoch_diff <= -20.05)].iloc[-1]
                        elif stochastic_crossover.stochastic_crossover == "BUY_CROSSOVER":
                            stochastic_crossover_signal = df_after_last_crossover.loc[(df_after_last_crossover.stoch_diff >= 22.80)].iloc[-1]
                    except:
                        stochastic_crossover_signal = pd.Series()
                    
                    if not stochastic_crossover_signal.empty:
                        time_diff = (macd_crossover_signal.date - stochastic_crossover_signal.date)
                        if time_diff < timedelta(minutes=30):
                            response = self.make_response(stock, entry_type, float(macd_crossover_signal.close_price), macd_crossover_signal.date, backtest, 10, **kwargs)
                            return response
                    return "Stochastic Signal not Found"
                return "Stochastic Crossover not Found"
            return "Macd Signal not Found"
        return "Macd Crossover not Found"

celery_app.tasks.register(StochasticMacdCrossover)


class AdxBollingerCrossover(BaseEntryStrategy):
    name = "find_adx_bollinger_crossover"
    queue = "strategy"
    strategy_type = "Entry"

    def find_adx_bollinger_crossover(self, stock_id, entry_type, backtest=False, backtesting_candles_cache_key=None, **kwargs):
        """Find bolling corssover with help of adx"""
        stock = Symbol.objects.get(id=stock_id)
        today_date = get_local_time().date()
        df = self.create_dataframe(backtesting_candles_cache_key, backtest, **{"symbol": stock, "with_live_candle": False, "candle_type": kwargs.get("candle_type", "M5"), "head_count": kwargs.get("head_count")})
        df["high_band"] = bollinger_hband(df.close_price)
        # df["medium_band"] = bollinger_mavg(df.close_price)
        df["low_band"] = bollinger_lband(df.close_price)
        
        df["adx"] = adx(df.high_price, df.low_price, df.close_price)
        df["adx_neg"] = adx_neg(df.high_price, df.low_price, df.close_price)
        df["adx_pos"] = adx_pos(df.high_price, df.low_price, df.close_price)
        
        if not backtest:
            df = df.loc[df["date"] > str(today_date)]
        
        df["bollinger_signal"] = "No Signal"
        df.loc[(df["close_price"] > df["high_band"]), "bollinger_signal"] = "SELL"
        df.loc[(df["close_price"] < df["low_band"]), "bollinger_signal"] = "BUY"
        try:
            df = df.drop(index=list(range(75,80)))
        except:
            df = pd.DataFrame()

        if not df.empty:
            try:
                if entry_type == "SELL":
                    bollinger_crossover = df[df.bollinger_signal.str.endswith("SELL")].iloc[-1]
                elif entry_type == "BUY":
                    bollinger_crossover = df[df.bollinger_signal.str.endswith("BUY")].iloc[-1]
            except:
                bollinger_crossover = pd.Series()

            if not bollinger_crossover.empty:
                if bollinger_crossover.adx <= 23:
                    response = self.make_response(stock, entry_type, float(bollinger_crossover.close_price), bollinger_crossover.date, backtest, 15, **kwargs)
                    return response
            return "Crossover Not Found"
        return "Dataframe not created"

celery_app.tasks.register(AdxBollingerCrossover)

class StochasticMacdSameTimeCrossover(BaseEntryStrategy):
    """This strategy is for future/equity long, future short position trade where it will find
    trading opportunity for hourly or 30 Minute candle, Combination of stochastic, macd and bollinger band """
    name = "find_stochastic_macd_same_time_crossover"
    queue = "strategy"
    strategy_type = "Entry"

    def create_dataframe(self, data:str, backtest=False, **kwargs):
        """Create pandas dataframe for backtesting and live analysis only
        Parameter:
        data : Json Data"""
        df = super(StochasticMacdSameTimeCrossover, self).create_dataframe(data, backtest, **kwargs)
        candle_type = kwargs.get("candle_type")
        symbol = kwargs.get("symbol")
        if not backtest and candle_type in ["1H", "M30"]:
            today_date = get_local_time().date()
            queryset = symbol.get_stock_data(days=40, end_date=today_date)
            df = symbol.get_stock_dataframe(queryset, candle_type=candle_type)
        return df


    def find_stochastic_macd_same_time_crossover(self, stock_id, entry_type, backtest=False, backtesting_candles_cache_key=None, **kwargs):
        stock = Symbol.objects.get(id=stock_id)
        today_date = get_local_time().date()
        df = self.create_dataframe(backtesting_candles_cache_key, backtest, **{"symbol": stock, "with_live_candle": False, "candle_type": kwargs.get("candle_type", "1H"), "head_count": kwargs.get("head_count")})
        df["macd"] = macd(df.close_price)
        df["macd_signal"] = macd_signal(df.close_price)
        df["macd_crossover"] = np.where(df.macd < df.macd_signal, "SELL", "BUY")
        df["medium_band"] = bollinger_mavg(df.close_price)
        df.loc[(df["macd_crossover"] != df["macd_crossover"].shift()) & (df["macd_crossover"] == "BUY"), "macd_crossover"] = "BUY_CROSSOVER"
        df.loc[(df["macd_crossover"] != df["macd_crossover"].shift()) & (df["macd_crossover"] == "SELL"), "macd_crossover"] = "SELL_CROSSOVER"
        df["stoch"] = stoch(high=df.high_price, close=df.close_price, low=df.low_price)
        df["stoch_signal"] = stoch_signal(high=df.high_price, close=df.close_price, low=df.low_price)
        df["stochastic_crossover"] = np.where(df.stoch < df.stoch_signal, "SELL", "BUY")
        df.loc[(df["stochastic_crossover"].shift() == "BUY") & (df["stochastic_crossover"] == "SELL") & (df["stochastic_crossover"].shift(-1) == "BUY"), "stochastic_crossover"] = "BUY"
        df.loc[(df["stochastic_crossover"].shift() == "SELL") & (df["stochastic_crossover"] == "BUY") & (df["stochastic_crossover"].shift(-1) == "SELL"), "stochastic_crossover"] = "SELL"
        df.loc[(df["stochastic_crossover"] != df["stochastic_crossover"].shift()) & (df["stochastic_crossover"] == "BUY"), "stochastic_crossover"] = "BUY_CROSSOVER"
        df.loc[(df["stochastic_crossover"] != df["stochastic_crossover"].shift()) & (df["stochastic_crossover"] == "SELL"), "stochastic_crossover"] = "SELL_CROSSOVER"
        df = df.dropna()
        matched_crossover = df[((df["macd_crossover"] == "SELL_CROSSOVER") & (df["stochastic_crossover"] == "SELL_CROSSOVER") | (df["macd_crossover"] == "BUY_CROSSOVER") & (df["stochastic_crossover"] == "BUY_CROSSOVER"))]
        entry_confirmed = False
        confirmed_matched_crossover = matched_crossover[((matched_crossover["macd_crossover"] == "SELL_CROSSOVER") & (matched_crossover["close_price"] < matched_crossover["medium_band"])) | ((matched_crossover["macd_crossover"] == "BUY_CROSSOVER") & (matched_crossover["close_price"] > matched_crossover["medium_band"]))]
        if not confirmed_matched_crossover.empty:
            last_candle = confirmed_matched_crossover.iloc[-1]
            if (last_candle.macd_crossover and last_candle.stochastic_crossover) == "BUY_CROSSOVER" and last_candle.close_price > last_candle.medium_band:
                entry_confirmed = True
            elif (last_candle.macd_crossover and last_candle.stochastic_crossover) == "SELL_CROSSOVER" and last_candle.close_price < last_candle.medium_band:
                entry_confirmed = True
            
            if entry_confirmed:
                response = self.make_response(stock, entry_type, float(last_candle.close_price), last_candle.date, backtest, 20, **kwargs)
                return response
            return "No Entry Found"
        return "No Crossover Found"

celery_app.tasks.register(StochasticMacdSameTimeCrossover)



# class OHLCrossover(BaseStrategyTask):
#     queue = "low_priority"
#     strategy_type = "Entry"
#     strategy_priority = "Support"
#     name = "find_ohl_in_stock"

#     def find_ohl_in_stock(self, stock_id, entry_type, backtest=False, backtesting_candles_data=None):
#         stock = Symbol.objects.get(id=stock_id)
#         today_date = get_local_time().date()
#         df = stock.get_stock_live_data(with_live_candle=False)
        
#         if backtest:
#             df = self.create_backtesting_dataframe(backtesting_candles_data)
        
#         ohl_condition = stock.is_stock_ohl()
#         if ohl_condition:
#             if entry_type == ohl_condition a




# @celery_app.task(queue="low_priority")
# def find_ohl_stocks():
#     """Based on Open high low strategy, it is supporting strategy only"""
#     current_time = get_local_time().time()
#     start_time = time(9,25)
#     if current_time > start_time:
#         cache_key = str(get_local_time().date()) + "_todays_sorted_stocks"
#         sorted_stocks = redis_cache.get(cache_key)
#         if sorted_stocks:
#             todays_timestamps = StrategyTimestamp.objects.select_related("stock", "strategy").filter(indicator__name="OHL", timestamp__date=get_local_time().date())
#             for stock in sorted_stocks:
#                 timestamps = todays_timestamps.filter(stock=stock)
#                 ohl_condition = stock.symbol.is_stock_ohl()
#                 if ohl_condition:
#                     if stock.entry_type == ohl_condition and not timestamps.exists():
#                         ohl_indicator = Indicator.objects.get(name="OHL")
#                         StrategyTimestamp.objects.create(indicator=ohl_indicator, stock=stock, timestamp=get_local_time().now())
#                     elif stock.entry_type != ohl_condition:
#                         timestamps.delete()
#                     elif timestamps.count() > 1:
#                         timestamps.exclude(id=timestamps.first().id).delete()
#             return "OHL Updated"
#         return "No Sorted Stocks Cached"
#     return f"Time {current_time} not > 9:25"


# @celery_app.task(queue="low_priority") # Will Work on These Functions Later
# def is_stock_pdhl(obj_id): 
#     """Based on previouse day high low strategy, supporting strategy"""
#     stock = SortedStocksList.objects.get(id=obj_id)
#     if stock.symbol.is_stock_pdhl() == stock.entry_type:
#         pdhl_indicator = Indicator.objects.get(name="PDHL")
#         pdhl, is_created = StrategyTimestamp.objects.get_or_create(indicator=pdhl_indicator, stock=stock)
#         pdhl.timestamp = get_local_time().now()
#         pdhl.save()
#         return "Stamp Created"

# @celery_app.task(queue="low_priority") # Will Work on These Functions Later
# def has_entry_for_long_short(obj_id):
#     """Entry available of long or short position, Supporting strategy"""
#     stock = SortedStocksList.objects.get(id=obj_id)
#     if stock.symbol.has_entry_for_long_short() == stock.entry_type:
#         long_short_entry = Indicator.objects.get(name="LONGSHORT")
#         long_short, is_created = StrategyTimestamp.objects.get_or_create(indicator=long_short_entry, stock=stock)
#         long_short.timestamp = get_local_time().now()
#         long_short.save()