from upstox_api.api import *

my_api_key = ""
my_secrect_key = ""
my_redirect_url = ""
login_response_code = ""
# Code Starts Below

login_session = Session(my_api_key)
login_session.set_redirect_uri(my_redirect_url)
login_session.set_api_secret(my_secrect_key)
print(login_session.get_login_url())
login_session.set_code(login_response_code)
access_token = login_session.retrieve_access_token()
print(access_token)

# Establish Connection

u = Upstox(my_api_key, access_token)


def event_handler_quote_update(message):
    print("Quote Update: %s" % str(message))

u.set_on_quote_update(event_handler_quote_update)
u.subscribe(u.get_instrument_by_symbol('NSE_EQ', 'TATASTEEL'), LiveFeedType.Full)
u.start_websocket(True)

