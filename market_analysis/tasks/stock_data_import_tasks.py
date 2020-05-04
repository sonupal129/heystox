from .notification_tasks import slack_message_sender
from market_analysis.models import Symbol, MasterContract, Candle, PreMarketOrderData, SortedStocksList
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
    today_date = str(get_local_time().date())
    stock_data_id = today_date + "_stock_data_" + symbol
    cache.delete(stock_data_id)
    return f"cache invalidated for {stock_data_id}"


@celery_app.task(queue="medium_priority", autoretry_for=(JSONDecodeError, TypeError, HTTPError), retry_kwargs={'max_retries': 2, 'countdown': 10})
def fetch_candles_data(symbol:str, interval="5 Minute", days=6, end_date=None, upstox_user_email="sonupal129@gmail.com", fetch_last_candle:int=None):
    if end_date == None:
        end_date = get_local_time().date()
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
def update_stocks_candle_data(days=6):
    """Update all stocks candles data after trading day"""
    for q in Symbol.objects.filter(exchange__name__in=["NSE_EQ", "NSE_INDEX"]):
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
    for symbol in Symbol.objects.filter(exchange__name="NSE_EQ"):
        if symbol.get_stock_data():
            symbol.last_day_closing_price = symbol.get_day_closing_price()
            symbol.last_day_opening_price = symbol.get_day_opening_price()
            symbol.save()
            updated_stocks.append(symbol.id)
    return "Updated Symbols Closing Price"


@celery_app.task(queue="medium_priority")
def import_premarket_stocks_data():
    urls = {"NFTY" : "https://www.nseindia.com/api/market-data-pre-open?key=NIFTY",
            "NFTYBNK": "https://www.nseindia.com/api/market-data-pre-open?key=BANKNIFTY"}
    
    proxy = {'http': 'http://165.22.223.235:8118'} # Modify Function And Create rotating proxy mechanism 
    
    def response_filter(obj):
        last_price = obj["metadata"]["previousClose"]
        if last_price > 60 and last_price < 300:
            return obj
    
    market_date_url = "https://www.nseindia.com/api/marketStatus"
    today_date = get_local_time().date()
    web_response = requests.get(market_date_url, headers=settings.NSE_HEADERS, proxies=proxy).json()["marketState"]
    market_trading_date = get_local_time().strptime(web_response[0]["tradeDate"], "%d-%b-%Y").date()
    
    if market_trading_date == today_date:
        for sector, url in urls.items():
            response = requests.get(url, headers=settings.NSE_HEADERS, proxies=proxy)
            sleep(1)
            if response.status_code == 200:
                response_data = response.json().get("data")
                bulk_data_upload = []
                if response_data:
                    response_data = filter(response_filter, response_data)
                    for data in response_data:
                        metadata = data["metadata"]
                        details = data["detail"]["preOpenMarket"]
                        context = {}
                        try:
                            symbol = Symbol.objects.get(symbol=metadata.get("symbol").lower())
                        except:
                            continue
                        pre_market_stock, is_created = PreMarketOrderData.objects.get_or_create(symbol=symbol, created_at__date=get_local_time().date())
                        if pre_market_stock:
                            pre_market_stock.sector = sector
                            pre_market_stock.open_price = details["IEP"]
                            pre_market_stock.change = metadata["change"]
                            pre_market_stock.change_percent = metadata["pChange"]
                            pre_market_stock.previous_close = metadata["previousClose"]
                            pre_market_stock.total_trade_qty = metadata["finalQuantity"]
                            pre_market_stock.buy_qty_ato = details["atoBuyQty"]
                            pre_market_stock.sell_qty_ato = details["atoSellQty"]
                            pre_market_stock.total_buy_qty = details["totalBuyQuantity"]
                            pre_market_stock.total_sell_qty = details["totalSellQuantity"]
                            pre_market_stock.save()
        return "Premarket Data Saved Successfully"
    return f"No Trading Day on {today_date}"


@celery_app.task(queue="medium_priority")
def import_daily_losers_gainers():
    current_time = get_local_time().time()
    start_time = time(9,30)
    end_time = time(15,30)
    if current_time > start_time and current_time < end_time:
        urls = (
        "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20NEXT%2050",
        "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050"
        )
        nifty_movement = Symbol.objects.get(symbol="nifty_50").get_nifty_movement()
    else:
        return f"Current Time {current_time} is greater or lower than Market start {start_time} and end time {end_time}"
    
    def response_filter(obj):
        open_price = obj.get("open")
        change = obj.get("pChange")
        if open_price >= 100 and open_price < 300:
            if change >= settings.MARKET_BULLISH_MOVEMENT or change <= settings.MARKET_BEARISH_MOVEMENT:
                return obj
            
    proxy = {'http': 'http://165.22.223.235:8118'} # Modify Function And Create rotating proxy mechanism
    if nifty_movement in ("BUY", "SELL"):
        created_stocks = []
        for url in urls:
            response = requests.get(url, headers=settings.NSE_HEADERS, proxies=proxy)
            sleep(1)
            if response.status_code == 200:
                sell_stocks = sorted(response.json().get("data"), key= lambda o : o.get("pChange"))[:15]
                buy_stocks = sorted(response.json().get("data"), key= lambda o : o.get("pChange"), reverse=True)[:15]
                responses = filter(response_filter, sell_stocks + buy_stocks)
                for symbol in responses:
                    try:
                        stock = Symbol.objects.get(symbol=symbol.get("symbol").lower())
                    except:
                        continue
                    sorted_stock, is_created = SortedStocksList.objects.get_or_create(symbol=stock, entry_type="BUY" if symbol.get("pChange") > 0 else "SELL", created_at__date=get_local_time().date())
                    if is_created:
                        created_stocks.append(stock.symbol)
        return f"Added Stocks {created_stocks}"


@celery_app.task(queue="low_priority")
def import_international_market_index_data():
    """This function will import international market index daily chart data for ex -- Dow Jones,
        NIKKI, HENSENG, SGX Nifty, For importing data it is using yahoo finance api"""
    index_unique_key = {
        "DOW_JONES" : "%5EDJI",
        "HSI" : "^HSI",
        "SGX" : "S68.SI"
    }
    
    today_date = get_local_time().date()
    today_date_timestamp = int(time_library.mktime(today_date.timetuple()))
    last_month_timestamp = int(time_library.mktime((get_local_time().date()- timedelta(days=30)).timetuple()))
    
    
    for index, unique_key in index_unique_key.items():
        try:
            index_symbol = Symbol.objects.get(symbol=index, exchange__name=index)
        except:
            index_symbol = Symbol.objects.create(symbol=index, exchange=MasterContract.objects.get(name=index))
        url = f"https://query1.finance.yahoo.com/v7/finance/download/{unique_key}?period1={last_month_timestamp}&period2={today_date_timestamp}&interval=1d&events=history"
        response = requests.get(url, allow_redirects=True)
        decode_response = response.content.decode('utf-8')
        csv_file = csv.reader(decode_response.splitlines(), delimiter=',')
        df = pd.DataFrame(list(csv_file))
        df.columns = df.iloc[0]
        df = df.drop(0)
        df["Open"] = df.Open.apply(roundup) 
        df["High"] = df.High.apply(roundup)
        df["Low"] = df.Low.apply(roundup)
        df["Close"] = df.Close.apply(roundup)
        df = df.dropna()
        for data in df.to_dict("records"):
            converted_date = datetime.strptime(data["Date"], "%Y-%m-%d")
            print(converted_date)
            candle, is_created = Candle.objects.get_or_create(symbol=index_symbol, candle_type="1D", date=converted_date)
            candle.open_price = data["Open"]
            candle.high_price = data["High"]
            candle.low_price = data["Low"]
            candle.close_price = data["Close"]
            candle.volume = data["Volume"]
            candle.save()
    return "Candle Data Saved for International Indexes"
