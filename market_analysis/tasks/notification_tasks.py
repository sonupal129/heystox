from market_analysis.imports import *
import slack
# Code Starts Below

@celery_app.task(queue="low_priority")
def slack_message_sender(channel='#heystox', text='Message', attachments=None):
    """Send Slack notification to user"""
    client = slack.WebClient(token=settings.SLACK_TOKEN)
    response = client.chat_postMessage(
        channel=channel,
        text=text,
        attachments=attachments
    )
    return response.get('ok', False)

# def chuma(a,b):
#     return a + b 

# @shared_task(queue="default")
# def add():
#     return 5+6