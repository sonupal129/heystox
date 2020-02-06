from market_analysis.slack import send_slack_message
from celery import shared_task

# Code Starts Below

@shared_task(queue="default")
def slack_message_sender(channel='#heystox', text='Message', attachments=None):
    return send_slack_message(channel, text, attachments)

# def chuma(a,b):
#     return a + b

# @shared_task(queue="default")
# def add():
#     return 5+6