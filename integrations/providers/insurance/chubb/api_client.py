import requests
from django.conf import settings

from .auth import get_chubb_access_token
from .exceptions import ChubbApiError


class ChubbApiClient:
    def __init__(self):
        self.base_url = settings.CHUBB_QUOTES_BASE_URL.rstrip("/")
        self.timeout = settings.CHUBB_TIMEOUT

    def _headers(self):
        return {
            "Authorization": f"Bearer {get_chubb_access_token()}",
            "apiVersion": str(settings.CHUBB_API_VERSION),
            "Accept": "application/json",
            "Content-Type": "application/json",
            "CB-SourceApplication": "23",
        }

    def get(self, path, params=None):
        url = f"{self.base_url}{path}"

        try:
            response = requests.get(
                url,
                headers=self._headers(),
                params=params or {},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ChubbApiError(f"Error conectando con Chubb: {exc}") from exc

        return self._handle_response(response)

    def post(self, path, payload=None):
        url = f"{self.base_url}{path}"

        try:
            response = requests.post(
                url,
                headers=self._headers(),
                json=payload or {},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ChubbApiError(f"Error conectando con Chubb: {exc}") from exc

        return self._handle_response(response)

    def post_quote(self, payload):
        return self.post("/quote", payload=payload)

    def _handle_response2(self, response):
        try:
            data = response.json()
        except ValueError:
            data = response.text

        if response.status_code >= 400:
            raise ChubbApiError(f"Chubb API error {response.status_code}: {data}")

        return data

    def _handle_response(self, response):
        try:
            data = response.json()
        except ValueError:
            data = response.text

        if response.status_code >= 400:
            raise ChubbApiError(
                f"Chubb API error {response.status_code}: "
                f"headers={dict(response.headers)} body={data!r}"
            )

        return data    