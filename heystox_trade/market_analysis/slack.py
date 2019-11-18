import slack

# CODE STARTS BELOW

def send_slack_message(channel='#heystox', text='Message', attachments=None):
    client = slack.WebClient(token=settings.SLACK_TOKEN)
    response = client.chat_postMessage(
        channel=channel,
        text=text,
        attachments=attachments
    )
    return response.get('ok', False)