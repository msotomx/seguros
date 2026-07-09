import requests
from django.conf import settings
from django.core.cache import cache

from .exceptions import ChubbAuthorizationError


CACHE_KEY = "chubb_access_token"


def get_chubb_access_token() -> str:
    cached = cache.get(CACHE_KEY)
    if cached:
        return cached

    headers = {
        "Content-Type": "application/json",
        "App_ID": settings.CHUBB_CLIENT_ID,
        "App_Key": settings.CHUBB_CLIENT_SECRET,
        "Resource": settings.CHUBB_RESOURCE_ID,
        "apiVersion": str(settings.CHUBB_API_VERSION),
    }

    try:
        response = requests.post(
            settings.CHUBB_TOKEN_URL,
            headers=headers,
            json={},
            timeout=settings.CHUBB_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise ChubbAuthorizationError(f"Error conectando con Chubb Auth: {exc}") from exc

    if response.status_code >= 400:
        raise ChubbAuthorizationError(f"Error obteniendo token Chubb: {response.status_code} {response.text}")

    data = response.json()
    token = data.get("access_token")

    if not token:
        raise ChubbAuthorizationError(f"Chubb no regresó access_token: {data}")

    expires_in = int(data.get("expires_in", 3599))
    cache.set(CACHE_KEY, token, max(expires_in - 300, 60))

    return token