from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, StrategyTimestamp, SortedStocksList, Symbol


# Code Starts Below

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=False, read_only=True)
    class Meta:
        model = UserProfile
        fields = ["mobile", "for_trade", 'subscribed_historical_api', "subscribed_live_api", "user"]

class StrategyTimestampSerializer(serializers.ModelSerializer):
    class Meta:
        model = StrategyTimestamp
        fields = ["timestamp", "indicator__name", "diff"]

class SortedStockDashboardSerializer(serializers.Serializer):
    stock_name = serializers.CharField(source="symbol.symbol")
    date = serializers.DateTimeField(source="created_at")
    entry_type = serializers.CharField()
    movement = serializers.FloatField(source="symbol.get_stock_movement")
    timestamps = serializers.SerializerMethodField("get_timestamps")
    current_price = serializers.FloatField(source="symbol.get_day_closing_price")

    def get_timestamps(self, obj):
        context = {
            "macd": obj.get_indicator_timestamp("MACD").timestamp if obj.get_indicator_timestamp("MACD") else None,
            "ohl": obj.get_indicator_timestamp("OHL").timestamp if obj.get_indicator_timestamp("OHL") else None,
            "pdhl": obj.get_indicator_timestamp("PDHL").timestamp if obj.get_indicator_timestamp("PDHL") else None,
            "stochastic": obj.get_indicator_timestamp("STOCHASTIC").timestamp if obj.get_indicator_timestamp("STOCHASTIC") else None,
        }
        return context

