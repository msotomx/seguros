from __future__ import annotations

from django.db import transaction

from cotizador.models import (
    CotizacionItem,
    CotizacionProveedor,
    CotizacionProveedorEmision,
)
from integrations.issues.contracts import IssueAttempt


class IssueAttemptPersistenceService:

    @classmethod
    @transaction.atomic
    def reserve(
        cls,
        *,
        cotizacion_item: CotizacionItem,
        cotizacion_proveedor: CotizacionProveedor,
        provider_configuration_id: int,
        provider_code: str,
    ) -> CotizacionProveedorEmision:

        if not isinstance(cotizacion_item, CotizacionItem):
            raise TypeError(
                "cotizacion_item debe ser CotizacionItem."
            )

        if not isinstance(
            cotizacion_proveedor,
            CotizacionProveedor,
        ):
            raise TypeError(
                "cotizacion_proveedor debe ser CotizacionProveedor."
            )

        # Bloqueamos una fila estable antes de comprobar
        # si existe una reserva anterior.
        CotizacionItem.objects.select_for_update().get(
            pk=cotizacion_item.pk,
        )

        existing_issue = (
            CotizacionProveedorEmision.objects
            .filter(
                cotizacion_item=cotizacion_item,
                estatus__in=[
                    CotizacionProveedorEmision.Estatus.EN_PROCESO,
                    CotizacionProveedorEmision.Estatus.INDETERMINADA,
                    CotizacionProveedorEmision.Estatus.EXITOSA,
                ],
            )
            .exists()
        )

        if existing_issue:
            raise ValueError(
                "Ya existe una emisión en proceso, "
                "indeterminada o exitosa para este CotizacionItem."
            )

        return CotizacionProveedorEmision.objects.create(
            cotizacion_item=cotizacion_item,
            cotizacion_proveedor=cotizacion_proveedor,
            provider_code=provider_code,
            provider_configuration_id=provider_configuration_id,
            estatus=CotizacionProveedorEmision.Estatus.EN_PROCESO,
        )

    @classmethod
    @transaction.atomic
    def finalize(
        cls,
        *,
        reservation: CotizacionProveedorEmision,
        attempt: IssueAttempt,
    ) -> CotizacionProveedorEmision:

        if not isinstance(
            reservation,
            CotizacionProveedorEmision,
        ):
            raise TypeError(
                "reservation debe ser CotizacionProveedorEmision."
            )

        if not isinstance(attempt, IssueAttempt):
            raise TypeError(
                "attempt debe ser IssueAttempt."
            )

        # Bloquear el registro antes de actualizarlo.
        emission = (
            CotizacionProveedorEmision.objects
            .select_for_update()
            .get(pk=reservation.pk)
        )

        # Solo se puede finalizar una reserva pendiente.
        if (
            emission.estatus
            != CotizacionProveedorEmision.Estatus.EN_PROCESO
        ):
            raise ValueError(
                "La reserva de emisión ya fue finalizada."
            )

        # El proveedor del resultado debe coincidir.
        if emission.provider_code != attempt.provider_code:
            raise ValueError(
                "El proveedor del intento no coincide "
                "con el de la reserva."
            )

        if attempt.success:
            estatus = CotizacionProveedorEmision.Estatus.EXITOSA
            error = None
        else:
            error = attempt.error

            if error is not None and error.outcome_unknown:
                estatus = (
                    CotizacionProveedorEmision.Estatus.INDETERMINADA
                )
            else:
                estatus = CotizacionProveedorEmision.Estatus.FALLIDA

        result = attempt.result

        emission.estatus = estatus
        emission.elapsed_ms = attempt.elapsed_ms

        emission.retryable = (
            error.retryable if error is not None else False
        )
        emission.outcome_unknown = (
            error.outcome_unknown if error is not None else False
        )
        emission.error_type = (
            error.error_type if error is not None else ""
        )
        emission.error_message = (
            error.message if error is not None else ""
        )

        emission.provider_policy_id = (
            result.provider_policy_id if result is not None else ""
        )
        emission.provider_policy_key = (
            result.provider_policy_key or ""
            if result is not None
            else ""
        )
        emission.response_json = (
            dict(result.raw_response or {})
            if result is not None
            else {}
        )

        emission.save()

        return emission

    @classmethod
    @transaction.atomic
    def save(
        cls,
        *,
        cotizacion_item: CotizacionItem,
        cotizacion_proveedor: CotizacionProveedor,
        provider_configuration_id: int,
        attempt: IssueAttempt,
    ) -> CotizacionProveedorEmision:
        if not isinstance(cotizacion_item, CotizacionItem):
            raise TypeError(
                "cotizacion_item debe ser CotizacionItem."
            )

        if not isinstance(
            cotizacion_proveedor,
            CotizacionProveedor,
        ):
            raise TypeError(
                "cotizacion_proveedor debe ser "
                "CotizacionProveedor."
            )

        if not isinstance(attempt, IssueAttempt):
            raise TypeError(
                "attempt debe ser IssueAttempt."
            )

        if attempt.success:
            estatus = (
                CotizacionProveedorEmision
                .Estatus
                .EXITOSA
            )
            error = None
        else:
            error = attempt.error

            if (
                error is not None
                and error.outcome_unknown
            ):
                estatus = (
                    CotizacionProveedorEmision
                    .Estatus
                    .INDETERMINADA
                )
            else:
                estatus = (
                    CotizacionProveedorEmision
                    .Estatus
                    .FALLIDA
                )

        result = attempt.result

        return CotizacionProveedorEmision.objects.create(
            cotizacion_item=cotizacion_item,
            cotizacion_proveedor=cotizacion_proveedor,
            provider_code=attempt.provider_code,
            provider_configuration_id=(
                provider_configuration_id
            ),
            estatus=estatus,
            elapsed_ms=attempt.elapsed_ms,
            retryable=(
                error.retryable
                if error is not None
                else False
            ),
            outcome_unknown=(
                error.outcome_unknown
                if error is not None
                else False
            ),
            error_type=(
                error.error_type
                if error is not None
                else ""
            ),
            error_message=(
                error.message
                if error is not None
                else ""
            ),
            provider_policy_id=(
                result.provider_policy_id
                if result is not None
                else ""
            ),
            provider_policy_key=(
                result.provider_policy_key or ""
                if result is not None
                else ""
            ),
            response_json=(
                dict(result.raw_response or {})
                if result is not None
                else {}
            ),
        )
