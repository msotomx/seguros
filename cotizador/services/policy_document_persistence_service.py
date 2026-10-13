from __future__ import annotations

import hashlib

from django.core.files.base import ContentFile
from django.db import transaction

from documentos.models import Documento
from integrations.documents.contracts import PolicyDocument
from polizas.models import Poliza


class PolicyDocumentPersistenceService:
    @classmethod
    @transaction.atomic
    def persist(
        cls,
        *,
        poliza: Poliza,
        document: PolicyDocument,
        subido_por=None,
    ) -> Documento:
        if not isinstance(poliza, Poliza):
            raise TypeError("poliza debe ser Poliza.")

        if not isinstance(document, PolicyDocument):
            raise TypeError(
                "document debe ser PolicyDocument."
            )

        file_name = document.file_name.strip()

        if not file_name:
            raise ValueError(
                "El documento no tiene nombre de archivo."
            )

        if not document.content:
            raise ValueError(
                "El documento no tiene contenido."
            )

        content_hash = hashlib.sha256(
            document.content
        ).hexdigest()

        locked_poliza = (
            Poliza.objects
            .select_for_update()
            .select_related("documento")
            .get(pk=poliza.pk)
        )

        if locked_poliza.documento_id is not None:
            existing = locked_poliza.documento

            if existing.hash == content_hash:
                return existing

            raise ValueError(
                "La póliza ya tiene un documento diferente."
            )

        django_file = ContentFile(
            document.content,
            name=file_name,
        )

        documento = Documento.objects.create(
            nombre_archivo=file_name,
            tipo=Documento.Tipo.PDF,
            file=django_file,
            tamano=len(document.content),
            hash=content_hash,
            subido_por=subido_por,
        )

        locked_poliza.documento = documento
        locked_poliza.save(
            update_fields=[
                "documento",
                "updated_at",
            ]
        )

        # Mantiene sincronizada la instancia recibida por el caller.
        poliza.documento_id = documento.id

        return documento

