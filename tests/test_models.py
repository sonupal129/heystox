from django.test import TestCase
from .base_test import BaseModelTest
from market_analysis.models import *
from model_mommy import mommy
# Code Start

class SymbolModelTest(BaseModelTest, TestCase):
    model = Symbol

    def test_model_str(self):
        obj = mommy.make(self.get_model())
        self.assertEquals(obj.__str__(), obj.symbol)

class CandleModelTest(BaseModelTest, TestCase):
    model = Candle

class SortedStocksModelTest(BaseModelTest, TestCase):
    model = SortedStocksList

class StrategyTimeStampModelTest(BaseModelTest, TestCase):
    model = StrategyTimestamp