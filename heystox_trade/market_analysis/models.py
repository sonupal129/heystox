from django.db import models
from django.contrib.postgres.fields import JSONField
from django.utils import timezone
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
      closing_price = models.FloatField(blank=True, null=True)
      tick_size = models.FloatField(blank=True, null=True)
      instrument_type = models.CharField(max_length=20, blank=True, null=True)
      isin = models.CharField(max_length=50)

      def __str__(self):
            return self.symbol

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

      def __str__(self):
            return self.email or self.client_id
