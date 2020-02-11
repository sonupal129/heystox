from heystox_intraday.intraday_fetchdata import *
from heystox_intraday.select_stocks_for_trading import *
from django.test import TestCase
from market_analysis.models import Symbol

# CODE HERE

class IntradayFetchDataTest(TestCase):

    def test_load_master_contract_data(self):
        self.assertEquals(load_master_contract_data(), "Contract Loaded Successfully")

    def test_get_candles_data_correct_symbol(self):
        self.assertEquals(get_candles_data(symbol="pnb"), "No Stock Found Please Try with Another")
    
    # def test_get_candles_data_incorrect_symbol(self):
    #     self.assertEquals(get_candles_data(symbol="pnb"), "pnb Candles Data Imported Sucessfully")


    # def test_cache_candles_data(self):
    #     self.assertEquals(cache_candles_data("bel"), "Data Cached")



class SelectStocksForTradingTest(TestCase):

    def test_get_cached_liquid_stocks(self):
        output = [1,2,3,4,5,6]
        self.assertEquals(type(get_cached_liquid_stocks()), type(Symbol.objects.all()))
        self.assertGreaterEqual(len(get_cached_liquid_stocks()), 0)