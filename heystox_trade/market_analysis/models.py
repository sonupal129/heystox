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

    def is_stock_ohl(self, date=datetime.now().date(), candle_type="M5"):
        """Find Stock falls in open high low strategy"""
        candles = self.get_stock_data().values()
        if candles:
            df = pd.DataFrame(list(candles))
            first_candle_price = df.loc[[0], ["open_price", "high_price", "low_price", "close_price"]]
            current_candle_price = df.loc[:, ["open_price", "high_price", "low_price", "close_price"]]
            if float(first_candle_price.open_price) == float(max(current_candle_price.max().values)):
                return "SELL"
            elif float(first_candle_price.open_price) == float(min(current_candle_price.min().values)):
                return "BUY"
            else:
                return None
        return None
    
    def is_stock_pdhl(self, date=datetime.now().date(), candle_type="M5"):
        """Finds stocks is fall under previous day high low conditions"""
        yesterday = date - timedelta(1)
        candles = self.get_stock_data(days=1).values()
        
        df = pd.DataFrame(list(candles))
        last_day_candles = df[(df.date <= date)]
        last_day_closing_price = float(last_day_candles.iloc[[-1]].close_price)
        last_day_opening_price = float(last_day_candles.iloc[[0]].open_price)
        today_open_price = float(df[(df.date >= date)].iloc[[0]].open_price)
        if last_day_opening_price > last_day_closing_price > today_open_price:
            return "SELL"
        elif last_day_opening_price < last_day_closing_price < today_open_price:
            return "BUY"
        else:
            return None

    def get_days_high_low_price(self, start_date=None, end_date=datetime.now().date(), price_type="HIGH", candle_type="M5"):
        start_date = start_date or datetime.now().date()
        if start_date == end_date:
            candles = Candle.objects.filter(symbol=self, candle_type=candle_type, date__date=start_date)
        else:
            candles = Candle.objects.filter(symbol=self, candle_type=candle_type, date__range=[start_date, end_date + timedelta(1)])
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
        opening_price = self.get_stock_data(end_date=date).first().open_price
        return opening_price

    def get_stock_data(self, days=None, end_date=datetime.now().date(), candle_type="M5"):
        if days:
            start_date = end_date - timedelta(days)               
            candles = Candle.objects.filter(candle_type=candle_type, date__range=[start_date, end_date + timedelta(1)], symbol=self)
        else:
            candles = Candle.objects.filter(candle_type=candle_type, date__date=end_date, symbol=self)
        return candles

    def get_day_closing_price(self, date=datetime.now().date()):
        """function will return last candle closing price"""
        closing_price = self.get_stock_data(end_date=date).last().close_price
        return closing_price

    def get_last_day_closing_price(self):
        return self.last_day_closing_price or None

    def get_last_day_opening_price(self):
        return self.last_day_opening_price or None

    def get_nifty_movement(self):
        if self.symbol == "nifty_50":
            current_price = self.get_stock_live_data().iloc[-1].close_price
            diff = int(current_price) - self.last_day_closing_price
            if diff >= 32:
                return "BUY"
            elif diff <= -22:
                return "SELL"
            else:
                return "SIDEWAYS" 
        else:
            raise TypeError("This Function is limited to nifty 50 only")

    def get_stock_current_candle(self):
        redis_cache = caches["redis"]
        cached_data = redis_cache.get(self.symbol)
        if len(cached_data) == 1:
            first_ticker = cached_data
            current_ticker = cached_data
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
            "volume": current_ticker.get("vtt"),
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
      
    def get_stock_live_data(self):
        today = datetime.today().date()
        if today.weekday() == 0:
            stock_data = self.get_stock_data(days=3)
        else:
            stock_data = self.get_stock_data(days=1)
        try:
            current_candle_data = self.get_stock_current_candle()
        except:
            current_candle_data = None
        df1 = pd.DataFrame(list(stock_data.values("candle_type", "open_price", "high_price", "low_price", "close_price", "volume", "total_buy_quantity", "total_sell_quantity", "date")))
        if current_candle_data:
            df2 = pd.DataFrame(current_candle_data, index=[0])
            df = pd.concat([df1, df2], ignore_index=True)
            return df
        return df1

    def get_stock_movement(self, date=datetime.now().date()):     
        """Return Movement of stock in %"""
        current_price = self.get_stock_live_data().iloc[-1].close_price
        try:
            variation = int(current_price) - self.last_day_closing_price
            return variation
        except:
            return None

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
        ("SELL", "SELL")
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

      