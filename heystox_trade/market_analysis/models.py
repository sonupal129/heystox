from django.db import models
from django.contrib.postgres.fields import JSONField
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Max, Min
import pandas as pd
from django.contrib.auth.models import User
from ta.trend import macd, macd_diff, macd_signal, ema, ema_indicator
from ta.momentum import stoch, stoch_signal


# Create your models here.

class BaseModel(models.Model):
      created_at = models.DateTimeField(auto_now=True, editable=False)
      modified_at = models.DateTimeField(auto_now_add=True, editable=False)



# class TickerData(models.Model):
#       timestamp = models.IntegerField(blank=True, null=True)
#       exchange = models.CharField(blank=True, null=True)
#       symbol = models.CharField(blank=True, null=True)
#       ltp = models.IntegerField("Last Traded Price", blank=True, null=True)
#       open_price = models.IntegerField("Last Traded Price", blank=True, null=True)
#       high_price = models.IntegerField("Last Traded Price", blank=True, null=True)
#       low_price = models.IntegerField("Last Traded Price", blank=True, null=True)
#       close_price = models.IntegerField("Last Traded Price", blank=True, null=True)
#       vtt = models.IntegerField("Last Traded Price", blank=True, null=True)
#       atp = models.IntegerField("Last Traded Price", blank=True, null=True)
#       oi = models.IntegerField("Last Traded Price", blank=True, null=True)
#       spot_price = models.IntegerField("Last Traded Price", blank=True, null=True)
#       total_buy_quantity = models.IntegerField("Last Traded Price", blank=True, null=True)
#       total_sell_quantity = models.IntegerField("Last Traded Price", blank=True, null=True)
#       lower_circuit = models.IntegerField("Last Traded Price", blank=True, null=True)
#       upper_circuit = models.IntegerField("Last Traded Price", blank=True, null=True)
#       bids = JSONField()
#       asks = JSONField()
#       ltt = models.IntegerField("Last Traded Price", blank=True, null=True)

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
      last_day_vtt = models.IntegerField("Last Traded Price", blank=True, null=True)
      vtt = models.IntegerField("Last Traded Price", blank=True, null=True)
      total_buy_quantity = models.IntegerField("Last Traded Price", blank=True, null=True)
      total_sell_quantity = models.IntegerField("Last Traded Price", blank=True, null=True)
      created_at = models.DateTimeField(auto_now=True, editable=False)
      modified_at = models.DateTimeField(auto_now_add=True, editable=False)

      def __str__(self):
            return self.symbol

      def is_stock_ohl(self, date=datetime.now().date(), candle_type="M5"):
            """Find Stock falls in open high low strategy"""
            candles = Candle.objects.filter(symbol=self, candle_type=candle_type, date__date=date).values()
            df = pd.DataFrame(list(candles))
            first_candle_price = df.loc[[0], ["open_price", "high_price", "low_price", "close_price", "date"]]
            current_candle_price = df.loc[:, ["open_price", "high_price", "low_price", "close_price"]]
            if float(first_candle_price.open_price) == float(max(current_candle_price.max().values)):
                  return "SELL"
            elif float(first_candle_price.open_price) == float(min(current_candle_price.min().values)):
                  return "BUY"
            else:
                  return None
      
      def is_stock_pdhl(self, date=datetime.now().date(), candle_type="M5"):
            """Finds stocks is fall under previous day high low conditions"""
            yesterday = date - timedelta(1)
            candles = Candle.objects.filter(symbol=self, candle_type=candle_type, date__range=[yesterday, date + timedelta(1)]).values()
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
                  candles = Candle.objecs.filter(symbol=self, candle_type=candle_type, date__range=[start_date, end_date + timedelta(1)])
            if price_type == "HIGH":
                  return candles.aggregate(Max("high_price"))
            elif price_type == "LOW":
                  return candles.aggregate(Min("low_price"))


      def has_entry_for_long_short(self, date=datetime.now().date(), candle_type="M5"):
            stock_date = date
            if self.is_stock_ohl(date=stock_date, candle_type=candle_type) == "BUY":
                  if get_days_high_low_price(start_date=stock_date - timedelta(1), price_type="HIGH", candle_type=candle_type)\
                        < get_days_high_low_price(start_date=stock_date, price_type="HIGH", candle_type=candle_type):
                        return "BUY"
            elif self.is_stock_ohl(date=stock_date, candle_type=candle_type) == "SELL":
                  if get_days_high_low_price(start_date=stock_date - timedelta(1), price_type="LOW", candle_type=candle_type)\
                        < get_days_high_low_price(start_date=stock_date, price_type="LOW", candle_type=candle_type):
                        return "SELL"

      def get_day_opening_price(self, date=datetime.now()):
            opening_price = Candle.objects.filter(symbol=self, date__date=date.date()).first().open_price
            return opening_price

      def get_day_closing_price(self, date=datetime.now()):
            """function will return last candle closing price"""
            closing_price = Candle.objects.filter(symbol=self, date__date=date.date()).last().close_price
            return closing_price

      def get_stock_data(self, days=None, end_date=datetime.now().date(), candle_type="M5"):
            if days:
                  start_date = end_date - timedelta(days)               
                  candles = Candle.objects.filter(candle_type=candle_type, date__range=[start_date, end_date + timedelta(1)], symbol=self)
            else:
                 candles = Candle.objects.filter(candle_type=candle_type, date__date=end_date, symbol=self)
            return candles

      def get_stock_movement(self, date=datetime.now()):     
            """Return Movement of stock in %"""
            current_price = Candle.objects.filter(symbol=self, date__date=date.date()).last().close_price
            variation = current_price - self.last_day_closing_price
            return variation / self.last_day_closing_price * 100

      def get_nifty_movement(self, data=datetime.now()):
            if self.symbol == "nifty_50":
                  current_price = Candle.objects.filter(symbol=self, date__date=date.date()).last().close_price
                  diff = current_price - self.last_day_closing_price
                  if diff >= 32:
                        return "BUY"
                  elif diff <= -32:
                        return "SELL"
                  else:
                        return "SIDEWAYS" 
            else:
                  raise TypeError("This Function is limited to nifty 50 only")

      def get_macd_crossover(self, date=datetime.now().date()):
            obj = self.get_stock_data(days=1, end_date=date)
            df = pd.DataFrame(list(obj.values()))
            df["macd"] = macd(df.close_price)
            df["macd_signal"] = macd_signal(df.close_price)
            df["diff"] = macd_diff(df.close_price)

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
      vtt = models.IntegerField("Last Traded Price", blank=True, null=True)
      atp = models.IntegerField("Last Traded Price", blank=True, null=True)
      total_buy_quantity = models.IntegerField("Last Traded Price", blank=True, null=True)
      total_sell_quantity = models.IntegerField("Last Traded Price", blank=True, null=True)
      lower_circuit = models.IntegerField("Last Traded Price", blank=True, null=True)
      upper_circuit = models.IntegerField("Last Traded Price", blank=True, null=True)
      bids = JSONField(default=dict)
      asks = JSONField(default=dict)
      date = models.DateTimeField()
      created_at = models.DateTimeField(auto_now=True, editable=False)
      modified_at = models.DateTimeField(auto_now_add=True, editable=False)

      objects = CandleManager()

      def __str__(self):
            return self.symbol.symbol


class UserProfile(models.Model):
      # email = models.CharField(max_length=100)
      user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="user_profile")
      mobile = models.IntegerField(blank=True, null=True)
      created_at = models.DateTimeField(auto_now=True, editable=False)
      modified_at = models.DateTimeField(auto_now_add=True, editable=False)
      for_trade = models.BooleanField(default=False)

      def __str__(self):
            return self.user.get_full_name() or self.user.email or self.user.username

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
            return "{} | {}".format(self.account.user_profile.user.get_full_name(), self.date)

      def save(self, *args, **kwargs):
            if self.account:
                  if self.account.current_balance:
                        self.opening_balance = self.account.current_balance
            super().save(*args, **kwargs)

class SortedStocksList(models.Model):
      symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE)
      entry_price = models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True)
      created_at = models.DateTimeField(auto_now=True, editable=False)
      modified_at = models.DateTimeField(auto_now_add=True, editable=False)

      def __str__(self):
            return "{} | {}".format(self.symbol.__str__(), self.created_at.date())

class Indicator(models.Model):
      name = models.CharField(max_length=50)
      description = models.TextField(null=True, blank=True)
      value = models.IntegerField()
      created_at = models.DateTimeField(auto_now=True, editable=False)
      modified_at = models.DateTimeField(auto_now_add=True, editable=False)

      def __str__(self):
            return self.name


class StrategyTimestamp(models.Model):
      stock = models.ForeignKey(SortedStocksList, on_delete=models.CASCADE)
      indicator = models.ForeignKey(Indicator, on_delete=models.CASCADE)
      timestamp = models.DateTimeField()
      diff = models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True)

      def __str__(self):
            return "{} | {}".format(self.stock.__str__(), self.timestamp.time())
