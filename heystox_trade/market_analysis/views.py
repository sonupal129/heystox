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
            # request.session["upstox_session"] = session
            cache.set("upstox_user", session)
            return redirect(session.get_login_url())

def get_access_token_from_upstox(request):
      upstox_response_code = request.GET.get("code")
      user_profile = request.user.user_profile
      session = request.session.get("upstox_session")
      print(cache.get("upstox_user"))
      if upstox_response_code and user_profile.updated.date() != datetime.datetime.now().date():
            session.set_code(upstox_response_code)
            access_token = session.retrieve_access_token()
            user_profile.response_code = upstox_response_code
            user_profile.access_token = access_token
            user_profile.save()
            upstox_user = Upstox(upstox_api_key, access_token)
            return HttpResponse("Successfully logged in Upstox now you can query Upstox api")
      return HttpResponse("Not log in upstox")