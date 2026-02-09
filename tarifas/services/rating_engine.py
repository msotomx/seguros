# tarifas/services/rating_engine.py
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple
from itertools import product

from catalogos.models import Aseguradora, ProductoSeguro


def money(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class QuoteResult:
    aseguradora_id: int
    producto_id: int

    prima_neta: Decimal
    derechos: Decimal
    recargos: Decimal
    descuentos: Decimal
    iva: Decimal
    prima_total: Decimal

    forma_pago: str = "CONTADO"
    meses: Optional[int] = None
    ranking: int = 0

    # trazabilidad (para CotizacionItemCalculo)
    prima_base: Decimal = Decimal("0.00")
    factor_total: Decimal = Decimal("1.000000")
    detalle_json: Dict[str, Any] = None

    # opcionales (para coberturas/reglas)
    coberturas: List[Dict[str, Any]] = None
    reglas: List[Dict[str, Any]] = None


class RatingEngine:
    """
    Motor de tarifas (versión inicial).
    - Genera N opciones (aseguradora, producto) y calcula importes.
    - Más adelante reemplazamos la parte de cálculo por reglas reales.
    """

    MAX_ITEMS = 3
    IVA_RATE = Decimal("0.16")
    DERECHOS_FIJO = Decimal("450.00")

    def quote(self, cotizacion) -> List[QuoteResult]:
        """
        Entrada: cotizacion (cotizador.models.Cotizacion)
        Salida: lista de QuoteResult (opciones)
        """
        # 1) Determinar universo de combinaciones
        aseguradoras = list(Aseguradora.objects.all()[:10])
        productos = list(ProductoSeguro.objects.all()[:10])

        if not aseguradoras or not productos:
            return []

        combos: List[Tuple[Aseguradora, ProductoSeguro]] = list(product(aseguradoras, productos))
        combos = combos[: self.MAX_ITEMS]  # tomamos hasta N combos únicos

        # 2) Calcular base “demostrativa” con datos de cotización
        # Puedes hacer algo más sofisticado luego (año, tipo_uso, etc.)
        prima_base = self._prima_base(cotizacion)

        results: List[QuoteResult] = []
        for i, (aseg, prod) in enumerate(combos, start=1):
            # Factor demo por ranking/opción (solo para variar precios)
            factor_total = Decimal("1.00") + (Decimal(i - 1) * Decimal("0.07"))  # 1.00, 1.07, 1.14

            prima_neta = money(prima_base * factor_total)
            derechos = money(self.DERECHOS_FIJO)
            recargos = money(Decimal("0.00"))
            descuentos = money(Decimal("0.00"))

            # IVA demo: sobre prima_neta + derechos (ajusta si tu negocio aplica distinto)
            iva = money((prima_neta + derechos + recargos - descuentos) * self.IVA_RATE)

            prima_total = money(prima_neta + derechos + recargos - descuentos + iva)

            results.append(
                QuoteResult(
                    aseguradora_id=aseg.id,
                    producto_id=prod.id,
                    prima_neta=prima_neta,
                    derechos=derechos,
                    recargos=recargos,
                    descuentos=descuentos,
                    iva=iva,
                    prima_total=prima_total,
                    forma_pago="CONTADO",
                    meses=None,
                    ranking=i,
                    prima_base=money(prima_base),
                    factor_total=factor_total.quantize(Decimal("0.000001")),
                    detalle_json={
                        "modo": "engine_demo_v1",
                        "inputs": {
                            "cotizacion_id": cotizacion.id,
                            "tipo_cotizacion": cotizacion.tipo_cotizacion,
                            "origen": cotizacion.origen,
                            "vigencia_desde": str(cotizacion.vigencia_desde),
                            "vigencia_hasta": str(cotizacion.vigencia_hasta),
                        },
                        "calculo": {
                            "prima_base": str(money(prima_base)),
                            "factor_total": str(factor_total.quantize(Decimal("0.000001"))),
                            "prima_neta": str(prima_neta),
                            "derechos": str(derechos),
                            "iva_rate": str(self.IVA_RATE),
                            "iva": str(iva),
                            "prima_total": str(prima_total),
                        },
                    },
                    coberturas=[],
                    reglas=[],
                )
            )

        # 3) Ordena por prima_total ascendente (opcional)
        results.sort(key=lambda r: (r.prima_total, r.ranking))
        # Re-ranking coherente con el orden final
        for idx, r in enumerate(results, start=1):
            r.ranking = idx

        return results

    def _prima_base(self, cotizacion) -> Decimal:
        """
        Prima base demo.
        Luego aquí puedes usar:
        - año del vehículo, uso, cp, edad conductor, etc.
        """
        base = Decimal("8500.00")

        # Ejemplo: flotilla un poco más alta
        if cotizacion.tipo_cotizacion == "FLOTILLA":
            base *= Decimal("1.15")

        return base
