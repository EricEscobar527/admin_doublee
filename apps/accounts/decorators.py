from functools import wraps

from django.contrib.auth.views import redirect_to_login


def admin_required(view_func):
    """Solo usuarios activos con perfil admin; el resto va al login."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = request.user
        if not (user.is_authenticated and user.is_admin):
            return redirect_to_login(request.get_full_path())
        return view_func(request, *args, **kwargs)

    return wrapper
