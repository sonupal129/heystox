from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from heystox_trade import settings
from django.core.exceptions import ImproperlyConfigured
# Codes

class BasePermissionMixin(LoginRequiredMixin):
    permission_denied_message = "You are not authenticated to view this page"