from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Group, Permission
from django.http import HttpResponseForbidden


# CODE BELOW

class GroupRequiredMixins(object):
    group_required = None  # Group Name Only

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied
        else:
            group_required = set(self.group_required)
            user_group = request.user.groups.values_list("name", flat=True)
            group_found = [group for group in group_required if group in user_group]
            if set(group_required) == set(group_found) or request.user.is_superuser:
                return super(GroupRequiredMixins, self).dispatch(request, *args, **kwargs)
        return HttpResponseForbidden("Not Allowed to View Stocks Data Please Contact Administrator")


