from market_analysis.imports import *
from .trading import get_upstox_user
from market_analysis.models import Symbol, SortedStockDashboardReport, OrderBook
from market_analysis.tasks.notification_tasks import slack_message_sender
# Code Below

def roundup(x, prec=2, base=.05):
  return round(base * round(float(x)/base), prec)

def get_stock_stoploss_price(price, entry_type):
    if price < 100:
        sl = settings.DEFAULT_STOPLOSS + 0.10
    elif price < 200:
        sl = settings.DEFAULT_STOPLOSS + 0.20
    elif price < 300:
        sl = settings.DEFAULT_STOPLOSS + 0.40
    else:
        sl = settings.DEFAULT_STOPLOSS + 0.70
    if entry_type == "SELL":
        stoploss = price + (price * sl /100)
    elif entry_type == "BUY":
        stoploss = price - (price * sl /100)
    return roundup(stoploss)

def get_stock_target_price(price, entry_type):
    if price < 100:
        tg = settings.DEFAULT_TARGET + 0.10
    elif price < 200:
        tg = settings.DEFAULT_TARGET + 0.20
    elif price < 300:
        tg = settings.DEFAULT_TARGET + 0.40
    else:
        tg = settings.DEFAULT_TARGET + 0.70
    if entry_type == "SELL":
        target = price - (price * tg /100)
    elif entry_type == "BUY":
        target = price + (price * tg /100)
    return roundup(target)

def calculate_order_quantity(share_price, entry_type):
    user = get_upstox_user()
    balance = user.get_balance()
    if balance:
        available_margin = balance["equity"].get("available_margin")
        bearable_loss = available_margin * settings.DEFAULT_STOPLOSS / 100
        stoploss = get_stock_stoploss_price(share_price, entry_type)
        diff = abs(share_price - stoploss)
        if diff < 1:
            diff = round(diff)
        qty = int(bearable_loss / diff)
        if qty > settings.MAX_ORDER_QUANTITY:
            return settings.MAX_ORDER_QUANTITY
        return abs(qty)

def get_stock_auto_exit_price():
    pass


@celery_app.task(queue="high_priority")
def send_order_place_request(signal_detail:dict=None):
    # This function will work as generic function where all functions will come under this function
    # So, whenever a signal found or any function which finds signal will send required parameter to this function and 
    # it will create a report based on that signal
    # Please Use this function for any order placing requests or report creation
    # Dictionary Format {name: xxxxx, entry_time: xxxxx, entry_type: xxxxx, entry_price: xxxxxxx}
    """Generic function to send order request and create order report"""
    order_place_start_time = time(9,25)
    order_place_end_time = time(14,30)
    entry_price = signal_detail.get("entry_price")
    entry_type = signal_detail.get("entry_type")
    name = signal_detail.get("name")
    entry_time = get_local_time().strptime(signal_detail.get("entry_time"), "%Y-%m-%dT%H:%M:%S")
    order_schema["transaction_type"] = entry_type
    order_schema["symbol"] = name
    order_schema["quantity"] = calculate_order_quantity(entry_price, entry_type)
    order_schema["price"] = entry_price
    order_schema["duarion_type"] = "DAY"
    order_schema["order_type"] = "LIMIT"
    order_schema["product_type"] = "INTRADAY"
    if entry_time.time() > order_place_start_time and entry_time.time() <= order_place_end_time:
        user = get_upstox_user()
        symbol = Symbol.objects.get(symbol=name)
        user.get_master_contract(symbol.exchange.name.upper())
        data = user.get_live_feed(user.get_instrument_by_symbol(symbol.exchange.name.upper(), symbol.symbol.upper()), LiveFeedType.Full)
        slack_message_sender.delay(text=f"{entry_price} Signal {entry_type} Stock Name {name} Time {entry_time.now()}", channel="#random")
        obj, is_created = SortedStockDashboardReport.objects.get_or_create(**signal_detail)
        add_expected_target_stoploss.delay(obj.id)
        percentage_calculator = lambda higher_number, lower_number : (higher_number - lower_number) / lower_number * 100
        buy_qty = data["total_buy_qty"]
        sell_qty = data["total_sell_qty"]
        if entry_type == "BUY" and (percentage_calculator(sell_qty, buy_qty) < 20 or percentage_calculator(buy_qty, sell_qty) > 20):
            # Send Order Place Request
            pass
        elif entry_type == "SELL" and (percentage_calculator(buy_qty, sell_qty) < 20 or percentage_calculator(sell_qty, buy_qty) > 20):
            # Send Order Place Request
            pass
        # Do All Function Logic Here

# od = {"name": "BEL", "entry_type": "BUY", "entry_price": 123, "entry_time": get_local_time().now()}

@celery_app.task(queue="low_priority")
def add_expected_target_stoploss(stock_report_id):
    report = SortedStockDashboardReport.objects.get(id=stock_report_id)
    price = report.entry_price
    report.stoploss_price = get_stock_stoploss_price(price, report.entry_type)
    report.target_price = get_stock_target_price(price, report.entry_type)
    report.save()



@celery_app.task(queue="high_priority")
def send_order_request(order_details:dict):
    user = get_upstox_user()
    today_date = get_local_time().date()
    orders_qty = OrderBook.objects.filter(created_at__date=today_date).count()
    if orders_qty >= settings.MAX_ORDER_QUANTITY:
        slack_message_sender.delay(text="Daily Order Limit Exceed No More Order Can Be Place Using Bot, Please Place Orders Manually")
        return "Daily Order Limit Exceed"
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
    # OrderBook.objects.get_or_create(symbol=symbol, order_id=order.get("order_id"))



