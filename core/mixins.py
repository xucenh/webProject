from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(role: str):
    """Require login *and* the given ``User.role``; otherwise 403."""

    def decorator(view):
        @wraps(view)
        def _wrapped(request, *args, **kwargs):
            if request.user.role != role:
                raise PermissionDenied("شما به این بخش دسترسی ندارید.")
            return view(request, *args, **kwargs)

        return login_required(_wrapped)

    return decorator
