from upstox_api.api import *
from .orders import create_update_order_on_update, cache_symbol_ticker_data
from .trading import get_upstox_user
from .notification_tasks import slack_message_sender
from market_analysis.imports import *
## Upstox Event Handler
### Quote Update, Order Update, Trade Update

def event_handler_on_quote_update(message):
    cache_symbol_ticker_data(message)
    return message

def event_handler_on_order_update(message):
    order_statuses = ["cancelled", "open", "complete", "rejected"]
    if message.get("status") in order_statuses:
        create_update_order_on_update.delay(message)
    return "Order Updated"

def event_handler_on_trade_update(message):
    # slack_message_sender(text="Trade Update" + str(message))
    return "Trade Updated"
    
def event_handler_on_error(message):
    slack_message_sender.delay(text="Error Received Please Check: " + str(message), channel="#random")
    return "Error Received"


def event_handler_on_disconnection(message):
    slack_message_sender.delay(text="Websocket Disconnected, Connecting Again")
    start_upstox_websocket(False)
    return "Start Websocket Again" 


def start_upstox_websocket(run_in_background=True):
    user = get_upstox_user()
    user.set_on_quote_update(event_handler_on_quote_update)
    user.set_on_trade_update(event_handler_on_trade_update)
    user.set_on_order_update(event_handler_on_order_update)
    user.set_on_disconnect(event_handler_on_disconnection)
    user.set_on_error(event_handler_on_error)
    user.start_websocket(run_in_background)
    slack_message_sender.delay(text="Websocket for Live Data Feed Started")
    return "Websocket Started"