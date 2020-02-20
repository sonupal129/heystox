from celery.schedules import crontab
from heystox_trade.celery import app
from market_analysis.models import SortedStocksList
from datetime import datetime
# Code Starts Below


misc_tasks = {
    "delete_stocks_candles": {
        "task": "market_analysis.tasks.misc.delete_stocks_candles",
        "schedule": crontab(day_of_week="2-6", hour=5, minute=50),
    },
    "clear_all_cache": {
        "task": "market_analysis.tasks.misc.clear_all_cache",
        "schedule": crontab(day_of_week="2-6", hour=5, minute=55),
    },
}


users_tasks = {
    "update_initial_balance": {
        "task": "market_analysis.tasks.users_tasks.update_initial_balance",
        "schedule": crontab(day_of_month=1, hour=8, minute=40),
    },
    "update_current_earning_balance": {
        "task": "market_analysis.tasks.users_tasks.update_current_earning_balance",
        "schedule": crontab(day_of_week="2-6", hour=8, minute=55),
    },
    "stop_trading_on_profit_loss": {
        "task": "market_analysis.tasks.users_tasks.stop_trading_on_profit_loss",
        "schedule": crontab(day_of_week="2-6", hour=2, minute=5),
    },
    "authenticate_users_in_morning": {
        "task": "market_analysis.tasks.users_tasks.authenticate_users_in_morning",
        "schedule": crontab(day_of_week="1-5", hour=7, minute=30),
    },
}


stock_data_import_tasks = {
    "update_create_stocks_data": {
        "task": "market_analysis.tasks.stock_data_import_tasks.update_create_stocks_data",
        "schedule": crontab(day_of_week="1-5", hour=19, minute=0),
        "kwargs": {"index": "NSE_EQ"},
    },
    "update_stocks_candle_data": {
        "task": "market_analysis.tasks.stock_data_import_tasks.update_stocks_candle_data",
        "schedule": crontab(day_of_week="1-5", hour=17, minute=10),
    },
    "update_stocks_volume": {
        "task": "market_analysis.tasks.stock_data_import_tasks.update_stocks_volume",
        "schedule": crontab(day_of_week="1-5", hour=19, minute=20),
    },
    "update_nifty_50_price_data": {
        "task": "market_analysis.tasks.stock_data_import_tasks.update_nifty_50_price_data",
        "schedule": crontab(day_of_week="1-5", hour=18, minute=50),
    },
    "update_symbols_closing_opening_price": {
        "task": "market_analysis.tasks.stock_data_import_tasks.update_symbols_closing_opening_price",
        "schedule": crontab(day_of_week="1-5", hour=23, minute=55),
    },
    "import_daily_losers_gainers": {
        "task": "market_analysis.tasks.stock_data_import_tasks.import_daily_losers_gainers",
        "schedule": crontab(day_of_week="1-5", hour="9-15", minute="*/4"),
    },
    "import_premarket_stocks_data": {
        "task": "market_analysis.tasks.stock_data_import_tasks.import_premarket_stocks_data",
        "schedule": crontab(day_of_week="1-5", hour=9, minute=9),
    },
}


day_trading_tasks = {
    "subscribe_today_trading_stocks": {
        "task": "market_analysis.tasks.day_trading_tasks.subscribe_today_trading_stocks",
        "schedule": crontab(day_of_week="1-5", hour=9, minute=14),
    },
    "unsubscribe_today_trading_stocks": {
        "task": "market_analysis.tasks.day_trading_tasks.unsubscribe_today_trading_stocks",
        "schedule": crontab(day_of_week="1-5", hour=15, minute=45),
    },
    "todays_movement_stocks_add": {
        "task": "market_analysis.tasks.day_trading_tasks.todays_movement_stocks_add",
        "schedule": crontab(day_of_week="1-5", hour="9-15", minute="*/3"),
    },
    "find_ohl_stocks": {
        "task": "market_analysis.tasks.day_trading_tasks.find_ohl_stocks",
        "schedule": crontab(day_of_week="1-5", hour="9-15", minute="*/6"),
    },
    "create_market_hour_candles": {
        "task": "market_analysis.tasks.day_trading_tasks.create_market_hour_candles",
        "schedule": crontab(day_of_week="1-5", hour="9-15", minute="1-59/5"),
    },
    "delete_last_cached_candles_data": {
        "task": "market_analysis.tasks.day_trading_tasks.delete_last_cached_candles_data",
        "schedule": crontab(day_of_week="1-5", hour="9-15", minute="1-59/5"),
    },
    "create_stocks_realtime_candle": {
        "task": "market_analysis.tasks.day_trading_tasks.create_stocks_realtime_candle",
        "schedule": crontab(day_of_week="1-5", hour="9-15", minute="*/1"),
    },
    "create_nifty_50_realtime_candle": {
        "task": "market_analysis.tasks.day_trading_tasks.create_nifty_50_realtime_candle",
        "schedule": crontab(day_of_week="1-5", hour="9-15", minute="*/1"),
    },
    "find_update_macd_stochastic_crossover_in_stocks": {
        "task": "market_analysis.tasks.day_trading_tasks.find_update_macd_stochastic_crossover_in_stocks",
        "schedule": crontab(day_of_week="1-5", hour="9-15", minute="*/1"),
    },
    "todays_movement_stocks_add_on_sideways": {
        "task": "market_analysis.tasks.day_trading_tasks.todays_movement_stocks_add_on_sideways",
        "schedule": crontab(day_of_week="1-5", hour="9-15", minute="*/3"),
    },
}
# CRON JOB SCHEDULES

app.conf.beat_schedule = {
    **misc_tasks, **users_tasks, **stock_data_import_tasks, **day_trading_tasks
}