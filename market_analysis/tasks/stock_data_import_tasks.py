from .notification_tasks import slack_message_sender
from market_analysis.models import Symbol, MasterContract, Candle, PreMarketOrderData
from .trading import get_upstox_user
from market_analysis.imports import *
# START CODE BELOW  

@celery_app.task(queue="low_priority")
def update_create_stocks_data(index:str, max_share_price:int=1000, min_share_price:int=40, upstox_user_email="sonupal129@gmail.com"):
    """Update all stocks data after trading day"""
    user = get_upstox_user(email=upstox_user_email)
    stock_list = user.get_master_contract(index)
    bulk_symbol = []
    index_obj = MasterContract.objects.get(name=index)
    for stock in stock_list:
        symbol = stock_list.get(stock)
        if symbol.token and symbol.isin and symbol.closing_price:
            if symbol.closing_price <= max_share_price or symbol.closing_price >= min_share_price:
                try:
                    stock = Symbol.objects.get(token=symbol.token, isin=symbol.isin)
                except Symbol.DoesNotExist:
                    bulk_symbol.append(Symbol(exchange=index_obj, token=symbol.token, symbol=symbol.symbol, name=symbol.name,
                        last_day_closing_price=symbol.closing_price, tick_size=symbol.tick_size, instrument_type=symbol.instrument_type, isin=symbol.isin))
    Symbol.objects.bulk_create(bulk_symbol)
    Symbol.objects.filter(last_day_closing_price__lt=min_share_price, exchange__name="NSE_EQ").delete()
    Symbol.objects.filter(last_day_closing_price__gt=max_share_price, exchange__name="NSE_EQ").delete()
    return "All Stocks Data Updated Sucessfully"


@celery_app.task(queue="low_priority")
def invalidate_stocks_cached_data(symbol:str):
    today_date = str(get_local_time.date())
    stock_data_id = today_date + "_stock_data_" + symbol
    stock_live_data_id = today_date + "_stock_live_data_" + symbol
    cache.delete(stock_data_id)
    cache.delete(stock_live_data_id)
    return f"cache invalidated for {stock_data_id} and {stock_live_data_id}"


@celery_app.task(queue="medium_priority")
def fetch_candles_data(symbol:str, interval="5 Minute", days=6, end_date=None, upstox_user_email="sonupal129@gmail.com", fetch_last_candle:int=None):
    if end_date == None:
        end_date = get_local_time.date()
    user = get_upstox_user(email=upstox_user_email)
    interval_dic = {
        "5 Minute": OHLCInterval.Minute_5,
        "10 Minute": OHLCInterval.Minute_10,
        "15 Minute": OHLCInterval.Minute_15,
    }
    candle_dic = {
        "5 Minute": "M5",
        "10 Minute": "M10",
        "15 Minute": "M15",
    }
    candle_interval = interval_dic.get(interval, "5 Minute")
    start_date = end_date - timedelta(days)
    try:
        stock = Symbol.objects.get(symbol=symbol)
    except Symbol.DoesNotExist:
        return "No Stock Found Please Try with Another"
    user.get_master_contract(stock.exchange.name.upper())
    stock_data = user.get_ohlc(user.get_instrument_by_symbol(stock.exchange.name, stock.symbol), candle_interval, start_date, end_date)
    bulk_candle_data = []
    candle_counter = 0
    if fetch_last_candle:
        stock_data = stock_data[-fetch_last_candle:]
    for data in stock_data:
        timestamp = int(data.get("timestamp")[:10])
        open_price = float(data.get("open"))
        close_price = float(data.get("close"))
        high_price = float(data.get("high"))
        low_price = float(data.get("low"))
        volume = int(data.get("volume"))
        try:
            candle = Candle.objects.get(date=datetime.fromtimestamp(timestamp), symbol=stock)
            candle.open_price = open_price
            candle.close_price = close_price
            candle.high_price = high_price
            candle.low_price = low_price
            candle.volume = volume
            candle.save()
        except Candle.DoesNotExist:
            bulk_candle_data.append(Candle(open_price=open_price, close_price=close_price, low_price=low_price,
                                        high_price=high_price, volume=volume, date=datetime.fromtimestamp(timestamp),
                                        symbol=stock, candle_type="M5"))
    Candle.objects.bulk_create(bulk_candle_data)
    invalidate_stocks_cached_data.delay(symbol)
    return "{0} Candles Data Imported Sucessfully".format(symbol)


@celery_app.task(queue="high_priority")
def update_stocks_candle_data(days=0):
    """Update all stocks candles data after trading day"""
    for q in Symbol.objects.all():
        fetch_candles_data.delay(symbol=q.symbol, days=days)
    return "All Stocks Candle Data Imported Successfully"


@celery_app.task(queue="low_priority")
def update_stocks_volume():
    """Update total traded volume in stock"""
    for stock in Symbol.objects.exclude(exchange__name="NSE_INDEX"):
        volume = stock.get_stock_data().aggregate(Sum("volume"))
        if volume.get("volume__sum"):
            stock.last_day_vtt = volume.get("volume__sum")
            stock.save(update_fields=["last_day_vtt"])
    return "All Stocks Volume Updated"

@celery_app.task(queue="low_priority")    
def update_nifty_50_price_data():
    nifty = Symbol.objects.get(symbol="nifty_50", exchange__name="NSE_INDEX")
    todays_candles = nifty.get_stock_data(days=0, cached=False)
    if todays_candles:
        nifty.last_day_closing_price = nifty.get_day_closing_price()
        nifty.last_day_opening_price = nifty.get_day_opening_price()
        nifty.save()
        return "Updated Nifty_50 Data"

@celery_app.task(queue="low_priority")
def update_symbols_closing_opening_price():
    """Update all stocks opening and closing price"""
    updated_stocks = []
    for symbol in Symbol.objects.exclude(exchange__name="NSE_INDEX"):
        if symbol.get_stock_data(days=0):
            symbol.last_day_closing_price = symbol.get_day_closing_price()
            symbol.last_day_opening_price = symbol.get_day_opening_price()
            symbol.save()
            updated_stocks.append(symbol.id)
    return "Updated Symbols Closing Price"


@celery_app.task(queue="medium_priority")
def import_premarket_stocks_data():
    urls = {"NFTY": "https://www1.nseindia.com/live_market/dynaContent/live_analysis/pre_open/nifty.json",
            "NFTYBNK": "https://www1.nseindia.com/live_market/dynaContent/live_analysis/pre_open/niftybank.json"}
    
    def convert_price(price:str):
        obj_price = price
        if "," in obj_price:
            obj_price = obj_price.replace(",", "")
        obj_price = float(obj_price)
        return obj_price
    
    market_date_url = "https://www1.nseindia.com/live_market/dynaContent/live_analysis/pre_open/pomMktStatus.jsp"
    today_date = get_local_time.date()
    web_response = requests.get(market_date_url, headers=settings.NSE_HEADERS)
    sleep(5)
    market_trading_date = get_local_time.strptime(web_response.text.strip().rsplit("|")[-1].rsplit(" ")[0], "%d-%m-%Y").date()
    slack_message_sender(channel="#random", text=market_trading_date)
    if market_trading_date == today_date:
        for sector, url in urls.items():
            response = requests.get(url, headers=settings.NSE_HEADERS)
            sleep(3)
            if response.status_code == 200:
                response_data = response.json().get("data")
                bulk_data_upload = []
                if response_data:
                    slack_message_sender(channel="#random", text=response)
                    for data in response_data:
                        context = {}
                        symbol = Symbol.objects.get(symbol=data.get("symbol").lower())
                        try:
                            pre_market_stock = PreMarketOrderData.objects.get(symbol=symbol, created_at__date=get_local_time.date())
                        except:
                            pre_market_stock = PreMarketOrderData.objects.create(symbol=symbol, created_at=get_local_time.now())
                        if pre_market_stock:
                            pre_market_stock.sector = sector
                            pre_market_stock.open_price = convert_price(data.get("iep"))
                            pre_market_stock.change = convert_price(data.get("chn"))
                            pre_market_stock.change_percent = convert_price(data.get("perChn"))
                            pre_market_stock.previous_close = convert_price(data.get("pCls"))
                            pre_market_stock.change_percent = convert_price(data.get("perChn"))
                            pre_market_stock.total_trade_qty = convert_price(data.get("trdQnty"))
                            pre_market_stock.save()
        return "Premarket Data Saved Successfully"
    return f"No Trading Day on {today_date}"

@celery_app.task(queue="medium_priority")
def import_daily_losers_gainers():
    current_time = get_local_time.time()
    start_time = time(9,30)
    end_time = time(15,30)
    if current_time > start_time and current_time < end_time:
        urls = {
                "BUY": ["https://www1.nseindia.com/live_market/dynaContent/live_analysis/gainers/niftyGainers1.json",
                        "https://www1.nseindia.com/live_market/dynaContent/live_analysis/gainers/jrNiftyGainers1.json"],
                "SELL": ["https://www1.nseindia.com/live_market/dynaContent/live_analysis/losers/niftyLosers1.json",
                        "https://www1.nseindia.com/live_market/dynaContent/live_analysis/losers/jrNiftyLosers1.json"]
            }
        
        nifty_movement = Symbol.objects.get(symbol="nifty_50").get_nifty_movement()
        
        def response_filter(obj):
            open_price = obj.get("openPrice")
            change = float(obj.get("netPrice"))
            if "," in open_price:
                open_price = open_price.replace(",","")
            open_price = float(open_price)
            if open_price >= 100 and open_price < 300 and change >= 1.2:
                return obj
            
        
        if nifty_movement in ("BUY", "SELL"):
            import_urls = urls.get(nifty_movement)
            if import_urls:
                for url in import_urls:
                    response = requests.get(url, headers=settings.NSE_HEADERS)
                    sleep(4)
                    if response.status_code == 200:
                        responses = filter(response_filter, response.json().get("data"))
                        sleep(1)
                        for symbol in responses:
                            try:
                                stock = Symbol.objects.get(symbol=symbol.get("symbol").lower())
                            except:
                                stock = None
                            if stock:
                                SortedStocksList.objects.get_or_create(symbol=stock, entry_type=nifty_movement, created_at__date=get_local_time.date())
                    else:
                        slack_message_sender.delay(channel="#random", text=f"Incorrect Url: {url}")
                return "All Urls Data Imported Succefully"
    return f"{current_time} Time is greater or lower than {start_time} {end_time}"