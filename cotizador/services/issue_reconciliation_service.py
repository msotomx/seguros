from __future__ import annotations

from django.db import transaction

from cotizador.models import (
    CotizacionItem,
    CotizacionProveedorEmision,
)
from cotizador.services.issue_persistence_service import (
    IssuePersistenceService,
)
from integrations.issues.contracts import IssueResult


class IssueReconciliationService:
    @classmethod
    @transaction.atomic
    def reconcile(
        cls,
        *,
        cotizacion_item: CotizacionItem,
        emision: CotizacionProveedorEmision,
        issue_result: IssueResult,
        persistence_service=IssuePersistenceService,
    ):
        if not isinstance(cotizacion_item, CotizacionItem):
            raise TypeError(
                "cotizacion_item debe ser CotizacionItem."
            )

        if not isinstance(
            emision,
            CotizacionProveedorEmision,
        ):
            raise TypeError(
                "emision debe ser CotizacionProveedorEmision."
            )

        if not isinstance(issue_result, IssueResult):
            raise TypeError(
                "issue_result debe ser IssueResult."
            )

        if emision.cotizacion_item_id != cotizacion_item.id:
            raise ValueError(
                "La emisión no corresponde al CotizacionItem."
            )

        if (
            emision.estatus
            != CotizacionProveedorEmision.Estatus.INDETERMINADA
        ):
            raise ValueError(
                "Solo puede reconciliarse una emisión "
                "indeterminada."
            )

        provider_code = (
            issue_result.provider_code or ""
        ).strip().upper()

        if provider_code != emision.provider_code.strip().upper():
            raise ValueError(
                "El provider del IssueResult no corresponde "
                "a la emisión."
            )

        if not issue_result.provider_policy_id:
            raise ValueError(
                "IssueResult no tiene provider_policy_id."
            )

        poliza = persistence_service.save(
            cotizacion_item=cotizacion_item,
            issue_result=issue_result,
        )

        emision.estatus = (
            CotizacionProveedorEmision.Estatus.EXITOSA
        )
        emision.outcome_unknown = False
        emision.retryable = False
        emision.provider_policy_id = (
            issue_result.provider_policy_id
        )
        emision.provider_policy_key = (
            issue_result.provider_policy_key or ""
        )
        emision.response_json = dict(
            issue_result.raw_response or {}
        )

        emision.save(
            update_fields=[
                "estatus",
                "outcome_unknown",
                "retryable",
                "provider_policy_id",
                "provider_policy_key",
                "response_json",
                "updated_at",
            ]
        )

        return poliza
