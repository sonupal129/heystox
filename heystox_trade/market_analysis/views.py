from django.shortcuts import render
from heystox_trade.settings import upstox_api_key, upstox_secrect_key, redirect_url
from django.shortcuts import redirect
from django.http import HttpResponse
from market_analysis.models import UserProfile
import datetime
from upstox_api.api import *
# Create your views here.
session = Session(upstox_api_key)
upstox_user = None

def upstox_login(request):
      global session
      session.set_redirect_uri(redirect_url)
      session.set_api_secret(upstox_secrect_key)
      return redirect(session.get_login_url())

def get_access_token_from_upstox(requests):
      response_code = requests.GET.get("code")
      user_profile = UserProfile.objects.get(email=requests.user.email)
      global session
      session.set_code(response_code)
      session.set_redirect_uri(redirect_url)
      session.set_api_secret(upstox_secrect_key)
      global upstox_user
      if response_code and user_profile.updated.date() != datetime.datetime.now().date():
            access_token = session.retrieve_access_token()
            user_profile.response_code = response_code
            user_profile.access_token = access_token
            user_profile.save()
            upstox_user = Upstox(upstox_api_key, access_token)     
            return HttpResponse("Successfully logged in Upstox now you can query Upstox api")
      else:
           upstox_user = Upstox(upstox_api_key, user_profile.access_token)
           return HttpResponse("Successfully logged in Upstox now you can query Upstox api")
      return HttpResponse("Not log in upstox")