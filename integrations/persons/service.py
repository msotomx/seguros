from __future__ import annotations

from integrations.persons.contracts import (
    PersonRequest,
    PersonResult,
)
from integrations.persons.provider import (
    PersonProvider,
)


class PersonService:
    def __init__(
        self,
        *,
        providers: list[PersonProvider],
    ):
        self._providers = {
            provider.provider_code.strip().upper(): provider
            for provider in providers
        }

    def create_one(
        self,
        *,
        provider_code: str,
        request: PersonRequest,
    ) -> PersonResult:

        code = provider_code.strip().upper()

        if code not in self._providers:
            raise ValueError(
                f"No existe PersonProvider para {code}."
            )

        provider = self._providers[code]

        return provider.create_person(
            request
        )
