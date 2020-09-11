from market_analysis.imports import *


# CODE BELOW

call_strategy = Signal(providing_args=["symbol_id", "symbol", "data"]) #This signal receive data from websocket and can call any function to use that data in calling strategies
update_profit_loss = Signal(providing_args=["symbol", "entry_type", "exit_price", "target_price", "stoploss_price"])