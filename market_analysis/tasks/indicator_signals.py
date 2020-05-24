from market_analysis.imports import *
from market_analysis.tasks.orders import send_order_place_request
from market_analysis.models import StrategyTimestamp, OrderBook
# CODE Below 

@celery_app.task(queue="high_priority")
def prepare_orderdata_from_signal(timestamp_id):
    """prepare order data on signal and verify order if order is already placed then do not place new order"""
    timestamp = StrategyTimestamp.objects.get(id=timestamp_id)
    sorted_stock = timestamp.stock
    entry_price = float(timestamp.entry_price) if timestamp.entry_price else None
    
    if is_time_between_range(timestamp.timestamp, 20):

        if sorted_stock.entry_type == "BUY":
            if timestamp.entry_price > timestamp.stock.symbol.get_stock_live_price(price_type="open") or entry_price == None:
                entry_price = timestamp.stock.symbol.get_stock_live_price(price_type="open")
        elif sorted_stock.entry_type == "SELL":
            if timestamp.entry_price < timestamp.stock.symbol.get_stock_live_price(price_type="open") or entry_price == None:
                entry_price = timestamp.stock.symbol.get_stock_live_price(price_type="open")

        entry_available = False

        try:
            existing_order = OrderBook.objects.get(symbol=sorted_stock.symbol, date=get_local_time().date())
            last_order = existing_order.get_last_order_by_status()
            if last_order.entry_type == "EX":
                entry_available = True
        except:
            existing_order = None

        sorted_stock.entry_price = entry_price
        sorted_stock.save()
        order_detail = {}
        order_detail["name"] = sorted_stock.symbol.symbol
        order_detail["entry_time"] = timestamp.timestamp
        order_detail["entry_type"] = sorted_stock.entry_type
        order_detail["entry_price"] = entry_price
        
        if existing_order == None or entry_available:
            send_order_place_request.delay(order_detail)
            return "Order Request Sent"
        elif existing_order:
            strength = existing_order.strength if existing_order.strength else ""
            existing_order.strength = ", ".join([strength, timestamp.indicator.name])
            existing_order.save()
    else:
        slack_message_sender.delay(text=f"Stock Entry Time is Out of Limit Could Not Place Order for {sorted_stock}")
        return "Crossover out of time limit"
        

# def indicator_routers(timestamp_id):
#     timestamp = StrategyTimestamp.objects.get(id=timestamp_id)
#     sorted_stock = timestamp.stock
#     if instance.indicator.indicator_type == "PR":
#         prepare_orderdata_from_signal.delay(timestamp_id)





