from celery import shared_task
import slack
from heystox_trade import settings
# Code Starts Below

@shared_task(queue="default")
def slack_message_sender(channel='#heystox', text='Message', attachments=None):
    """Send Slack notification to user"""
    if not settings.DEBUG:
        client = slack.WebClient(token=settings.SLACK_TOKEN)
        response = client.chat_postMessage(
            channel=channel,
            text=text,
            attachments=attachments
        )
        return response.get('ok', False)
    pass

# def chuma(a,b):
#     return a + b 

# @shared_task(queue="default")
# def add():
#     return 5+6