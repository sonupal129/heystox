from django.db import models
from django.contrib.postgres.fields import JSONField
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Max, Min
import pandas as pd
from django.contrib.auth.models import User
from ta.trend import macd, macd_diff, macd_signal, ema, ema_indicator
from ta.momentum import stoch, stoch_signal
from django.core.cache import cache, caches
from upstox_api.api import *
from heystox_trade import settings
from django.core.cache import caches, cache
# Create your models here.

class MasterContract(models.Model):
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now=True, editable=False)
    modified_at = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return self.name

class Symbol(models.Model):
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
    created_at = models.DateTimeField(auto_now=True, editable=False)
    modified_at = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return self.symbol

    def get_last_trading_day_count(self, today=datetime.today().date()):
        yesterday = today - timedelta(1)
        weekend = ["Sunday", "Saturday"]
        holiday = MarketHoliday.objects.filter(date__lte=today).last().date
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
        return (today - previous_day).days

    def is_stock_ohl(self, date=datetime.now().date(), candle_type="M5"):
        """Find Stock falls in open high low strategy"""
        stock_open_price = self.get_day_opening_price()
        stock_high_price = self.get_days_high_low_price(price_type="HIGH")
        stock_low_price = self.get_days_high_low_price(price_type="LOW")
        if stock_open_price == stock_high_price:
            return "SELL"
        elif stock_open_price == stock_low_price:
            return "BUY"
        else:
            return None
    
    def is_stock_pdhl(self, date=datetime.now().date(), candle_type="M5"):
        """Finds stocks is fall under previous day high low conditions"""
        candles = self.get_stock_data(end_date=date).values()
        df = pd.DataFrame(list(candles))
        previous_trading_day = date - timedelta(self.get_last_trading_day_count(date))
        last_day_candles = df[(df["date"].dt.date.astype(str) == previous_trading_day.strftime("%Y-%m-%d"))]
        last_day_closing_price = float(last_day_candles.iloc[[-1]].close_price)
        last_day_opening_price = float(last_day_candles.iloc[[0]].open_price)
        today_open_price = float(df[(df["date"].dt.date.astype(str) == date.strftime("%Y-%m-%d"))].iloc[[0]].open_price)
        if last_day_opening_price > last_day_closing_price > today_open_price:
            return "SELL"
        elif last_day_opening_price < last_day_closing_price < today_open_price:
            return "BUY"
        else:
            return None

    def get_days_high_low_price(self, start_date=None, end_date=datetime.now().date(), price_type="HIGH", candle_type="M5"):
        start_date = start_date or end_date
        if start_date == end_date:
            candles = self.get_stock_data(days=0)
        else:
            candles = self.get_stock_data(days=(end_date - start_date).days)
        if price_type == "HIGH":
            return candles.aggregate(Max("high_price")).get("high_price__max")
        elif price_type == "LOW":
            return candles.aggregate(Min("low_price")).get("low_price__min")


    def has_entry_for_long_short(self, date=datetime.now().date(), candle_type="M5"):
        stock_date = date
        if self.is_stock_ohl(date=stock_date, candle_type=candle_type) == "BUY":
            if self.get_days_high_low_price(start_date=stock_date - timedelta(1), price_type="HIGH", candle_type=candle_type)\
                < self.get_days_high_low_price(start_date=stock_date, price_type="HIGH", candle_type=candle_type):
                return "BUY"
        elif self.is_stock_ohl(date=stock_date, candle_type=candle_type) == "SELL":
            if self.get_days_high_low_price(start_date=stock_date - timedelta(1), price_type="LOW", candle_type=candle_type)\
                < self.get_days_high_low_price(start_date=stock_date, price_type="LOW", candle_type=candle_type):
                return "SELL"

    def get_day_opening_price(self, date=datetime.now().date()):
        stock_data = self.get_stock_data(end_date=date, days=0)
        if stock_data:
            return stock_data.first().open_price or None

    def get_stock_data(self, days=None, end_date=datetime.now().date(), candle_type="M5", cached=True):
        cache_id = str(end_date) + "_stock_data_" + self.symbol
        redis_cache = cache
        if not cached or not redis_cache.get(cache_id):
            candles = Candle.objects.filter(candle_type=candle_type, date__range=[end_date - timedelta(5), end_date + timedelta(1)], symbol=self)
            redis_cache.set(cache_id, candles, 300)
        else:
            candles = redis_cache.get(cache_id)
        day_count = None
        if days == 0:
            day_count = days
        else:
            day_count = self.get_last_trading_day_count(end_date)
        if day_count > 0:
            start_date = end_date - timedelta(day_count)               
            candles = candles.filter(candle_type=candle_type, date__range=[start_date, end_date + timedelta(1)], symbol=self)
        else:
            candles = candles.filter(candle_type=candle_type, date__date=end_date, symbol=self)
        return candles

    def get_day_closing_price(self, date=datetime.now().date()):
        """function will return last candle closing price"""
        stock_data = self.get_stock_data(end_date=date, days=0)
        if stock_data:
            return stock_data.last().close_price or None

    def get_last_day_closing_price(self):
        return self.last_day_closing_price or None

    def get_last_day_opening_price(self):
        return self.last_day_opening_price or None

    def get_nifty_movement(self, bull_point=32, bear_point=-22 ):
        if self.symbol == "nifty_50":
            movement = self.get_stock_movement()
            if movement >= bull_point:
                return "BUY"
            elif movement <= bear_point:
                return "SELL"
            else:
                return "SIDEWAYS"
        else:
            raise TypeError("This Function is limited to nifty 50 only")

    def get_stock_current_candle(self):
        redis_cache = cache
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
            "atp": current_ticker.get("atp"),
            "total_buy_quantity": current_ticker.get("total_buy_quantity"),
            "total_sell_quantity": current_ticker.get("total_sell_quantity"),
            "lower_circuit": current_ticker.get("lower_circuit"),
            "upper_circuit": current_ticker.get("upper_circuit"),
            "bids": {},
            "asks": {},
            "date": datetime.fromtimestamp(int(current_ticker.get("timestamp")[:10]))
        }
        return df_ticker
      
    def get_stock_live_data(self, is_cache=True):
        today_date = datetime.today().date()
        cache_id = str(today_date) + "_stock_live_data_" + self.symbol
        redis_cache = cache
        if is_cache:
            df = redis_cache.get(cache_id)
        else:
            stock_data = self.get_stock_data(cached=is_cache)
            df = pd.DataFrame(list(stock_data.values("candle_type", "open_price", "high_price", "low_price", "close_price", "volume", "total_buy_quantity", "total_sell_quantity", "date")))
            redis_cache.set(cache_id, df, 300)
        try:
            current_candle_data = self.get_stock_current_candle()
        except:
            current_candle_data = None
        if df is not None:
            if current_candle_data:
                df2 = pd.DataFrame(current_candle_data, index=[0])
                df = pd.concat([df, df2], ignore_index=True)
                return df
            return df

    def get_stock_movement(self, date=datetime.now().date()):    
        """Return Movement of stock in %"""
        try:
            current_price = self.get_stock_live_data().iloc[-1].close_price
            variation = float(current_price) - self.get_last_day_closing_price()
            return variation
        except:
            return None

    def is_stock_moved_good_for_trading(self, movement_percent:float=1.2, date=datetime.now().date()): #Need to work more on this function
        stock_movement = self.get_stock_movement(date=date)
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

class CandleQuerySet(models.QuerySet):
    def get_by_candle_type(self, type_of_candle):
        return self.filter(candle_type=type_of_candle)


class CandleManager(models.Manager):
    def get_queryset(self):
        return CandleQuerySet(self.model, using=self._db).order_by("date")
    
    def get_candles(self, candle_type="M5", date=None):
        if date:
            return self.get_queryset.get_by_candle_type(candle_type, date__gte=date)
        return self.get_queryset().get_by_candle_type(candle_type)

class Candle(models.Model):
    candle_type_choice = {
        ("M5", "5 Minute"),
        ("M10", "10 Minute"),
        ("M15", "15 Minute"),
        ("M60", "60 Minute"),
        ("1D", "1 Day"),
    }
    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE, related_name="candles", null=True)
    candle_type = models.CharField(choices=candle_type_choice, max_length=50, blank=False, null=True, default=None)
    open_price = models.FloatField("Candle Open Price", blank=True, null=True)
    high_price = models.FloatField("Candle High Price", blank=True, null=True)
    low_price = models.FloatField("Candle Low Price", blank=True, null=True)
    close_price = models.FloatField("Candle Close Price", blank=True, null=True)
    volume = models.IntegerField("Volume", blank=True, null=True)
    atp = models.IntegerField("Average Traded Price", blank=True, null=True)
    total_buy_quantity = models.IntegerField("Total Buy Quantity", blank=True, null=True)
    total_sell_quantity = models.IntegerField("Total Sell Quantity", blank=True, null=True)
    lower_circuit = models.IntegerField("Lower Circuit Price", blank=True, null=True)
    upper_circuit = models.IntegerField("Upper Circuit Price", blank=True, null=True)
    bids = JSONField(default=dict)
    asks = JSONField(default=dict)
    date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now=True, editable=False)
    modified_at = models.DateTimeField(auto_now_add=True, editable=False)

    objects = CandleManager()

    def __str__(self):
        return self.symbol.symbol

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="user_profile")
    mobile = models.IntegerField(blank=True, null=True)
    bearable_loss = models.IntegerField("Bearable loss in percent", blank=True, null=False, default=0)
    expected_profit = models.IntegerField("Expected profit in percent", blank=True, null=False, default=0)
    created_at = models.DateTimeField(auto_now=True, editable=False)
    modified_at = models.DateTimeField(auto_now_add=True, editable=False)
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
            user = cache.get(user_email + "_upstox_login_user")
            return user

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
                    pl = Earning.objects.get(user=self, date=datetime.now().date() - timedelta(1))
                except:
                    pl = Earning.objects.create(user=self, date=datetime.now().date() - timedelta(1), opening_balance=self.bank.current_balance)
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

class BankDetail(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name="bank")
    bank_name = models.CharField(max_length=200)
    bank_account_number = models.CharField(max_length=50)
    initial_balance = models.DecimalField(decimal_places=2, max_digits=10, help_text='Initial balance at the starting of month')
    current_balance = models.DecimalField(decimal_places=2, max_digits=10)
    created_at = models.DateTimeField(auto_now=True, editable=False)
    modified_at = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return "{} | {}".format(self.user_profile.__str__(), self.bank_name)

class Credentials(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name="credential", null=True)
    api_key = models.CharField(max_length=150, null=True, blank=True)
    secret_key = models.CharField(max_length=150, null=True, blank=True)
    access_token = models.CharField(max_length=200, null=True, blank=True)
    created_at = models.DateTimeField(auto_now=True, editable=False)
    modified_at = models.DateTimeField(auto_now_add=True, editable=False)

    class Meta:
        verbose_name_plural = "Credentials"

    def __str__(self):
        return str(self.user_profile)

class Earning(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.PROTECT, related_name="earnings", null=True)
    date = models.DateField()
    opening_balance = models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True)
    profit_loss = models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Profit & Loss', null=True, blank=True)
    created_at = models.DateTimeField(auto_now=True, editable=False)
    modified_at = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return "{} | {}".format(self.user.user.get_full_name(), self.date)

    def save(self, *args, **kwargs):
        if self.user.bank:
            if self.user.bank.current_balance:
                self.opening_balance = self.user.bank.current_balance
        super().save(*args, **kwargs)

class SortedStocksList(models.Model):
    entry_choices = {
        ("BUY", "BUY"),
        ("SELL", "SELL"),
        ("SB", "SIDEWAYS_BUY"),
        ("SS", "SIDEWAYS_SELL"),
    }

    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE)
    entry_price = models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True)
    entry_type = models.CharField(max_length=20, choices=entry_choices, default="BUY")
    created_at = models.DateTimeField(auto_now=True, editable=False)
    modified_at = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return "{} | {}".format(self.symbol.__str__(), self.created_at.date())

    def get_first_timestamp(self):
        return self.timestamps.first()

    def get_last_timestamp(self):
        return self.timestamps.last()

    def get_second_last_timestamp(self):
        return self.timestamps.order_by("timestamp").reverse()[1]

    def get_indicator_timestamp(self, indicator_name=None):
        return self.timestamps.filter(indicator__name=indicator_name).order_by("timestamp").last() or None

class Indicator(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)
    value = models.IntegerField()
    created_at = models.DateTimeField(auto_now=True, editable=False)
    modified_at = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return self.name


class StrategyTimestamp(models.Model):
    stock = models.ForeignKey(SortedStocksList, on_delete=models.CASCADE, related_name="timestamps")
    indicator = models.ForeignKey(Indicator, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    diff = models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True)

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

class MarketHoliday(models.Model):
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


class PreMarketOrderData(models.Model):
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
    created_at = models.DateTimeField(auto_now=True, editable=False)
    modified_at = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return self.symbol.symbol + " | " + str(self.created_at.date())


# class PreMarketSymbolOrderBook(models.Model):
#     created_at = models.DateTimeField(auto_now=True, editable=False)
#     modified_at = models.DateTimeField(auto_now_add=True, editable=False)
#     symbol = models.ForeignKey(PreMarketSymbol, on_delete=models.CASCADE, related_name="order_book")
#     price = models.FloatField(blank=True, null=True)
#     buy_qty = models.IntegerField(blank=True, null=True)
#     sell_qty = models.IntegerField(blank=True, null=True)



