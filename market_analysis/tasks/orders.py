from market_analysis.imports import *
from .trading import get_upstox_user
from market_analysis.models import Symbol, SortedStockDashboardReport, OrderBook, Order
from market_analysis.tasks.notification_tasks import slack_message_sender

# Code Below

# Signals

analyse_ticker_data_signal = Signal(providing_args=["context"])


# Orders Functions

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
        tg = settings.DEFAULT_TARGET + 0.5
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

def get_auto_exit_price(price, entry_type):
    fixed_auto_exit_percentage = settings.DEFAULT_STOPLOSS / 2
    if price < 100:
        sl = fixed_auto_exit_percentage
    elif price < 200:
        sl = fixed_auto_exit_percentage + 0.10
    elif price < 300:
        sl = fixed_auto_exit_percentage + 0.15
    else:
        sl = fixed_auto_exit_percentage + 0.20
    if entry_type == "SELL":
        stoploss = price - (price * sl /100)
    elif entry_type == "BUY":
        stoploss = price + (price * sl /100)
    return roundup(stoploss)

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


find_last_order = lambda order1, order2 : order1 if order1.entry_time > order2.entry_time else order2


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
        obj, is_created = SortedStockDashboardReport.objects.get_or_create(**signal_detail)
        add_expected_target_stoploss.delay(obj.id)
        slack_message_sender.delay(text=f"{entry_price} Signal {entry_type} Stock Name {name} Time {entry_time}", channel="#random")
        percentage_calculator = lambda higher_number, lower_number : (higher_number - lower_number) / lower_number * 100
        buy_qty = data["total_buy_qty"]
        sell_qty = data["total_sell_qty"]
        if entry_type == "BUY" and (percentage_calculator(sell_qty, buy_qty) < 20 or percentage_calculator(buy_qty, sell_qty) > 20):
            # Send Order Place Request
            send_order_request.delay(order_schema)
        elif entry_type == "SELL" and (percentage_calculator(buy_qty, sell_qty) < 20 or percentage_calculator(sell_qty, buy_qty) > 20):
            # Send Order Place Request
            send_order_request.delay(order_schema)
        # Do All Function Logic Here

@celery_app.task(queue="low_priority")
def add_expected_target_stoploss(stock_report_id):
    report = SortedStockDashboardReport.objects.get(id=stock_report_id)
    price = report.entry_price
    report.stoploss_price = get_stock_stoploss_price(price, report.entry_type)
    report.target_price = get_stock_target_price(price, report.entry_type)
    report.save()

# od = {'transaction_type': 'SELL', 'symbol': 'CANBK', 'order_type': 'LIMIT', 'quantity': 1, 'price': 87.20, ', duarion_type': 'DAY', 'product_type': 'INTRADAY'}


@celery_app.task(queue="high_priority")
def send_order_request(order_details:dict): # Don't Change This Function Format, Because This is As per Upstox Format, 
    user = get_upstox_user()
    today_date = get_local_time().date()
    orders_qty = OrderBook.objects.filter(created_at__date=today_date).count()
    if orders_qty >= settings.MAX_ORDER_QUANTITY:
        slack_message_sender.delay(text="Daily Order Limit Exceed No More Order Can Be Place Using Bot, Please Place Orders Manually")
        return "Daily Order Limit Exceed"
    symbol = Symbol.objects.get(symbol__iexact=order_details.get("symbol"))
    order_book, is_created = OrderBook.objects.get_or_create(symbol=symbol, date=get_local_time().date())
    transaction_type = order_details.get("transaction_type", None)
    quantity = order_details.get("quantity", None)
    order_type = order_details.get("order_type", None)
    price = order_details.get("price", None)
    duration_type = order_details.get("duarion_type", None)
    product_type = order_details.get("product_type", None)
    trigger_price = order_details.get("trigger_price", None)
    disclosed_quantity = order_details.get("disclosed_quantity", None)
    stop_loss = order_details.get("stop_loss", None)
    square_off = order_details.get("square_off", None)
    trailing_ticks = order_details.get("trailing_ticks", None)
    user.get_master_contract(symbol.exchange.name)
    last_completed_order = order_book.get_last_order_by_status("CO")
    last_open_order = order_book.get_last_order_by_status("OP")
    if last_completed_order and last_open_order:
        last_order = find_last_order(last_open_order, last_completed_order)
    else:
        last_order = last_completed_order or last_open_order
    if is_created:
        order = Order.objects.create(order_book=order_book, transaction_type=transaction_type)
    else:
        if last_order:
            if last_order.transaction_type != transaction_type:
                order = Order.objects.create(order_book=order_book, transaction_type=transaction_type)
        else:
            order = Order.objects.create(order_book=order_book, transaction_type=transaction_type)
    if order:
        upstox_order = user.place_order(
            transaction_types.get(transaction_type),
            user.get_instrument_by_symbol(symbol.exchange.name, symbol.symbol.upper()),
            quantity,
            order_types.get(order_type),
            product_types.get(product_type),
            float(price),
            trigger_price,
            disclosed_quantity,
            duration_types.get(duration_type),
            stop_loss,
            square_off,
            trailing_ticks,
        )
        if upstox_order:
            order.order_id = str(upstox_order.get("order_id"))
            order.entry_time = get_local_time().now()
            if last_order and last_order.entry_type == "ET":
                order.entry_type = "EX"
            else:
                order.entry_type = "ET"
            order.quantity = quantity
            order.entry_price = price
            order.stoploss = get_stock_stoploss_price(price, transaction_type)
            order.target_price = get_stock_target_price(price, transaction_type)
            order.save()
        

@celery_app.task(queue="high_priority")
def create_update_order_on_update(order_data):
    order_choices = {
        "cancelled": "CA",
        "open": "OP",
        "complete": "CO",
        "rejected": "RE"
    }
    order_id = order_data.get("order_id")
    user = get_upstox_user()
    user.get_master_contract(order_data.get("exchange"))
    order, is_created = Order.objects.get_or_create(order_id=order_id)
    exchange_time = get_local_time().strptime(order_data.get("exchange_time"), "%d-%b-%Y %H:%M:%S") if order_data.get("exchange_time") else get_local_time().now()
    if is_created:
        order_book = OrderBook.objects.get(symbol__symbol__iexact=order_data.get("symbol"), date=get_local_time().date())
        order.entry_price = order_data.get("price") or order_data.get("average_price")
        order.transaction_type = "BUY" if order_data.get("transaction_type") == "BUY" else "SELL"
        order.status = order_choices.get(order_data["status"])
        order.order_book = order_book
        order.entry_time = exchange_time if exchange_time else None
        order.stoploss = get_stock_stoploss_price(order.entry_price, order.transaction_type)
        order.target_price = get_stock_target_price(order.entry_price, order.transaction_type)
        order.save()
    else:
        order.status = order_choices.get(order_data["status"])
        order.entry_time = exchange_time if exchange_time else None
        order.entry_price = order_data.get("price") or order_data.get("average_price")
        order.save()
    if order.status not in ["CO", "OP"]:
        order.entry_type = ""
        order.save()
    if order.status == "CO":
        # Create Logic About when to Subscribe for instrument
        cache_key = "_".join([order_data["symbol"].lower(), "cached_ticker_data"])
        if order.entry_type == "ET":
            data = {
                "symbol": order_data.get("symbol"),
                "target_price" : order.target_price,
                "stoploss": order.stoploss,
                "auto_exit_price" : get_auto_exit_price(order.entry_price, order.entry_type),
                "entry_type" : order.entry_type,
                "order_id" : order.order_id,
                "stock_data" : None,
                "entry_price" : order.entry_price,
                "entry_time" : order.entry_time,
                "quantity" : order.quantity
            }
            redis_cache.set(cache_key, data)
            user.subscribe(user.get_instrument_by_symbol(order_data.get("exchange"), order_data.get("symbol")), LiveFeedType.Full)
        elif order.order_type == "EX":
            redis_cache.delete(cache_key)
            user.unsubscribe(user.get_instrument_by_symbol(order_data.get("exchange"), order_data.get("symbol")), LiveFeedType.Full)
    slack_message_sender.delay(text=str(order.order_id) + " Order Status Changed to {0} Please Check".format(order_data["status"]), channel="#random")


@celery_app.task(queue="high_priority")
def cancel_not_executed_orders(from_last_minutes=20):
    """Cancel orders which are not executed after 20 minutes of placing"""
    orders = Order.objects.filter(entry_time__lte=get_local_time().now() - timedelta(minutes=from_last_minutes), status="OP")
    user = get_upstox_user()
    for order in orders:
        user.cancel_order(order.order_id)


def cache_symbol_ticker_data(data:dict):
    cache_key = "_".join([data["symbol"].lower(), "cached_ticker_data"])
    cached_value = redis_cache.get(cache_key)
    price_type = "high" if cached_value.get("entry_type") == "BUY" else "low"
    new_price = data[price_type]
    if not cached_value.get(price_type):
        cached_value[price_type] = new_price
    old_price = cached_value.get(price_type)
    if price_type == "high" and new_price > old_price:
        cached_value[price_type] = new_price
    elif price_type == "low" and new_price < old_price:
        cached_value[price_type] = new_price
    context = {
            "high": data["high"],
            "low": data["low"],
            "open": data["open"],
            "close": data["close"],
            "ltp": data["ltp"],
            "timestamp": data["timestamp"][:10],
            "total_buy_qty": data["total_buy_qty"],
            "total_sell_qty": data["total_sell_qty"]
        }
    if not cached_value.get("stock_data"):
        cached_value["stock_data"] = [context]
    if data["ltp"] != cached_value["stock_data"][-1]["ltp"]:
        cached_value["stock_data"].append(context)
    redis_cache.set(cache_key, cached_value)
    analyse_ticker_data_signal.send(sender=cache_symbol_ticker_data.__name__, **redis_cache.get(cache_key))
    return cached_value


@receiver(analyse_ticker_data_signal)
def analyse_stock_price_place_order(**data:dict):
    cache_key = "_".join([data["symbol"].lower(), "cached_ticker_data"])
    cached_value = redis_cache.get(cache_key)
    df = pd.DataFrame(cached_value["stock_data"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    df.timestamp = df.timestamp.dt.tz_localize('UTC').dt.tz_convert(get_local_time().tzinfo).dt.tz_localize(None)
    price_type = "high" if cached_value["entry_type"]  == "BUY" else "low"
    limit_price = cached_value[price_type]
    price_hit = False
    hit_price = cached_value["auto_exit_price"]
    if price_type == "high" and limit_price > hit_price:
        price_hit = True
        price_hit_row = df.loc[df["ltp"] >= hit_price].iloc[0]
    elif price_type == "low" and limit_price < hit_price:
        price_hit = True
        price_hit_row = df.loc[df["ltp"] <= hit_price].iloc[0]
    df = df.loc[df["timestamp"] > price_hit_row.timestamp + timedelta(minutes=10)] # Time Increament should happen automatically, Implement Later
    last_ticker = df.iloc[-1]
    context = {'transaction_type': cached_value["entry_type"],
        'symbol': data["symbol"],
        'order_type': 'LIMIT',
        'quantity': data["quantity"],
        'price': 0.0,
        'duarion_type': 'DAY',
        'product_type': 'INTRADAY'
    }

    if cached_value["entry_type"]  == "BUY" and price_hit:
        context["transaction_type"] = "SELL"
        if last_ticker.ltp in [np.arange(hit_price, hit_price+0.05, 0.05)]:
            context["price"] = hit_price   
            send_order_request.delay(context) # send order request with limit
            slack_message_sender.delay(text="Auto Exit Order Sent for {0}".format(data["symbol"]), channel="#random")
        elif last_ticker.ltp in [np.arange(hit_price-0.05, hit_price-0.15, 0.05)]:
            context["price"] = 0.0
            context["order_type"] = "MARKET"
            send_order_request.delay(context) # send order request with market order
            slack_message_sender.delay(text="Auto Exit Order Sent for {0}".format(data["symbol"]), channel="#random")
    elif cached_value["entry_type"]  == "SELL" and price_hit:
        context["transaction_type"] = "BUY"
        if last_ticker.ltp in [np.arange(hit_price, hit_price+0.15, 0.05)]:
            context["price"] = 0.0
            context["order_type"] = "MARKET"
            send_order_request.delay(context) # send order request with market order
            slack_message_sender.delay(text="Auto Exit Order Sent for {0}".format(data["symbol"]), channel="#random")
        elif last_ticker.ltp in [np.arange(hit_price, hit_price+0.05, 0.05)]:
            context["price"] = 0.0
            send_order_request.delay(context) # send order request with market order
            slack_message_sender.delay(text="Auto Exit Order Sent for {0}".format(data["symbol"]), channel="#random")



@receiver(analyse_ticker_data_signal)
def exit_on_stoploss_target_hit(**kwargs:dict):
    cache_key = "_".join([kwargs["symbol"].lower(), "cached_ticker_data"])
    cached_value = redis_cache.get(cache_key)
    df = pd.DataFrame(cached_value["stock_data"])
    last_ticker = df.iloc[-1]
    stoploss = cached_value["stoploss"]
    target_price = cached_value["target_price"]
    entry_type = cached_value["entry_type"]
    context = {'transaction_type': cached_value["entry_type"],
        'symbol': kwargs["symbol"],
        'order_type': 'LIMIT',
        'quantity': kwargs["quantity"],
        'price': 0.0,
        'duarion_type': 'DAY',
        'product_type': 'INTRADAY'
    }


    if entry_type == "BUY":
        context["transaction_type"] = "SELL"
        if last_ticker.ltp >= target_price:
            context["price"] = target_price
            send_order_request.delay(context) # send order request with market order
            slack_message_sender.delay(text="Target Hit Order Sent for {0}".format(kwargs["symbol"]), channel="#random")
        elif last_ticker.ltp <= stoploss:
            context["price"] = stoploss
            send_order_request.delay(context) # send order request with market order
            slack_message_sender.delay(text="Stoploss Hit Order Sent for {0}".format(kwargs["symbol"]), channel="#random")
    elif entry_type == "SELL":
        context["transaction_type"] = "BUY"
        if last_ticker.ltp <= target_price:
            context["price"] = target_price
            send_order_request.delay(context) # send order request with market order
            slack_message_sender.delay(text="Target Hit Order Sent for {0}".format(kwargs["symbol"]), channel="#random")
        elif last_ticker.ltp >= stoploss:
            context["price"] = stoploss
            send_order_request.delay(context) # send order request with market order
            slack_message_sender.delay(text="Stoploss Hit Order Sent for {0}".format(kwargs["symbol"]), channel="#random")



