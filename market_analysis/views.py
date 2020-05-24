from market_analysis.imports import *
from market_analysis.models import UserProfile, MasterContract, SortedStocksList, Symbol, StrategyTimestamp, SortedStockDashboardReport
from market_analysis.filters import SymbolFilters, SortedStocksFilter
from market_analysis.tasks.trading import get_cached_liquid_stocks
from market_analysis.view_mixins import BasePermissionMixin
from .forms import UserLoginRegisterForm, BacktestForm
from .mixins import GroupRequiredMixins
from market_analysis.tasks.notification_tasks import slack_message_sender
from market_analysis.tasks.users_tasks import login_upstox_user
from market_analysis.tasks.intraday_indicator import prepare_n_call_backtesting_strategy
# Create your views here.


class UpstoxLogin(BasePermissionMixin, View):
    http_method_names = ["get"]

    def get(self, request):
        user_profile = request.user.user_profile
        if user_profile and user_profile.for_trade and user_profile.subscribed_historical_api or user_profile.subscribed_live_api:
            login_url = user_profile.get_authentication_url()
            return redirect(login_url)
        else:
            return(HttpResponse("Requested User UserProfile Not Created or Not Subscribed for Api's"))


class UpstoxLoginComplete(BasePermissionMixin, View):
    http_method_names = ["get"]

    def get(self, request):
        upstox_response_code = request.GET.get("code", None)
        user_profile = request.user.user_profile
        session_cache_key = request.user.email + "_upstox_user_session"
        response_code_cache_key = request.user.email + "_upstox_user_response_code"
        session = cache.get(session_cache_key)
        cached_response_code = cache.get(response_code_cache_key)
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


# class UpstoxUserLogoutView(View):


class SortedStocksDashBoardView(BasePermissionMixin, GroupRequiredMixins, ListView):
    template_name = "sorted_stocks_dashboard.html"
    context_object_name = "symbols"
    group_required = ["trader"]

    def get_queryset(self):
        date = self.request.GET.get("created_at")
        if date:
            requested_date = get_local_time().strptime(date, "%Y-%m-%d").date()
            timestamps = StrategyTimestamp.objects.filter(timestamp__date=requested_date, indicator__name="MACD")
        else:
            timestamps = StrategyTimestamp.objects.filter(timestamp__date=get_local_time().date(), indicator__name="MACD")
        sorted_stock_id = []
        
        if self.request.GET.get("sara"):
            sorted_stocks = SortedStocksList.objects.filter(created_at__date=get_local_time().date())
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


class BacktestSortedStocksView(FormView):
    template_name = "sorted_stocks_backtest.html"
    group_required = ["trader"]
    http_method_names = ["get", "post"]
    form_class = BacktestForm
    success_url = "/backtest-stocks/"

    def get_context_data(self, **kwargs):
        context = super(BacktestSortedStocksView, self).get_context_data(**kwargs)
        form = self.get_form()
        # print(context)
        # print(self.request.GET)
        # print(self.request.POST)
        # print(form.is_valid())
        # print(form.errors)
        
        return context


    def post(self, request, *args, **kwargs):
        form = self.get_form()
        function_called_before = False
        context = super(BacktestSortedStocksView, self).get_context_data(*args, **kwargs)
        if form.is_valid():
            is_function_called_before = redis_cache.get(form.create_form_cache_key()) # This will check if function called 5 minute before is yest, it will as to wait
            if is_function_called_before:
                context["response"] = "Strategy request already sent before, please try after 5 minute to check status"
                return self.render_to_response(context)
            symbol = form.cleaned_data["symbol"]
            strategy = form.cleaned_data["strategy"]
            entry_type = form.cleaned_data["entry_type"]
            from_date = form.cleaned_data["from_date"]
            candle_type = "M5"
            current_date = get_local_time().date()
            to_days = (current_date - from_date).days
            
            data = {
                "stock_id": symbol.id,
                "end_date": str(current_date),
                "to_days": to_days,
                "strategy_id": strategy.id,
                "entry_type": entry_type,
                "form_cache_key": form.create_form_cache_key()
            }

            cache_key = "_".join([symbol.symbol, str(to_days), str(current_date), str(strategy.strategy_name), str(candle_type), "backtest_strategy"])
            cached_value = redis_cache.get(cache_key)

            func_module = importlib.import_module(strategy.strategy_location)
            st_func = getattr(func_module, strategy.strategy_name)
            print(st_func.delay(4,5))
            # if cached_value == None:
            #     prepare_n_call_backtesting_strategy.delay(**data)
            #     context["response"] = "Backtesting request sent, Please try after 5 minute to check backtest result"
            #     return self.render_to_response(context)
            # Write Profite Lostt Funcion
            # context["df"] = cached_value.to_html()
            return self.render_to_response(context)
        return super(BacktestSortedStocksView, self).get(request, *args, **kwargs)



