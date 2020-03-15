from market_analysis.imports import *
from market_analysis.tasks.orders import send_order_place_request
from market_analysis.models import StrategyTimestamp
# CODE Below

@celery_app.task(queue="low_priority")
def macd_stochastic_signal(macd_stamp_id, stochastic_stamp_id):
    """generate signal on macd and stochastic combination"""
    macd_timestamp = StrategyTimestamp.objects.get(pk=macd_stamp_id)
    stoch_timestamp = StrategyTimestamp.objects.get(pk=stochastic_stamp_id)
    if macd_timestamp.timestamp - stoch_timestamp.timestamp < timedelta(minutes=30):
        entry_price = macd_timestamp.stock.symbol.get_stock_live_price(price_type="open")
        macd_timestamp.stock.entry_price = entry_price
        macd_timestamp.stock.save()
        order_detail = {}
        order_detail["name"] = macd_timestamp.stock.symbol.symbol
        order_detail["entry_time"] = macd_timestamp.timestamp
        order_detail["entry_type"] = macd_timestamp.stock.entry_type
        order_detail["entry_price"] = entry_price
        send_order_place_request.delay(order_detail)
        return "Order Request Sent"