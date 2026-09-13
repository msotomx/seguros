from __future__ import annotations

import unicodedata


class SuburbCodeService:
    @classmethod
    def build(
        cls,
        *,
        zip_code: str,
        name: str,
    ) -> str:
        zip_code = cls._normalize_zip_code(
            zip_code
        )

        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                "El nombre de la colonia no puede estar vacío."
            )

        normalized = unicodedata.normalize(
            "NFKD",
            name.strip(),
        )

        normalized = "".join(
            character
            for character in normalized
            if not unicodedata.combining(character)
        )

        normalized = normalized.upper()

        normalized = "".join(
            character
            if character.isalnum()
            else "_"
            for character in normalized
        )

        normalized = "_".join(
            part
            for part in normalized.split("_")
            if part
        )

        return f"{zip_code}_{normalized}"

    @staticmethod
    def _normalize_zip_code(
        value: str,
    ) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                "zip_code no puede estar vacío."
            )

        return value.strip()
