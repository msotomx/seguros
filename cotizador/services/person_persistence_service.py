from __future__ import annotations

from cotizador.models import (
    Cotizacion,
    CotizacionProveedorPersona,
)
from integrations.persons.contracts import PersonResult


class PersonPersistenceService:
    """
    Persiste la identidad externa de una persona
    asociada a una cotización y proveedor.
    """

    @classmethod
    def save(
        cls,
        *,
        cotizacion: Cotizacion,
        person_result: PersonResult,
        rol: str,
    ) -> CotizacionProveedorPersona:

        if not isinstance(cotizacion, Cotizacion):
            raise TypeError(
                "cotizacion debe ser una instancia de Cotizacion."
            )

        if not isinstance(person_result, PersonResult):
            raise TypeError(
                "person_result debe ser una instancia de PersonResult."
            )

        if rol not in CotizacionProveedorPersona.Rol.values:
            raise ValueError(
                f"Rol de persona no válido: {rol}."
            )

        provider_code = (
            person_result.provider_code.strip().upper()
        )

        if not provider_code:
            raise ValueError(
                "person_result.provider_code es obligatorio."
            )

        persona, _ = (
            CotizacionProveedorPersona.objects.update_or_create(
                cotizacion=cotizacion,
                provider_code=provider_code,
                rol=rol,
                defaults={
                    "provider_tran_id": (
                        person_result.provider_tran_id
                    ),
                    "provider_person_id": (
                        person_result.provider_person_id
                    ),
                    "provider_address_id": (
                        person_result.provider_address_id
                    ),
                    "raw_response": dict(
                        person_result.raw_response
                    ),
                },
            )
        )

        return persona
