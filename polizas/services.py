from django.utils import timezone

def generar_numero_poliza(aseguradora_id: int) -> str:
    # Provisional, pero suficientemente único por aseguradora:
    # POL-<aseg>-<YYYYMMDDHHMMSS>-<ms>
    now = timezone.now()
    return f"POL-{aseguradora_id}-{now:%Y%m%d%H%M%S}-{now.microsecond//1000:03d}"

from polizas.models import PolizaEvento

def log_poliza_event(poliza, tipo, actor=None, titulo="", detalle="", data=None):
    PolizaEvento.objects.create(
        poliza=poliza,
        tipo=tipo,
        actor=actor,
        titulo=titulo or dict(PolizaEvento.Tipo.choices).get(tipo, tipo),
        detalle=detalle or "",
        data=data,
    )
