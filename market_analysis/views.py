from market_analysis.imports import *
from market_analysis.models import UserProfile, MasterContract, SortedStocksList, Symbol, StrategyTimestamp, SortedStockDashboardReport, DeployedStrategies
from market_analysis.filters import SymbolFilters, SortedStocksFilter
from market_analysis.tasks.trading import get_cached_liquid_stocks, get_liquid_stocks, get_upstox_user
from market_analysis.view_mixins import BasePermissionMixin
from .forms import UserLoginRegisterForm, BacktestForm, StrategyDeployForm
from .mixins import *
from market_analysis.tasks.notification_tasks import slack_message_sender
from market_analysis.tasks.users_tasks import login_upstox_user
from market_analysis.tasks.strategies.backtest import SendBackTestingRequest
# Create your views here.

class HomeView(BasePermissionMixin, TemplateView):

    def get(self, request, **kwargs):
        return HttpResponse("Welcome to Heystox")
        

class UpstoxLogin(BasePermissionMixin, View):
    http_method_names = ["get"]

    def get(self, request):
        user_profile = request.user.user_profile
        if user_profile and user_profile.for_trade and user_profile.subscribed_historical_api or user_profile.subscribed_live_api:
            login_url = user_profile.get_authentication_url()
            return redirect(login_url)
        else:
            return HttpResponse("Requested User UserProfile Not Created or Not Subscribed for Api's")


class UpstoxLogoutView(BasePermissionMixin, View):
    http_method_names = ["get"]

    def get(self, request):
        email = "sonupal129@gmail.com"
        upstox_user = get_upstox_user(email=email)
        if upstox_user:
            upstox_user.logout()
            cache_key = "_".join([str(get_local_time().date()), email, "local_upstox_user"])
            cache.delete(cache_key)
            return HttpResponse("User Logout successfully")
        return HttpResponse("User not found/logged in")



class UpstoxLoginComplete(BasePermissionMixin, View):
    http_method_names = ["get"]

    def get(self, request):
        upstox_response_code = request.GET.get("code", None)
        user_profile = request.user.user_profile
        session_cache_key = request.user.email + "_upstox_user_session"
        session = cache.get(session_cache_key)
        session.set_code(upstox_response_code)
        if request.user.is_superuser:
            try:
                access_token_data = session.retrieve_access_token()
                token = access_token_data["access_token"]
                user_profile.credential.access_token = token
                user_profile.credential.save()
                login_upstox_user.delay(request.user.email)
            except Exception as e:
                slack_message_sender.delay(text=str(e), channel="#random")
                return redirect("market_analysis_urls:upstox-login")
            return HttpResponse("Successfully logged in Upstox now you can query Upstox api")
        return redirect("market_analysis_urls:sorted-dashboard-report")


class SortedStocksDashBoardReportView(BasePermissionMixin, GroupRequiredMixins, ListView):
    template_name = "sorted_stocks_dashboard_report.html"
    context_object_name = "symbols"
    group_required = ["trader"]
    movement = {
        "BUY" : "HIGH",
        "SELL" : "LOW"
    }


    def get_queryset(self): 
        requested_date = self.request.GET.get("created_at", None)
        if requested_date:
            date_obj = get_local_time().strptime(requested_date, "%Y-%m-%d").date()
        else:
            date_obj = get_local_time().date()
        qs = SortedStockDashboardReport.objects.filter(created_at__date=date_obj)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_superuser:
            upstox_user = self.request.user.user_profile.get_upstox_user()
            context["upstox_user"] = upstox_user
        if self.context_object_name is not None:
            context[self.context_object_name] = self.get_queryset()
        return context


class UserLoginRegisterView(LoginView):
    http_method_names = ["post", "get"]
    template_name = "login.html"
    form_class = UserLoginRegisterForm
    success_url = "/report/"

    def get_success_url(self):
        if self.success_url:
            return resolve_url(self.success_url)
        raise ImproperlyConfigured("Success Url not defined")

    def post(self, request, *args, **kwargs):
        if request.method == "POST" and "email" in request.POST:
            form = self.get_form()
            if form.is_valid():
                email = form.cleaned_data["email"]
                try:
                    user = User.objects.get(email=email)
                except:
                    return HttpResponse("No User Found, Please contact Administrator")
                return self.form_valid(form)
            else:
                return self.form_invalid(form)
        elif request.method == "POST" and "register-email" in request.POST:
            return redirect("market_analysis_urls:login-register")
        return super(UserLoginRegisterView, self).post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.get_success_url())
        return super(UserLoginRegisterView, self).get(request, *args, **kwargs)


class BacktestSortedStocksView(BasePermissionMixin, SuperUserRequiredMixins, View):
    template_name = "sorted_stocks_backtest.html"
    group_required = ["trader"]
    http_method_names = ["get", "post"]
    success_url = "/backtest-stocks/"

    def get_context_data(self, request, **kwargs):
        if "backtest_form" not in kwargs:
            kwargs["backtest_form"] = BacktestForm
        if "strategy_deploy_form" not in kwargs and request.user.is_superuser:
            kwargs["strategy_deploy_form"] = StrategyDeployForm
        return kwargs

    def get(self, request, **kwargs):
        context = {}
        # if request.method == "GET":
        # #     if ""
        #     print(request.GET)
        return render(request, self.template_name, self.get_context_data(request))

    def get_cache_key(self, *args):
        cache_key = "_".join([*args])
        return cache_key
    
    def get_backtested_cached_value(self, symbol, cache_key, **kwargs):
        force_backtesting = kwargs.get("force")
        if force_backtesting:
            return None
        cached_value = symbol.get_backtested_data(cache_key)
        if not cached_value.empty:
            return cached_value

        all_redis_cache_keys = redis_cache.keys("*")
        split_cache = cache_key.split("_")
        matched_keys = [key for key in all_redis_cache_keys if key.endswith("_".join(split_cache[2:]))]
        backtest_start_date = datetime.strptime(split_cache[0], "%Y-%m-%d").date()
        backtest_end_date = datetime.strptime(split_cache[1], "%Y-%m-%d").date()
        
        new_cache_key = None
        for key in matched_keys:
            split_key = key.split("_")
            key_start_date = datetime.strptime(split_key[0], "%Y-%m-%d").date()
            key_end_date = datetime.strptime(split_key[1], "%Y-%m-%d").date()
            if key_end_date == backtest_end_date and key_start_date <= backtest_start_date:
                new_cache_key = key
                break

        if new_cache_key:
            cached_value = symbol.get_backtested_data(new_cache_key)
            if cached_value is not None:
                if cached_value.empty:
                    return cached_value
                return cached_value.loc[cached_value["entry_time"] >= pd.to_datetime(backtest_start_date)]
        return None

    def get_cached_value(self, cache_key):
        cached_value = redis_cache.get(cache_key)
        if cached_value != None:
            return cached_value
        return None


    def post(self, request, *args, **kwargs):
        context = {}
        print(args)
        print(kwargs)
        
        if "backtest_form" in request.POST:
            backtest_form = BacktestForm(request.POST)
            if backtest_form.is_valid():
                symbol = backtest_form.cleaned_data["symbol"]
                strategy = backtest_form.cleaned_data["strategy"]
                entry_type = backtest_form.cleaned_data["entry_type"]
                from_date = backtest_form.cleaned_data["from_date"]
                candle_type = backtest_form.cleaned_data["candle_type"]
                current_date = get_local_time().date()
                to_days = (current_date - from_date).days
                
                cache_key = self.get_cache_key(str(current_date - timedelta(to_days)), str(current_date), symbol.symbol, str(strategy.strategy_name), str(candle_type), entry_type, "backteststrategy")
                cached_value = self.get_backtested_cached_value(symbol, cache_key, **kwargs)
                
                data = {
                    "stock_id": symbol.id,
                    "end_date": str(current_date),
                    "to_days": to_days,
                    "strategy_id": strategy.id,
                    "entry_type": entry_type,
                    "candle_type": backtest_form.cleaned_data["candle_type"],
                    "cache_key" : cache_key
                }
                if cached_value is None:
                    is_function_called_before = redis_cache.get(cache_key + "_requested") # This will check if function called 5 minute before is yest, it will as to wait
                    if is_function_called_before:
                        context["response"] = "Backtesting request for strategy already sent before, please try after 5 minute to check status"
                        return render(request, self.template_name, self.get_context_data(request, **context))
                    SendBackTestingRequest().delay(**data)
                    redis_cache.set(cache_key + "_requested", True, 60*20)
                    context["response"] = "Backtesting request sent, Please try after 5 minute to check backtest result"
                    return render(request, self.template_name, self.get_context_data(request, **context))
                
                if not cached_value.empty:
                    strt, strt_count = np.unique(cached_value.strategy_status, return_counts=True)
                    df_extrct = dict(zip(strt, strt_count))
                    df_extrct["Profit or Loss"] = round(cached_value["pl"].sum(), 2)
                    df_extrct["Entry Type"] = entry_type
                    df_extrct["Candle Type"] = candles_types.get(candle_type)
                    df_extrct["Average Entry Price"] = round(cached_value.entry_price.mean(), 2)
                    df_extrct["Average Exit Price"] = round(cached_value.exit_price.mean(), 2)
                    context["vars"] = df_extrct
                context["df"] = cached_value.to_html() if not cached_value.empty else "No Entry Point Found for Strategy"
                return render(request, self.template_name, self.get_context_data(request, **context))
            else:
                context["backtest_form"] = backtest_form
                return render(request, self.template_name, self.get_context_data(request, **context))

        elif "strategy_deploy_form" in request.POST:
            strategy_form = StrategyDeployForm(request.POST)
            if strategy_form.is_valid():
                strategy_form.save()
                context["deploy_status"] = "Strategy Deployed Successfully"
                return render(request, self.template_name, self.get_context_data(request, **context))
            
            context["strategy_deploy_form"] = strategy_form
            return render(request, self.template_name, self.get_context_data(request, **context))

        return render(request, self.template_name, self.get_context_data(request))



