from django.db import models
from django.contrib.postgres.fields import JSONField
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

class Candle(models.Model):
      candle_type_choice = {
            ("M5", "5 Minute"),
            ("M10", "10 Minute"),
            ("M15", "15 Minute"),
            ("M60", "60 Minute"),
            ("1D", "1 Day"),
      }

      candle_type = models.CharField(choices=candle_type_choice, max_length=50, blank=False, null=True, default=None)
      open_price = models.IntegerField("Candle Open Price", blank=True, null=True)
      high_price = models.IntegerField("Candle High Price", blank=True, null=True)
      low_price = models.IntegerField("Candle Low Price", blank=True, null=True)
      close_price = models.IntegerField("Candle Close Price", blank=True, null=True)
      ltt = models.IntegerField("Candle Last Traded Time", blank=True, null=True)
      date = models.DateTimeField()

class UserProfile(models.Model):
      email = models.CharField(max_length=100)
      mobile = models.IntegerField(max_length=10, blank=True, null=True)
      api_key = models.CharField(max_length=100, null=True, blank=True)
      secret_key = models.CharField(max_length=100, null=True, blank=True)
      redirect_url = models.CharField(max_length=100, null=True, blank=True)
      response_code = models.CharField(max_length=100, null=True, blank=True)


