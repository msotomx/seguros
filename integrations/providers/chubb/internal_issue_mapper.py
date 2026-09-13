from __future__ import annotations

from collections.abc import Mapping

from integrations.issues.contracts import (
    InternalIssueRequest,
    IssueInvoice,
    IssuePartyReference,
    IssueRisk,
)

from .issue_contracts import (
    ChubbIssueInvoiceRequest,
    ChubbIssueItemDetailRequest,
    ChubbIssueItemRequest,
    ChubbIssuePersonRequest,
    ChubbIssueRequest,
)


class ChubbInternalIssueRequestMapper:
    """
    Convierte el contrato interno de emisión del ERP
    al contrato específico de Chubb.

    Los identificadores propios de Chubb se reciben ya resueltos.
    Este mapper no consulta ORM, configuración ni catálogos.
    """

    def __init__(
        self,
        *,
        payment_type_ids: Mapping[str, int],
        legal_personality_ids: Mapping[str, int],
        tax_regime_ids: Mapping[str, int],
        cfdi_use_ids: Mapping[str, int],
    ) -> None:
        self._payment_type_ids = self._normalize_mapping(
            payment_type_ids
        )
        self._legal_personality_ids = self._normalize_mapping(
            legal_personality_ids
        )
        self._tax_regime_ids = self._normalize_mapping(
            tax_regime_ids
        )
        self._cfdi_use_ids = self._normalize_mapping(
            cfdi_use_ids
        )

    def issue(
        self,
        request: InternalIssueRequest,
    ) -> ChubbIssueRequest:
        if not isinstance(
            request,
            InternalIssueRequest,
        ):
            raise TypeError(
                "request debe ser una instancia de "
                "InternalIssueRequest."
            )

        if not request.risks:
            raise ValueError(
                "La solicitud de emisión requiere "
                "al menos un riesgo."
            )

        return ChubbIssueRequest(
            quote_id=self._positive_int(
                request.provider_quote_id,
                "provider_quote_id",
            ),
            payment_type_id=self._mapped_id(
                mapping=self._payment_type_ids,
                code=request.payment_method_code,
                description="forma de pago",
            ),
            insured=self._person(
                request.insured,
                require_address=True,
            ),
            items=tuple(
                self._risk(risk)
                for risk in request.risks
            ),
            invoice=(
                self._invoice(request.invoice)
                if request.invoice is not None
                else None
            ),
        )

    def _risk(
        self,
        risk: IssueRisk,
    ) -> ChubbIssueItemRequest:
        if not isinstance(risk, IssueRisk):
            raise TypeError(
                "risk debe ser una instancia de IssueRisk."
            )

        if risk.owner is None:
            raise ValueError(
                "El riesgo requiere propietario para Chubb."
            )

        if risk.beneficiary is None:
            raise ValueError(
                "El riesgo requiere beneficiario para Chubb."
            )

        owner = self._person(
            risk.owner,
            require_address=True,
        )

        beneficiary = self._person(
            risk.beneficiary,
            require_address=False,
        )

        vin = str(risk.vin).strip()

        if not vin:
            raise ValueError(
                "VIN es obligatorio para emisión Chubb."
            )

        reference = str(risk.reference).strip()

        if not reference:
            raise ValueError(
                "reference es obligatorio para emisión Chubb."
            )

        return ChubbIssueItemRequest(
            item=ChubbIssueItemDetailRequest(
                number=self._positive_int(
                    risk.risk_number,
                    "risk_number",
                ),
                package_id=self._positive_int(
                    risk.provider_package_id,
                    "provider_package_id",
                ),
                no_serie=vin,
                plate=str(
                    risk.plate or ""
                ).strip(),
                engine_number=str(
                    risk.engine_number or ""
                ).strip(),
                reference=reference,
                owner_tran_id=owner.tran_id,
                owner_id=owner.person_id,
                owner_address_id=owner.address_id,
                beneficiary_tran_id=(
                    beneficiary.tran_id
                ),
                beneficiary_id=(
                    beneficiary.person_id
                ),
            )
        )

    def _person(
        self,
        person: IssuePartyReference,
        *,
        require_address: bool,
    ) -> ChubbIssuePersonRequest:
        if not isinstance(
            person,
            IssuePartyReference,
        ):
            raise TypeError(
                "person debe ser una instancia de "
                "IssuePartyReference."
            )

        address_id = 0

        if person.provider_address_id not in (
            None,
            "",
        ):
            address_id = self._positive_int(
                person.provider_address_id,
                "provider_address_id",
            )
        elif require_address:
            raise ValueError(
                "provider_address_id es obligatorio."
            )

        return ChubbIssuePersonRequest(
            tran_id=self._positive_int(
                person.provider_tran_id,
                "provider_tran_id",
            ),
            person_id=self._positive_int(
                person.provider_person_id,
                "provider_person_id",
            ),
            address_id=address_id,
        )

    def _invoice(
        self,
        invoice: IssueInvoice,
    ) -> ChubbIssueInvoiceRequest:
        if not isinstance(
            invoice,
            IssueInvoice,
        ):
            raise TypeError(
                "invoice debe ser una instancia de IssueInvoice."
            )

        return ChubbIssueInvoiceRequest(
            legal_personality_id=self._mapped_non_negative_id(
                mapping=self._legal_personality_ids,
                code=invoice.legal_personality_code,
                description="personalidad jurídica",
            ),
            rfc=str(invoice.tax_id).strip(),
            name=str(invoice.name).strip(),
            postal_code=str(
                invoice.postal_code
            ).strip(),
            tax_regime=self._mapped_id(
                mapping=self._tax_regime_ids,
                code=invoice.tax_regime_code,
                description="régimen fiscal",
            ),
            use_cfdi_id=self._mapped_id(
                mapping=self._cfdi_use_ids,
                code=invoice.cfdi_use_code,
                description="uso CFDI",
            ),
            email=str(invoice.email).strip(),
            email_payment=str(
                invoice.payment_email
                or invoice.email
            ).strip(),
            comments=str(
                invoice.comments
            ).strip(),
            purchase_order=str(
                invoice.purchase_order
            ).strip(),
        )

    @staticmethod
    def _normalize_mapping(
        mapping: Mapping[str, int],
    ) -> dict[str, int]:
        return {
            str(code).strip().upper(): int(value)
            for code, value in mapping.items()
        }

    @staticmethod
    def _mapped_id(
        *,
        mapping: Mapping[str, int],
        code: str,
        description: str,
    ) -> int:
        normalized = str(code).strip().upper()

        try:
            value = mapping[normalized]
        except KeyError as exc:
            raise ValueError(
                f"{description.capitalize()} no configurada "
                f"para Chubb: {code}"
            ) from exc

        if value <= 0:
            raise ValueError(
                f"El identificador Chubb para "
                f"{description} debe ser mayor que cero."
            )

        return value

    @staticmethod
    def _mapped_non_negative_id(
        *,
        mapping: Mapping[str, int],
        code: str,
        description: str,
    ) -> int:
        normalized = str(code).strip().upper()

        try:
            value = mapping[normalized]
        except KeyError as exc:
            raise ValueError(
                f"{description.capitalize()} no configurada "
                f"para Chubb: {code}"
            ) from exc

        if value < 0:
            raise ValueError(
                f"El identificador Chubb para "
                f"{description} debe ser cero o mayor."
            )

        return value

    @staticmethod
    def _positive_int(
        value,
        field_name: str,
    ) -> int:
        if isinstance(value, bool):
            raise ValueError(
                f"{field_name} debe ser un entero mayor que cero."
            )

        try:
            normalized = int(value)
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                f"{field_name} debe ser un entero mayor que cero."
            ) from exc

        if normalized <= 0:
            raise ValueError(
                f"{field_name} debe ser un entero mayor que cero."
            )

        return normalized
