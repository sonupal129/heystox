from __future__ import absolute_import
import os
from celery import Celery
from django.conf import settings
from celery_slack import Slackify

# Code Below


# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'heystox_trade.settings')

app = Celery('heystox_trade')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks() # lambda: settings.INSTALLED_APPS

if settings.DEBUG:
    slack_app = Slackify(app, settings.SLACK_WEBHOOK)

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))