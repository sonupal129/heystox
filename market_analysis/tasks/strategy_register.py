from market_analysis.imports import *
from market_analysis.models import Strategy
from market_analysis.tasks.intraday_indicator import (StochasticBollingerCrossover, AdxBollingerCrossover, StochasticMacdCrossover)

# Start Code Below

def register_strategy(cls):
    """Function register strategy on strategy model"""
    cache_key = ".".join([cls.__module__, cls.__name__])
    is_strategy, created = Strategy.objects.get_or_create(strategy_location=cls.__module__, strategy_name=cls.__name__, strategy_type=cls.strategy_type)
    redis_cache.set(cache_key, is_strategy, 30*60*48)
    return is_strategy


strategy_list = [
    register_strategy(StochasticBollingerCrossover),
    register_strategy(AdxBollingerCrossover),
    register_strategy(StochasticMacdCrossover)
]

