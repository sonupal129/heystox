from django.shortcuts import render
from django.core.cache import cache, caches
from django.shortcuts import redirect
from django.http import HttpResponse
from market_analysis.models import UserProfile, MasterContract
import datetime
from upstox_api.api import *
from heystox_trade.settings import upstox_redirect_url
from django.contrib.auth.decorators import login_required
# Create your views here.

@login_required
def upstox_login(request):
      try:
            user_profile = request.user.user_profile
      except:
            redirect(HttpResponse("User Not Found Please Login to heystox first"))
      session = Session(user_profile.credential.api_key)
      session.set_redirect_uri(upstox_redirect_url)
      session.set_api_secret(user_profile.credential.secret_key)
      cache_key = request.user.email + "_upstox_user_session"
      cache.set(cache_key, session)
      return redirect(session.get_login_url())

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