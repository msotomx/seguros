from __future__ import annotations

from typing import Any, Mapping
from .issue_contracts import (
    ChubbIssueInvoiceRequest,
    ChubbIssueItemDetailRequest,
    ChubbIssueItemRequest,
    ChubbIssueItemResult,
    ChubbIssuePersonRequest,
    ChubbIssueRequest,
    ChubbIssueResult,
)


class ChubbIssueRequestMapper:
    """
    Valida y serializa el contrato de Issue al formato
    exacto esperado por la API de Chubb.
    """

    @classmethod
    def issue(
        cls,
        request: ChubbIssueRequest,
    ) -> dict[str, Any]:
        if not isinstance(request, ChubbIssueRequest):
            raise ValueError(
                "request debe ser una instancia de ChubbIssueRequest."
            )

        cls._require_positive_int(
            request.quote_id,
            "quote_id",
        )
        cls._require_positive_int(
            request.payment_type_id,
            "payment_type_id",
        )

        if not isinstance(
            request.insured,
            ChubbIssuePersonRequest,
        ):
            raise ValueError(
                "insured debe ser ChubbIssuePersonRequest."
            )

        if not isinstance(request.items, tuple):
            raise ValueError(
                "items debe ser una tupla."
            )

        if not request.items:
            raise ValueError(
                "Issue debe contener al menos un item."
            )

        payload = {
            "quoteId": request.quote_id,
            "paymentTypeId": request.payment_type_id,
            "insured": cls._person(request.insured),
            "items": [
                cls._item(item)
                for item in request.items
            ],
        }

        if request.invoice is not None:
            payload["invoice"] = cls._invoice(
                request.invoice
            )

        return payload

    @classmethod
    def _person(
        cls,
        person: ChubbIssuePersonRequest,
    ) -> dict[str, Any]:
        if not isinstance(
            person,
            ChubbIssuePersonRequest,
        ):
            raise ValueError(
                "person debe ser ChubbIssuePersonRequest."
            )

        cls._require_positive_int(
            person.tran_id,
            "tran_id",
        )
        cls._require_positive_int(
            person.person_id,
            "person_id",
        )
        cls._require_positive_int(
            person.address_id,
            "address_id",
        )

        return {
            "tranId": person.tran_id,
            "id": person.person_id,
            "addressId": person.address_id,
        }

    @classmethod
    def _item(
        cls,
        item: ChubbIssueItemRequest,
    ) -> dict[str, Any]:
        if not isinstance(
            item,
            ChubbIssueItemRequest,
        ):
            raise ValueError(
                "Cada item debe ser ChubbIssueItemRequest."
            )

        if not isinstance(
            item.item,
            ChubbIssueItemDetailRequest,
        ):
            raise ValueError(
                "item.item debe ser "
                "ChubbIssueItemDetailRequest."
            )

        detail = item.item

        cls._require_positive_int(
            detail.number,
            "item.number",
        )
        cls._require_positive_int(
            detail.package_id,
            "item.package_id",
        )
        cls._require_non_empty_string(
            detail.no_serie,
            "item.no_serie",
        )
        cls._require_string(
            detail.plate,
            "item.plate",
        )
        cls._require_string(
            detail.engine_number,
            "item.engine_number",
        )
        cls._require_non_empty_string(
            detail.reference,
            "item.reference",
        )

        cls._require_positive_int(
            detail.owner_tran_id,
            "item.owner_tran_id",
        )
        cls._require_positive_int(
            detail.owner_id,
            "item.owner_id",
        )
        cls._require_positive_int(
            detail.owner_address_id,
            "item.owner_address_id",
        )
        cls._require_positive_int(
            detail.beneficiary_tran_id,
            "item.beneficiary_tran_id",
        )
        cls._require_positive_int(
            detail.beneficiary_id,
            "item.beneficiary_id",
        )

        return {
            "item": {
                "number": detail.number,
                "packageId": detail.package_id,
                "noSerie": detail.no_serie.strip(),
                "plate": detail.plate.strip(),
                "engineNumber": detail.engine_number.strip(),
                "reference": detail.reference.strip(),
                "ownerTranId": detail.owner_tran_id,
                "ownerId": detail.owner_id,
                "ownerAddressId": detail.owner_address_id,
                "beneficiaryTranId": detail.beneficiary_tran_id,
                "beneficiaryId": detail.beneficiary_id,
            }
        }

    @classmethod
    def _invoice(
        cls,
        invoice: ChubbIssueInvoiceRequest,
    ) -> dict[str, Any]:
        if not isinstance(
            invoice,
            ChubbIssueInvoiceRequest,
        ):
            raise ValueError(
                "invoice debe ser ChubbIssueInvoiceRequest."
            )

        cls._require_non_negative_int(
            invoice.legal_personality_id,
            "invoice.legal_personality_id",
        )
        cls._require_non_empty_string(
            invoice.rfc,
            "invoice.rfc",
        )
        cls._require_non_empty_string(
            invoice.name,
            "invoice.name",
        )
        cls._require_non_empty_string(
            invoice.postal_code,
            "invoice.postal_code",
        )
        cls._require_positive_int(
            invoice.tax_regime,
            "invoice.tax_regime",
        )
        cls._require_positive_int(
            invoice.use_cfdi_id,
            "invoice.use_cfdi_id",
        )
        cls._require_non_empty_string(
            invoice.email,
            "invoice.email",
        )
        cls._require_non_empty_string(
            invoice.email_payment,
            "invoice.email_payment",
        )
        cls._require_string(
            invoice.comments,
            "invoice.comments",
        )
        cls._require_string(
            invoice.purchase_order,
            "invoice.purchase_order",
        )

        return {
            "legalPersonalityId": (
                invoice.legal_personality_id
            ),
            "rfc": invoice.rfc.strip(),
            "name": invoice.name.strip(),
            "postalCode": invoice.postal_code.strip(),
            "taxRegime": invoice.tax_regime,
            "useCFDId": invoice.use_cfdi_id,
            "email": invoice.email.strip(),
            "emailPayment": invoice.email_payment.strip(),
            "coments": invoice.comments.strip(),
            "purchaseOrder": invoice.purchase_order.strip(),
        }

    @staticmethod
    def _require_positive_int(
        value: int,
        field_name: str,
    ) -> None:
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value <= 0
        ):
            raise ValueError(
                f"{field_name} debe ser un entero mayor que cero."
            )

    @staticmethod
    def _require_non_negative_int(
        value: int,
        field_name: str,
    ) -> None:
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 0
        ):
            raise ValueError(
                f"{field_name} debe ser un entero cero o mayor."
            )

    @staticmethod
    def _require_string(
        value: str,
        field_name: str,
    ) -> None:
        if not isinstance(value, str):
            raise ValueError(
                f"{field_name} debe ser una cadena."
            )

    @classmethod
    def _require_non_empty_string(
        cls,
        value: str,
        field_name: str,
    ) -> None:
        cls._require_string(
            value,
            field_name,
        )

        if not value.strip():
            raise ValueError(
                f"{field_name} no puede estar vacío."
            )

class ChubbIssueResponseMapper:
    """
    Valida y transforma la respuesta de Issue
    al contrato específico de Chubb.
    """

    @classmethod
    def issue(
        cls,
        payload: Any,
    ) -> ChubbIssueResult:
        root = cls._require_mapping(
            payload,
            "response",
        )

        success = cls._success(root)

        if not success:
            raise ValueError(
                cls._error_message(root)
            )

        response_data = cls._require_list(
            root.get("responseData"),
            "responseData",
        )

        if not response_data:
            raise ValueError(
                "responseData no puede estar vacío."
            )

        if len(response_data) != 1:
            raise ValueError(
                "responseData debe contener exactamente "
                "una póliza emitida."
            )

        policy = cls._require_mapping(
            response_data[0],
            "responseData[0]",
        )

        items_payload = cls._require_list(
            policy.get("items"),
            "responseData[0].items",
        )

        if not items_payload:
            raise ValueError(
                "responseData[0].items no puede estar vacío."
            )

        items = tuple(
            cls._item(
                item,
                index=index,
            )
            for index, item in enumerate(
                items_payload
            )
        )

        return ChubbIssueResult(
            quote_key=cls._non_empty_string(
                policy.get("quoteKey"),
                "responseData[0].quoteKey",
            ),
            quote_policy_id=cls._positive_int(
                policy.get("quotePolicyId"),
                "responseData[0].quotePolicyId",
            ),
            net_premium_amount=cls._number(
                policy.get("netPremiumAmount"),
                "responseData[0].netPremiumAmount",
            ),
            bonification_amount=cls._number(
                policy.get("bonificationAmount"),
                "responseData[0].bonificationAmount",
            ),
            surcharge_amount=cls._number(
                policy.get("surchargeAmount"),
                "responseData[0].surchargeAmount",
            ),
            discount_amount=cls._number(
                policy.get("discountAmount"),
                "responseData[0].discountAmount",
            ),
            total_premium_amount=cls._number(
                policy.get("totalPremiumAmount"),
                "responseData[0].totalPremiumAmount",
            ),
            insured_id=cls._positive_int(
                policy.get("insuredId"),
                "responseData[0].insuredId",
            ),
            insured_address_id=cls._positive_int(
                policy.get("insuredAddressId"),
                "responseData[0].insuredAddressId",
            ),
            items=items,
            raw_response=dict(root),
        )

    @classmethod
    def _item(
        cls,
        payload: Any,
        *,
        index: int,
    ) -> ChubbIssueItemResult:
        prefix = (
            f"responseData[0].items[{index}]"
        )

        wrapper = cls._require_mapping(
            payload,
            prefix,
        )

        item = cls._require_mapping(
            wrapper.get("item"),
            f"{prefix}.item",
        )

        return ChubbIssueItemResult(
            number=cls._positive_int(
                item.get("number"),
                f"{prefix}.item.number",
            ),
            net_premium_amount=cls._number(
                item.get("netPremiumAmount"),
                f"{prefix}.item.netPremiumAmount",
            ),
            right_amount=cls._number(
                item.get("rightAmount"),
                f"{prefix}.item.rightAmount",
            ),
            discount_amount=cls._number(
                item.get("discountAmount"),
                f"{prefix}.item.discountAmount",
            ),
            surcharge_amount=cls._number(
                item.get("surchargeAmount"),
                f"{prefix}.item.surchargeAmount",
            ),
            iva_amount=cls._number(
                item.get("ivaAmount"),
                f"{prefix}.item.ivaAmount",
            ),
            total_premium_amount=cls._number(
                item.get("totalPremiumAmount"),
                f"{prefix}.item.totalPremiumAmount",
            ),
        )

    @staticmethod
    def _success(
        root: Mapping[str, Any],
    ) -> bool:
        """
        Chubb ha respondido con ambos nombres:
        success e isSuccess.
        """

        if "success" in root:
            success = root["success"]
        elif "isSuccess" in root:
            success = root["isSuccess"]
        else:
            raise ValueError(
                "La respuesta de Chubb no contiene "
                "success ni isSuccess."
            )

        if not isinstance(success, bool):
            raise ValueError(
                "La respuesta de Chubb no contiene "
                "un indicador de éxito válido."
            )

        return success

    @classmethod
    def _error_message(
        cls,
        root: Mapping[str, Any],
    ) -> str:
        messages = root.get("messages") or []

        if not isinstance(messages, list):
            return "Chubb rechazó la emisión."

        details = []

        for item in messages:
            if not isinstance(item, Mapping):
                continue

            message = str(
                item.get("message", "")
            ).strip()

            if message:
                details.append(message)

        return (
            "; ".join(details)
            or "Chubb rechazó la emisión."
        )

    @staticmethod
    def _require_mapping(
        value: Any,
        field_name: str,
    ) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise ValueError(
                f"{field_name} debe ser un objeto."
            )

        return value

    @staticmethod
    def _require_list(
        value: Any,
        field_name: str,
    ) -> list:
        if not isinstance(value, list):
            raise ValueError(
                f"{field_name} debe ser una lista."
            )

        return value

    @staticmethod
    def _positive_int(
        value: Any,
        field_name: str,
    ) -> int:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value <= 0
        ):
            raise ValueError(
                f"{field_name} debe ser un entero mayor que cero."
            )

        return value

    @staticmethod
    def _number(
        value: Any,
        field_name: str,
    ) -> float:
        if (
            isinstance(value, bool)
            or not isinstance(
                value,
                (int, float),
            )
        ):
            raise ValueError(
                f"{field_name} debe ser numérico."
            )

        return float(value)

    @staticmethod
    def _non_empty_string(
        value: Any,
        field_name: str,
    ) -> str:
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                f"{field_name} no puede estar vacío."
            )

        return value.strip()
