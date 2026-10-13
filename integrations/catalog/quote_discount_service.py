from __future__ import annotations

from integrations.models import (
    ProviderCatalogMapping,
)


class QuoteDiscountService:
    CATALOG_CODE = "DISCOUNT"

    @classmethod
    def list_internal_codes_for_provider(
        cls,
        *,
        provider_id: int,
    ) -> tuple[str, ...]:

        if not isinstance(provider_id, int) or provider_id <= 0:
            raise ValueError(
                "provider_id debe ser un entero mayor que cero."
            )

        mappings = (
            ProviderCatalogMapping.objects
            .filter(
                provider_id=provider_id,
                catalog__code=cls.CATALOG_CODE,
                catalog__is_active=True,
                catalog_item__is_active=True,
                is_active=True,
            )
            .order_by(
                "catalog_item__sort_order",
                "catalog_item__name",
            )
            .values_list(
                "catalog_item__code",
                flat=True,
            )
        )

        return tuple(mappings)
