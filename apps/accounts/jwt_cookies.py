from django.conf import settings


def _cookie_kwargs(max_age):
    return {
        "max_age": int(max_age.total_seconds()),
        "httponly": True,
        "secure": settings.JWT_COOKIE_SECURE,
        "samesite": "Lax",
    }


def set_access_cookie(response, access):
    response.set_cookie(
        settings.JWT_ACCESS_COOKIE, str(access), **_cookie_kwargs(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"])
    )


def set_auth_cookies(response, refresh):
    set_access_cookie(response, refresh.access_token)
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE, str(refresh), **_cookie_kwargs(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"])
    )


def clear_auth_cookies(response):
    response.delete_cookie(settings.JWT_ACCESS_COOKIE)
    response.delete_cookie(settings.JWT_REFRESH_COOKIE)
