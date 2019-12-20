from django.shortcuts import render
from django.core.cache import cache, caches
from django.shortcuts import redirect
from django.http import HttpResponse
from market_analysis.models import UserProfile, MasterContract
import datetime
from upstox_api.api import *
from heystox_trade import settings
from django.contrib.auth.decorators import login_required
# Create your views here.

@login_required
def upstox_login(request):
      if request.user:
            user_profile= request.user.user_profile
      else:
            return redirect("market_analysis:upstox-login")
      if user_profile and user_profile.for_trade and user_profile.subscribed_historical_api or user_profile.subscribed_live_api:
            login_url = user_profile.get_authentication_url()
            return redirect(login_url)
      else:
            return(HttpResponse("Requested User UserProfile Not Created or Not Subscribed for Api's"))
      

@login_required
def get_access_token_from_upstox(request):
      upstox_response_code = request.GET.get("code", None)
      user_profile = request.user.user_profile
      session = cache.get(request.user.email + "_upstox_user_session")
      if upstox_response_code != cache.get(request.user.email + "_upstox_user_response_code"):
            cache.set(request.user.email + "_upstox_user_response_code", upstox_response_code)
      if upstox_response_code is not None:
            session.set_code(upstox_response_code)
            try:
                  access_token = session.retrieve_access_token()
                  user_profile.credential.access_token = access_token
                  user_profile.credential.save()
                  upstox_user = Upstox(user_profile.credential.api_key, access_token)
                  cache.set(request.user.email + "_upstox_login_user", upstox_user)
                  master_contracts = MasterContract.objects.values()
                  return HttpResponse("Successfully logged in Upstox now you can query Upstox api")
            except SystemError:
                  return redirect("market_analysis:upstox-login")
      return redirect("market_analysis:upstox-login")