from __future__ import annotations

from typing import Any

import requests

from integrations.configuration.services import (
    ProviderConfigurationService,
)
from integrations.providers.chubb.contracts import (
    ChubbAccessToken,
)
from integrations.providers.exceptions import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
)


class ChubbAuthClient:
    """
    Cliente responsable exclusivamente de obtener tokens Chubb.

    No construye cotizaciones.
    No consulta catálogos.
    No guarda tokens en base de datos.
    """

    def __init__(
        self,
        *,
        provider: str = "CHUBB",
        ambiente: str,
        ramo: str,
        configuration_service: Any = ProviderConfigurationService,
        session: requests.Session | None = None,
    ):
        self.provider = provider
        self.ambiente = ambiente
        self.ramo = ramo
        self.configuration_service = configuration_service
        self.session = session or requests.Session()

    def get_token(self) -> ChubbAccessToken:
        configuration = self.configuration_service.get_active(
            provider=self.provider,
            ambiente=self.ambiente,
            ramo=self.ramo,
        )

        self._validate_configuration(configuration)

        identity = str(
            configuration.settings.get("IDENTITY", "")
        ).strip()

        if not identity:
            raise ProviderAuthenticationError(
                "Chubb no tiene configurado el parámetro obligatorio "
                "'IDENTITY'."
            )

        headers = {
            "Content-Type": "application/json",
            "App_ID": str(configuration.client_id).strip(),
            "App_Key": str(configuration.client_secret).strip(),
            "Resource": str(configuration.resource_id).strip(),
            "apiVersion": str(configuration.api_version).strip(),
        }

        try:
            response = self.session.post(
                configuration.token_url,
                params={
                    "Identity": identity,
                },
                headers=headers,
                json={},
                timeout=configuration.timeout,
            )
        except requests.Timeout as exc:
            raise ProviderAuthenticationError(
                "Chubb no respondió dentro del tiempo configurado."
            ) from exc
        except requests.RequestException as exc:
            raise ProviderAuthenticationError(
                "No fue posible conectar con el servicio "
                "de autenticación de Chubb."
            ) from exc

        if not response.ok:
            detail = self._extract_error_detail(response)

            message = (
                "Chubb rechazó la solicitud de autenticación. "
                f"HTTP {response.status_code}."
            )

            if detail:
                message += f" Detalle: {detail}"

            raise ProviderAuthenticationError(message)

        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderAuthenticationError(
                "Chubb devolvió una respuesta de autenticación "
                "que no contiene JSON válido."
            ) from exc

        return self._parse_token(payload)

    @staticmethod
    def _validate_configuration(configuration) -> None:
        required_fields = {
            "token_url": configuration.token_url,
            "client_id": configuration.client_id,
            "client_secret": configuration.client_secret,
            "resource_id": configuration.resource_id,
            "api_version": configuration.api_version,
        }

        missing = [
            field_name
            for field_name, value in required_fields.items()
            if value is None or str(value).strip() == ""
        ]

        if missing:
            raise ProviderConfigurationError(
                "La configuración de Chubb está incompleta. "
                f"Faltan: {', '.join(missing)}."
            )

        if not configuration.timeout:
            raise ProviderConfigurationError(
                "La configuración de Chubb no tiene un timeout válido."
            )

    @classmethod
    def _parse_token(
        cls,
        payload: dict,
    ) -> ChubbAccessToken:
        access_token = str(
            payload.get("access_token", "")
        ).strip()

        token_type = str(
            payload.get("token_type", "")
        ).strip()

        if not access_token:
            raise ProviderAuthenticationError(
                "La respuesta de Chubb no contiene access_token."
            )

        if not token_type:
            raise ProviderAuthenticationError(
                "La respuesta de Chubb no contiene token_type."
            )

        return ChubbAccessToken(
            access_token=access_token,
            token_type=token_type,
            expires_in=cls._to_required_int(
                payload.get("expires_in"),
                field_name="expires_in",
            ),
            ext_expires_in=cls._to_optional_int(
                payload.get("ext_expires_in")
            ),
            expires_on=cls._to_optional_int(
                payload.get("expires_on")
            ),
            not_before=cls._to_optional_int(
                payload.get("not_before")
            ),
            resource=str(
                payload.get("resource", "")
            ).strip(),
        )

    @staticmethod
    def _to_required_int(
        value,
        *,
        field_name: str,
    ) -> int:
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ProviderAuthenticationError(
                f"La respuesta de Chubb contiene "
                f"'{field_name}' inválido."
            ) from exc

    @staticmethod
    def _to_optional_int(value) -> int | None:
        if value in (None, ""):
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None
        
    @staticmethod
    def _extract_error_detail(response) -> str:
        try:
            payload = response.json()

            if isinstance(payload, dict):
                detail = (
                    payload.get("message")
                    or payload.get("error_description")
                    or payload.get("error")
                    or payload.get("Message")
                )

                if detail:
                    return str(detail)

                return str(payload)

            return str(payload)

        except ValueError:
            return str(
                getattr(response, "text", "")
            ).strip()[:500]
                