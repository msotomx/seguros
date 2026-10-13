from __future__ import annotations

from hashlib import sha256

from django.db import transaction
from django.utils import timezone

from cotizador.models import Cotizacion, CotizacionItem
from integrations.issues.contracts import IssueResult
from polizas.models import Poliza, PolizaProveedor, PolizaEvento
from polizas.services import log_poliza_event

class IssuePersistenceService:
    """
    Persiste en el ERP una emisión confirmada por un provider.

    No realiza llamadas externas.
    """

    @classmethod
    @transaction.atomic
    def save(
        cls,
        *,
        cotizacion_item: CotizacionItem,
        issue_result: IssueResult,
    ) -> Poliza:
        if not isinstance(cotizacion_item, CotizacionItem):
            raise TypeError(
                "cotizacion_item debe ser una instancia "
                "de CotizacionItem."
            )

        if not isinstance(issue_result, IssueResult):
            raise TypeError(
                "issue_result debe ser una instancia "
                "de IssueResult."
            )

        provider_code = cls._normalize_provider_code(
            issue_result.provider_code
        )

        item_provider = (
            cotizacion_item.provider or ""
        ).strip().upper()

        if not item_provider:
            raise ValueError(
                "El CotizacionItem no tiene provider."
            )

        if item_provider != provider_code:
            raise ValueError(
                "El provider del resultado de emisión "
                "no corresponde al CotizacionItem."
            )

        provider_policy_id = str(
            issue_result.provider_policy_id
        ).strip()

        if not provider_policy_id:
            raise ValueError(
                "IssueResult no contiene provider_policy_id."
            )

        # Bloquea la cotización durante la persistencia
        # para reducir riesgo de doble creación concurrente.
        cotizacion = (
            Cotizacion.objects
            .select_for_update()
            .get(pk=cotizacion_item.cotizacion_id)
        )

        existing = (
            Poliza.objects
            .select_related("resultado_proveedor")
            .filter(cotizacion_item=cotizacion_item)
            .first()
        )

        if existing is not None:
            try:
                existing.resultado_proveedor
            except PolizaProveedor.DoesNotExist:
                return cls._complete_prepared_policy(
                    poliza=existing,
                    cotizacion=cotizacion,
                    cotizacion_item=cotizacion_item,
                    issue_result=issue_result,
                    provider_code=provider_code,
                    provider_policy_id=provider_policy_id,
                )

            return cls._validate_existing(
                poliza=existing,
                provider_code=provider_code,
                provider_policy_id=provider_policy_id,
            )

        policy_number = cls._policy_number(
            issue_result=issue_result,
            provider_code=provider_code,
            provider_policy_id=provider_policy_id,
        )
        
        subtotal = (
            issue_result.net_premium
            + issue_result.fees
            + issue_result.surcharge
            - issue_result.discount
        )

        forma_pago = (
            cotizacion_item.forma_pago
            or cotizacion.forma_pago_preferida
        )

        poliza = Poliza.objects.create(
            cliente=cotizacion.cliente,
            vehiculo=cotizacion.vehiculo,
            flotilla=cotizacion.flotilla,
            aseguradora=cotizacion_item.aseguradora,
            producto=cotizacion_item.producto,
            cotizacion_item=cotizacion_item,
            numero_poliza=policy_number,
            fecha_emision=timezone.localdate(),
            vigencia_desde=cotizacion.vigencia_desde,
            vigencia_hasta=cotizacion.vigencia_hasta,
            estatus=Poliza.Estatus.EN_PROCESO,
            prima_neta=issue_result.net_premium,
            financiamiento=issue_result.surcharge,
            gastos_expedicion=issue_result.fees,
            subtotal=subtotal,
            iva=issue_result.taxes,
            prima_total=issue_result.total_premium,
            forma_pago=forma_pago,
            agente=cotizacion.owner,
        )

        PolizaProveedor.objects.create(
            poliza=poliza,
            provider_code=provider_code,
            provider_policy_id=provider_policy_id,
            provider_policy_key=(
                issue_result.provider_policy_key or ""
            ).strip(),
            currency=(
                issue_result.currency or ""
            ).strip().upper(),
            raw_response=dict(
                issue_result.raw_response or {}
            ),
        )

        cotizacion.estatus = Cotizacion.Estatus.EMITIDA
        cotizacion.emitida_at = timezone.now()
        cotizacion.save(
            update_fields=[
                "estatus",
                "emitida_at",
            ]
        )

        return poliza

    @classmethod
    def _complete_prepared_policy(
        cls,
        *,
        poliza: Poliza,
        cotizacion: Cotizacion,
        cotizacion_item: CotizacionItem,
        issue_result: IssueResult,
        provider_code: str,
        provider_policy_id: str,
    ) -> Poliza:
        policy_number = cls._policy_number(
            issue_result=issue_result,
            provider_code=provider_code,
            provider_policy_id=provider_policy_id,
        )
        previous_number = poliza.numero_poliza
        
        subtotal = (
            issue_result.net_premium
            + issue_result.fees
            + issue_result.surcharge
            - issue_result.discount
        )

        forma_pago = (
            cotizacion_item.forma_pago
            or cotizacion.forma_pago_preferida
        )

        poliza.numero_poliza = policy_number
        poliza.fecha_emision = timezone.localdate()
        poliza.prima_neta = issue_result.net_premium
        poliza.financiamiento = issue_result.surcharge
        poliza.gastos_expedicion = issue_result.fees
        poliza.subtotal = subtotal
        poliza.iva = issue_result.taxes
        poliza.prima_total = issue_result.total_premium
        poliza.forma_pago = forma_pago
        poliza.agente = cotizacion.owner

        poliza.save(
            update_fields=[
                "numero_poliza",
                "fecha_emision",
                "prima_neta",
                "financiamiento",
                "gastos_expedicion",
                "subtotal",
                "iva",
                "prima_total",
                "forma_pago",
                "agente",
                "updated_at",
            ]
        )

        if previous_number != policy_number:
            log_poliza_event(
                poliza=poliza,
                tipo=PolizaEvento.Tipo.NUMERO_ACTUALIZADO,
                titulo="Número de póliza actualizado",
                detalle=(
                    "Se sustituyó el número provisional "
                    "por el número de la emisión confirmada."
                ),
                data={
                    "numero_anterior": previous_number,
                    "numero_nuevo": policy_number,
                    "provider_code": provider_code,
                    "provider_policy_id": provider_policy_id,
                },
                dedupe_key=f"NUMERO_ACTUALIZADO:{poliza.pk}",
            )

        PolizaProveedor.objects.create(
            poliza=poliza,
            provider_code=provider_code,
            provider_policy_id=provider_policy_id,
            provider_policy_key=(
                issue_result.provider_policy_key or ""
            ).strip(),
            currency=(
                issue_result.currency or ""
            ).strip().upper(),
            raw_response=dict(
                issue_result.raw_response or {}
            ),
        )

        cotizacion.estatus = Cotizacion.Estatus.EMITIDA
        cotizacion.emitida_at = timezone.now()
        cotizacion.save(
            update_fields=[
                "estatus",
                "emitida_at",
            ]
        )

        return poliza

    @classmethod
    def _validate_existing(
        cls,
        *,
        poliza: Poliza,
        provider_code: str,
        provider_policy_id: str,
    ) -> Poliza:
        try:
            provider_result = poliza.resultado_proveedor
        except PolizaProveedor.DoesNotExist as exc:
            raise ValueError(
                "Ya existe una póliza para el CotizacionItem, "
                "pero no tiene resultado de provider."
            ) from exc

        if (
            provider_result.provider_code.strip().upper()
            != provider_code
            or provider_result.provider_policy_id.strip()
            != provider_policy_id
        ):
            raise ValueError(
                "El CotizacionItem ya tiene una póliza asociada "
                "a una emisión diferente."
            )

        return poliza

    @staticmethod
    def _policy_number(
        *,
        issue_result: IssueResult,
        provider_code: str,
        provider_policy_id: str,
    ) -> str:
        policy_number = (
            issue_result.policy_number or ""
        ).strip()

        if policy_number:
            if len(policy_number) > 80:
                raise ValueError(
                    "policy_number excede la longitud permitida."
                )
            return policy_number

        provisional = (
            f"PEND-{provider_code}-{provider_policy_id}"
        )

        if len(provisional) <= 80:
            return provisional

        digest = sha256(
            provider_policy_id.encode("utf-8")
        ).hexdigest()[:24]

        return f"PEND-{provider_code[:30]}-{digest}"

    @staticmethod
    def _normalize_provider_code(
        provider_code: str,
    ) -> str:
        if not isinstance(provider_code, str):
            raise TypeError(
                "provider_code debe ser una cadena."
            )

        normalized = provider_code.strip().upper()

        if not normalized:
            raise ValueError(
                "provider_code no puede estar vacío."
            )

        return normalized
