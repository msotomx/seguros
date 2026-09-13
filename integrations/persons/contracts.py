from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class PersonAddress:
    street: str
    exterior_number: str
    interior_number: str | None
    neighborhood_code: str
    city: str
    state: str
    postal_code: str


@dataclass(frozen=True, slots=True)
class PersonRequest:
    first_name: str
    paternal_surname: str
    maternal_surname: str
    rfc: str
    birth_date: date
    gender: str

    email: str
    phone: str
    curp: str

    address: PersonAddress


@dataclass(frozen=True, slots=True)
class PersonResult:
    provider_code: str

    provider_tran_id: str
    provider_person_id: str
    provider_address_id: str

    raw_response: dict
