from cotizador.models import (
    CotizacionItem,
    CotizacionProveedorPersona,
)
from integrations.issues.contracts import (
    InternalIssueRequest,
    IssuePartyReference,
    IssueRisk,
)


class IssueRequestService:
    """
    Construye el contrato interno de emisión a partir
    de la opción comercial seleccionada.

    No contiene conocimiento específico de Chubb.
    """

    @classmethod
    def build(
        cls,
        *,
        cotizacion_item: CotizacionItem,
    ) -> InternalIssueRequest:
        cls._validate_item(cotizacion_item)

        cotizacion = cotizacion_item.cotizacion
        vehiculo = cotizacion.vehiculo
        option = cotizacion_item.provider_option
        quote_attempt = option.cotizacion_proveedor
        risk = option.riesgo

        insured_person = cls._get_person(
            cotizacion=cotizacion,
            provider_code=quote_attempt.provider_code,
            role=CotizacionProveedorPersona.Rol.ASEGURADO,
        )

        insured = cls._party_reference(insured_person)

        payment_method_code = (
            cotizacion_item.forma_pago
            or cotizacion.forma_pago_preferida
        )

        return InternalIssueRequest(
            provider_quote_id=quote_attempt.provider_quote_id,
            provider_quote_version_id=(
                quote_attempt.provider_quote_version_id or None
            ),
            payment_method_code=payment_method_code,
            insured=insured,
            risks=(
                IssueRisk(
                    risk_number=risk.risk_number,
                    provider_package_id=option.provider_package_id,
                    vin=vehiculo.vin.strip(),
                    plate=(vehiculo.placas or "").strip() or None,
                    engine_number=None,
                    reference=cotizacion.folio,
                    owner=insured,
                    beneficiary=insured,
                ),
            ),
            invoice=None,
        )

    @staticmethod
    def _get_person(
        *,
        cotizacion,
        provider_code: str,
        role: str,
    ) -> CotizacionProveedorPersona:
        try:
            return CotizacionProveedorPersona.objects.get(
                cotizacion=cotizacion,
                provider_code=provider_code,
                rol=role,
            )
        except CotizacionProveedorPersona.DoesNotExist as exc:
            raise ValueError(
                "No existe la persona persistida para emisión: "
                f"provider={provider_code}, rol={role}."
            ) from exc

    @staticmethod
    def _party_reference(
        person: CotizacionProveedorPersona,
    ) -> IssuePartyReference:
        if not person.provider_tran_id:
            raise ValueError(
                "La persona de proveedor no tiene provider_tran_id."
            )

        if not person.provider_person_id:
            raise ValueError(
                "La persona de proveedor no tiene provider_person_id."
            )

        if not person.provider_address_id:
            raise ValueError(
                "La persona de proveedor no tiene provider_address_id."
            )

        return IssuePartyReference(
            provider_tran_id=person.provider_tran_id,
            provider_person_id=person.provider_person_id,
            provider_address_id=person.provider_address_id,
        )

    @staticmethod
    def _validate_item(cotizacion_item: CotizacionItem) -> None:
        if cotizacion_item is None:
            raise ValueError("cotizacion_item es obligatorio.")

        cotizacion = cotizacion_item.cotizacion

        if cotizacion.tipo_cotizacion != cotizacion.Tipo.INDIVIDUAL:
            raise ValueError(
                "Por ahora la emisión sólo soporta cotizaciones individuales."
            )

        if cotizacion.vehiculo is None:
            raise ValueError(
                "La cotización individual no tiene vehículo."
            )

        if cotizacion_item.provider_option_id is None:
            raise ValueError(
                "El CotizacionItem no tiene una opción de proveedor asociada."
            )

        option = cotizacion_item.provider_option

        if option.riesgo_id is None:
            raise ValueError(
                "La opción de proveedor no tiene riesgo asociado."
            )

        risk = option.riesgo

        if risk.risk_number is None:
            raise ValueError(
                "El riesgo de proveedor no tiene risk_number."
            )

        if risk.risk_number <= 0:
            raise ValueError(
                "risk_number debe ser mayor que cero."
            )

        if not option.provider_package_id:
            raise ValueError(
                "La opción no tiene provider_package_id."
            )

        quote_attempt = option.cotizacion_proveedor

        if not quote_attempt.success:
            raise ValueError(
                "No se puede emitir desde una cotización de proveedor fallida."
            )

        if not quote_attempt.provider_quote_id:
            raise ValueError(
                "No existe provider_quote_id para emitir."
            )

        if not quote_attempt.provider_code:
            raise ValueError(
                "No existe provider_code para emitir."
            )

        vin = (cotizacion.vehiculo.vin or "").strip()

        if not vin:
            raise ValueError(
                "El vehículo no tiene VIN."
            )

        if len(vin) != 17:
            raise ValueError(
                "El VIN debe tener exactamente 17 caracteres."
            )

        payment_method_code = (
            cotizacion_item.forma_pago
            or cotizacion.forma_pago_preferida
        )

        if not payment_method_code:
            raise ValueError(
                "No existe forma de pago para la emisión."
            )
