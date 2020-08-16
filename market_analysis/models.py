from django.db import models
from market_analysis.imports import *

# Create your models here.

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True

class MasterContract(BaseModel):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class Symbol(BaseModel):
    exchange = models.ForeignKey(MasterContract, related_name="symbols", on_delete=models.DO_NOTHING)
    token = models.IntegerField(blank=True, null=True)
    symbol = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    last_day_closing_price = models.FloatField(blank=True, null=True)
    last_day_opening_price = models.FloatField(blank=True, null=True)
    tick_size = models.FloatField(blank=True, null=True)
    instrument_type = models.CharField(max_length=20, blank=True, null=True)
    isin = models.CharField(max_length=50)
    last_day_vtt = models.IntegerField("Last Day Traded Volume", blank=True, null=True)
    vtt = models.IntegerField("Total Traded Volume", blank=True, null=True)
    total_buy_quantity = models.IntegerField("Total Buy Quantity", blank=True, null=True)
    total_sell_quantity = models.IntegerField("Total Sell Quantity", blank=True, null=True)
    trade_manually = MultiSelectField(choices={("BUY", "BUY"), ("SELL", "SELL")}, blank=True, null=True)

    class Meta:
        unique_together = ("symbol", "exchange")

    def __str__(self):
        return self.symbol

    def get_strategies(self, strategy_type="Entry", entry_type="BUY", cached=True):
        """Return Deployed Strategy Objects"""
        strategy_choice = {
            "Entry" : "ET",
            "Exit" : "EX"
        }
        cache_key = "_".join([self.symbol, strategy_type, "strategies"])
        cached_value = redis_cache.get(cache_key)
        if cached_value != None and cached:
            return cached_value
        strategies = self.deployed_strategies.filter(strategy__strategy_type=strategy_choice.get(strategy_type), active=True, entry_type=entry_type).prefetch_related("strategy")
        if strategies.exists():
            redis_cache.set(cache_key, strategies, 60*60*24)
        return strategies

    def get_last_backtesting_log(self, strategy_name, timeframe, entry_type):
        qs = BacktestLogs.objects.filter(entry_type=entry_type, strategy_name=strategy_name, symbol_name=self.symbol, candle_type=timeframe)
        if qs.exists():
            return qs.last()
        return None

    def get_backtested_data(self, cache_key):
        cached_value = redis_cache.get(cache_key)
        dict_keys = ['start_date', 'end_date', 'symbol', 'strategy_name', 'candle_type', 'entry_type']
        if cached_value != None:
            return pd.DataFrame(list(cached_value.values()))
        new_obj = cache_key.split("_")
        new_obj.pop(-1)
        obj_dict = dict(zip(dict_keys, new_obj))
        obj_dict["start_date"] = datetime.strptime(obj_dict.get("start_date"), "%Y-%m-%d")
        obj_dict["end_date"] = datetime.strptime(obj_dict.get("end_date"), "%Y-%m-%d")
        reports = BacktestReport.objects.filter(entry_time__range=[obj_dict["start_date"], obj_dict["end_date"]],
                                                strategy_name=obj_dict["strategy_name"], symbol_name=obj_dict["symbol"],
                                                candle_type=obj_dict["candle_type"], entry_type=obj_dict["entry_type"])
        if reports.exists():
            redis_cache.set(cache_key, reports, 15*20*12*2*3)
        return pd.DataFrame(list(reports.values()))
        

    def get_last_trading_day_count(self, date_obj=None):
        """date_obj should be date only, return last trading day count from today"""
        if date_obj == None:
            date_obj = get_local_time().date()
        yesterday = date_obj - timedelta(1)
        weekend = ["Sunday", "Saturday"]
        holiday = MarketHoliday.objects.filter(date__lte=date_obj).last().date
        last_holiday = holiday
        previous_day = yesterday
        while previous_day.strftime("%A") in weekend or previous_day == holiday:
            previous_day = previous_day - timedelta(1)
            try:
                holiday = MarketHoliday.objects.get(date=previous_day).date
                last_holiday = holiday
            except:
                holiday = last_holiday
        if yesterday == previous_day:
            return  1
        return (date_obj - previous_day).days

    def get_stock_data(self, days=None, end_date=None, candle_type="M5", cached=True):
        if end_date == None:
            end_date = get_local_time().date()
        cache_id = "_".join([ str(end_date), str(days), self.symbol, candle_type, "stock_data" ])
        cached_value = redis_cache.get(cache_id)
        if cached_value != None and cached:
            candles = cached_value
        else:
            if days and days > 0:
                candles = Candle.objects.filter(candle_type=candle_type, date__range=[end_date - timedelta(days), end_date + timedelta(1)], symbol=self)
            else:
                candles = Candle.objects.filter(candle_type=candle_type, date__range=[end_date - timedelta(5), end_date + timedelta(1)], symbol=self)
            redis_cache.set(cache_id, candles, 300)
        day_count = None
        if days and days >= 0:
            day_count = days
        else:
            day_count = self.get_last_trading_day_count(end_date)
        
        if day_count > 0:
            start_date = end_date - timedelta(day_count)               
            candles = candles.filter(candle_type=candle_type, date__range=[start_date, end_date + timedelta(1)], symbol=self)
        else:
            candles = candles.filter(candle_type=candle_type, date__date=end_date, symbol=self)
        return candles

    def get_stock_current_candle(self):
        """By default this function will fetch 5 minute candle"""
        cached_data = redis_cache.get(self.symbol)
        if len(cached_data) == 1:
            first_ticker = cached_data[0]
            current_ticker = cached_data[0]
        elif len(cached_data) == 2:
            first_ticker, current_ticker = cached_data
        elif len(cached_data) > 2:
            first_ticker, *rest_ticker, current_ticker = cached_data
        df_ticker = {
            "candle_type": "M5",
            "open_price": first_ticker.get("open"),
            "high_price": max(data.get("high") for data in cached_data),
            "close_price": current_ticker.get("close"),
            "low_price": min(data.get("low") for data in cached_data),
            "volume": sum(data.get("volume") for data in cached_data),
            # "atp": current_ticker.get("atp"),
            "total_buy_quantity": current_ticker.get("total_buy_quantity"),
            "total_sell_quantity": current_ticker.get("total_sell_quantity"),
            # "lower_circuit": current_ticker.get("lower_circuit"),
            # "upper_circuit": current_ticker.get("upper_circuit"),
            # "bids": {},
            # "asks": {},
            "date": get_local_time().fromtimestamp(int(current_ticker.get("timestamp")[:10]))
        }
        return df_ticker

    def get_stock_live_price(self, price_type):
        """Fetch stock realtime cached ticker data or 
        1 minute latency in data"""
        data = None
        try:
            user = UserProfile.objects.get(user__email="sonupal129@gmail.com").get_upstox_user()
            user.get_master_contract(self.exchange.name.upper())
            data = user.get_live_feed(user.get_instrument_by_symbol(self.exchange.name.upper(), self.symbol.upper()), LiveFeedType.Full)
        except:
            pass
        if data:
            return data.get("ltp", None)
        current_ticker = redis_cache.get(self.symbol)[-1]
        return current_ticker.get(price_type, None)

    def get_stock_dataframe(self, candle_queryset, candle_type="M5"):
        candles_type = {
            "M5" : "5T",
            "M10" : "10T",
            "M15" : "15T",
            "M30" : "30T",
            "1H" : "60T",
            # "2H" : "120T",
            # "3H" : "180T",
            "1D" : "1D",
            }

        if not isinstance(candle_queryset, QuerySet):
            raise TypeError("candle_queryset is not a itearable queryset")
        
        candles = candle_queryset.values("open_price", "high_price", "low_price", "close_price", "volume", "date")
        candle_type_timing = candles_type.get(candle_type, "5T")
        df = pd.DataFrame(candles)
        if not df.empty:
            df = df.set_index("date")
            candle_open = df.open_price.resample(candle_type_timing, base=15).first()
            candle_close = df.close_price.resample(candle_type_timing, base=15).last()
            candle_high = df.high_price.resample(candle_type_timing, base=15).max()
            candle_low = df.low_price.resample(candle_type_timing, base=15).min()
            candle_volume = df.volume.resample(candle_type_timing, base=15).last()
            new_df = pd.concat([candle_open, candle_close, candle_high, candle_low, candle_volume], axis=1, keys=["open_price", "close_price", "high_price", "low_price", "volume"])
            new_df["date"] = new_df.index
            new_df.index = np.arange(0, len(new_df))
            new_df = new_df.dropna()
            new_df["candle_type"] = candles_types.get(candle_type) if candle_type_timing != "5T" else candles_types.get("M5")
            new_df = new_df.reset_index().drop("index", axis=1)
            return new_df


    def get_stock_live_data(self, date_obj=None, with_live_candle=True, candle_type="M5"):
        if date_obj == None:
            date_obj = get_local_time().date()
        stock_data = self.get_stock_data(end_date=date_obj)
        df = self.get_stock_dataframe(stock_data, candle_type=candle_type)
        if with_live_candle:
            try:
                current_candle_data = self.get_stock_current_candle()
            except:
                current_candle_data = None
            if df is not None and current_candle_data != None:
                df2 = pd.DataFrame(current_candle_data, index=[0])
                df1 = pd.concat([df, df2], ignore_index=True, sort=False)
                return df1
        return df

    def get_day_opening_price(self, date_obj=None):
        if date_obj == None:
            date_obj = get_local_time().date()
        stock_data = self.get_stock_data(end_date=date_obj, days=0)
        if stock_data:
            return stock_data.first().open_price or None

    def get_day_closing_price(self, date_obj=None):
        """function will return last candle closing price"""
        if date_obj == None:
            date_obj = get_local_time().date()
        stock_data = self.get_stock_data(end_date=date_obj, days=0)
        if stock_data:
            return stock_data.last().close_price or None

    def get_last_day_closing_price(self):
        return self.last_day_closing_price or None

    def get_last_day_opening_price(self):
        return self.last_day_opening_price or None
    
    def get_days_high_low_price(self, date_obj=None, price_type="HIGH", candle_type="M5"):
        if date_obj == None:
            date_obj = get_local_time().date()
        days = 0
        if date_obj != get_local_time().date():
            days = (get_local_time().date() - date_obj).days
        candles = self.get_stock_data(days=days, end_date=date_obj)
        if price_type == "HIGH":
            return candles.aggregate(Max("high_price")).get("high_price__max")
        elif price_type == "LOW":
            return candles.aggregate(Min("low_price")).get("low_price__min")

    def is_stock_ohl(self, date_obj=None, candle_type="M5"):
        """Find Stock falls in open high low strategy"""
        if date_obj == None:
            date_obj = get_local_time().date()
        stock_open_price = self.get_day_opening_price(date_obj=date_obj)
        stock_high_price = self.get_days_high_low_price(price_type="HIGH", date_obj=date_obj)
        stock_low_price = self.get_days_high_low_price(price_type="LOW", date_obj=date_obj)
        if stock_open_price == stock_high_price:
            return "SELL"
        elif stock_open_price == stock_low_price:
            return "BUY"
        else:
            return None
    
    def get_stock_movement(self, date_obj=None):    
        """Return Movement of stock in %"""
        if date_obj == None:
            date_obj = get_local_time().date()
        try:
            if date_obj != get_local_time().date():
                day_closing_price = self.get_day_closing_price(date_obj=date_obj)
                trading_day = self.get_last_trading_day_count(date_obj=date_obj)
                previous_day_closing_price = self.get_day_closing_price(date_obj=date_obj-timedelta(trading_day))
            else:
                day_closing_price = self.get_stock_live_data().iloc[-1].close_price    
                previous_day_closing_price = self.get_last_day_closing_price()
            variation = float(day_closing_price) - previous_day_closing_price
            return variation
        except:
            return None

    def get_nifty_movement(self, bull_point=32, bear_point=-22, date_obj=None):
        if date_obj == None:
            date_obj = get_local_time().date()
        if self.symbol == "nifty_50":
            movement = self.get_stock_movement(date_obj=date_obj)
            if movement >= bull_point:
                return "BUY"
            elif movement <= bear_point:
                return "SELL"
            else:
                return "SIDEWAYS"
        else:
            raise TypeError("This Function is limited to nifty 50 only")

    def is_stock_moved_good_for_trading(self, movement_percent:float): #Need to work more on this function
        """This function will check if stock moved good for trading or not, work on current data only"""
        stock_movement = self.get_stock_movement()
        stock_closing_price_movement_percent = self.get_last_day_closing_price() * movement_percent / 100
        if stock_movement:
            if movement_percent > 0:
                if stock_movement >= stock_closing_price_movement_percent:
                    return True
                else:
                    return False
            elif movement_percent < 0:
                if stock_movement <= stock_closing_price_movement_percent:
                    return True
                else:
                    return False

    def is_stock_pdhl(self, date_obj=None, candle_type="M5"):
        """Finds stocks is fall under previous day high low conditions"""
        if date_obj == None:
            date_obj = get_local_time().date()
        previous_trading_day = self.get_last_trading_day_count(date_obj)
        last_day_closing_price = self.get_day_closing_price(date_obj=date_obj - timedelta(previous_trading_day))
        last_day_opening_price = self.get_day_opening_price(date_obj=date_obj - timedelta(previous_trading_day))
        today_open_price = self.get_day_opening_price(date_obj=date_obj)
        if last_day_opening_price > last_day_closing_price > today_open_price:
            return "SELL"
        elif last_day_opening_price < last_day_closing_price < today_open_price:
            return "BUY"
        else:
            return None

    def has_entry_for_long_short(self, date_obj=None, candle_type="M5"):
        if date_obj == None:
            date_obj = get_local_time().date()
        if self.is_stock_ohl(date_obj=date_obj, candle_type=candle_type) == "BUY":
            if self.get_days_high_low_price(date_obj=date_obj - timedelta(1), price_type="HIGH", candle_type=candle_type)\
                < self.get_days_high_low_price(date_obj=date_obj, price_type="HIGH", candle_type=candle_type):
                return "BUY"
        elif self.is_stock_ohl(date_obj=date_obj, candle_type=candle_type) == "SELL":
            if self.get_days_high_low_price(date_obj=date_obj - timedelta(1), price_type="LOW", candle_type=candle_type)\
                < self.get_days_high_low_price(date_obj=date_obj, price_type="LOW", candle_type=candle_type):
                return "SELL"

    def get_sorted_stock(self, entry_type:str, date_obj=None):
        if date_obj == None:
            date_obj = get_local_time().date()
        try:
            sorted_stock = self.sorted_stocks.get(created_at__date=date_obj, entry_type=entry_type)
            return sorted_stock
        except:
            return None
        

class CandleQuerySet(models.QuerySet):
    def get_by_candle_type(self, type_of_candle):
        return self.filter(candle_type=type_of_candle)


class CandleManager(models.Manager):
    def get_queryset(self):
        return CandleQuerySet(self.model, using=self._db).order_by("date")
    

class Candle(BaseModel):
    candle_type_choice = {(k,v) for k,v in candles_types.items()}

    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE, related_name="candles", null=True)
    candle_type = models.CharField(choices=candle_type_choice, max_length=50, blank=False, null=True, default=None)
    open_price = models.FloatField("Candle Open Price", blank=True, null=True)
    high_price = models.FloatField("Candle High Price", blank=True, null=True)
    low_price = models.FloatField("Candle Low Price", blank=True, null=True)
    close_price = models.FloatField("Candle Close Price", blank=True, null=True)
    volume = models.BigIntegerField("Volume", blank=True, null=True)
    atp = models.IntegerField("Average Traded Price", blank=True, null=True)
    total_buy_quantity = models.IntegerField("Total Buy Quantity", blank=True, null=True)
    total_sell_quantity = models.IntegerField("Total Sell Quantity", blank=True, null=True)
    lower_circuit = models.IntegerField("Lower Circuit Price", blank=True, null=True)
    upper_circuit = models.IntegerField("Upper Circuit Price", blank=True, null=True)
    bids = JSONField(default=dict)
    asks = JSONField(default=dict)
    date = models.DateTimeField()

    objects = CandleManager()

    def __str__(self):
        return self.symbol.symbol

class UserProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="user_profile")
    mobile = models.IntegerField(blank=True, null=True)
    bearable_loss = models.IntegerField("Bearable loss in percent", blank=True, null=False, default=0)
    expected_profit = models.IntegerField("Expected profit in percent", blank=True, null=False, default=0)
    for_trade = models.BooleanField(default=False)
    subscribed_historical_api = models.BooleanField(default=False)
    subscribed_live_api = models.BooleanField(default=False)

    def __str__(self):
        return self.user.get_full_name() or self.user.email or self.user.username

    def get_user_email(self):
        return self.user.email

    def get_upstox_user(self):
        """Returns upstox logged in user object"""
        user_email = self.get_user_email()
        if self.user.is_active and self.subscribed_historical_api or self.subscribed_live_api:
            cached_upstox_user = cache.get(user_email + "_upstox_login_user")
            return cached_upstox_user

    def update_initial_balance(self):
        """This function will run on 1st of every month and update balance of user"""
        if self.for_trade and self.subscribed_live_api:
            upstox_user = self.get_upstox_user()
            balance = upstox_user.get_balance()
            current_balance = balance.get("equity").get("available_margin")
            self.bank.initial_balance = current_balance
            self.bank.current_balance = current_balance
            self.bank.save()

    def update_current_earning_balance(self):
        """This function will update daily earnings and current balance of user"""
        if self.for_trade and self.subscribed_live_api:
            upstox_user = self.get_upstox_user()
            balance = upstox_user.get_balance()
            current_balance = balance.get("equity").get("available_margin")
            if self.bank.current_balance != current_balance:
                pl = None
                try:
                    pl = Earning.objects.get(user=self, date=get_local_time().date() - timedelta(1))
                except:
                    pl = Earning.objects.create(user=self, date=get_local_time().date() - timedelta(1), opening_balance=self.bank.current_balance)
                pl.profit_loss = float(current_balance) - float(pl.opening_balance)
                pl.save()
                self.bank.current_balance = current_balance
                self.bank.save(update_fields=["current_balance"])

    def get_authentication_url(self):
        if self.for_trade and self.subscribed_live_api or self.subscribed_historical_api:
            session = Session(self.credential.api_key)
            session.set_redirect_uri(settings.UPSTOX_REDIRECT_URL)
            session.set_api_secret(self.credential.secret_key)
            cache_key = self.get_user_email() + "_upstox_user_session"
            cache.set(cache_key, session)
            login_url = session.get_login_url()
            return login_url


class BankDetail(BaseModel):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name="bank")
    bank_name = models.CharField(max_length=200)
    bank_account_number = models.CharField(max_length=50)
    initial_balance = models.DecimalField(decimal_places=2, max_digits=10, help_text='Initial balance at the starting of month')
    current_balance = models.DecimalField(decimal_places=2, max_digits=10)

    def __str__(self):
        return "{} | {}".format(self.user_profile.__str__(), self.bank_name)

class Credentials(BaseModel):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name="credential", null=True)
    api_key = models.CharField(max_length=150, null=True, blank=True)
    secret_key = models.CharField(max_length=150, null=True, blank=True)
    access_token = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Credentials"

    def __str__(self):
        return str(self.user_profile)

class Earning(BaseModel):
    user = models.ForeignKey(UserProfile, on_delete=models.PROTECT, related_name="earnings", null=True)
    date = models.DateField()
    opening_balance = models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True)
    profit_loss = models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Profit & Loss', null=True, blank=True)

    def __str__(self):
        return "{} | {}".format(self.user.user.get_full_name(), self.date)

    def save(self, *args, **kwargs):
        if self.user.bank:
            if self.user.bank.current_balance:
                self.opening_balance = self.user.bank.current_balance
        super().save(*args, **kwargs)

class SortedStocksList(BaseModel):
    entry_choices = {
        ("BUY", "BUY"),
        ("SELL", "SELL"),
    }

    added_choice = {
        ("AT", "Automatically"),
        ("ML", "Manually")
    }

    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE, related_name="sorted_stocks")
    added = models.CharField(max_length=10, choices=added_choice, default="AT")
    entry_price = models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True)
    entry_type = models.CharField(max_length=20, choices=entry_choices, default="BUY")

    # def clean(self, *args, **kwargs):
    #     today_date = get_local_time().date()
    #     sorted_stocks_count = SortedStocksList.objects.filter(symbol=self.symbol, entry_type=self.entry_type, created_at__date=today_date).count()
        
    #     if sorted_stocks_count == 1:
    #         pass
    #     elif sorted_stocks_count > 1:
    #         raise ValidationError(f"""Sorted stock already available on date '{today_date}' with symbol '{self.symbol}' & entry type '{self.entry_type}'""")
    #     super(SortedStocksList, self).clean   (*args, **kwargs)

    def __str__(self):
        return "{} | {}".format(self.symbol.__str__(), self.created_at.date())

    def get_first_timestamp(self):
        return self.timestamps.first()

    def get_last_timestamp(self):
        return self.timestamps.last()

    def get_second_last_timestamp(self):
        return self.timestamps.order_by("timestamp").reverse()[1]

    def get_strategy_timestamp(self, strategy_name=None):
        return self.timestamps.filter(strategy__strategy_name=strategy_name).order_by("timestamp").last() or None


class StrategyTimestamp(BaseModel):
    stock = models.ForeignKey(SortedStocksList, on_delete=models.CASCADE, related_name="timestamps")
    strategy = models.ForeignKey("DeployedStrategies", on_delete=models.CASCADE, blank=True, null=True)
    timestamp = models.DateTimeField(null=True, blank=True)
    entry_price = models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True)

    def __str__(self):
        return "{} | {}".format(self.stock.__str__(), self.timestamp.time())

    def is_last_timestamp(self):
        if self == self.stock.timestamps.last():
            return True
        return False

    def is_first_timestamp(self):
        if self == self.stock.timestamps.first():
            return True
        return False

class MarketHolidayManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().order_by("date")

class MarketHoliday(BaseModel):
    type_of_holiday = {
        ("PU", "Public Holiday"),
    }

    date = models.DateField()
    holiday_type = models.CharField(choices=type_of_holiday, default="PU", max_length=15)

    objects = MarketHolidayManager()
    
    def __str__(self):
        return str(date)

    # def is_today_holiday(self):
    #     today = datetime.today().date()
    #     if self.date == today:
    #         return True
    #     return False


class PreMarketOrderData(BaseModel):
    sector_choices = {
        ("NFTYBNK", "Nifty Bank"),
        ("NFTY", "Nifty")
    }

    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE, related_name="pre_market")
    sector = models.CharField(choices=sector_choices, default="NFTYBNK", max_length=20)
    open_price = models.FloatField(blank=True, null=True)
    change = models.FloatField(blank=True, null=True)
    change_percent = models.FloatField(blank=True, null=True)
    previous_close = models.FloatField(blank=True, null=True)
    buy_qty_ato = models.IntegerField(blank=True, null=True)
    sell_qty_ato = models.IntegerField(blank=True, null=True)
    total_buy_qty = models.IntegerField(blank=True, null=True)
    total_sell_qty = models.IntegerField(blank=True, null=True)
    total_trade_qty = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.symbol.symbol + " | " + str(self.created_at.date())


# class PreMarketSymbolOrderBook(BaseModel):
#     created_at = models.DateTimeField(auto_now=True, editable=False)
#     modified_at = models.DateTimeField(auto_now_add=True, editable=False)
#     symbol = models.ForeignKey(PreMarketSymbol, on_delete=models.CASCADE, related_name="order_book")
#     price = models.FloatField(blank=True, null=True)
#     buy_qty = models.IntegerField(blank=True, null=True)
#     sell_qty = models.IntegerField(blank=True, null=True)


class SortedStockDashboardReport(BaseModel):
    name = models.CharField(blank=True, null=True, max_length=50)
    entry_time = models.DateTimeField(blank=True, null=True)
    exit_time = models.DateTimeField(blank=True, null=True)
    entry_type = models.CharField(blank=True, null=True, max_length=10)
    entry_price = models.FloatField(blank=True, null=True)
    target_price = models.FloatField(blank=True, null=True)
    stoploss_price = models.FloatField(blank=True, null=True)
    exit_price = models.FloatField(blank=True, null=True)
    current_price = models.FloatField(blank=True, null=True)
    pl = models.FloatField(blank=True, null=True)
    
    def __str__(self):
        return self.name
    
    
class OrderBook(BaseModel):
    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE, related_name="order_books")
    date = models.DateField(blank=True, null=True)
    strength = models.CharField(blank=True, max_length=50, null=True)

    def __str__(self):
        return self.symbol.symbol

    def get_first_order_by_status(self, status="CO"):
        """return order based on order status"""
        return self.orders.filter(status=status).first()

    def get_last_order_by_status(self, status="CO"):
        """return order based on order status"""
        return self.orders.filter(status=status).last()


class Order(BaseModel):
    status_choices = {
        ("CA", "Cancelled"),
        ("OP", "Open"),
        ("CO", "Completed"),
        ("RE", "Rejected")
    }

    entry_type_choices = {
        ("ET", "Entry"),
        ("EX", "Exit"),
    }

    transaction_choices = {
        ("BUY", "BUY"),
        ("SELL", "SELL"),
    }

    order_book = models.ForeignKey(OrderBook, on_delete=models.CASCADE, related_name="orders", null=True, blank=True)
    strategy = models.ForeignKey("DeployedStrategies", on_delete=models.SET_NULL, blank=True, null=True, related_name="orders")
    order_id = models.CharField(unique=True, max_length=30)
    entry_time = models.DateTimeField(blank=True, null=True)
    entry_price = models.FloatField(blank=True, null=True)
    target_price = models.FloatField(blank=True, null=True)
    stoploss = models.FloatField(blank=True, null=True)
    quantity = models.IntegerField(blank=True, null=True)
    pl = models.FloatField(blank=True, null=True)
    transaction_type = models.CharField(blank=True, null=True, max_length=10, choices=transaction_choices)
    status = models.CharField(choices=status_choices, max_length=10, default='OP')
    entry_type = models.CharField(choices=entry_type_choices, max_length=10, default='', blank=True)
    message = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        ordering = ["entry_time"]

    def __str__(self):
        return str(self.order_id)

    def get_exit_strategy(self):
        self.strategy.strategy.get_exit_strategy()

    def is_first_order_in_order_book(self, status="CO"):
        if self.order_id == self.order_book.get_first_order_by_status(status).order_id:
            return True
        return False

    def is_last_order_in_order_book(self, status="CO"):
        if self.order_id == self.order_book.get_last_order_by_status(status).order_id:
            return True
        return False


class Strategy(BaseModel):
    strategy_choices = {
        ("ET", "Entry"),
        ("EX", "Exit"),
    }

    priority_choices = {
        ("PR", "Primary"),
        ("SC", "Secondary"),
        ("SP", "Support")
    }

    candle_type_choice = {(k,v) for k,v in candles_types.items()}
        
    strategy_name = models.CharField(max_length=200, blank=True, null=True)
    strategy_location = models.CharField(max_length=500)
    strategy_type = models.CharField(max_length=20, choices=strategy_choices, default="ET")
    priority_type = models.CharField(max_length=20, choices=priority_choices, default="SU")
    timeframe = MultiSelectField(choices=candle_type_choice, blank=True, null=True)
    strategy_for = models.CharField(max_length=10, choices={(k,v) for k,v in strategies_for.items()}, default="EI")
    exit_strategy = models.ForeignKey("self", related_name="strategy", blank=True, null=True, limit_choices_to={"strategy_type": "EX"}, on_delete=models.CASCADE)
    backtesting_ready = models.BooleanField(default=False, help_text="Check if you think that strategy is ready for backtesting, Please use this function carefully as this put burden on server")
    description = models.TextField(max_length=1000, blank=True, null=True)

    def __str__(self):
        return self.get_strategy_name()

    def __init__(self, *args, **kwargs):
        super(Strategy, self).__init__(*args, **kwargs)
        self._backtesting_ready = self.backtesting_ready


    def clean(self, *args, **kwargs):
        if self.strategy_type == "EX" and self.exit_strategy:
            raise ValidationError("Exit strategy can't assign, when strategy type is already exit strategy")
        backtest_start_time = time(16,30)
        backtest_end_time = time(7,30)
        current_day = get_local_time()
        if current_day.weekday() not in [5,6] and self.backtesting_ready != self._backtesting_ready:
            if not (current_day.time() < backtest_start_time or current_day.time() > backtest_end_time):
                raise ValidationError("Backtesting is only allowed after market hours, Please try after 4:30 PM")
        super(Strategy, self).clean(*args, **kwargs)

    def get_strategy_name(self):
        return self.strategy_name.replace("_", " ").strip().title()

    def get_strategy(self):
        func_module = importlib.import_module(self.strategy_location)  
        st_func = getattr(func_module, self.strategy_name)
        if callable(st_func):
            return st_func()
        raise TypeError("Strategy class is not callable")

    def get_exit_strategy(self):
        """Function will return exit strategy of strategy if not strategy assigned then return GlobalExitStrategy"""
        if self.strategy_type == "EX":
            raise AlreadyExitStrategyError("Strategy is already Exit strategy")
        if self.exit_strategy:
            func_module = importlib.import_module(self.exit_strategy.strategy_location)
            st_func = getattr(func_module, self.exit_strategy.strategy_name)
        else:
            func_module = importlib.import_module("market_analysis.tasks.strategies.intraday_exit_strategies")
            st_func = getattr(func_module, "GlobalExitStrategy")
        if callable(st_func):
            return st_func()
        raise TypeError("Strategy class is not callable")


class DeployedStrategies(BaseModel):
    candle_type_choice = {(k,v) for k,v in candles_types.items()}

    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE, related_name="deployed_strategies")
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE, limit_choices_to={"strategy_type": "ET"})
    timeframe = models.CharField(choices=candle_type_choice, max_length=5, default="M5")
    entry_type = models.CharField(default="BUY", max_length=10, choices={
        ("BUY", "BUY"), ("SELL", "SELL") })
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Deployed Strategies"
        unique_together = ("symbol", "strategy", "timeframe", "entry_type")

    def __str__(self):
        return " | ".join([self.symbol.symbol, str(self.strategy), str(self.timeframe), str(self.entry_type)])
    
    def call_entry_strategy(self, **kwargs):
        strategy = self.strategy.get_strategy()
        kwargs["candle_type"] = self.timeframe
        kwargs["entry_type"] = self.entry_type
        strategy.delay(**kwargs)
        return True

    def call_exit_strategy(self, **kwargs):
        exit_strategy = self.strategy.get_exit_strategy()
        kwargs["candle_type"] = self.timeframe
        kwargs["entry_type"] = self.entry_type
        exit_strategy.delay(**kwargs)
        return True

    
class BacktestReport(BaseModel):
    symbol_name = models.CharField(max_length=100)
    strategy_name = models.CharField(max_length=100)
    entry_price = models.DecimalField(decimal_places=2, max_digits=5)
    entry_time = models.DateTimeField()
    stoploss = models.DecimalField(decimal_places=2, max_digits=5, blank=True)
    target = models.DecimalField(decimal_places=2, max_digits=5, blank=True)
    strategy_status = models.CharField(max_length=50)
    exit_price = models.DecimalField(decimal_places=2, max_digits=5)
    exit_time = models.DateTimeField()
    entry_type = models.CharField(max_length=10)
    candle_type = models.CharField(max_length=20)
    pl = models.DecimalField(decimal_places=2, max_digits=5)
    
    def __str__(self):
        return " | ".join([self.symbol_name, self.strategy_name, str(self.entry_time)])


class BacktestLogs(BaseModel):
    candle_type = models.CharField(max_length=20)
    strategy_name = models.CharField(max_length=100)
    symbol_name = models.CharField(max_length=100)
    entry_type = models.CharField(max_length=10)
    backtest_date = models.DateField(auto_now_add=True, editable=False)
 
    def __str__(self):
        return " | ".join([self.symbol_name, self.strategy_name, self.candle_type])
    