from __future__ import annotations

from integrations.providers.chubb.person_contracts import (
    ChubbCreatePersonRequest,
)


class ChubbPersonRequestMapper:

    @classmethod
    def create_person(
        cls,
        request: ChubbCreatePersonRequest,
    ) -> dict:

        return {
            "personTypeId": request.person_type_id,
            "legalPersonalityId": (
                request.legal_personality_id
            ),
            "rfc": request.rfc,
            "homoClave": request.homo_clave,
            "firstName": request.first_name,
            "secondName": request.second_name,
            "paternalSurname": (
                request.paternal_surname
            ),
            "maternalSurname": (
                request.maternal_surname
            ),
            "birthOrConstitutionDate": (
                request
                .birth_or_constitution_date
                .isoformat()
            ),
            "genderId": request.gender_id,
            "curp": request.curp,
            "maritalStatusId": (
                request.marital_status_id
            ),
            "address": {
                "addressTypeId": (
                    request.address.address_type_id
                ),
                "street": request.address.street,
                "exteriorNumber": (
                    request.address.exterior_number
                ),
                "interiorNumber": (
                    request.address.interior_number
                ),
                "neighborhoodId": (
                    request.address.neighborhood_id
                ),
            },
            "email": request.email,
            "personalPhone": {
                "areaCode": (
                    request.personal_phone.area_code
                ),
                "number": (
                    request.personal_phone.number
                ),
            },
            "cellPhone": {
                "areaCode": (
                    request.cell_phone.area_code
                ),
                "number": (
                    request.cell_phone.number
                ),
            },
        }

from typing import Any, Mapping

from integrations.providers.chubb.person_contracts import (
    ChubbCreatePersonResult,
)


class ChubbPersonResponseMapper:

    @classmethod
    def create_person(
        cls,
        payload: Mapping[str, Any],
    ) -> ChubbCreatePersonResult:

        if not isinstance(payload, Mapping):
            raise ValueError(
                "La respuesta de Chubb Person debe ser "
                "un objeto JSON."
            )

        return ChubbCreatePersonResult(
            tran_id=cls._positive_int(
                payload.get("tranId"),
                "tranId",
            ),
            person_id=cls._positive_int(
                payload.get("personId"),
                "personId",
            ),
            address_id=cls._positive_int(
                payload.get("addressId"),
                "addressId",
            ),
            raw_response=dict(payload),
        )

    @staticmethod
    def _positive_int(
        value,
        field_name: str,
    ) -> int:
        try:
            result = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"'{field_name}' debe ser un entero válido."
            ) from exc

        if result <= 0:
            raise ValueError(
                f"'{field_name}' debe ser mayor que cero."
            )

        return result
