from django.db import models
from django.contrib.postgres.fields import JSONField
from django.utils import timezone
from datetime import datetime, timedelta
# Create your models here.

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

      def __str__(self):
            return self.symbol

      def is_stock_ohl(self, date=datetime.now(), candle_type="M5"):
            """Find Stock falls in open high low strategy"""
            try:
                  stock_date = datetime.strptime(date,'%d/%m/%Y').date()
            except:
                  stock_date = date.date()
            todays_candles = Candle.objects.filter(symbol=self, candle_type=candle_type, date__date=stock_date)
            first_candle = todays_candles.first()
            first_candle_open_price = first_candle.open_price
            first_candle_low_price = first_candle.low_price
            first_candle_high_price = first_candle.high_price
            current_prices = todays_candles.aggregate(Max("high_price"), Min("low_price"))
            if first_candle_open_price == current_prices.get("high_price__max"):
                  return "SELL"
            elif first_candle_open_price == current_prices.get("low_price__min"):
                  return "BUY"
            else:
                  return False
      
      def is_stock_pdhl(self, date=datetime.now(), candle_type="M5"):
            """Finds stocks is fall under previous day high low conditions"""
            today = datetime.strptime(date,'%d/%m/%Y').date()
            yesterday = datetime.strptime(date,'%d/%m/%Y').date() - timedelta(1)
            candles = Candle.objects.filter(symbol=self, candle_type=candle_type, date__range=[yesterday, today + timedelta(1)])
            last_day_closing_price = candles.filter(date__date=yesterday).last().close_price
            last_day_opening_price = candles.filter(date__date=yesterday).first().open_price
            today_opening_price = candles.filter(date__date=today).first().open_price
            if last_day_opening_price > last_day_closing_price > today_opening_price:
                  return "SELL"
            elif last_day_opening_price < last_day_closing_price < today_opening_price:
                  return "BUY"
            else:
                  return False

      def get_days_high_low_price(self, start_date, end_date=datetime.now(), price_type="HIGH", candle_type="M5"):
            try:
                  start_date = datetime.strptime(start_date,'%d/%m/%Y').date()
                  end_date = datetime.strptime(end_date,'%d/%m/%Y').date()
            except:
                  start_date = start_date.date()
                  end_date = end_date.date()
            if start_date == end_date:
                  candles = Candle.objects.filter(symbol=self, candle_type=candle_type, date__date=start_date)
            else:
                  candles = Candle.objecs.filter(symbol=self, candle_type=candle_type, date__range=[start_date, end_date + timedelta(1)])
            if price_type == "HIGH":
                  return candles.aggregate(Max("high_price"))
            elif price_type == "LOW":
                  return candles.aggregate(Min("low_price"))


      def has_entry_for_long_short(self, date=datetime.now(), candle_type="M5"):
            try:
                  stock_date = datetime.strptime(date,'%d/%m/%Y').date()
            except:
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
      bids = JSONField(default=dict())
      asks = JSONField(default=dict())
      date = models.DateTimeField()

      objects = CandleManager()

      def __str__(self):
            return self.symbol.symbol


class UserProfile(models.Model):
      email = models.CharField(max_length=100)
      mobile = models.IntegerField(blank=True, null=True)
      api_key = models.CharField(max_length=100, null=True, blank=True)
      secret_key = models.CharField(max_length=100, null=True, blank=True)
      redirect_url = models.CharField(max_length=100, null=True, blank=True)
      response_code = models.CharField(max_length=100, null=True, blank=True)
      access_token = models.CharField(max_length=100, null=True, blank=True)
      client_id = models.IntegerField(blank=True, null=True)
      bank_name = models.CharField(max_length=100, blank=True, null=True)
      bank_account = models.CharField(max_length=100, blank=True, null=True)
      updated = models.DateTimeField("Recently Updated", auto_now=True)

      def __str__(self):
            return self.email or self.client_id

