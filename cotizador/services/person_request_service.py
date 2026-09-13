# responsabilidad única: construir PersonRequest desde Cotizacion + Cliente + Direccion, 
# sin conocer Chubb.
from __future__ import annotations

from cotizador.models import Cotizacion
from integrations.catalog.suburb_code_service import (
    SuburbCodeService,
)
from integrations.persons.contracts import (
    PersonAddress,
    PersonRequest,
)
from crm.models import Cliente


class PersonRequestService:
    """
    Construye el contrato canónico de persona
    a partir de una Cotizacion del ERP.

    No conoce implementaciones específicas de aseguradoras.
    """

    @classmethod
    def build(
        cls,
        *,
        cotizacion: Cotizacion,
    ) -> PersonRequest:

        cls._validate(
            cotizacion=cotizacion,
        )

        cliente = cotizacion.cliente
        direccion = cliente.direccion_contacto

        neighborhood_code = SuburbCodeService.build(
            zip_code=direccion.cp,
            name=direccion.colonia,
        )

        address = PersonAddress(
            street=direccion.calle.strip(),
            exterior_number=direccion.num_ext.strip(),
            interior_number=(
                direccion.num_int.strip()
                or None
            ),
            neighborhood_code=neighborhood_code,
            city=direccion.ciudad.strip(),
            state=direccion.estado.strip(),
            postal_code=direccion.cp.strip(),
        )

        return PersonRequest(
            first_name=cotizacion.conductor_nombre.strip(),
            paternal_surname=(
                cotizacion.conductor_apellido_paterno.strip()
            ),
            maternal_surname=(
                cotizacion.conductor_apellido_materno.strip()
            ),
            rfc=cotizacion.conductor_rfc.strip().upper(),
            birth_date=cotizacion.conductor_fecha_nacimiento,
            gender=cotizacion.conductor_genero.strip().upper(),
            email=cliente.email_principal.strip(),
            phone=cliente.telefono_principal.strip(),
            curp=cliente.curp.strip().upper(),
            address=address,
        )

    @staticmethod
    def _validate(
        *,
        cotizacion: Cotizacion,
    ) -> None:

        if not isinstance(cotizacion, Cotizacion):
            raise TypeError(
                "cotizacion debe ser una instancia de Cotizacion."
            )

        if cotizacion.tipo_cotizacion != Cotizacion.Tipo.INDIVIDUAL:
            raise ValueError(
                "Esta versión de PersonRequestService sólo "
                "soporta cotizaciones individuales."
            )

        cliente = cotizacion.cliente

        if cliente.tipo_cliente != Cliente.TipoCliente.PERSONA:
            raise ValueError(
                "La cotización debe pertenecer a un cliente persona."
            )

        if not cotizacion.conductor_nombre.strip():
            raise ValueError(
                "La cotización no contiene nombre del conductor."
            )

        if not cotizacion.conductor_apellido_paterno.strip():
            raise ValueError(
                "La cotización no contiene apellido paterno "
                "del conductor."
            )

        if not cotizacion.conductor_rfc.strip():
            raise ValueError(
                "La cotización no contiene RFC del conductor."
            )

        if cotizacion.conductor_fecha_nacimiento is None:
            raise ValueError(
                "La cotización no contiene fecha de nacimiento "
                "del conductor."
            )

        if not cotizacion.conductor_genero.strip():
            raise ValueError(
                "La cotización no contiene género del conductor."
            )

        if not cliente.email_principal.strip():
            raise ValueError(
                "El cliente no contiene email principal."
            )

        if not cliente.telefono_principal.strip():
            raise ValueError(
                "El cliente no contiene teléfono principal."
            )

        if not cliente.curp.strip():
            raise ValueError(
                "El cliente no contiene CURP."
            )

        direccion = cliente.direccion_contacto

        if direccion is None:
            raise ValueError(
                "El cliente no contiene dirección de contacto."
            )

        required_address_fields = {
            "calle": direccion.calle,
            "num_ext": direccion.num_ext,
            "colonia": direccion.colonia,
            "ciudad": direccion.ciudad,
            "estado": direccion.estado,
            "cp": direccion.cp,
        }

        for field_name, value in required_address_fields.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"La dirección no contiene {field_name}."
                )
