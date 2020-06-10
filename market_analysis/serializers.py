from market_analysis.imports import *
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
        fields = ["timestamp", "strategy__strategy_name", "diff"]

class SortedStockDashboardSerializer(serializers.Serializer):
    stock_name = serializers.CharField(source="symbol.symbol")
    date = serializers.DateTimeField(source="created_at")
    entry_type = serializers.CharField()
    movement = serializers.FloatField(source="symbol.get_stock_movement")
    timestamps = serializers.SerializerMethodField("get_timestamps")
    current_price = serializers.FloatField(source="symbol.get_day_closing_price")

    def get_timestamps(self, obj):
        context = {
            "macd": obj.get_strategy_timestamp("MACD").timestamp if obj.get_strategy_timestamp("MACD") else None,
            "ohl": obj.get_strategy_timestamp("OHL").timestamp if obj.get_strategy_timestamp("OHL") else None,
            "pdhl": obj.get_strategy_timestamp("PDHL").timestamp if obj.get_strategy_timestamp("PDHL") else None,
            "stochastic": obj.get_strategy_timestamp("STOCHASTIC").timestamp if obj.get_strategy_timestamp("STOCHASTIC") else None,
        }
        return context

