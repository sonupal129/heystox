from django.apps import AppConfig


class MarketAnalysisConfig(AppConfig):
    name = 'market_analysis'
    verbose_name = "Market Analysis"

    def ready(self):
        import market_analysis.signals
