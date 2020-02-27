from market_analysis.imports import *

# Codes

class BasePermissionMixin(LoginRequiredMixin):
    permission_denied_message = "You are not authenticated to view this page"