from __future__ import annotations

from typing import Protocol

from integrations.persons.contracts import (
    PersonRequest,
    PersonResult,
)


class PersonProvider(Protocol):
    provider_code: str

    def create_person(
        self,
        request: PersonRequest,
    ) -> PersonResult:
        ...
