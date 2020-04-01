from upstox_api.api import *
from .orders import create_updated_order_on_update
from .trading import get_upstox_user
from .notification_tasks import slack_message_sender

## Upstox Event Handler
### Quote Update, Order Update, Trade Update

def event_handler_on_quote_update(message):
    cache_key = message.get("symbol").lower() + "_quote_data"
    redis_cache.set(cache_key, message)
    print(message)
    return message

def event_handler_on_order_update(message):
    order_statuses = ["cancelled", "open", "completed", "rejected"]
    if message.get("status") in order_statuses:
        create_updated_order_on_update.delay(message)
    print(str(message))
    return "Order Updated"

def event_handler_on_trade_update(message):
    print(str(message))
    slack_message_sender(text=str(message))
    return "Trade Updated"
    
def event_handler_on_error(message):
    slack_message_sender(text=str(message), channel="#random")
    return "Error Received"


def event_handler_on_disconnection(message):
    user = get_upstox_user()
    user.start_websocket(True)
    slack_message_sender.delay(text="Websocket Disconnected, Connecting Again")
    return "Start Websocket Again" 
