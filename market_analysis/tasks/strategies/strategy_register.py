from market_analysis.imports import *
from market_analysis.models import Strategy
from .intraday_entry_strategies import *
from .intraday_exit_strategies import GlobalExitStrategy
from .realtime_trade_strategy import RangeReversalStrategy
# Start Code Below

def register_strategy(cls):
    """Function register strategy on strategy model"""
    strategy_choices = {
        "Entry": "ET",
        "Exit": "EX",
    }

    strategy_for_choices = {v:k for k,v in strategies_for.items()}
    priority_choices = {
        "Primary": "PR",
        "Secondary": "SC",
        "Support": "SP"
    }

    is_strategy, created = Strategy.objects.update_or_create(strategy_location=cls.__module__, strategy_name=cls.__name__, defaults={
        "strategy_type" : strategy_choices.get(cls.strategy_type),
        "priority_type" : priority_choices.get(cls.strategy_priority),
        "strategy_for" : strategy_for_choices.get(cls.strategy_for)
    })
    return is_strategy


strategy_list = [
    register_strategy(StochasticBollingerCrossover),
    register_strategy(AdxBollingerCrossover),
    register_strategy(StochasticMacdCrossover),
    register_strategy(StochasticMacdSameTimeCrossover),
    register_strategy(RangeReversalStrategy),
    
]

