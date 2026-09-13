from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class ChubbPersonPhoneRequest:
    area_code: str
    number: str


@dataclass(frozen=True, slots=True)
class ChubbPersonAddressRequest:
    address_type_id: int
    street: str
    exterior_number: str
    interior_number: str | None
    neighborhood_id: int


@dataclass(frozen=True, slots=True)
class ChubbCreatePersonRequest:
    person_type_id: int | None
    legal_personality_id: int

    rfc: str
    homo_clave: str

    first_name: str
    second_name: str
    paternal_surname: str
    maternal_surname: str

    birth_or_constitution_date: date
    gender_id: int

    curp: str
    marital_status_id: int

    address: ChubbPersonAddressRequest

    email: str

    personal_phone: ChubbPersonPhoneRequest
    cell_phone: ChubbPersonPhoneRequest


@dataclass(frozen=True, slots=True)
class ChubbCreatePersonResult:
    tran_id: int
    person_id: int
    address_id: int

    raw_response: Mapping[str, Any]
