from market_analysis.models import (Candle, SortedStockDashboardReport)
from market_analysis.imports import *
from market_analysis.tasks.notification_tasks import slack_message_sender
# Code Starts Below

@celery_app.task(queue="low_priority")    
def delete_stocks_candles():
    """Delete All candles older more than 30-90 days, currently 32 days"""
    return Candle.objects.filter(date__lte=get_local_time().date() - timedelta(32)).delete()

@celery_app.task(queue="low_priority")
def clear_all_cache():
    """Clear Default Cache"""
    cache.clear()
    redis_cache.clear()

@celery_app.task(queue="low_priority")
def create_stocks_report():
    reports = SortedStockDashboardReport.objects.all().values()
    df = pd.DataFrame(list(reports))
    filepath = "".join(['media/exports/stocks_report_' + str(get_local_time().date()) + ".csv"])
    df.to_csv(filepath, encoding="utf-8")
    slack_message_sender(text=settings.SITE_URL + filepath)
    return "Report Exported Successfully"


# @celery_app.task(queue="low_priority")
# def add_together():
#     print(get_focal_time)
#     print(get_local_time())
#     print(datetime.now())
#     return 5+6



