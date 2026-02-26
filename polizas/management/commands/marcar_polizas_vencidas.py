# polizas/management/commands/marcar_polizas_vencidas.py
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import localdate

from polizas.models import Poliza

# Regla: si estatus=VIGENTE y vigencia_hasta < hoy → VENCIDA.

class Command(BaseCommand):
    help = "Actualiza estatus de pólizas: VIGENTE -> VENCIDA por vigencia_hasta."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--log-events", action="store_true")
        parser.add_argument("--limit", type=int, default=0)

    def handle(self, *args, **options):
        today = localdate()
        dry = options["dry_run"]
        log_events = options["log_events"]
        limit = options["limit"] or 0

        # Bitácora (opcional)
        log_poliza_event = None
        PolizaEvento = None
        if log_events:
            try:
                from polizas.services import log_poliza_event as _log
                from polizas.models import PolizaEvento as _evt
                log_poliza_event = _log
                PolizaEvento = _evt
            except Exception:
                log_poliza_event = None
                PolizaEvento = None

        qs = (
            Poliza.objects
            .filter(
                estatus=Poliza.Estatus.VIGENTE,
                vigencia_hasta__lt=today,
            )
            .order_by("vigencia_hasta", "id")
        )

        if limit:
            qs = qs[:limit]

        total = qs.count()

        if dry:
            self.stdout.write(self.style.WARNING(
                f"[DRY RUN] hoy={today} | VENCER={total} (vigencia_hasta < hoy)"
            ))
            return

        if total == 0:
            self.stdout.write(self.style.SUCCESS(f"No hay pólizas por actualizar. (hoy={today})"))
            return

        # Modo rápido sin bitácora (bulk update)
        if not log_poliza_event or not PolizaEvento:
            updated = qs.update(estatus=Poliza.Estatus.VENCIDA)
            self.stdout.write(self.style.SUCCESS(
                f"Actualizadas (sin bitácora): VENCIDA={updated}. (hoy={today})"
            ))
            return

        # Con bitácora: iterar
        updated = 0
        with transaction.atomic():
            for poliza in qs.iterator(chunk_size=500):
                poliza.estatus = Poliza.Estatus.VENCIDA
                poliza.save(update_fields=["estatus", "updated_at"])
                updated += 1

                log_poliza_event(
                    poliza=poliza,
                    tipo=PolizaEvento.Tipo.POLIZA_VENCIDA,
                    actor=None,
                    titulo="Póliza vencida automáticamente",
                    detalle=f"Vigencia hasta {poliza.vigencia_hasta}",
                    data={"vigencia_hasta": str(poliza.vigencia_hasta)},
                    dedupe_key=f"POLIZA_VENCIDA:{poliza.id}",
                )

        self.stdout.write(self.style.SUCCESS(
            f"Actualizadas (con bitácora): VENCIDA={updated}. (hoy={today})"
        ))
