from django import template
# Code Starts

register = template.Library()

@register.simple_tag
def get_day_high_low(symbol, price_type):
    return symbol.get_days_high_low_price(price_type=price_type)
