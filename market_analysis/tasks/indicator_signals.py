from market_analysis.imports import *
from market_analysis.tasks.orders import send_order_place_request
from market_analysis.models import StrategyTimestamp, OrderBook
# CODE Below 

# @celery_app.task(queue="high_priority")
# def macd_stochastic_combination_signal(macd_stamp_id, stochastic_stamp_id):
#     """generate signal on macd and stochastic combination"""
#     macd_timestamp = StrategyTimestamp.objects.get(id=macd_stamp_id)
#     stoch_timestamp = StrategyTimestamp.objects.get(id=stochastic_stamp_id)
#     if macd_timestamp.timestamp - stoch_timestamp.timestamp < timedelta(minutes=30):
#         entry_price = macd_timestamp.stock.symbol.get_stock_live_price(price_type="open")
#         sorted_stock = macd_timestamp.stock
#         is_stock_moved = sorted_stock.symbol.is_stock_moved_good_for_trading(movement_percent=stock_movement.get(sorted_stock.entry_type))
#         if is_stock_moved:
#             sorted_stock.entry_price = entry_price
#             sorted_stock.save()
#             order_detail = {}
#             order_detail["name"] = sorted_stock.symbol.symbol
#             order_detail["entry_time"] = macd_timestamp.timestamp
#             order_detail["entry_type"] = sorted_stock.entry_type
#             order_detail["entry_price"] = entry_price
#             send_order_place_request.delay(order_detail)
#             return "Order Request Sent"

@celery_app.task(queue="high_priority")
def prepare_orderdata_from_signal(timestamp_id):
    """prepare order data on signal and verify order if order is already placed then do not place new order"""
    timestamp = StrategyTimestamp.objects.get(id=timestamp_id)
    sorted_stock = timestamp.stock
    entry_price = float(timestamp.entry_price)
    
    if sorted_stock.entry_type == "BUY":
        if timestamp.entry_price > timestamp.stock.symbol.get_stock_live_price(price_type="open"):
            entry_price = timestamp.stock.symbol.get_stock_live_price(price_type="open")
    elif sorted_stock.entry_type == "SELL":
        if timestamp.entry_price < timestamp.stock.symbol.get_stock_live_price(price_type="open"):
            entry_price = timestamp.stock.symbol.get_stock_live_price(price_type="open")

    entry_available = False

    try:
        existing_order = OrderBook.objects.get(symbol=sorted_stock.symbol, date__date=get_local_time().date())
        last_order = existing_order.get_last_order_by_status()
        if last_order.entry_type == "EX":
            entry_available = True
    except:
        existing_order = None

    if existing_order == None or entry_available:
        is_stock_moved = sorted_stock.symbol.is_stock_moved_good_for_trading(movement_percent=stock_movement.get(sorted_stock.entry_type))
        if is_stock_moved:
            sorted_stock.entry_price = entry_price
            sorted_stock.save()
            order_detail = {}
            order_detail["name"] = sorted_stock.symbol.symbol
            order_detail["entry_time"] = timestamp.timestamp
            order_detail["entry_type"] = sorted_stock.entry_type
            order_detail["entry_price"] = entry_price
            send_order_place_request.delay(order_detail)
            return "Order Request Sent"
        return "Not Enough Movement in Stock"
    elif existing_order:
        strength = existing_order.strength
        existing_order.strength = ", ".join(strength, timestamp.indicator.name)
        existing_order.save()




