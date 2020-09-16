from django import template
# Code Starts

register = template.Library()

@register.simple_tag
def get_day_high_low(symbol, price_type):
    return symbol.get_stock_high_low_price(price_type=price_type)

@register.simple_tag
def get_timestamp_by_indicator(sorted_stock, indicator_name):
    return sorted_stock.get_indicator_timestamp(indicator_name=indicator_name)

@register.simple_tag
def get_sorted_stock_closing_price(sorted_stock):
    closing_price = sorted_stock.symbol.get_day_closing_price(date_obj=sorted_stock.created_at.date())
    if closing_price:
        return closing_price
    return None

@register.simple_tag
def get_total_loss(symbol):
    if symbol.quantity and symbol.pl:
        return symbol.quantity * symbol.pl
    