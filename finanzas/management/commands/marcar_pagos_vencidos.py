# finanzas/management/commands/marcar_pagos_vencidos.py
# Marca Pagos con estatus PENDIENTE como VENCIDO
# En PRODUCCION se va a hacer un cron que se ejecute automatico diariamente

# Regla: SI fecha_programada y estatus=PENDIENTE → si fecha_programada < hoy --> VENCIDO.
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import localdate

from finanzas.models import Pago, Poliza
from polizas.services import log_poliza_event

class Command(BaseCommand):
    help = "Actualiza estatus de pagos: PENDIENTE->VENCIDO por fecha, y PENDIENTE/VENCIDO->CANCELADO si póliza cancelada."

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

        # 1) Pagos a CANCELAR por póliza cancelada
        qs_cancelar = (
            Pago.objects
            .select_related("poliza")
            .filter(
                estatus__in=[Pago.Estatus.PENDIENTE, Pago.Estatus.VENCIDO],
                poliza__estatus=Poliza.Estatus.CANCELADA,
            )
            .order_by("id")
        )

        # 2) Pagos a VENCER (pendiente y ya pasó fecha), excluye póliza cancelada
        qs_vencer = (
            Pago.objects
            .select_related("poliza")
            .filter(
                estatus=Pago.Estatus.PENDIENTE,
                fecha_programada__lt=today,
            )
            .exclude(poliza__estatus=Poliza.Estatus.CANCELADA)
            .order_by("fecha_programada", "id")
        )

        if limit:
            qs_cancelar = qs_cancelar[:limit]
            qs_vencer = qs_vencer[:limit]

        n_cancelar = qs_cancelar.count()
        n_vencer = qs_vencer.count()

        if dry:
            self.stdout.write(self.style.WARNING(
                f"[DRY RUN] hoy={today} | CANCELAR={n_cancelar} (póliza cancelada) | VENCER={n_vencer} (pendiente vencido)"
            ))
            return

        if n_cancelar == 0 and n_vencer == 0:
            self.stdout.write(self.style.SUCCESS(f"No hay pagos por actualizar. (hoy={today})"))
            return

        # Modo rápido sin bitácora: bulk update
        if not log_poliza_event or not PolizaEvento:
            upd_cancelar = qs_cancelar.update(estatus=Pago.Estatus.CANCELADO)
            upd_vencer = qs_vencer.update(estatus=Pago.Estatus.VENCIDO)
            self.stdout.write(self.style.SUCCESS(
                f"Actualizados (sin bitácora): CANCELADO={upd_cancelar}, VENCIDO={upd_vencer}. (hoy={today})"
            ))
            return

        # Con bitácora: iterar
        updated_cancelar = 0
        updated_vencer = 0

        with transaction.atomic():
            for pago in qs_cancelar.iterator(chunk_size=500):
                pago.estatus = Pago.Estatus.CANCELADO
                pago.save(update_fields=["estatus", "updated_at"])

                log_poliza_event(
                    poliza=pago.poliza,
                    tipo=PolizaEvento.Tipo.PAGO_CANCELADO,
                    actor=None,
                    titulo="Pago cancelado automáticamente",
                    data={
                        "pago_id": pago.id,
                        "fecha_programada": str(pago.fecha_programada),
                        "monto": str(pago.monto),
                        "razon": "POLIZA_CANCELADA",
                    },
                    dedupe_key=f"PAGO_CANCELADO:{pago.id}",
                )

            for pago in qs_vencer.iterator(chunk_size=500):
                pago.estatus = Pago.Estatus.VENCIDO
                pago.save(update_fields=["estatus", "updated_at"])

                log_poliza_event(
                    poliza=pago.poliza,
                    tipo=PolizaEvento.Tipo.PAGO_VENCIDO,
                    actor=None,
                    titulo="Pago vencido automáticamente",
                    data={
                        "pago_id": pago.id,
                        "fecha_programada": str(pago.fecha_programada),
                        "monto": str(pago.monto),
                    },
                    dedupe_key=f"PAGO_VENCIDO:{pago.id}",
                )

        self.stdout.write(self.style.SUCCESS(
            f"Actualizados (con bitácora): CANCELADO={updated_cancelar}, VENCIDO={updated_vencer}. (hoy={today})"
        ))

