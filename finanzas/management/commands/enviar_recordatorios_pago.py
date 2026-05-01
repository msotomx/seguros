from django.core.management.base import BaseCommand
from finanzas.services.recordatorios_automaticos import generar_recordatorios_automaticos


class Command(BaseCommand):
    help = "Genera recordatorios automáticos para pagos por vencer y vencidos."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry = options["dry_run"]
        total, detalle = generar_recordatorios_automaticos(dry_run=dry)

        modo = "[DRY RUN] " if dry else ""
        self.stdout.write(self.style.SUCCESS(f"{modo}Recordatorios generados: {total}"))
        self.stdout.write(
            f"{modo}Por vencer: 7d={detalle['por_vencer'][7]}, 3d={detalle['por_vencer'][3]}, 1d={detalle['por_vencer'][1]}"
        )
        self.stdout.write(
            f"{modo}Vencido: 1d={detalle['vencido'][1]}, 3d={detalle['vencido'][3]}, 7d={detalle['vencido'][7]}"
        )

        if detalle["errores"]:
            self.stdout.write(self.style.WARNING(f"{modo}Errores: {len(detalle['errores'])}"))
            for err in detalle["errores"][:20]:
                self.stdout.write(
                    f"  pago={err['pago_id']} categoria={err['categoria']} dias={err['dias']} error={err['error']}"
                )
