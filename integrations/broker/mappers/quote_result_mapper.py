from django.db import transaction

from catalogos.models import Aseguradora, ProductoSeguro


class BrokerQuoteResultMapper:
    """
    Convierte un BrokerQuoteResult en CotizacionItem(s) del ERP.
    """

    @staticmethod
    @transaction.atomic
    def save_to_cotizacion(cotizacion, result):
        created_items = []

        for index, option in enumerate(result.options, start=1):
            aseguradora = Aseguradora.objects.filter(
                nombre__iexact=option.provider
            ).first()

            if not aseguradora:
                aseguradora = Aseguradora.objects.filter(
                    nombre__icontains=option.provider
                ).first()

            if not aseguradora:
                raise ValueError(
                    f"No existe Aseguradora para provider={option.provider}"
                )

            producto = ProductoSeguro.objects.filter(
                aseguradora=aseguradora,
                nombre_producto__iexact=option.product_name,
                is_active=True,
            ).first()

            if not producto:
                raise ValueError(
                    f"No existe ProductoSeguro '{option.product_name}' "
                    f"para la aseguradora '{aseguradora.nombre}'."
                )

            item, _created = cotizacion.items.update_or_create(
                aseguradora=aseguradora,
                producto=producto,
                defaults={
                    "prima_neta": option.prima_neta or 0,
                    "derechos": option.derechos or 0,
                    "recargos": option.recargos or 0,
                    "iva": option.iva or 0,
                    "prima_total": option.prima_total or 0,
                    "forma_pago": option.payment_type or "",
                    "ranking": index,
                    "provider": option.provider,
                    "provider_quote_id": option.provider_quote_id or "",
                    "provider_raw_response": option.raw_response or {},
                    "paquete_nombre": option.package_name or "",
                },
            )

            created_items.append(item)

        return created_items
    