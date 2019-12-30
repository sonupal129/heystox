from django import forms
from market_analysis.models import Symbol

# Code Starts

class SymbolForm(forms.ModelForm):
    class Meta:
        model = Symbol
        fields = ["symbol", "exchange"]