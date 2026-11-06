from functools import wraps

from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapped_view
