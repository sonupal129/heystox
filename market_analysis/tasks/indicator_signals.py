from market_analysis.imports import *
from market_analysis.tasks.orders import send_order_place_request
from market_analysis.models import StrategyTimestamp
# CODE Below 

@celery_app.task(queue="high_priority")
def macd_stochastic_signal(macd_stamp_id, stochastic_stamp_id):
    """generate signal on macd and stochastic combination"""
    macd_timestamp = StrategyTimestamp.objects.get(id=macd_stamp_id)
    stoch_timestamp = StrategyTimestamp.objects.get(id=stochastic_stamp_id)
    if macd_timestamp.timestamp - stoch_timestamp.timestamp < timedelta(minutes=30):
        entry_price = macd_timestamp.stock.symbol.get_stock_live_price(price_type="open")
        sorted_stock = macd_timestamp.stock
        if sorted_stock.symbol.is_stock_moved_good_for_trading(movement_percent=stock_movement.get(sorted_stock.entry_type)):
            sorted_stock.entry_price = entry_price
            sorted_stock.save()
            order_detail = {}
            order_detail["name"] = sorted_stock.symbol.symbol
            order_detail["entry_time"] = macd_timestamp.timestamp
            order_detail["entry_type"] = sorted_stock.entry_type
            order_detail["entry_price"] = entry_price
            send_order_place_request.delay(order_detail)
            return "Order Request Sent"