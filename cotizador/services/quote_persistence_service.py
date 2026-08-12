from __future__ import annotations

from typing import Any, Mapping

from django.db import transaction

from cotizador.models import (
    Cotizacion,
    CotizacionProveedor,
    CotizacionProveedorCobertura,
    CotizacionProveedorOpcion,
    CotizacionProveedorRiesgo,
)
from integrations.quotes.contracts import (
    QuoteAttempt,
    QuoteCoverage,
    QuoteOption,
    QuoteRiskResult,
)


class QuotePersistenceService:
    """
    Persiste el resultado normalizado de una ejecución
    de cotización contra un proveedor.

    No conoce implementaciones específicas de aseguradoras.
    """

    @classmethod
    @transaction.atomic
    def persist(
        cls,
        *,
        cotizacion: Cotizacion,
        attempt: QuoteAttempt,
        request_json: Mapping[str, Any] | None = None,
    ) -> CotizacionProveedor:

        if not isinstance(cotizacion, Cotizacion):
            raise TypeError(
                "cotizacion debe ser una instancia de Cotizacion."
            )

        if not isinstance(attempt, QuoteAttempt):
            raise TypeError(
                "attempt debe ser una instancia de QuoteAttempt."
            )

        if attempt.success:
            return cls._persist_success(
                cotizacion=cotizacion,
                attempt=attempt,
                request_json=request_json,
            )

        return cls._persist_failure(
            cotizacion=cotizacion,
            attempt=attempt,
            request_json=request_json,
        )

    @classmethod
    def _persist_success(
        cls,
        *,
        cotizacion: Cotizacion,
        attempt: QuoteAttempt,
        request_json: Mapping[str, Any] | None,
    ) -> CotizacionProveedor:

        result = attempt.result

        if result is None:
            raise ValueError(
                "Un QuoteAttempt exitoso debe contener result."
            )

        registro = CotizacionProveedor.objects.create(
            cotizacion=cotizacion,
            provider_code=attempt.provider_code,
            success=True,
            elapsed_ms=attempt.elapsed_ms,

            provider_quote_id=(
                result.provider_quote_id or ""
            ),
            provider_quote_version_id=(
                result.provider_quote_version_id or ""
            ),
            reference=result.reference or "",
            currency=result.currency or "",

            net_premium=result.net_premium,
            fees=result.fees,
            taxes=result.taxes,
            total_premium=result.total_premium,

            request_json=dict(request_json or {}),
            response_json=dict(result.raw_response or {}),

            messages_json=[
                {
                    "level": message.level,
                    "message": message.message,
                    "code": message.code,
                }
                for message in result.messages
            ],
        )

        if result.risks:
            for risk in result.risks:
                cls._persist_risk(
                    cotizacion_proveedor=registro,
                    risk=risk,
                )
        else:
            for option in result.options:
                cls._persist_option(
                    cotizacion_proveedor=registro,
                    riesgo=None,
                    option=option,
                )

        return registro

    @classmethod
    def _persist_failure(
        cls,
        *,
        cotizacion: Cotizacion,
        attempt: QuoteAttempt,
        request_json: Mapping[str, Any] | None,
    ) -> CotizacionProveedor:

        error = attempt.error

        if error is None:
            raise ValueError(
                "Un QuoteAttempt fallido debe contener error."
            )

        return CotizacionProveedor.objects.create(
            cotizacion=cotizacion,
            provider_code=attempt.provider_code,
            success=False,
            elapsed_ms=attempt.elapsed_ms,

            request_json=dict(request_json or {}),

            error_message=error.message,
            error_type=error.error_type,
            error_retryable=error.retryable,
        )

    @classmethod
    def _persist_risk(
        cls,
        *,
        cotizacion_proveedor: CotizacionProveedor,
        risk: QuoteRiskResult,
    ) -> CotizacionProveedorRiesgo:

        riesgo = CotizacionProveedorRiesgo.objects.create(
            cotizacion_proveedor=cotizacion_proveedor,
            reference=risk.reference or "",
            provider_risk_id=risk.provider_risk_id or "",
            risk_number=risk.risk_number,
            vehicle_key=risk.vehicle_key or "",
        )

        for option in risk.options:
            cls._persist_option(
                cotizacion_proveedor=cotizacion_proveedor,
                riesgo=riesgo,
                option=option,
            )

        return riesgo

    @classmethod
    def _persist_option(
        cls,
        *,
        cotizacion_proveedor: CotizacionProveedor,
        riesgo: CotizacionProveedorRiesgo | None,
        option: QuoteOption,
    ) -> CotizacionProveedorOpcion:

        opcion = CotizacionProveedorOpcion.objects.create(
            cotizacion_proveedor=cotizacion_proveedor,
            riesgo=riesgo,
            code=option.code,
            provider_package_id=(
                ""
                if option.provider_package_id is None
                else str(option.provider_package_id)
            ),
            name=option.name,
            total_premium=option.total_premium,
            currency=option.currency,
            selected=option.selected,
        )

        for coverage in option.coverages:
            cls._persist_coverage(
                opcion=opcion,
                coverage=coverage,
            )

        return opcion

    @staticmethod
    def _persist_coverage(
        *,
        opcion: CotizacionProveedorOpcion,
        coverage: QuoteCoverage,
    ) -> CotizacionProveedorCobertura:

        return CotizacionProveedorCobertura.objects.create(
            opcion=opcion,
            code=coverage.code,
            name=coverage.name,
            insured_amount=coverage.insured_amount,
            deductible=coverage.deductible,
            premium=coverage.premium,
        )
