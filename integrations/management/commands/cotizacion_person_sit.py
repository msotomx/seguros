from __future__ import annotations

import json
import traceback

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from cotizador.models import Cotizacion
from cotizador.services.portal_person_application_service import (
    PortalPersonApplicationService,
)


class Command(BaseCommand):
    help = (
        "Crea la persona asegurada de una Cotizacion real del ERP "
        "contra el provider y ambiente indicados."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--cotizacion-id",
            type=int,
            required=True,
            help="ID de la Cotizacion del ERP.",
        )

        parser.add_argument(
            "--provider-code",
            required=True,
            help="Código del provider configurado en el ERP.",
        )

        parser.add_argument(
            "--ambiente",
            required=True,
            help="Ambiente configurado del provider.",
        )

        parser.add_argument(
            "--ramo",
            required=True,
            help="Ramo configurado del provider.",
        )

        parser.add_argument(
            "--send",
            action="store_true",
            help=(
                "Ejecuta realmente Create Person contra el provider. "
                "Sin este flag sólo valida la Cotizacion."
            ),
        )

        parser.add_argument(
            "--show-response",
            action="store_true",
            help="Muestra la respuesta completa del provider.",
        )

    def handle(self, *args, **options) -> None:
        cotizacion_id = options["cotizacion_id"]
        provider_code = options["provider_code"].strip()
        ambiente = options["ambiente"].strip()
        ramo = options["ramo"].strip()

        if not provider_code:
            raise CommandError(
                "provider-code no puede estar vacío."
            )

        if not ambiente:
            raise CommandError(
                "ambiente no puede estar vacío."
            )

        if not ramo:
            raise CommandError(
                "ramo no puede estar vacío."
            )

        try:
            cotizacion = (
                Cotizacion.objects
                .select_related(
                    "cliente",
                    "cliente__direccion_contacto",
                )
                .get(pk=cotizacion_id)
            )
        except Cotizacion.DoesNotExist as exc:
            raise CommandError(
                f"No existe Cotizacion id={cotizacion_id}."
            ) from exc

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n=== COTIZACION ERP → CREATE PERSON ==="
            )
        )

        self.stdout.write(
            f"Cotizacion : {cotizacion.id}"
        )
        self.stdout.write(
            f"Folio      : {cotizacion.folio}"
        )
        self.stdout.write(
            f"Cliente    : {cotizacion.cliente.nombre_mostrar}"
        )
        self.stdout.write(
            f"Provider   : {provider_code}"
        )
        self.stdout.write(
            f"Ambiente   : {ambiente}"
        )
        self.stdout.write(
            f"Ramo       : {ramo}"
        )

        if not options["send"]:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "No se realizó llamada al provider."
                )
            )
            self.stdout.write(
                "La Cotizacion fue encontrada correctamente."
            )
            self.stdout.write("")
            self.stdout.write(
                "Para enviar realmente:"
            )
            self.stdout.write(
                self.style.HTTP_INFO(
                    "python manage.py cotizacion_person_sit "
                    f"--cotizacion-id {cotizacion.id} "
                    f"--provider-code {provider_code} "
                    f"--ambiente {ambiente} "
                    f"--ramo {ramo} "
                    "--send"
                )
            )
            return

        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                "Ejecutando Create Person real..."
            )
        )

        try:
            result = (
                PortalPersonApplicationService.create_one(
                    cotizacion=cotizacion,
                    provider_code=provider_code,
                    ambiente=ambiente,
                    ramo=ramo,
                )
            )
        except Exception as exc:
            self.stderr.write("")
            self.stderr.write(
                self.style.ERROR(
                    "Create Person terminó con error."
                )
            )
            self.stderr.write(
                traceback.format_exc()
            )

            raise CommandError(
                f"Create Person falló: {exc}"
            ) from exc

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Create Person ejecutado correctamente."
            )
        )

        self.stdout.write("")
        self.stdout.write(
            f"Provider   : {result.provider_code}"
        )
        self.stdout.write(
            f"Tran ID    : {result.provider_tran_id}"
        )
        self.stdout.write(
            f"Person ID  : {result.provider_person_id}"
        )
        self.stdout.write(
            f"Address ID : {result.provider_address_id}"
        )

        if options["show_response"]:
            self.stdout.write("")
            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    "Respuesta completa:"
                )
            )
            self.stdout.write(
                json.dumps(
                    result.raw_response,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )
            )
