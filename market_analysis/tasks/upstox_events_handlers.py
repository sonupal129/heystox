from upstox_api.api import *
from .orders import create_update_order_on_update
from .trading import get_upstox_user
from .notification_tasks import slack_message_sender
from market_analysis.imports import *
## Upstox Event Handler
### Quote Update, Order Update, Trade Update

def event_handler_on_quote_update(message):
    cache_key = message.get("symbol").lower() + "_quote_data"
    redis_cache.set(cache_key, message)
    print(message)
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
    user = get_upstox_user()
    for i in range(0,3):
        user.start_websocket(True)
        sleep(0.5)
    slack_message_sender.delay(text="Websocket Disconnected, Connecting Again")
    return "Start Websocket Again" 
