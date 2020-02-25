
from django.core.cache import cache, caches
from django.shortcuts import redirect, render, get_object_or_404, resolve_url
from django.http import HttpResponse
from market_analysis.models import UserProfile, MasterContract, SortedStocksList, Symbol, StrategyTimestamp
from datetime import datetime, timedelta
from upstox_api.api import *
from heystox_trade import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.views.generic import ListView, View, TemplateView
from market_analysis.filters import SymbolFilters, SortedStocksFilter
from market_analysis.tasks.trading import get_cached_liquid_stocks
from django.core.exceptions import ImproperlyConfigured
from market_analysis.view_mixins import BasePermissionMixin
from .forms import UserLoginRegisterForm
from django.contrib.auth import authenticate, login
from .mixins import GroupRequiredMixins
# Create your views here.




@login_required
def upstox_login(request):
    if request.user:
        user_profile= request.user.user_profile
    else:
        return redirect("market_analysis_urls:upstox-login")
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
            return HttpResponse("Successfully logged in Upstox now you can query Upstox api")
        except SystemError:
            return redirect("market_analysis_urls:upstox-login")
    return redirect("market_analysis_urls:upstox-login")


class StockDashboardView(ListView):
    template_name = 'dashboard.html'
    context_object_name = "symbols"

    def get_queryset(self):
        filters = SymbolFilters(self.request.GET, queryset=Symbol.objects.filter(id__in=get_cached_liquid_stocks()))
        return filters

class LiveStockDataView(View):
    template_name = "stock_live_data.html"

    def get_template(self):
        if self.template_name:
            return self.template_name
        raise ImproperlyConfigured("Attribute template_name not found, please define attribute first")

    def get(self, request, pk):
        obj = get_object_or_404(Symbol, pk=pk)
        context = {}
        context["obj"] = obj
        context["data"] = obj.get_stock_live_data().to_html()
        template = self.get_template()
        return render(request, template, context)

# class SortedStocksDashBoardView(BasePermissionMixin, GroupRequiredMixins, ListView):
#     template_name = "sorted_stocks_dashboard.html"
#     context_object_name = "symbols"
#     group_required = ["trader"]

#     def get_queryset(self):
#         date = self.request.GET.get("created_at")
#         if date:
#             requested_date = datetime.strptime(date, "%Y-%m-%d").date()
#             filters = SortedStocksList.objects.filter(created_at__date=requested_date).order_by("symbol__symbol")
#             return filters
#         return SortedStocksList.objects.filter(created_at__date=datetime.now().date())


class SortedStocksDashBoardView(BasePermissionMixin, GroupRequiredMixins, ListView):
    template_name = "sorted_stocks_dashboard.html"
    context_object_name = "symbols"
    group_required = ["trader"]

    def get_queryset(self):
        date = self.request.GET.get("created_at")
        if date:
            requested_date = datetime.strptime(date, "%Y-%m-%d").date()
            # filtered_qs = SortedStocksList.objects.filter(created_at__date=requested_date)
            timestamps = StrategyTimestamp.objects.filter(timestamp__date=requested_date, indicator__name="MACD")
        else:
            # filtered_qs = SortedStocksList.objects.filter(created_at__date=datetime.now().date())
            timestamps = StrategyTimestamp.objects.filter(timestamp__date=datetime.now().date(), indicator__name="MACD")
        sorted_stock_id = []
        
        if self.request.GET.get("sara"):
            sorted_stocks = SortedStocksList.objects.filter(created_at__date=datetime.now().date())
            return sorted_stocks
                   
        for stamp in timestamps:
            if stamp.is_last_timestamp():
                try:
                    secondlast_timestamp = stamp.stock.get_second_last_timestamp()
                except:
                    secondlast_timestamp = None
                if secondlast_timestamp and secondlast_timestamp.indicator.name == "STOCHASTIC":
                    if stamp.timestamp - secondlast_timestamp.timestamp < timedelta(minutes=50):
                        sorted_stock_id.append(stamp.stock.id)
        return SortedStocksList.objects.filter(id__in=sorted_stock_id)


class UserLoginRegisterView(LoginView):
    http_method_names = ["post", "get"]
    template_name = "login.html"
    form_class = UserLoginRegisterForm
    success_url = "/dashboard/sorted-stocks/"

    def get_success_url(self):
        if self.success_url:
            return resolve_url(self.success_url)
        raise ImproperlyConfigured("Success Url not defined")

    def post(self, request, *args, **kwargs):
        if request.method == "POST" and "email" in request.POST:
            form = self.get_form()
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)
        elif request.method == "POST" and "register-email" in request.POST:
            return redirect("market_analysis_urls:login-register")

            