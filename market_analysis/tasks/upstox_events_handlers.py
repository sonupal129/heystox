from upstox_api.api import *
from .orders import UpdateOrder
from .strategies.intraday_exit_strategies import TickerDataCaller
from .trading import get_upstox_user
from .notification_tasks import slack_message_sender
from market_analysis.imports import *
## Upstox Event Handler
### Quote Update, Order Update, Trade Update

def event_handler_on_quote_update(message):
    TickerDataCaller(message).run()
    return message

def event_handler_on_order_update(message):
    order_statuses = ["cancelled", "open", "complete", "rejected"]
    if message.get("status") in order_statuses:
        UpdateOrder().delay(message)
    return "Order Updated"

def event_handler_on_trade_update(message):
    # slack_message_sender(text="Trade Update" + str(message))
    return "Trade Updated"
    
def event_handler_on_error(message):
    slack_message_sender.delay(text="Error Received Please Check: " + str(message), channel="#random")
    return "Error Received"


def event_handler_on_disconnection(message):
    slack_message_sender.delay(text="Websocket Disconnected, Connecting Again")
    start_upstox_websocket(True)
    return "Start Websocket Again"


restart_counter = 0

def start_upstox_websocket(run_in_background=True):
    global restart_counter
    if restart_counter < 5 or restart_counter > 30:
        sleep(5)
        user = get_upstox_user() 
        user.set_on_quote_update(event_handler_on_quote_update)
        user.set_on_trade_update(event_handler_on_trade_update)
        user.set_on_order_update(event_handler_on_order_update)
        user.set_on_disconnect(event_handler_on_disconnection)
        user.set_on_error(event_handler_on_error)
        user.start_websocket(run_in_background)
        slack_message_sender.delay(text="Websocket for Live Data Feed Started")
    
    if restart_counter > 32:
        restart_counter = 0
    
    restart_counter += 1
    
    return "Websocket Started"