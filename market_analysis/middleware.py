from market_analysis.imports import *
from .tasks.notification_tasks import slack_message_sender

#  CODE 

class UserAuthRequired(object):

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated and request.path not in settings.LOGIN_REDIRECT_EXEMPTED_URLS:
            return HttpResponseRedirect(settings.LOGIN_URL)
        response = self.get_response(request)
        return response

