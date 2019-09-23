from upstox_api.api import *
from market_analysis.models import Symbol, MasterContract
import datetime


my_api_key = "VpcuCaUDK91y9JPy358T19nUWtq0UF6J8Yl3qVmr"
my_secrect_key = "2oq0c08yce"
my_redirect_url = "http://127.0.0.1:8000/"
login_response_code = "ba1fc28b9f84fe0d5362c0ea10fcf74667d995cd"
my_access_token = 'c29f7da405b4b0e2ebb09fb9ddc8c6aeb00902b7'
# Code Starts Below

login_session = Session(my_api_key)


def get_upstox_login_url(api_key, session, redirect_url):
      session.set_redirect_uri(my_redirect_url)
      session.set_api_secret(my_secrect_key)
      return session.get_login_url()

def get_access_token(login_response_code, session):
      session.set_code(login_response_code)
      return session.retrieve_access_token()

def logged_in_user(api_key, access_token):
      return Upstox(api_key, access_token)

# Establish Connection


# def event_handler_quote_update(message):
#     print("Quote Update: %s" % str(message))

# u.set_on_quote_update(event_handler_quote_update)
# u.subscribe(u.get_instrument_by_symbol('NSE_EQ', 'TATASTEEL'), LiveFeedType.Full)
# u.start_websocket(True)

def update_index_data(user, index):
      stock_list = user.get_master_contract(index)
      bulk_symbol = []
      index_obj = MasterContract.objects.get(name=index)
      for stock in stock_list:
            symbol = stock_list.get(stock)
            try:
                  stock = Symbol.objects.get(token=symbol.token, isin=symbol.isin)
                  stock.closing_price = symbol.closing_price
                  stock.save()
            except Symbol.DoesNotExist:
                  bulk_symbol.append(Symbol(exchange=index_obj, token=symbol.token, symbol=symbol.symbol, name=symbol.name,
                        closing_price=symbol.closing_price, tick_size=symbol.tick_size, instrument_type=symbol.instrument_type,
                        isin=symbol.isin))
      Symbol.objects.bulk_create(bulk_symbol)
      return "All Stock Price Updated Sucessfully"

def get_stock_data(user, symbol, interval, start_date, end_date):
      interval_dic = {
            "5 Minute": OHLCInterval.Minute_5,
            "10 Minute": OHLCInterval.Minute_10,
            "15 Minute": OHLCInterval.Minute_15,
      }
      candle_interval = interval_dic.get(interval, "5 Minute")
      start_date = datetime.datetime.strptime(start_date,'%d/%m/%Y').date()
      end_date = datetime.datetime.strptime(end_date,'%d/%m/%Y').date()
      try:
            stock = Symbol.objects.get(symbol=symbol)
      except Symbol.DoesNotExist:
            return "No Stock Found Please Try with Another"
      stock_data = user.get_ohlc(user.get_instrument_by_symbol(stock.exchange.name, stock.symbol), candle_interval, start_date, end_date)
      return stock_data