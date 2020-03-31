from upstox_api.api import *
from .orders import slack_message_sender
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
    print(str(message))
    return "Order Updated"
    

def event_handler_on_trade_update(message):
    print(str(message))
    return "Trade Updated"
    

def event_handler_on_disconnection(message):
    user = get_upstox_user()
    slack_message_sender.delay(text="Websocket Connection Disconnected")
    user.start_websocket(True)
    slack_message_sender.delay(text="Websocket Connected Again")
    return "Start Websocket Again" 
