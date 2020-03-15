from market_analysis.imports import *
from .trading import get_upstox_user
from market_analysis.models import Symbol, SortedStockDashboardReport
from market_analysis.tasks.notification_tasks import slack_message_sender
# Code Below

@celery_app.task(queue="medium_priority")
def send_order_place_request(signal_detail:dict=None):
    # This function will work as generic function where all functions will come under this function
    # So, whenever a signal found or any function which finds signal will send required parameter to this function and 
    # it will create a report based on that signal
    # Please Use this function for any order placing requests or report creation
    # Dictionary Format {name: xxxxx, entry_time: xxxxx, entry_type: xxxxx, entry_price: xxxxxxx}
    """Generic function to send order request and create order report"""
    current_time = get_local_time().time()
    order_place_start_time = time(9,25)
    order_place_end_time = time(14,30)
    entry_price = signal_detail.get("entry_price")
    entry_type = signal_detail.get("entry_type")
    name = signal_detail.get("name")
    entry_time = signal_detail.get("entry_time")
    if current_time >= order_place_start_time and current_time <= order_place_end_time:
        obj, is_created = SortedStockDashboardReport.objects.get_or_create(**signal_detail)
        slack_message_sender.delay(text=f"{entry_price} Signal {entry_type} Stock Name {name} Time {entry_time}", channel="#random")
        # Do All Function Logic Here
    pass


def send_order_request(order_details:dict):
    user = get_upstox_user()
    symbol = Symbol.objects.get(symbol=order_details.get("symbol"))
    transaction_type = order_details.get("transaction_type")
    quantity = order_details.get("quantity")
    order_type = order_details.get("order_type")
    price = order_details.get("price")
    duration_type = order_details.get("duarion_type")
    order = user.place_order(
        transaction_types.get(transaction_type),
        user.get_instrument_by_symbol(symbol.symbol.upper(), symbol.exchange.name.upper()),
        order_types.get(order_type),
        price,
        duration_types.get(duration_type)
    )


