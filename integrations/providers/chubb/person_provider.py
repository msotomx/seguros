from __future__ import annotations

from integrations.catalog.services import CatalogService
from integrations.persons.contracts import (
    PersonRequest,
    PersonResult,
)
from integrations.providers.chubb.internal_person_mapper import (
    ChubbInternalPersonRequestMapper,
)
from integrations.providers.chubb.person_client import (
    ChubbPersonClient,
)
from integrations.providers.exceptions import (
    ProviderInvalidResponseError,
)
from integrations.catalog.exceptions import (
    ProviderCatalogMappingNotFoundError,
)
from integrations.providers.chubb.suburb_sync_service import (
    ChubbSuburbSyncService,
)


class ChubbPersonProvider:
    """
    Adaptador entre PersonService y Create Person de Chubb.

    Responsabilidades:
    - resolver códigos canónicos requeridos por Chubb;
    - transformar PersonRequest al contrato Chubb;
    - ejecutar Create Person;
    - normalizar el resultado al contrato interno PersonResult.

    No obtiene ProviderConfiguration.
    No construye clientes.
    No contiene IDs operativos hardcodeados.
    """

    provider_code = "CHUBB"
    suburb_catalog_code = "SUBURB"

    def __init__(
        self,
        *,
        provider_id: int,
        client: ChubbPersonClient,
        request_mapper: ChubbInternalPersonRequestMapper,
        catalog_service=CatalogService,
        catalog_client=None,
        suburb_sync_service=ChubbSuburbSyncService,
    ) -> None:
        self._provider_id = provider_id
        self._client = client
        self._request_mapper = request_mapper
        self._catalog_service = catalog_service
        self._catalog_client = catalog_client
        self._suburb_sync_service = suburb_sync_service

    def create_person(
        self,
        request: PersonRequest,
    ) -> PersonResult:
        try:
            provider_suburb = self._catalog_service.to_provider(
                provider_id=self._provider_id,
                catalog_code=self.suburb_catalog_code,
                internal_code=(
                    request.address.neighborhood_code
                ),
            )
        except ProviderCatalogMappingNotFoundError:
            if self._catalog_client is None:
                raise

            self._suburb_sync_service.sync(
                provider_id=self._provider_id,
                zip_code=request.address.postal_code,
                catalog_client=self._catalog_client,
            )

            provider_suburb = self._catalog_service.to_provider(
                provider_id=self._provider_id,
                catalog_code=self.suburb_catalog_code,
                internal_code=(
                    request.address.neighborhood_code
                ),
            )

        neighborhood_id = self._neighborhood_id(
            provider_suburb.external_code
        )

        chubb_request = self._request_mapper.create_person(
            request=request,
            neighborhood_id=neighborhood_id,
        )

        chubb_result = self._client.create_person(
            chubb_request
        )

        return PersonResult(
            provider_code=self.provider_code,
            provider_tran_id=str(
                chubb_result.tran_id
            ),
            provider_person_id=str(
                chubb_result.person_id
            ),
            provider_address_id=str(
                chubb_result.address_id
            ),
            raw_response=dict(
                chubb_result.raw_response
            ),
        )

    @staticmethod
    def _neighborhood_id(
        value,
    ) -> int:
        if isinstance(value, bool):
            raise ProviderInvalidResponseError(
                "El código externo SUBURB debe ser "
                "un identificador entero."
            )

        try:
            normalized = int(value)
        except (TypeError, ValueError) as exc:
            raise ProviderInvalidResponseError(
                "El código externo SUBURB debe ser "
                "un identificador entero."
            ) from exc

        if normalized <= 0:
            raise ProviderInvalidResponseError(
                "El código externo SUBURB debe ser "
                "mayor que cero."
            )

        return normalized
