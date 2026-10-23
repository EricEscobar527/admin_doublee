from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

_jwt_auth = JWTAuthentication()


def user_from_jwt_cookies(cookies):
    """Resuelve el usuario a partir de las cookies JWT del panel.

    Regresa (user, new_access): new_access viene cuando el access expiró y se
    emitió uno nuevo con el refresh. user es None si no hay sesión válida.
    """
    raw_access = cookies.get(settings.JWT_ACCESS_COOKIE)
    if raw_access:
        try:
            return _jwt_auth.get_user(_jwt_auth.get_validated_token(raw_access.encode())), None
        except (TokenError, AuthenticationFailed):
            pass

    raw_refresh = cookies.get(settings.JWT_REFRESH_COOKIE)
    if not raw_refresh:
        return None, None
    try:
        refresh = RefreshToken(raw_refresh)
    except TokenError:
        return None, None
    user_id = refresh.get(settings.SIMPLE_JWT.get("USER_ID_CLAIM", "user_id"))
    user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        return None, None
    return user, refresh.access_token
