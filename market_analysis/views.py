from market_analysis.imports import *
from market_analysis.models import UserProfile, MasterContract, SortedStocksList, Symbol, StrategyTimestamp, SortedStockDashboardReport
from market_analysis.filters import SymbolFilters, SortedStocksFilter
from market_analysis.tasks.trading import get_cached_liquid_stocks
from market_analysis.view_mixins import BasePermissionMixin
from .forms import UserLoginRegisterForm
from .mixins import GroupRequiredMixins
from market_analysis.tasks.notification_tasks import slack_message_sender
from market_analysis.tasks.users_tasks import login_upstox_user
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
                access_token = session.retrieve_access_token()
                user_profile.credential.access_token = access_token["access_token"]
                user_profile.credential.save()
                login_upstox_user.delay(request.user.email)
            except Exception as e:
                slack_message_sender.delay(text=str(e), channel="#random")
                return redirect("market_analysis_urls:upstox-login")
            return HttpResponse("Successfully logged in Upstox now you can query Upstox api")
        return redirect("market_analysis_urls:sorted-dashboard-report")

        #         try:
        #             upstox_user = Upstox(user_profile.credential.api_key, access_token)
        #             cache.set(request.user.email + "_upstox_login_user", upstox_user, 30*60*48)
                
        #         except Exception as e:
        #             slack_message_sender.delay(text=str(e))
        #             return redirect("market_analysis_urls:upstox-login")
        #     return redirect("market_analysis_urls:upstox-login")
        # return redirect("market_analysis_urls:sorted-dashboard-report")

# class UpstoxUserLogoutView(View):
        
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
            requested_date = get_local_time().strptime(date, "%Y-%m-%d").date()
            # filtered_qs = SortedStocksList.objects.filter(created_at__date=requested_date)
            timestamps = StrategyTimestamp.objects.filter(timestamp__date=requested_date, indicator__name="MACD")
        else:
            # filtered_qs = SortedStocksList.objects.filter(created_at__date=datetime.now().date())
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

            