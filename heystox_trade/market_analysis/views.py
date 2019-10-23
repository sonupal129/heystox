from django.shortcuts import render
from django.core.cache import cache
from django.shortcuts import redirect
from django.http import HttpResponse
from market_analysis.models import UserProfile
import datetime
from upstox_api.api import *
# Create your views here.

def upstox_login(request):
      try:
            user_profile = request.user.user_profile
      except:
            redirect(HttpResponse("User Not Found Please Login to heystox first"))
      if user_profile:
            session = Session(user_profile.api_key)
            session.set_redirect_uri("http://127.0.0.1:8000/")
            session.set_api_secret(user_profile.secret_key)
            cache.set("upstox_user_session", session)
            return redirect(session.get_login_url())

def get_access_token_from_upstox(request):
      upstox_response_code = request.GET.get("code", None)
      user_profile = request.user.user_profile
      session = cache.get("upstox_user_session")
      print(session)
      if upstox_response_code != user_profile.response_code:
            user_profile.response_code = upstox_response_code
            user_profile.save()
      if upstox_response_code:
            print(session)
            session.set_code(upstox_response_code)
            access_token = session.retrieve_access_token()
            user_profile.access_token = access_token
            user_profile.save()
            upstox_user = Upstox(user_profile.api_key, access_token)
            cache.set("upstox_login_user", upstox_user)
            print(cache.get("upstox_login_user"))
            return HttpResponse("Successfully logged in Upstox now you can query Upstox api")
      return HttpResponse("Not log in upstox")