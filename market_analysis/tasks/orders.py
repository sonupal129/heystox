from market_analysis.imports import *
from .trading import get_upstox_user
from market_analysis.models import Symbol, SortedStockDashboardReport, OrderBook, Order
from market_analysis.tasks.notification_tasks import slack_message_sender
from market_analysis.custom_exception import *
# Code Below


# Orders Functions
class BaseOrderTask(celery_app.Task):
    """Base order task which will place order and update everything related to order details"""
    name = "place_order"
    queue = "high_priority"

    def find_last_order(self, order1, order2):
        if order1.entry_time > order2.entry_time:
            return order1
        return order2

    def calculate_order_quantity(self, share_price, entry_type):
        user = get_upstox_user()
        balance = user.get_balance()
        if balance:
            available_margin = balance["equity"].get("available_margin")
            if available_margin <= 1000:
                raise NotEnoughFundError("Not enough fund availble to trade")
            bearable_loss = available_margin * settings.DEFAULT_STOPLOSS / 100
            stoploss = get_stock_stoploss_price(share_price, entry_type)
            diff = abs(share_price - stoploss)
            if diff < 1:
                diff = 1
            qty = int(bearable_loss / diff)
            if qty > settings.MAX_ORDER_QUANTITY:
                return settings.MAX_ORDER_QUANTITY
            return abs(qty)
        raise AttributeError("Unable to fetch user balance")

    def get_or_update_order_quantity(self, update=False):
        cache_key = str(get_local_time().date()) + "_total_order_quantity"
        cached_value = redis_cache.get(cache_key)
        if cached_value == None:
            redis_cache.set(cache_key, 0)
            return 0
        if update and (cached_value == 0 or cached_value):
            cached_value += 1
            redis_cache.set(cache_key, cached_value)
            return cached_value
        return cached_value

    def send_order_request(self, order_details:dict, ignore_max_trade_quantity:bool=False): # Don't Change This Function Format, Because This is As per Upstox Format, 
        user = get_upstox_user()
        today_date = get_local_time().date()
        orders_qty = self.get_or_update_order_quantity()
        if not ignore_max_trade_quantity:
            if orders_qty >= settings.MAX_DAILY_TRADE:
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
            last_order = self.find_last_order(last_open_order, last_completed_order)
        else:
            last_order = last_completed_order or last_open_order
        
        # order = None
        if is_created:
            order = Order.objects.create(order_book=order_book, transaction_type=transaction_type)
        elif last_order:
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
                    order.stoploss = get_stock_stoploss_price(price, transaction_type)
                    order.target_price = get_stock_target_price(price, transaction_type)
                order.quantity = quantity
                order.entry_price = price
                order.save()
                return True
        return False


    def run(self, order_details:dict, ignore_max_trade_quantity:bool=False, **kwargs):
        place_order = self.send_order_request(order_details, ignore_max_trade_quantity)
        if callable(place_order):
            return "Something Wrong in function"
        return place_order

class EntryOrder(BaseOrderTask):
    """Place entry order receive data from router signals class is used only for placing entry orders"""
    name = "place_market_entry_order"
    
    def add_expected_target_stoploss(self, stock_report_id):
        report = SortedStockDashboardReport.objects.get(id=stock_report_id)
        price = report.entry_price
        report.stoploss_price = get_stock_stoploss_price(price, report.entry_type)
        report.target_price = get_stock_target_price(price, report.entry_type)
        report.save()
        
    def send_order_place_request(self, signal_detail:dict=None):
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
        order_schema["quantity"] = self.calculate_order_quantity(entry_price, entry_type)
        order_schema["price"] = entry_price
        order_schema["duarion_type"] = "DAY"
        order_schema["order_type"] = "LIMIT"
        order_schema["product_type"] = "INTRADAY"
        print(order_schema)
        if entry_time.time() > order_place_start_time and entry_time.time() < order_place_end_time:
            obj, is_created = SortedStockDashboardReport.objects.get_or_create(**signal_detail)
            self.add_expected_target_stoploss(obj.id)
            slack_message_sender.delay(text=f"{entry_price} Signal {entry_type} Stock Name {name} Time {entry_time}", channel="#random")
            self.send_order_request(order_schema)

    def run(self, signal_detail:dict):
        self.send_order_place_request(signal_detail)
        return "Order Place Request Sent"

celery_app.tasks.register(EntryOrder)

class ExitOrder(BaseOrderTask):
    name = "place_market_exit_order"
    pass

celery_app.tasks.register(ExitOrder)

# od = {'transaction_type': 'SELL', 'symbol': 'CANBK', 'order_type': 'LIMIT', 'quantity': 1, 'price': 87.20, ', duarion_type': 'DAY', 'product_type': 'INTRADAY'}

class UpdateOrder(BaseOrderTask):
    """This class/function update or create order in database """
    name = "create_update_order_on_update"

    def create_update_order_on_update(self, order_data):
        sleep(0.2)
        order_choices = {
            "cancelled": "CA",
            "open": "OP",
            "complete": "CO",
            "rejected": "RE"
        }
        if order_data.get("transaction_type") == "B":
            order_data["transaction_type"] = "BUY"
        elif order_data.get("transaction_type") == "S":
            order_data["transaction_type"] = "SELL"
        else:
            pass

        order_id = order_data.get("order_id")
        user = get_upstox_user()
        user.get_master_contract(order_data.get("exchange"))
        exchange_time = get_local_time().now()
        order, is_created = Order.objects.get_or_create(order_id=order_id)
        
        if is_created:
            order_book = OrderBook.objects.get(symbol__symbol__iexact=order_data.get("symbol"), date=get_local_time().date())
            order.transaction_type = "BUY" if order_data.get("transaction_type") == "BUY" else "SELL"
            order.order_book = order_book
            order.save()
        
        if order.entry_type != "" and order.status not in ["CO", "OP"]:
            order.entry_type = ""
        
        order.message = order_data.get("message")
        order.entry_price = order_data.get("price") or order_data.get("average_price")
        order.entry_time = exchange_time if exchange_time else get_local_time().now()
        order.status = order_choices.get(order_data["status"])
        
        if order.status in ["CO", "OP"] and order.entry_type == "":
            
            last_completed_order = order.order_book.get_last_order_by_status("CO")
            last_open_order = order.order_book.get_last_order_by_status("OP")
            
            if last_completed_order and last_open_order:
                last_order = self.find_last_order(last_open_order, last_completed_order)
            else:
                last_order = last_completed_order or last_open_order
            
            if last_order and last_order.entry_type == "ET":
                order.entry_type = "EX"
            else:
                order.entry_type = "ET"

        if order.entry_type == "ET":
            order.stoploss = get_stock_stoploss_price(order.entry_price, order.transaction_type)
            order.target_price = get_stock_target_price(order.entry_price, order.transaction_type)
        
        order.save()

        if order.status == "CO":
            # Create Logic About when to Subscribe for instrument
            cache_key = "_".join([order_data["symbol"].lower(), "cached_ticker_data"])
            if order.entry_type == "ET":
                self.get_or_update_order_quantity(True)
                data = {
                    "symbol": order_data.get("symbol"),
                    "target_price" : order.target_price,
                    "stoploss": order.stoploss,
                    "auto_exit_price" : get_auto_exit_price(order.entry_price, order.transaction_type),
                    "transaction_type" : order.transaction_type,
                    "order_id" : order.order_id,
                    "stock_data" : None,
                    "entry_price" : order.entry_price,
                    "entry_time" : order.entry_time,
                    "quantity" : order.quantity
                }
                redis_cache.set(cache_key, data)
                user.subscribe(user.get_instrument_by_symbol(order_data.get("exchange"), order_data.get("symbol")), LiveFeedType.Full)
            elif order.entry_type == "EX":
                stoploss_target_cache_key = "_".join([order_data.get("symbol").lower(), "stoploss_target_hit"])
                auto_exit_cache_key = "_".join([order_data.get("symbol").lower(), "auto_exit_price"])
                redis_cache.delete(auto_exit_cache_key)
                redis_cache.delete(stoploss_target_cache_key)
                redis_cache.delete(cache_key)
                user.unsubscribe(user.get_instrument_by_symbol(order_data.get("exchange"), order_data.get("symbol")), LiveFeedType.Full)
        slack_message_sender.delay(text=str(order.order_id) + " Order Status Changed to {0} Please Check".format(order_data["status"]), channel="#random")

    def run(self, order_data:dict, *args, **kwargs):
        self.create_update_order_on_update(order_data)


celery_app.tasks.register(UpdateOrder)

@celery_app.task(queue="high_priority")
def cancel_not_executed_orders(from_last_minutes=20):
    """Cancel orders which are not executed after 20 minutes of placing"""
    orders = Order.objects.filter(entry_time__range=[get_local_time().date(), get_local_time().now() - timedelta(minutes=from_last_minutes)], status="OP")
    user = get_upstox_user()
    if orders.exists():
        for order in orders:
            user.cancel_order(order.order_id)


def cache_symbol_ticker_data(data:dict):
    cache_key = "_".join([data["symbol"].lower(), "cached_ticker_data"])
    cached_value = redis_cache.get(cache_key)
    price_type = "high" if cached_value.get("transaction_type") == "BUY" else "low"
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
    exit_on_stoploss_target_hit.delay(data["symbol"].lower())
    # exit_on_auto_hit_price.delay(data["symbol"].lower())
    return cached_value


@celery_app.task(queue="tickers")
def exit_on_auto_hit_price(symbol_name:str):
    """This function will take exit if price after reaching a certain price coming down or vice versa"""
    cache_key = "_".join([symbol_name.lower(), "cached_ticker_data"])
    cached_value = redis_cache.get(cache_key)
    df = pd.DataFrame(cached_value["stock_data"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    df.timestamp = df.timestamp.dt.tz_localize('UTC').dt.tz_convert(get_local_time().tzinfo).dt.tz_localize(None)
    price_type = "high" if cached_value["transaction_type"]  == "BUY" else "low"
    limit_price = cached_value[price_type]
    price_hit = False
    hit_price = cached_value["auto_exit_price"]

    price_hit_row = pd.Series()
    
    try:
        if price_type == "high" and limit_price > hit_price:
            price_hit = True
            price_hit_row = df.loc[df["ltp"] >= hit_price].iloc[0]
        elif price_type == "low" and limit_price < hit_price:
            price_hit = True
            price_hit_row = df.loc[df["ltp"] <= hit_price].iloc[0]
    except:
        pass
        
    if not price_hit_row.empty:
        df = df.loc[df["timestamp"] > price_hit_row.timestamp + timedelta(minutes=15)] # Time Increament should happen automatically, Implement Later
        auto_exit_cache_key = "_".join([symbol_name.lower(), "auto_exit_price"])
        if not df.empty:
            last_ticker = df.iloc[-1]
            last_ticker_ltp = last_ticker.ltp
            
            context = {'transaction_type': cached_value["transaction_type"],
                'symbol': cached_value["symbol"],
                'order_type': 'LIMIT',
                'quantity': cached_value["quantity"],
                'price': 0.0,
                'duarion_type': 'DAY',
                'product_type': 'INTRADAY'
            }

            auto_exit_hit = False

            if cached_value["transaction_type"]  == "BUY" and price_hit:
                context["transaction_type"] = "SELL"
                if last_ticker_ltp in np.arange(hit_price, hit_price+0.05, 0.05):
                    context["price"] = hit_price   
                    # print("BUY Auto Exit Limit")
                    auto_exit_hit = True
                elif last_ticker_ltp in np.arange(hit_price-0.05, hit_price-0.15, 0.05):
                    context["price"] = 0.0
                    context["order_type"] = "MARKET"
                    auto_exit_hit = True
                    # print("BUY Auto Exit Market")
            elif cached_value["transaction_type"]  == "SELL" and price_hit:
                context["transaction_type"] = "BUY"
                if last_ticker_ltp in np.arange(hit_price, hit_price+0.15, 0.05):
                    context["price"] = 0.0
                    context["order_type"] = "MARKET"
                    auto_exit_hit = True
                    # print("Sell Auto Exit Limit")
                elif last_ticker_ltp in np.arange(hit_price, hit_price+0.05, 0.05):
                    context["price"] = 0.0
                    auto_exit_hit = True
                    # print("Sell Auto Exit Market")

            if auto_exit_hit:
                if not redis_cache.get(auto_exit_cache_key):
                    send_order_request.delay(context, True) # send order request with market order
                    slack_message_sender.delay(text="Auto Exit Order Sent for {0}".format(symbol_name), channel="#random")
                    redis_cache.set(auto_exit_cache_key)


@celery_app.task(queue="high_priority")
def update_orders_status():
    """This function will run asynchrously to check if order status not get updated by socket will update it"""
    orders = Order.objects.filter(entry_time__date=get_local_time().date(), status="OP")
    user = get_upstox_user()
    orders_history = user.get_order_history()
    if orders.exists():
        for order in orders:
            try:
                order_detail = list(filter(lambda o: o.get("order_id") == int(order.order_id) and o.get("status") in ["complete", "cancelled", "rejected"] , orders_history))[0]
                UpdateOrder().delay(order_detail)
            except:
                continue
    order_ids = Order.objects.filter(entry_time__date=get_local_time().date()).values_list("order_id", flat=True)
    new_orders = [order for order in orders_history if str(order.get("order_id")) not in order_ids]
    if new_orders:
        for order in new_orders:
            UpdateOrder().delay(order)