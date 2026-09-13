from __future__ import annotations

from collections.abc import Mapping

from integrations.persons.contracts import PersonRequest

from .person_contracts import (
    ChubbCreatePersonRequest,
    ChubbPersonAddressRequest,
    ChubbPersonPhoneRequest,
)


class ChubbInternalPersonRequestMapper:
    """
    Convierte el contrato interno del ERP al contrato específico de Chubb.

    Los identificadores propios de Chubb se reciben ya resueltos mediante
    configuración o equivalencias de catálogo.

    El mapper no consulta ORM, configuración ni catálogos.
    """

    def __init__(
        self,
        *,
        person_type_id: int | None,
        legal_personality_id: int,
        marital_status_id: int,
        address_type_id: int,
        gender_ids: Mapping[str, int],
    ) -> None:
        self._person_type_id = person_type_id
        self._legal_personality_id = legal_personality_id
        self._marital_status_id = marital_status_id
        self._address_type_id = address_type_id

        self._gender_ids = {
            str(code).strip().upper(): int(external_id)
            for code, external_id in gender_ids.items()
        }

    def create_person(
        self,
        *,
        request: PersonRequest,
        neighborhood_id: int,
    ) -> ChubbCreatePersonRequest:

        if not isinstance(request, PersonRequest):
            raise TypeError(
                "request debe ser una instancia de PersonRequest."
            )

        if not isinstance(neighborhood_id, int):
            raise TypeError(
                "neighborhood_id debe ser entero."
            )

        if neighborhood_id <= 0:
            raise ValueError(
                "neighborhood_id debe ser mayor que cero."
            )

        rfc, homo_clave = self._split_rfc(
            request.rfc
        )

        phone = self._phone(
            request.phone
        )

        return ChubbCreatePersonRequest(
            person_type_id=self._person_type_id,
            legal_personality_id=self._legal_personality_id,
            rfc=rfc,
            homo_clave=homo_clave,
            first_name=request.first_name.strip(),
            second_name="",
            paternal_surname=request.paternal_surname.strip(),
            maternal_surname=request.maternal_surname.strip(),
            birth_or_constitution_date=request.birth_date,
            gender_id=self._gender_id(
                request.gender
            ),
            curp=request.curp.strip().upper(),
            marital_status_id=self._marital_status_id,
            address=ChubbPersonAddressRequest(
                address_type_id=self._address_type_id,
                street=request.address.street.strip(),
                exterior_number=(
                    request.address.exterior_number.strip()
                ),
                interior_number=(
                    request.address.interior_number.strip()
                    if request.address.interior_number
                    else None
                ),
                neighborhood_id=neighborhood_id,
            ),
            email=request.email.strip(),
            personal_phone=phone,
            cell_phone=phone,
        )

    def _gender_id(
        self,
        gender: str,
    ) -> int:
        normalized = str(gender).strip().upper()

        try:
            return self._gender_ids[normalized]
        except KeyError as exc:
            raise ValueError(
                f"Género no configurado para Chubb: {gender}"
            ) from exc

    @staticmethod
    def _split_rfc(
        value: str,
    ) -> tuple[str, str]:
        normalized = str(value).strip().upper()

        if len(normalized) != 13:
            raise ValueError(
                "El RFC de persona física debe tener 13 caracteres."
            )

        return normalized[:10], normalized[10:]

    @staticmethod
    def _phone(
        value: str,
    ) -> ChubbPersonPhoneRequest:
        normalized = "".join(
            character
            for character in str(value)
            if character.isdigit()
        )

        if len(normalized) != 10:
            raise ValueError(
                "El teléfono debe contener 10 dígitos."
            )

        return ChubbPersonPhoneRequest(
            area_code=normalized[:3],
            number=normalized[3:],
        )
