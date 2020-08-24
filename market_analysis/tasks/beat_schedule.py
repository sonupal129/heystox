from market_analysis.imports import *
from market_analysis.models import SortedStocksList
# Code Starts Below


misc_tasks = {
    "delete_stocks_candles": {
        "task": "market_analysis.tasks.misc_tasks.delete_stocks_candles",
        "schedule": crontab(hour=5, minute=50),
    },
    "create_stocks_report": {
        "task": "market_analysis.tasks.misc_tasks.create_stocks_report",
        "schedule": crontab(day_of_week="1-5", hour=21, minute=0),
    },
    "clear_all_cache": {
        "task": "market_analysis.tasks.misc_tasks.clear_all_cache",
        "schedule": crontab(hour=5, minute=51),
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
    "import_stocks_candle_data": {
        "task": "market_analysis.tasks.stock_data_import_tasks.import_stocks_candle_data",
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
        "schedule": crontab(day_of_week="1-5", hour=19, minute=30),
    },
    "import_daily_losers_gainers": {
        "task": "market_analysis.tasks.stock_data_import_tasks.import_daily_losers_gainers",
        "schedule": crontab(day_of_week="1-5", hour="9-15", minute="*/4"),
    },
    "import_premarket_stocks_data": {
        "task": "market_analysis.tasks.stock_data_import_tasks.import_premarket_stocks_data",
        "schedule": crontab(day_of_week="1-5", hour=9, minute=9),
    },
    "import_international_market_index_data": {
        "task": "market_analysis.tasks.stock_data_import_tasks.import_international_market_index_data",
        "schedule": crontab(day_of_week="2-6", hour=4, minute=10),
    },
    "subscribe_stocks_for_realtime_trading": {
        "task": "market_analysis.tasks.stock_data_import_tasks.subscribe_stocks_for_realtime_trading",
        "schedule": crontab(day_of_week="1-5", hour=9, minute=15),
    },
    "unsubscribe_stocks_for_realtime_trading": {
        "task": "market_analysis.tasks.stock_data_import_tasks.subscribe_stocks_for_realtime_trading",
        "schedule": crontab(day_of_week="1-5", hour=15, minute=40),
        "kwargs": {"subscribe": False},
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
    # "find_ohl_stocks": {
    #     "task": "market_analysis.tasks.intraday_entry_indicator.find_ohl_stocks",
    #     "schedule": crontab(day_of_week="1-5", hour="9-15", minute="*/6"),
    # },
    "create_market_hour_candles_every_five_minute": {
        "task": "market_analysis.tasks.day_trading_tasks.create_market_hour_candles",
        "schedule": crontab(day_of_week="1-5", hour="9-15", minute="*/5"),
        "kwargs": {"days": 0, "fetch_last_candle_number": 2},
    },
    "create_market_hour_candles_every_two_hour": {
        "task": "market_analysis.tasks.day_trading_tasks.create_market_hour_candles",
        "schedule": crontab(day_of_week="1-5", hour="9-15", minute="*/118"),
        "kwargs": {"days": 0, "fetch_last_candle_number": None},
    },
    "delete_last_cached_candles_data": {
        "task": "market_analysis.tasks.day_trading_tasks.delete_last_cached_candles_data",
        "schedule": crontab(day_of_week="1-5", hour="9-15", minute="*/5"),
    },
    "create_stocks_realtime_candle": {
        "task": "market_analysis.tasks.day_trading_tasks.create_stocks_realtime_candle",
        "schedule": crontab(day_of_week="1-5", hour="9-15", minute="*/1"),
    },
    "create_nifty_50_realtime_candle": {
        "task": "market_analysis.tasks.day_trading_tasks.create_nifty_50_realtime_candle",
        "schedule": crontab(day_of_week="1-5", hour="9-15", minute="*/1"),
    },
    "apply_intraday_indicator_on_sorted_stocks": {
        "task": "market_analysis.tasks.day_trading_tasks.apply_intraday_indicator_on_sorted_stocks",
        "schedule": crontab(day_of_week="1-5", hour="9-15", minute="*/1"),
    },
    "todays_movement_stocks_add_on_sideways": {
        "task": "market_analysis.tasks.day_trading_tasks.todays_movement_stocks_add_on_sideways",
        "schedule": crontab(day_of_week="1-5", hour="9-15", minute="*/3"),
    },
    # "calculate_profit_loss_on_entry_stocks": {
    #     "task": "market_analysis.tasks.day_trading_tasks.calculate_profit_loss_on_entry_stocks",
    #     "schedule": crontab(day_of_week="1-5", hour="9-15", minute="*/3"),
    # },
    "start_websocket": {
        "task": "market_analysis.tasks.day_trading_tasks.start_websocket",
        "schedule": crontab(day_of_week="1-5", hour=9, minute=17),
    },
}

orders = {
    "cancel_not_executed_orders": {
        "task": "market_analysis.tasks.orders.cancel_not_executed_orders",
        "schedule": crontab(day_of_week="1-5", hour="10-14", minute="*/12"),
    },
    "cancel_not_executed_orders_all": {
        "task": "market_analysis.tasks.orders.cancel_not_executed_orders",
        "schedule": crontab(day_of_week="1-5", hour=14, minute=50),
        "kwargs": {"from_last_minutes": 0},
    },
    "update_orders_status": {
        "task": "market_analysis.tasks.orders.update_orders_status",
        "schedule": crontab(day_of_week="1-5", hour="10-14", minute="*/6"),
    },
    "auto_square_off_all_positions": {
        "task": "market_analysis.tasks.orders.auto_square_off_all_positions",
        "schedule": crontab(day_of_week="1-5", hour=14, minute=50),
    },
}

backtest = {
    "create_backtesting_data_async": {
        "task": "market_analysis.tasks.strategies.backtest.create_backtesting_data_async",
        "schedule": crontab(minute="*/11"),
    },
}

trading = {
    "add_manual_sorted_stocks": {
        "task": "market_analysis.tasks.trading.add_manual_sorted_stocks",
        "schedule": crontab(day_of_week="1-5", hour="9-14", minute="*/9"),
    },
    "add_manually_traded_sorted_stocks": {
        "task": "market_analysis.tasks.trading.update_remove_manually_traded_stocks",
        "schedule": crontab(day_of_week="1-5", hour=9, minute=18),
        "kwargs": {"stock_add": True},
    },
    "remove_manually_traded_sorted_stocks": {
        "task": "market_analysis.tasks.trading.update_remove_manually_traded_stocks",
        "schedule": crontab(day_of_week="1-5", hour=16, minute=2),
        "kwargs": {"stock_add": False},
    },
}

# CRON JOB SCHEDULES


celery_app.conf.beat_schedule = {
    **misc_tasks, 
    **users_tasks,
    **stock_data_import_tasks,
    **day_trading_tasks,
    **orders,
    **trading,
    **backtest
}