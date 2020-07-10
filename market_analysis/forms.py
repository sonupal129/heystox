from django import forms
from market_analysis.models import Symbol, User, SortedStocksList, Strategy, DeployedStrategies
from market_analysis.imports import *
from market_analysis.tasks.trading import get_liquid_stocks
# Code Starts

class UserLoginRegisterForm(forms.Form):
    email = forms.EmailField(required=False, widget=forms.TextInput(attrs={"placeholder":"Your Email *"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Your Password *"}), required=True, initial="Your Password *")

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_user(self):
        email = self.data["email"]
        password = self.data["password"]
        user = authenticate(username=email, password=password)
        if user is not None:
            return user
        

class BacktestForm(forms.Form):
    entry_choices = {
        ("BUY", "BUY"),
        ("SELL", "SELL")
    }

    candle_choices = {(k,v) for k,v in candles_types.items() if k not in ["1D", "1H", "M60"]}

    symbol = forms.ModelChoiceField(queryset=get_liquid_stocks(max_price=300), to_field_name="id", label="Select Stock")
    strategy = forms.ModelChoiceField(queryset=Strategy.objects.filter(strategy_type="ET"), to_field_name="id", label="Strategy")
    entry_type = forms.ChoiceField(choices=entry_choices)
    candle_type = forms.ChoiceField(choices=candle_choices)
    from_date = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'date'}))
    

    def clean_from_date(self):
        today_date = get_local_time().date()
        from_date = self.cleaned_data["from_date"]
        if from_date < today_date - timedelta(90):
            raise forms.ValidationError("Maximum Testing is allowed for 90 days only, Please select a lower date")
        elif from_date > today_date:
            raise forms.ValidationError(f"From date should be lower than {today_date}, Please select a lower date")
        return from_date

    def create_form_cache_key(self):
        symbol = self.cleaned_data["symbol"].symbol
        strategy = self.cleaned_data["strategy"].strategy_name
        entry_type = self.cleaned_data["entry_type"]
        from_date = str(self.cleaned_data["from_date"])
        cache_key = "_".join([symbol, strategy, entry_type, from_date])
        return cache_key
    

class StrategyDeployForm(forms.ModelForm):
    symbol = forms.ModelChoiceField(queryset=get_liquid_stocks(max_price=300), label="Select Stock")
    
    class Meta:
        model = DeployedStrategies
        fields = ["symbol", "strategy", "timeframe", "entry_type"]