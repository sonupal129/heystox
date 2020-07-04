from market_analysis.models import (Candle, SortedStockDashboardReport)
from market_analysis.imports import *
from market_analysis.tasks.notification_tasks import slack_message_sender
# Code Starts Below

@celery_app.task(queue="low_priority")    
def delete_stocks_candles():
    """Delete All candles older more than 30-120 days, currently 120 days"""
    return Candle.objects.filter(date__lte=get_local_time().date() - timedelta(120)).delete()

@celery_app.task(queue="low_priority")
def clear_all_cache():
    """Clear Default Cache"""
    cache.clear()
    redis_cache.clear()
    r = redis.Redis()
    r.flushall()

@celery_app.task(queue="low_priority")
def create_stocks_report():
    reports = SortedStockDashboardReport.objects.filter(entry_time__date=get_local_time().date()).values()
    df = pd.DataFrame(list(reports)).set_index("id")
    filepath = "".join(['media/exports/stocks_report_' + str(get_local_time().date()) + ".csv"])
    df.to_csv(filepath, encoding="utf-8")
    message = "".join(["Daily Trade Report: ", settings.SITE_URL, filepath])
    slack_message_sender(text=message)
    return "Report Exported Successfully"


# @celery_app.task(queue="low_priority")
# def add_together():
#     print(get_focal_time)
#     print(get_local_time())
#     print(datetime.now())
#     return 5+6



