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

@celery_app.task(queue="low_priority")
def create_stocks_report(): # Need to work more on this function currently giving file not found error
    reports = SortedStockDashboardReport.objects.filter(created_at__date=get_local_time().date()).values()
    data = pd.DataFrame(list(reports))
    filepath = settings.MEDIA_URL + 'exports/stocks_report_' + str(get_local_time().date()) + ".csv"
    data.to_csv(filepath, encoding="utf-8")
    return slack_message_sender(text=filepath)


# @celery_app.task(queue="low_priority")
# def add_together():
#     print(get_focal_time)
#     print(get_local_time())
#     print(datetime.now())
#     return 5+6



