from market_analysis.slack import send_slack_message
from celery.task import periodic_task
from celery.schedules import crontab
from celery.decorators import task

# from heystox_intraday.intraday_fetchdata import update_symbol_data, update_all_symbol_candles
# Code Starts Below

@task(queue="default")
def slack_message_sender(channel='#heystox', text='Message', attachments=None):
    send_slack_message(channel, text, attachments)