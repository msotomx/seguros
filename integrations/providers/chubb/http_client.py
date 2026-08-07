from __future__ import annotations

from typing import Any, Mapping

import requests

from integrations.providers.chubb.contracts import (
    ChubbAccessToken,
    ChubbHttpResponse,
)
from integrations.providers.exceptions import (
    ProviderHttpConnectionError,
    ProviderHttpResponseError,
    ProviderHttpTimeoutError,
    ProviderInvalidResponseError,
)


class ChubbHttpClient:
    """
    Cliente HTTP común para los servicios de Chubb.

    Responsabilidades:
    - Agregar autenticación Bearer.
    - Agregar ApiVersion.
    - Ejecutar GET y POST.
    - Aplicar timeout.
    - Normalizar errores HTTP y respuestas JSON.

    No obtiene tokens.
    No construye payloads de cotización.
    No conoce modelos Django.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_version: str,
        timeout: int | float,
        session: requests.Session | None = None,
    ):
        self.base_url = self._normalize_base_url(base_url)
        self.api_version = self._require_text(
            api_version,
            field_name="api_version",
        )
        self.timeout = self._validate_timeout(timeout)
        self.session = session or requests.Session()

    def get(
        self,
        path: str,
        *,
        token: ChubbAccessToken,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ChubbHttpResponse:
        return self.request(
            method="GET",
            path=path,
            token=token,
            params=params,
            headers=headers,
        )

    def post(
        self,
        path: str,
        *,
        token: ChubbAccessToken,
        payload: Any | None = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ChubbHttpResponse:
        return self.request(
            method="POST",
            path=path,
            token=token,
            payload=payload,
            params=params,
            headers=headers,
        )

    def request(
        self,
        *,
        method: str,
        path: str,
        token: ChubbAccessToken,
        payload: Any | None = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ChubbHttpResponse:
        normalized_method = self._normalize_method(method)
        url = self._build_url(path)

        request_headers = self._build_headers(
            token=token,
            custom_headers=headers,
        )

        request_kwargs: dict[str, Any] = {
            "method": normalized_method,
            "url": url,
            "headers": request_headers,
            "params": dict(params or {}),
            "timeout": self.timeout,
            "allow_redirects": False,
        }

        if payload is not None:
            request_kwargs["json"] = payload

        try:
            response = self.session.request(
                **request_kwargs,
            )
        except requests.Timeout as exc:
            raise ProviderHttpTimeoutError(
                f"Chubb excedió el timeout de {self.timeout} "
                f"segundos para {normalized_method} {path}."
            ) from exc
        except requests.ConnectionError as exc:
            raise ProviderHttpConnectionError(
                f"No fue posible establecer conexión con Chubb "
                f"para {normalized_method} {path}."
            ) from exc
        except requests.RequestException as exc:
            raise ProviderHttpConnectionError(
                f"Error de comunicación con Chubb "
                f"durante {normalized_method} {path}."
            ) from exc

        if not response.ok:
            raise ProviderHttpResponseError(
                self._build_http_error_message(
                    method=normalized_method,
                    path=path,
                    response=response,
                )
            )

        data = self._parse_response(response)

        return ChubbHttpResponse(
            status_code=response.status_code,
            data=data,
            headers=dict(response.headers),
        )

    def _build_headers(
        self,
        *,
        token: ChubbAccessToken,
        custom_headers: Mapping[str, str] | None,
    ) -> dict[str, str]:
        if not isinstance(token, ChubbAccessToken):
            raise TypeError(
                "token debe ser una instancia de ChubbAccessToken."
            )

        headers = {
            "Accept": "application/json",
            "Authorization": token.authorization_header,
            "apiVersion": self.api_version,
        }

        if custom_headers:
            headers.update(
                {
                    str(key): str(value)
                    for key, value in custom_headers.items()
                }
            )

        return headers

    @staticmethod
    def _parse_response(response) -> Any:
        if response.status_code == 204:
            return None

        content = getattr(response, "content", b"")

        if not content:
            return None

        try:
            return response.json()
        except ValueError as exc:
            raise ProviderInvalidResponseError(
                "Chubb devolvió una respuesta exitosa, "
                "pero el contenido no es JSON válido."
            ) from exc

    @staticmethod
    def _build_http_error_message(
        *,
        method: str,
        path: str,
        response,
    ) -> str:
        detail = ""

        try:
            payload = response.json()

            if isinstance(payload, dict):
                detail = (
                    payload.get("message")
                    or payload.get("error_description")
                    or payload.get("error")
                    or ""
                )

                if not detail and payload.get("messages"):
                    detail = str(payload["messages"])
            else:
                detail = str(payload)

        except ValueError:
            detail = str(
                getattr(response, "text", "")
            ).strip()

        base_message = (
            f"Chubb devolvió HTTP {response.status_code} "
            f"para {method} {path}."
        )

        if detail:
            return f"{base_message} Detalle: {detail}"

        return base_message

    def _build_url(self, path: str) -> str:
        normalized_path = self._require_text(
            path,
            field_name="path",
        )

        return (
            f"{self.base_url}/"
            f"{normalized_path.lstrip('/')}"
        )

    @staticmethod
    def _normalize_base_url(value: str) -> str:
        normalized = ChubbHttpClient._require_text(
            value,
            field_name="base_url",
        )

        return normalized.rstrip("/")

    @staticmethod
    def _normalize_method(value: str) -> str:
        normalized = ChubbHttpClient._require_text(
            value,
            field_name="method",
        ).upper()

        allowed_methods = {
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        }

        if normalized not in allowed_methods:
            raise ValueError(
                f"Método HTTP no soportado: {normalized}."
            )

        return normalized

    @staticmethod
    def _validate_timeout(
        value: int | float,
    ) -> int | float:
        if isinstance(value, bool):
            raise ValueError(
                "timeout debe ser un número mayor que cero."
            )

        try:
            normalized = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "timeout debe ser un número mayor que cero."
            ) from exc

        if normalized <= 0:
            raise ValueError(
                "timeout debe ser un número mayor que cero."
            )

        return value

    @staticmethod
    def _require_text(
        value: Any,
        *,
        field_name: str,
    ) -> str:
        if value is None:
            raise ValueError(
                f"{field_name} no puede estar vacío."
            )

        normalized = str(value).strip()

        if not normalized:
            raise ValueError(
                f"{field_name} no puede estar vacío."
            )

        return normalized
    