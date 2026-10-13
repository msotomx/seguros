import json
import hashlib
import shutil
import tempfile

from decimal import Decimal
from datetime import timedelta, date
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from unittest.mock import Mock

from autos.models import Vehiculo, VehiculoCatalogo, Marca, SubMarca
from crm.models import Cliente
from documentos.models import Documento
from cotizador.models import (
    Cotizacion,
    CotizacionItem,
    CotizacionProveedor,
    CotizacionProveedorCobertura,
    CotizacionProveedorOpcion,
    CotizacionProveedorRiesgo,
    CotizacionProveedorPersona,
    CotizacionProveedorEmision,
)
from cotizador.services.quote_persistence_service import (
    QuotePersistenceService,
)
from cotizador.services.provider_quote_service import (
    CotizacionProviderService,
)
from cotizador.services.issue_reconciliation_service import (
    IssueReconciliationService,
)
from integrations.quotes.contracts import (
    QuoteAttempt,
    QuoteCoverage,
    QuoteOption,
    QuoteProviderError,
    QuoteResult,
    QuoteRiskResult,
    InternalQuoteRequest,
    QuoteDriver,
    QuoteRisk,
    QuoteVehicle,
)
from integrations.quotes.service import QuoteService
from cotizador.services.quote_request_service import (
    QuoteRequestService,
)
from integrations.catalog.contracts import (
    ProviderCatalogValue,
)
from cotizador.services.cotizacion_quote_service import (
    CotizacionQuoteService,
)
from integrations.broker.provider_configuration import (
    ProviderConfiguration,
)
from integrations.catalog import CatalogService
from integrations.models import (
    AseguradoraConfiguracion,
    Catalog,
    CatalogItem,
    ProviderCatalogMapping,
    ProviderSetting,
)
from integrations.configuration.services import (
    ProviderConfigurationService,
)
from integrations.providers.chubb.quote_client import (
    ChubbQuoteClient,
)
from integrations.providers.chubb.quote_provider_builder import (
    ChubbQuoteProviderBuilder,
)
from integrations.providers.chubb.contracts import (
    ChubbHttpResponse,
)
from cotizador.services.quote_reconciliation_service import (
    QuoteReconciliationService,
)
from catalogos.models import (
    Aseguradora,
    ProductoSeguro,
)
from cotizador.models import CotizacionItem
from integrations.broker.provider_configuration import (
    ProviderConfiguration,
)
from cotizador.services.provider_option_projection_service import (
    ProviderOptionProjectionService,
)
from cotizador.models import (
    CotizacionProveedor,
    CotizacionProveedorOpcion,
)
from cotizador.services.portal_quote_application_service import (
    PortalQuoteApplicationService,
)
from cotizador.services.portal_multi_provider_quote_service import (
    PortalMultiProviderQuoteService,
)
from crm.models import Cliente, Direccion

from cotizador.services.person_request_service import (
    PersonRequestService,
)
from cotizador.services.cotizacion_person_service import (
    CotizacionPersonService,
)
from integrations.persons.contracts import (
    PersonRequest,
    PersonResult,
)
from cotizador.services.portal_person_application_service import (
    PortalPersonApplicationService,
)
from crm.models import CodigoPostal
from cotizador.services.person_persistence_service import (
    PersonPersistenceService,
)
from cotizador.services.issue_request_service import IssueRequestService
from cotizador.services.portal_issue_application_service import (
    PortalIssueApplicationService,
)
from cotizador.services.issue_persistence_service import (
    IssuePersistenceService,
)
from integrations.issues.contracts import IssueResult
from polizas.models import Poliza, PolizaProveedor, PolizaEvento
from cotizador.services.portal_document_application_service import (
    PortalDocumentApplicationService,
)
from integrations.documents.contracts import (
    PolicyDocumentRequest,
    PolicyDocument,
    PolicyDocumentResult,
)
from cotizador.services.policy_document_persistence_service import (
    PolicyDocumentPersistenceService,
)
from django.test import override_settings
from integrations.providers.exceptions import (
    ProviderHttpTimeoutError,
)
from cotizador.services.policy_preparation_service import (
    PolicyPreparationService,
)
from finanzas.models import Pago
from finanzas.services.pagos import crear_plan_pagos

class CotizacionConductorTests(TestCase):
    def test_guarda_datos_del_conductor(self):
        cliente = Cliente.objects.create(
            tipo_cliente=Cliente.TipoCliente.PERSONA,
            nombre="Miguel",
            email_principal="miguel@example.com",
        )

        vehiculo = Vehiculo.objects.create(
            cliente=cliente,
            marca_texto="Nissan",
            submarca_texto="Versa",
            modelo_anio=2024,
        )

        hoy = timezone.localdate()

        cotizacion = Cotizacion.objects.create(
            cliente=cliente,
            vehiculo=vehiculo,
            flotilla=None,
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=hoy,
            vigencia_hasta=hoy + timedelta(days=365),
            conductor_nombre="Miguel",
            conductor_genero=(
                Cotizacion.GeneroConductor.MASCULINO
            ),
            conductor_edad=45,
        )

        self.assertEqual(
            cotizacion.conductor_nombre,
            "Miguel",
        )
        self.assertEqual(
            cotizacion.conductor_genero,
            Cotizacion.GeneroConductor.MASCULINO,
        )
        self.assertEqual(
            cotizacion.conductor_edad,
            45,
        )

class QuotePersistenceServiceTests(TestCase):

    def setUp(self):
        self.cliente = Cliente.objects.create(
            tipo_cliente=Cliente.TipoCliente.PERSONA,
            nombre="Miguel",
            email_principal="miguel@example.com",
        )

        self.vehiculo = Vehiculo.objects.create(
            cliente=self.cliente,
            marca_texto="Nissan",
            submarca_texto="Versa",
            modelo_anio=2024,
        )

        hoy = timezone.localdate()

        self.cotizacion = Cotizacion.objects.create(
            cliente=self.cliente,
            vehiculo=self.vehiculo,
            flotilla=None,
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=hoy,
            vigencia_hasta=hoy + timedelta(days=365),
            conductor_nombre="Miguel",
            conductor_genero=(
                Cotizacion.GeneroConductor.MASCULINO
            ),
            conductor_edad=45,
        )

    def test_persiste_cotizacion_exitosa_completa(self):
        coverage = QuoteCoverage(
            code="101",
            name="Daños materiales",
            insured_amount=Decimal("300000.00"),
            deductible=Decimal("5.00"),
            premium=Decimal("2500.00"),
        )

        option = QuoteOption(
            code="10",
            provider_package_id=10,
            name="Amplia",
            total_premium=Decimal("12500.00"),
            currency="MXN",
            selected=True,
            coverages=(coverage,),
        )

        risk = QuoteRiskResult(
            reference="VEH-1",
            provider_risk_id="98765",
            risk_number=1,
            vehicle_key="ABC123",
            options=(option,),
        )

        result = QuoteResult(
            provider_code="CHUBB",
            provider_quote_id="123456",
            provider_quote_version_id="2",
            reference="COT-EXT-1",
            currency="MXN",
            net_premium=Decimal("10000.00"),
            fees=Decimal("500.00"),
            taxes=Decimal("2000.00"),
            total_premium=Decimal("12500.00"),
            options=(option,),
            risks=(risk,),
            raw_response={
                "quoteId": 123456,
                "quoteVersionId": 2,
            },
        )

        attempt = QuoteAttempt(
            provider_code="CHUBB",
            success=True,
            elapsed_ms=350,
            result=result,
        )

        registro = QuotePersistenceService.persist(
            cotizacion=self.cotizacion,
            attempt=attempt,
            provider_configuration_id=123,
            request_json={
                "reference": self.cotizacion.folio,
            },
        )

        self.assertTrue(registro.success)
        self.assertEqual(
            registro.provider_code,
            "CHUBB",
        )
        self.assertEqual(
            registro.provider_quote_id,
            "123456",
        )
        self.assertEqual(
            registro.provider_quote_version_id,
            "2",
        )
        self.assertEqual(
            registro.total_premium,
            Decimal("12500.00"),
        )
        self.assertEqual(
            CotizacionProveedor.objects.count(),
            1,
        )
        self.assertEqual(
            CotizacionProveedorRiesgo.objects.count(),
            1,
        )
        self.assertEqual(
            CotizacionProveedorOpcion.objects.count(),
            1,
        )
        self.assertEqual(
            CotizacionProveedorCobertura.objects.count(),
            1,
        )
        self.assertEqual(
            registro.provider_configuration_id,
            123,
        )
        riesgo = registro.riesgos.get()

        self.assertEqual(
            riesgo.provider_risk_id,
            "98765",
        )
        self.assertEqual(
            riesgo.vehicle_key,
            "ABC123",
        )

        opcion = registro.opciones.get()

        self.assertEqual(
            opcion.provider_package_id,
            "10",
        )
        self.assertEqual(
            opcion.name,
            "Amplia",
        )

        cobertura = opcion.coberturas.get()

        self.assertEqual(
            cobertura.code,
            "101",
        )
        self.assertEqual(
            cobertura.name,
            "Daños materiales",
        )

        self.assertEqual(
            registro.response_json["quoteId"],
            123456,
        )

    def test_persiste_intento_fallido(self):
        error = QuoteProviderError(
            provider_code="CHUBB",
            message="Chubb devolvió HTTP 500 para POST /quote.",
            error_type="ProviderHttpResponseError",
            retryable=False,
            status_code=500,
            response_data={
                "responseData": None,
                "messages": [
                    {
                        "message": "Dato inválido",
                        "messageCode": 1004,
                        "messageType": 2,
                    }
                ],
            },
        )

        attempt = QuoteAttempt(
            provider_code="CHUBB",
            success=False,
            elapsed_ms=30000,
            error=error,
        )

        registro = QuotePersistenceService.persist(
            cotizacion=self.cotizacion,
            attempt=attempt,
            provider_configuration_id=456,
            request_json={
                "reference": self.cotizacion.folio,
            },
        )

        self.assertFalse(registro.success)

        self.assertEqual(
            registro.provider_code,
            "CHUBB",
        )
        self.assertEqual(
            registro.elapsed_ms,
            30000,
        )
        self.assertEqual(
            registro.error_message,
            "Chubb devolvió HTTP 500 para POST /quote.",
        )
        self.assertEqual(
            registro.error_type,
            "ProviderHttpResponseError",
        )
        self.assertEqual(
            registro.provider_configuration_id,
            456,
        )
        self.assertFalse(
            registro.error_retryable,
        )
        self.assertEqual(
            registro.riesgos.count(),
            0,
        )
        self.assertEqual(
            registro.opciones.count(),
            0,
        )
        self.assertEqual(
            registro.response_json,
            {
                "responseData": None,
                "messages": [
                    {
                        "message": "Dato inválido",
                        "messageCode": 1004,
                        "messageType": 2,
                    }
                ],
            },
        )

    def test_persiste_opciones_sin_riesgos(self):
        option = QuoteOption(
            code="BASICA",
            provider_package_id=None,
            name="Básica",
            total_premium=Decimal("8500.00"),
            currency="MXN",
            selected=False,
            coverages=(),
        )

        result = QuoteResult(
            provider_code="OTRO",
            provider_quote_id="Q-001",
            provider_quote_version_id=None,
            reference=None,
            currency="MXN",
            net_premium=Decimal("7000.00"),
            fees=Decimal("300.00"),
            taxes=Decimal("1200.00"),
            total_premium=Decimal("8500.00"),
            options=(option,),
            risks=(),
            raw_response={},
        )

        attempt = QuoteAttempt(
            provider_code="OTRO",
            success=True,
            elapsed_ms=125,
            result=result,
        )

        registro = QuotePersistenceService.persist(
            cotizacion=self.cotizacion,
            attempt=attempt,
        )

        self.assertEqual(
            registro.riesgos.count(),
            0,
        )

        self.assertEqual(
            registro.opciones.count(),
            1,
        )

        opcion = registro.opciones.get()

        self.assertIsNone(
            opcion.riesgo,
        )

        self.assertEqual(
            opcion.code,
            "BASICA",
        )

        self.assertEqual(
            opcion.provider_package_id,
            "",
        )

        self.assertEqual(
            opcion.total_premium,
            Decimal("8500.00"),
        )

    def test_rejects_invalid_provider_configuration_id(
        self,
    ):
        attempt = Mock(spec=QuoteAttempt)
        attempt.success = True

        with self.assertRaisesRegex(
            ValueError,
            "provider_configuration_id debe ser",
        ):
            QuotePersistenceService.persist(
                cotizacion=self.cotizacion,
                attempt=attempt,
                provider_configuration_id=0,
            )

    def test_rechaza_provider_configuration_id_invalido(self):
        option = QuoteOption(
            code="BASICA",
            provider_package_id=None,
            name="Básica",
            total_premium=Decimal("8500.00"),
            currency="MXN",
            selected=False,
            coverages=(),
        )

        result = QuoteResult(
            provider_code="CHUBB",
            provider_quote_id="Q-001",
            provider_quote_version_id=None,
            reference=None,
            currency="MXN",
            net_premium=Decimal("7000.00"),
            fees=Decimal("300.00"),
            taxes=Decimal("1200.00"),
            total_premium=Decimal("8500.00"),
            options=(option,),
            risks=(),
            raw_response={},
        )

        attempt = QuoteAttempt(
            provider_code="CHUBB",
            success=True,
            elapsed_ms=125,
            result=result,
        )

        with self.assertRaisesRegex(
            ValueError,
            "provider_configuration_id debe ser",
        ):
            QuotePersistenceService.persist(
                cotizacion=self.cotizacion,
                attempt=attempt,
                provider_configuration_id=0,
            )


class CotizacionProviderServiceTests(TestCase):

    def setUp(self):
        self.cliente = Cliente.objects.create(
            tipo_cliente=Cliente.TipoCliente.PERSONA,
            nombre="Miguel",
            email_principal="miguel@example.com",
        )

        self.vehiculo = Vehiculo.objects.create(
            cliente=self.cliente,
            marca_texto="Nissan",
            submarca_texto="Versa",
            modelo_anio=2024,
        )

        hoy = timezone.localdate()

        self.cotizacion = Cotizacion.objects.create(
            cliente=self.cliente,
            vehiculo=self.vehiculo,
            flotilla=None,
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=hoy,
            vigencia_hasta=hoy + timedelta(days=365),
            conductor_nombre="Miguel",
            conductor_genero=(
                Cotizacion.GeneroConductor.MASCULINO
            ),
            conductor_edad=45,
        )

        self.request = InternalQuoteRequest(
            effective_date=hoy,
            expiration_date=hoy + timedelta(days=365),
            prospect_name="Miguel",
            reference=self.cotizacion.folio,
            risks=(),
        )

    def test_ejecuta_quote_service_y_persiste_attempt(self):
        result = QuoteResult(
            provider_code="CHUBB",
            provider_quote_id="123456",
            provider_quote_version_id="2",
            reference=None,
            currency="MXN",
            net_premium=Decimal("10000.00"),
            fees=Decimal("500.00"),
            taxes=Decimal("2000.00"),
            total_premium=Decimal("12500.00"),
            options=(),
            risks=(),
            raw_response={
                "quoteId": 123456,
            },
        )

        attempt = QuoteAttempt(
            provider_code="CHUBB",
            success=True,
            elapsed_ms=350,
            result=result,
        )

        provider = Mock()
        provider.provider_code = "CHUBB"

        quote_service = QuoteService(
            providers=[provider],
        )

        quote_service.quote_one = Mock(
            return_value=attempt,
        )

        persistence_service = Mock()

        registro_esperado = Mock(
            spec=CotizacionProveedor,
        )

        persistence_service.persist.return_value = (
            registro_esperado
        )

        service = CotizacionProviderService(
            quote_service=quote_service,
            persistence_service=persistence_service,
        )

        request_json = {
            "reference": self.cotizacion.folio,
        }

        registro = service.quote_one(
            cotizacion=self.cotizacion,
            provider_code="CHUBB",
            request=self.request,
            provider_configuration_id=77,
            request_json=request_json,
        )

        quote_service.quote_one.assert_called_once_with(
            "CHUBB",
            self.request,
        )

        persistence_service.persist.assert_called_once_with(
            cotizacion=self.cotizacion,
            attempt=attempt,
            provider_configuration_id=77,
            request_json=request_json,
        )

        self.assertIs(
            registro,
            registro_esperado,
        )

class QuoteRequestServiceTests(TestCase):

    def setUp(self):
        self.cliente = Cliente.objects.create(
            tipo_cliente=Cliente.TipoCliente.PERSONA,
            nombre="Miguel",
            apellido_paterno="Soto",
            email_principal="miguel@example.com",
        )

        marca = Marca.objects.create(
            nombre="ACURA",
        )

        submarca = SubMarca.objects.create(
            marca=marca,
            nombre="TL",
        )

        self.vehiculo_catalogo = (
            VehiculoCatalogo.objects.create(
                marca=marca,
                submarca=submarca,
                anio=2015,
                version="SEDAN 3.7L AUT",
            )
        )

        self.vehiculo = Vehiculo.objects.create(
            cliente=self.cliente,
            catalogo=self.vehiculo_catalogo,
            marca_texto="ACURA",
            submarca_texto="TL",
            modelo_anio=2015,
            version="SEDAN 3.7L AUT",
            tipo_uso=Vehiculo.TipoUso.PARTICULAR,
            placas="TR543",
        )

        CodigoPostal.objects.create(
            codigo_postal="32500",
            colonia="Centro",
            municipio="Juarez",
            ciudad="Ciudad Juarez",
            estado="Chihuahua",
        )

        hoy = timezone.localdate()

        self.cotizacion = Cotizacion.objects.create(
            cliente=self.cliente,
            vehiculo=self.vehiculo,
            flotilla=None,
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=hoy,
            vigencia_hasta=hoy + timedelta(days=365),
            conductor_nombre="Miguel Soto",
            conductor_genero=(
                Cotizacion.GeneroConductor.MASCULINO
            ),
            conductor_edad=25,
            estado="CHIHUAHUA",
            ciudad="CIUDAD JUAREZ",
            codigo_postal="32500",
        )

    def test_construye_internal_quote_request_con_mappings(self):
        catalog_service = Mock()

        mappings = {
            (
                "VEHICLE",
                f"VEHICULO_CATALOGO_{self.vehiculo_catalogo.id}",
            ): "01010100101",
            (
                "VEHICLE_USE",
                "PARTICULAR",
            ): "01",
            (
                "STATE",
                "CHIHUAHUA",
            ): "5",
            (
                "MUNICIPALITY",
                "JUAREZ",
            ): "863",
            (
                "COVERAGE_PACKAGE",
                "AMPLIA",
            ): "1",
        }

        def to_provider(
            *,
            provider_id,
            catalog_code,
            internal_code,
        ):
            external_code = mappings[
                (catalog_code, internal_code)
            ]

            return ProviderCatalogValue(
                provider_id=provider_id,
                catalog_code=catalog_code,
                internal_code=internal_code,
                internal_name=internal_code,
                external_code=external_code,
                external_name=internal_code,
                metadata={},
            )

        catalog_service.to_provider.side_effect = (
            to_provider
        )

        request = QuoteRequestService.build(
            cotizacion=self.cotizacion,
            provider_id=1,
            package_code="AMPLIA",
            garage=False,
            catalog_service=catalog_service,
        )

        self.assertEqual(
            request.prospect_name,
            "Miguel Soto",
        )

        self.assertEqual(
            request.reference,
            self.cotizacion.folio,
        )

        self.assertEqual(
            len(request.risks),
            1,
        )

        risk = request.risks[0]

        self.assertEqual(
            risk.vehicle.vehicle_key,
            "01010100101",
        )

        self.assertEqual(
            risk.vehicle.year,
            2015,
        )

        self.assertEqual(
            risk.vehicle.use_code,
            "01",
        )

        self.assertEqual(
            risk.vehicle.state_code,
            "5",
        )

        self.assertEqual(
            risk.vehicle.municipality_code,
            "863",
        )

        self.assertFalse(
            risk.vehicle.garage,
        )

        self.assertEqual(
            risk.vehicle.plate,
            "TR543",
        )

        self.assertEqual(
            risk.driver.age,
            25,
        )

        self.assertEqual(
            risk.driver.gender,
            "MASCULINO",
        )

        self.assertEqual(
            len(risk.packages),
            1,
        )

        self.assertEqual(
            risk.packages[0].code,
            "1",
        )

        self.assertTrue(
            risk.packages[0].selected,
        )

        self.assertEqual(
            risk.packages[0].coverages,
            (),
        )

    def test_construye_descuentos_desde_catalogo_proveedor(self):
        catalog_service = Mock()
        discount_service = Mock()

        discount_service.list_internal_codes_for_provider.return_value = (
            "DESCUENTO",
            "BONIFICACION",
        )

        mappings = {
            (
                "VEHICLE",
                f"VEHICULO_CATALOGO_{self.vehiculo_catalogo.id}",
            ): ("01010100101", "Vehículo"),
            (
                "VEHICLE_USE",
                "PARTICULAR",
            ): ("01", "Particular"),
            (
                "STATE",
                "CHIHUAHUA",
            ): ("5", "Chihuahua"),
            (
                "MUNICIPALITY",
                "JUAREZ",
            ): ("863", "Juárez"),
            (
                "COVERAGE_PACKAGE",
                "AMPLIA",
            ): ("1", "Amplia"),
            (
                "DISCOUNT",
                "DESCUENTO",
            ): ("1", "Descuento"),
            (
                "DISCOUNT",
                "BONIFICACION",
            ): ("2", "Bonificacion"),
        }

        def to_provider(
            *,
            provider_id,
            catalog_code,
            internal_code,
        ):
            external_code, external_name = mappings[
                (catalog_code, internal_code)
            ]

            return ProviderCatalogValue(
                provider_id=provider_id,
                catalog_code=catalog_code,
                internal_code=internal_code,
                internal_name=internal_code,
                external_code=external_code,
                external_name=external_name,
                metadata={},
            )

        catalog_service.to_provider.side_effect = to_provider

        request = QuoteRequestService.build(
            cotizacion=self.cotizacion,
            provider_id=1,
            package_code="AMPLIA",
            garage=False,
            catalog_service=catalog_service,
            discount_service=discount_service,
        )

        discounts = request.risks[0].discounts

        self.assertEqual(
            len(discounts),
            2,
        )

        self.assertEqual(
            discounts[0].code,
            "1",
        )
        self.assertEqual(
            discounts[0].name,
            "Descuento",
        )
        self.assertEqual(
            discounts[0].percentage,
            Decimal("0.00"),
        )

        self.assertEqual(
            discounts[1].code,
            "2",
        )
        self.assertEqual(
            discounts[1].name,
            "Bonificacion",
        )
        self.assertEqual(
            discounts[1].percentage,
            Decimal("0.00"),
        )

    def test_serializa_internal_quote_request_para_json(self):
        catalog_service = Mock()

        mappings = {
            (
                "VEHICLE",
                f"VEHICULO_CATALOGO_{self.vehiculo_catalogo.id}",
            ): "01010100101",
            ("VEHICLE_USE", "PARTICULAR"): "01",
            ("STATE", "CHIHUAHUA"): "5",
            ("MUNICIPALITY", "JUAREZ"): "863",
            ("COVERAGE_PACKAGE", "AMPLIA"): "1",
        }

        def to_provider(
            *,
            provider_id,
            catalog_code,
            internal_code,
        ):
            external_code = mappings[
                (catalog_code, internal_code)
            ]

            return ProviderCatalogValue(
                provider_id=provider_id,
                catalog_code=catalog_code,
                internal_code=internal_code,
                internal_name=internal_code,
                external_code=external_code,
                external_name=internal_code,
                metadata={},
            )

        catalog_service.to_provider.side_effect = to_provider

        request = QuoteRequestService.build(
            cotizacion=self.cotizacion,
            provider_id=1,
            package_code="AMPLIA",
            garage=False,
            catalog_service=catalog_service,
        )

        data = QuoteRequestService.to_dict(
            request
        )

        self.assertEqual(
            data["effective_date"],
            self.cotizacion.vigencia_desde.isoformat(),
        )

        self.assertEqual(
            data["expiration_date"],
            self.cotizacion.vigencia_hasta.isoformat(),
        )

        self.assertEqual(
            data["risks"][0]["vehicle"]["vehicle_key"],
            "01010100101",
        )

        self.assertEqual(
            data["risks"][0]["packages"][0]["code"],
            "1",
        )
    def test_usa_municipio_del_codigo_postal_y_no_ciudad(self):
        catalog_service = Mock()

        def to_provider(
            *,
            provider_id,
            catalog_code,
            internal_code,
        ):
            external_codes = {
                "VEHICLE": "01010100101",
                "VEHICLE_USE": "01",
                "STATE": "5",
                "MUNICIPALITY": "863",
                "COVERAGE_PACKAGE": "1",
            }

            return ProviderCatalogValue(
                provider_id=provider_id,
                catalog_code=catalog_code,
                internal_code=internal_code,
                internal_name=internal_code,
                external_code=external_codes[catalog_code],
                external_name=internal_code,
                metadata={},
            )

        catalog_service.to_provider.side_effect = to_provider

        QuoteRequestService.build(
            cotizacion=self.cotizacion,
            provider_id=1,
            package_code="AMPLIA",
            garage=False,
            catalog_service=catalog_service,
        )

        catalog_service.to_provider.assert_any_call(
            provider_id=1,
            catalog_code="MUNICIPALITY",
            internal_code="JUAREZ",
        )


class CotizacionQuoteServiceTests(TestCase):

    def setUp(self):
        self.cliente = Cliente.objects.create(
            tipo_cliente=Cliente.TipoCliente.PERSONA,
            nombre="Miguel",
            apellido_paterno="Soto",
            email_principal="miguel@example.com",
        )

        marca = Marca.objects.create(
            nombre="ACURA",
        )

        submarca = SubMarca.objects.create(
            marca=marca,
            nombre="TL",
        )

        vehiculo_catalogo = VehiculoCatalogo.objects.create(
            marca=marca,
            submarca=submarca,
            anio=2015,
            version="SEDAN 3.7L AUT",
        )

        vehiculo = Vehiculo.objects.create(
            cliente=self.cliente,
            catalogo=vehiculo_catalogo,
            marca_texto="ACURA",
            submarca_texto="TL",
            modelo_anio=2015,
            version="SEDAN 3.7L AUT",
            tipo_uso=Vehiculo.TipoUso.PARTICULAR,
        )

        hoy = timezone.localdate()

        self.cotizacion = Cotizacion.objects.create(
            cliente=self.cliente,
            vehiculo=vehiculo,
            flotilla=None,
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=hoy,
            vigencia_hasta=hoy + timedelta(days=365),
            conductor_nombre="Miguel Soto",
            conductor_genero=(
                Cotizacion.GeneroConductor.MASCULINO
            ),
            conductor_edad=25,
            estado="CHIHUAHUA",
            ciudad="CHIHUAHUA",
        )

    def test_coordina_request_quote_service_y_persistencia(self):
        configuration = Mock(
            spec=ProviderConfiguration,
        )

        configuration.id = 1
        configuration.provider = "CHUBB"

        provider = Mock()
        provider.provider_code = "CHUBB"

        request = Mock(
            spec=InternalQuoteRequest,
        )

        request_service = Mock()
        request_service.build.return_value = request

        registro_esperado = Mock(
            spec=CotizacionProveedor,
        )

        provider_service = Mock()
        provider_service.quote_one.return_value = (
            registro_esperado
        )

        provider_service_factory = Mock(
            return_value=provider_service,
        )

        registro = CotizacionQuoteService.quote_one(
            cotizacion=self.cotizacion,
            configuration=configuration,
            provider=provider,
            package_code="AMPLIA",
            garage=False,
            request_json={
                "reference": self.cotizacion.folio,
            },
            request_service=request_service,
            provider_service_factory=(
                provider_service_factory
            ),
        )

        request_service.build.assert_called_once_with(
            cotizacion=self.cotizacion,
            provider_id=1,
            package_code="AMPLIA",
            garage=False,
        )

        provider_service_factory.assert_called_once()

        provider_service.quote_one.assert_called_once_with(
            cotizacion=self.cotizacion,
            provider_code="CHUBB",
            request=request,
            provider_configuration_id=1,
            request_json={
                "reference": self.cotizacion.folio,
            },
        )

        self.assertIs(
            registro,
            registro_esperado,
        )

class CotizacionChubbIntegrationTests(TestCase):

    def setUp(self):
        #
        # Configuración real del provider en BD de test
        #
        self.configuration = (
            AseguradoraConfiguracion.objects.create(
                provider="CHUBB",
                ambiente="SIT",
                ramo="AUTOS",
                nombre="Chubb Test",
                activo=True,
                prioridad=1,

                token_url="https://example.com/token",
                base_url="https://example.com/chubb",

                client_id="test-client",
                client_secret="test-secret",
                resource_id="test-resource",

                api_version="1",
                timeout=30,

                grouping_id=353991,
                rate_id=308,
                business_profile_id=7195,
                business_profile_name="BASE_TOM",
                source_application_id=23,

                supports_quote=True,
            )
        )

        settings = [
            (
                "PRODUCT_ID",
                "1",
                ProviderSetting.ValueType.INTEGER,
            ),
            (
                "AGENT_OPTION_ID",
                "91840",
                ProviderSetting.ValueType.STRING,
            ),
            (
                "CONDUIT_ID",
                "0",
                ProviderSetting.ValueType.INTEGER,
            ),
            (
                "CALCULATION_TYPE_ID",
                "2",
                ProviderSetting.ValueType.INTEGER,
            ),
            (
                "CURRENCY_ID",
                "1",
                ProviderSetting.ValueType.INTEGER,
            ),
            (
                "PAYMENT_TYPE_ID",
                "12",
                ProviderSetting.ValueType.INTEGER,
            ),
            (
                "INSURED_AMOUNT_TYPE_ID",
                "2",
                ProviderSetting.ValueType.INTEGER,
            ),
            (
                "DEDUCTIBLE_TYPE_ID",
                "1",
                ProviderSetting.ValueType.INTEGER,
            ),
            (
                "NADASC",
                "false",
                ProviderSetting.ValueType.BOOLEAN,
            ),
            (
                "GENDER_IDS",
                json.dumps({
                    "MASCULINO": 1,
                    "FEMENINO": 2,
                }),
                ProviderSetting.ValueType.JSON,
            ),
        ]

        for key, value, value_type in settings:
            ProviderSetting.objects.create(
                configuracion=self.configuration,
                key=key,
                value=value,
                value_type=value_type,
                activo=True,
            )

        #
        # Cliente
        #
        self.cliente = Cliente.objects.create(
            tipo_cliente=Cliente.TipoCliente.PERSONA,
            nombre="Miguel",
            apellido_paterno="Soto",
            email_principal="miguel@example.com",
        )

        CodigoPostal.objects.create(
            codigo_postal="32500",
            colonia="Centro",
            municipio="Juarez",
            ciudad="Ciudad Juarez",
            estado="Chihuahua",
        )

        #
        # Vehículo canónico
        #
        marca = Marca.objects.create(
            nombre="ACURA",
        )

        submarca = SubMarca.objects.create(
            marca=marca,
            nombre="TL",
        )

        self.vehiculo_catalogo = (
            VehiculoCatalogo.objects.create(
                marca=marca,
                submarca=submarca,
                anio=2015,
                version="SEDAN 3.7L AUT",
            )
        )

        self.vehiculo = Vehiculo.objects.create(
            cliente=self.cliente,
            catalogo=self.vehiculo_catalogo,
            marca_texto="ACURA",
            submarca_texto="TL",
            modelo_anio=2015,
            version="SEDAN 3.7L AUT",
            tipo_uso=Vehiculo.TipoUso.PARTICULAR,
            placas="TR543",
        )

        hoy = timezone.localdate()

        self.cotizacion = Cotizacion.objects.create(
            cliente=self.cliente,
            vehiculo=self.vehiculo,
            flotilla=None,
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=hoy,
            vigencia_hasta=hoy + timedelta(days=365),
            conductor_nombre="Miguel Soto",
            conductor_genero=(
                Cotizacion.GeneroConductor.MASCULINO
            ),
            conductor_edad=25,
            codigo_postal="32500",
            estado="CHIHUAHUA",
            ciudad="CIUDAD JUAREZ",
        )

        self._create_catalog_mappings()

    def _create_catalog_mappings(self):
        mappings = [
            (
                "VEHICLE",
                (
                    f"VEHICULO_CATALOGO_"
                    f"{self.vehiculo_catalogo.id}"
                ),
                "ACURA TL 2015",
                "01010100101",
            ),
            (
                "VEHICLE_USE",
                "PARTICULAR",
                "Particular",
                "01",
            ),
            (
                "STATE",
                "CHIHUAHUA",
                "Chihuahua",
                "5",
            ),
            (
                "MUNICIPALITY",
                "JUAREZ",
                "Juarez",
                "863",
            ),
            (
                "COVERAGE_PACKAGE",
                "AMPLIA",
                "Amplia",
                "1",
            ),
        ]

        for (
            catalog_code,
            internal_code,
            internal_name,
            external_code,
        ) in mappings:

            catalog, _ = Catalog.objects.get_or_create(
                code=catalog_code,
                defaults={
                    "name": catalog_code,
                },
            )

            item = CatalogItem.objects.create(
                catalog=catalog,
                code=internal_code,
                name=internal_name,
            )

            ProviderCatalogMapping.objects.create(
                provider=self.configuration,
                catalog=catalog,
                catalog_item=item,
                external_code=external_code,
                external_name=internal_name,
            )

    def test_flujo_chubb_completo_persiste_resultado(self):
        #
        # Respuesta que ya está validada por
        # ChubbQuoteResponseMapperTests.
        #
        response_payload = {
            "success": True,
            "messages": [],
            "responseData": {
                "quoteId": 2061062766,
                "quoteVersionId": 2061297738,
                "baseNetPremium": 27078.182,
                "baseNetPremiumWithoutDiscount": 27078.182,
                "discounts": [],
                "surchargePercentage": 0.0,
                "surchargeAmount": 0.0,
                "feeAmount": 600.0,
                "taxPercentage": None,
                "taxAmount": 4428.5091,
                "totalPremiumAmount": 32106.6911,
                "commissionPorcentage": None,
                "commissionAmount": None,
                "surchargeCommissionAmount": None,
                "items": [
                    {
                        "riskId": 2061426582,
                        "riskNumber": 1,
                        "totalPremiumAmount": 639.798,
                        "vehicle": {
                            "vehicleId": 4,
                            "vehicleKey": "01010100101",
                            "vehicleDescription": (
                                "TL SEDAN 3.7L AUT CA"
                            ),
                        },
                        "packages": [
                            {
                                "packageId": 1,
                                "quoteVersionId": 2061297738,
                                "riskId": 2061426582,
                                "selected": True,
                                "baseNetPremium": 551.55,
                                "totalPremiumAmount": 639.798,
                                "coverages": [
                                    {
                                        "coverageId": 1,
                                        "coverageName": (
                                            "DAÑOS MATERIALES"
                                        ),
                                        "coverageCustomName": "",
                                        "selected": True,
                                        "insuranceAmount": 10000.0,
                                        "deductibleValue": 4.0,
                                        "baseNetPremium": 551.55,
                                        "totalPremiumAmount": 639.798,
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
        }

        fake_auth_client = Mock()
        fake_auth_client.get_token.return_value = Mock()

        fake_http_client = Mock()

        fake_http_client.post.return_value = (
            ChubbHttpResponse(
                status_code=200,
                data=response_payload,
                headers={},
            )
        )

        def client_factory(
            *,
            ambiente,
            ramo,
            configuration_service,
        ):
            return ChubbQuoteClient(
                ambiente=ambiente,
                ramo=ramo,
                configuration_service=configuration_service,
                auth_client=fake_auth_client,
                http_client=fake_http_client,
            )

        builder = ChubbQuoteProviderBuilder(
            client_factory=client_factory,
        )

        provider = builder.build(
            ambiente="SIT",
            ramo="AUTOS",
        )

        configuration = (
            ProviderConfigurationService.get_active(
                provider="CHUBB",
                ambiente="SIT",
                ramo="AUTOS",
            )
        )

        registro = CotizacionQuoteService.quote_one(
            cotizacion=self.cotizacion,
            configuration=configuration,
            provider=provider,
            package_code="AMPLIA",
            garage=False,
            request_json={
                "folio": self.cotizacion.folio,
            },
        )

        #
        # Cabecera
        #
        registro.refresh_from_db()

        self.assertTrue(
            registro.success,
        )

        self.assertEqual(
            registro.provider_code,
            "CHUBB",
        )

        self.assertEqual(
            registro.provider_quote_id,
            "2061062766",
        )

        self.assertEqual(
            registro.provider_quote_version_id,
            "2061297738",
        )

        self.assertEqual(
            registro.total_premium,
            Decimal("32106.69"),
        )

        #
        # Riesgo
        #
        self.assertEqual(
            registro.riesgos.count(),
            1,
        )

        riesgo = registro.riesgos.get()

        self.assertEqual(
            riesgo.provider_risk_id,
            "2061426582",
        )

        self.assertEqual(
            riesgo.vehicle_key,
            "01010100101",
        )

        #
        # Paquete
        #
        self.assertEqual(
            registro.opciones.count(),
            1,
        )

        opcion = registro.opciones.get()

        self.assertEqual(
            opcion.provider_package_id,
            "1",
        )

        self.assertTrue(
            opcion.selected,
        )

        #
        # Cobertura
        #
        self.assertEqual(
            opcion.coberturas.count(),
            1,
        )

        cobertura = opcion.coberturas.get()

        self.assertEqual(
            cobertura.code,
            "1",
        )

        self.assertEqual(
            cobertura.name,
            "DAÑOS MATERIALES",
        )

        #
        # Verificamos además que el request realmente
        # llegó hasta el cliente Chubb.
        #
        fake_http_client.post.assert_called_once()

        call_kwargs = (
            fake_http_client.post.call_args.kwargs
        )

        self.assertEqual(
            call_kwargs["headers"][
                "CB-SourceApplication"
            ],
            "23",
        )

        payload = call_kwargs["payload"]

        self.assertEqual(
            payload["items"][0]["vehicle"]["vehicleKey"],
            "01010100101",
        )

        self.assertEqual(
            payload["items"][0]["vehicle"][
                "countrySubdivisionId"
            ],
            5,
        )

        self.assertEqual(
            payload["items"][0]["vehicle"][
                "municipalityId"
            ],
            863,
        )

        self.assertEqual(
            payload["items"][0]["vehicle"]["useId"],
            1,
        )

        self.assertEqual(
            payload["items"][0]["packages"][0][
                "packageId"
            ],
            1,
        )
    def test_reconciliation_persiste_quote_result_exitoso(self):
        result = QuoteResult(
            provider_code="CHUBB",
            provider_quote_id="2061090336",
            provider_quote_version_id="2061333219",
            reference=None,
            currency="MXN",
            net_premium=Decimal("16984.7275"),
            fees=Decimal("600.00"),
            taxes=Decimal("2813.5564"),
            total_premium=Decimal("20398.2839"),
            risks=(
                QuoteRiskResult(
                    provider_risk_id="2061468037",
                    risk_number=1,
                    vehicle_key="010101001001",
                    options=(
                        QuoteOption(
                            code="1",
                            provider_package_id=1,
                            name="",
                            total_premium=Decimal(
                                "20398.2839"
                            ),
                            currency="MXN",
                            selected=True,
                            coverages=(
                                QuoteCoverage(
                                    code="1",
                                    name="DAÑOS MATERIALES",
                                    insured_amount=Decimal(
                                        "314358.00"
                                    ),
                                    deductible=Decimal("7.00"),
                                    premium=Decimal(
                                        "12141.546"
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )

        registro = QuoteReconciliationService.persist_result(
            cotizacion=self.cotizacion,
            result=result,
            provider_configuration_id=88,
        )

        self.assertTrue(registro.success)

        self.assertEqual(
            registro.provider_quote_id,
            "2061090336",
        )

        self.assertEqual(
            registro.provider_quote_version_id,
            "2061333219",
        )

        self.assertEqual(
            registro.riesgos.count(),
            1,
        )
        self.assertEqual(
            registro.provider_configuration_id,
            88,
        )

        riesgo = registro.riesgos.get()

        self.assertEqual(
            riesgo.provider_risk_id,
            "2061468037",
        )

        self.assertEqual(
            registro.opciones.count(),
            1,
        )

        opcion = registro.opciones.get()

        self.assertEqual(
            opcion.provider_package_id,
            "1",
        )

        self.assertEqual(
            opcion.coberturas.count(),
            1,
        )

    def test_permite_varias_opciones_misma_aseguradora_y_producto(self):
        aseguradora = Aseguradora.objects.create(
            nombre="Chubb Test",
        )

        producto = ProductoSeguro.objects.create(
            aseguradora=aseguradora,
            nombre_producto="Autos",
            tipo_producto=ProductoSeguro.TipoProducto.AUTO,
            modelo_calculo=ProductoSeguro.ModeloCalculo.SIMPLE,
        )

        item_1 = CotizacionItem.objects.create(
            cotizacion=self.cotizacion,
            aseguradora=aseguradora,
            producto=producto,
            prima_neta="10000.00",
            derechos="600.00",
            iva="1696.00",
            prima_total="12296.00",
            provider="CHUBB",
            provider_quote_id="QUOTE-1",
            paquete_nombre="AMPLIA",
        )

        item_2 = CotizacionItem.objects.create(
            cotizacion=self.cotizacion,
            aseguradora=aseguradora,
            producto=producto,
            prima_neta="8000.00",
            derechos="600.00",
            iva="1376.00",
            prima_total="9976.00",
            provider="CHUBB",
            provider_quote_id="QUOTE-1",
            paquete_nombre="LIMITADA",
        )

        self.assertNotEqual(
            item_1.id,
            item_2.id,
        )

        self.assertEqual(
            CotizacionItem.objects.filter(
                cotizacion=self.cotizacion,
                aseguradora=aseguradora,
                producto=producto,
            ).count(),
            2,
        )

        self.assertEqual(
            {
                item_1.paquete_nombre,
                item_2.paquete_nombre,
            },
            {
                "AMPLIA",
                "LIMITADA",
            },
        )

    def test_proyecta_varias_opciones_proveedor_a_cotizacion_items(self):
        aseguradora = Aseguradora.objects.create(
            nombre="Chubb Projection Test",
        )

        producto = ProductoSeguro.objects.create(
            aseguradora=aseguradora,
            nombre_producto="Chubb Auto Test",
            tipo_producto=ProductoSeguro.TipoProducto.AUTO,
            modelo_calculo=ProductoSeguro.ModeloCalculo.SIMPLE,
        )

        resultado = CotizacionProveedor.objects.create(
            cotizacion=self.cotizacion,
            provider_code="CHUBB",
            success=True,
            elapsed_ms=100,
            provider_quote_id="QUOTE-123",
            provider_quote_version_id="VERSION-456",
            currency="MXN",
            total_premium=Decimal("20000.00"),
            response_json={
                "test": True,
            },
        )

        opcion_1 = CotizacionProveedorOpcion.objects.create(
            cotizacion_proveedor=resultado,
            code="1",
            provider_package_id="1",
            name="AMPLIA",
            total_premium=Decimal("12000.00"),
            currency="MXN",
            selected=False,
        )

        opcion_2 = CotizacionProveedorOpcion.objects.create(
            cotizacion_proveedor=resultado,
            code="2",
            provider_package_id="2",
            name="LIMITADA",
            total_premium=Decimal("8000.00"),
            currency="MXN",
            selected=False,
        )

        configuration = ProviderConfiguration(
            id=1,
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            nombre="Chubb Test",
            aseguradora_id=aseguradora.id,
            producto_seguro_id=producto.id,
        )

        items = ProviderOptionProjectionService.project(
            resultado_proveedor=resultado,
            configuration=configuration,
        )

        self.assertEqual(
            len(items),
            2,
        )

        self.assertEqual(
            CotizacionItem.objects.filter(
                cotizacion=self.cotizacion,
                aseguradora=aseguradora,
                producto=producto,
            ).count(),
            2,
        )

        item_1 = CotizacionItem.objects.get(
            provider_option=opcion_1,
        )

        item_2 = CotizacionItem.objects.get(
            provider_option=opcion_2,
        )

        self.assertEqual(
            item_1.paquete_nombre,
            "AMPLIA",
        )

        self.assertEqual(
            item_2.paquete_nombre,
            "LIMITADA",
        )

        self.assertEqual(
            item_1.prima_total,
            opcion_1.total_premium,
        )

        self.assertEqual(
            item_2.prima_total,
            opcion_2.total_premium,
        )

        self.assertEqual(
            item_1.provider,
            "CHUBB",
        )

        self.assertEqual(
            item_1.provider_quote_id,
            "QUOTE-123",
        )

        self.assertEqual(
            item_1.provider_option_id,
            opcion_1.id,
        )

        self.assertEqual(
            item_2.provider_option_id,
            opcion_2.id,
        )

    def test_portal_quote_application_service_proyecta_resultado_exitoso(
        self,
    ):
        configuration = ProviderConfiguration(
            id=1,
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            nombre="Chubb Test",
            aseguradora_id=1,
            producto_seguro_id=1,
        )

        provider = Mock()
        provider.provider_code = "CHUBB"

        resultado_proveedor = Mock(
            spec=CotizacionProveedor,
        )
        resultado_proveedor.success = True

        item_1 = Mock(
            spec=CotizacionItem,
        )

        item_2 = Mock(
            spec=CotizacionItem,
        )

        quote_service = Mock()

        quote_service.quote_one.return_value = (
            resultado_proveedor
        )

        projection_service = Mock()

        projection_service.project.return_value = (
            item_1,
            item_2,
        )

        items = PortalQuoteApplicationService.quote_one(
            cotizacion=self.cotizacion,
            configuration=configuration,
            provider=provider,
            package_code="AMPLIA",
            garage=False,
            quote_service=quote_service,
            projection_service=projection_service,
        )

        quote_service.quote_one.assert_called_once_with(
            cotizacion=self.cotizacion,
            configuration=configuration,
            provider=provider,
            package_code="AMPLIA",
            garage=False,
        )

        projection_service.project.assert_called_once_with(
            resultado_proveedor=resultado_proveedor,
            configuration=configuration,
        )

        self.assertEqual(
            items,
            (
                item_1,
                item_2,
            ),
        )

    def test_portal_quote_application_service_no_proyecta_resultado_fallido(
        self,
    ):
        configuration = ProviderConfiguration(
            id=1,
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            nombre="Chubb Test",
            aseguradora_id=1,
            producto_seguro_id=1,
        )

        provider = Mock()
        provider.provider_code = "CHUBB"

        resultado_proveedor = Mock(
            spec=CotizacionProveedor,
        )
        resultado_proveedor.success = False

        quote_service = Mock()
        quote_service.quote_one.return_value = (
            resultado_proveedor
        )

        projection_service = Mock()

        items = PortalQuoteApplicationService.quote_one(
            cotizacion=self.cotizacion,
            configuration=configuration,
            provider=provider,
            package_code="AMPLIA",
            garage=False,
            quote_service=quote_service,
            projection_service=projection_service,
        )

        self.assertEqual(
            items,
            (),
        )

        projection_service.project.assert_not_called()

    def test_multi_provider_quote_agrega_opciones_de_providers_activos(
        self,
    ):
        configuration_1 = ProviderConfiguration(
            id=1,
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            nombre="Chubb Test",
            aseguradora_id=1,
            producto_seguro_id=1,
            settings={
                "GARAGE_USE": False,
            },
        )

        configuration_2 = ProviderConfiguration(
            id=2,
            provider="AXA",
            ambiente="SIT",
            ramo="AUTOS",
            nombre="AXA Test",
            aseguradora_id=2,
            producto_seguro_id=2,
            settings={
                "GARAGE_USE": False,
            },
        )

        configuration_service = Mock()

        configuration_service.list_active_for_quote.return_value = (
            configuration_1,
            configuration_2,
        )

        provider_1 = Mock()
        provider_1.provider_code = "CHUBB"

        provider_2 = Mock()
        provider_2.provider_code = "AXA"

        resolver = Mock()

        resolver.build.side_effect = (
            provider_1,
            provider_2,
        )

        resolver_factory = Mock(
            return_value=resolver,
        )

        package_service = Mock()

        package_service.list_internal_codes_for_provider.side_effect = (
            (
                "AMPLIA",
                "LIMITADA",
            ),
            (
                "AMPLIA",
            ),
        )

        item_1 = Mock(
            spec=CotizacionItem,
        )

        item_2 = Mock(
            spec=CotizacionItem,
        )

        item_3 = Mock(
            spec=CotizacionItem,
        )

        application_service = Mock()

        application_service.quote_one.side_effect = (
            (
                item_1,
            ),
            (
                item_2,
            ),
            (
                item_3,
            ),
        )

        items = PortalMultiProviderQuoteService.quote(
            cotizacion=self.cotizacion,
            ambiente="SIT",
            ramo="AUTOS",
            configuration_service=configuration_service,
            package_service=package_service,
            resolver_factory=resolver_factory,
            application_service=application_service,
        )

        self.assertEqual(
            items,
            (
                item_1,
                item_2,
                item_3,
            ),
        )

        configuration_service.list_active_for_quote.assert_called_once_with(
            ambiente="SIT",
            ramo="AUTOS",
        )

        self.assertEqual(
            resolver.build.call_count,
            2,
        )

        self.assertEqual(
            package_service
            .list_internal_codes_for_provider
            .call_count,
            2,
        )

        self.assertEqual(
            [
                call.kwargs["garage"]
                for call in application_service.quote_one.call_args_list
            ],
            [
                False,
                False,
                False,
            ],
        )

        self.assertEqual(
            [
                call.kwargs["provider_id"]
                for call in (
                    package_service
                    .list_internal_codes_for_provider
                    .call_args_list
                )
            ],
            [
                1,
                2,
            ],
        )

        self.assertEqual(
            application_service.quote_one.call_count,
            3,
        )

        self.assertEqual(
            [
                call.kwargs["package_code"]
                for call in (
                    application_service
                    .quote_one
                    .call_args_list
                )
            ],
            [
                "AMPLIA",
                "LIMITADA",
                "AMPLIA",
            ],
        )

    def test_multi_provider_quote_sin_providers_activos_regresa_vacio(
        self,
    ):
        configuration_service = Mock()

        configuration_service.list_active_for_quote.return_value = ()

        resolver = Mock()

        resolver_factory = Mock(
            return_value=resolver,
        )

        package_service = Mock()

        application_service = Mock()

        items = PortalMultiProviderQuoteService.quote(
            cotizacion=self.cotizacion,
            ambiente="SIT",
            ramo="AUTOS",
            configuration_service=configuration_service,
            package_service=package_service,
            resolver_factory=resolver_factory,
            application_service=application_service,
        )

        self.assertEqual(
            items,
            (),
        )

        resolver.build.assert_not_called()

        (
            package_service
            .list_internal_codes_for_provider
            .assert_not_called()
        )

        application_service.quote_one.assert_not_called()

    def test_cotizacion_guarda_datos_completos_del_conductor(
        self,
    ):
        self.cotizacion.conductor_nombre = "Miguel"
        self.cotizacion.conductor_apellido_paterno = "Soto"
        self.cotizacion.conductor_apellido_materno = "Lopez"
        self.cotizacion.conductor_rfc = "SOLM800101ABC"
        self.cotizacion.conductor_fecha_nacimiento = date(
            1980,
            1,
            1,
        )

        self.cotizacion.save()

        self.cotizacion.refresh_from_db()

        self.assertEqual(
            self.cotizacion.conductor_apellido_paterno,
            "Soto",
        )

        self.assertEqual(
            self.cotizacion.conductor_apellido_materno,
            "Lopez",
        )

        self.assertEqual(
            self.cotizacion.conductor_rfc,
            "SOLM800101ABC",
        )

        self.assertEqual(
            self.cotizacion.conductor_fecha_nacimiento,
            date(1980, 1, 1),
        )

class PersonRequestServiceTests(TestCase):

    def setUp(self):
        self.direccion = Direccion.objects.create(
            calle="Av. Tecnologico",
            num_ext="1234",
            num_int="",
            colonia="Tecnologico",
            ciudad="Ciudad Juarez",
            estado="Chihuahua",
            cp="32500",
        )

        self.cliente = Cliente.objects.create(
            tipo_cliente=Cliente.TipoCliente.PERSONA,
            nombre="Miguel",
            apellido_paterno="Soto",
            apellido_materno="Lopez",
            rfc="SOLM800101ABC",
            curp="SOLM800101HCHXXX00",
            fecha_nacimiento=date(1980, 1, 1),
            genero=Cliente.Genero.MASCULINO,
            email_principal="miguel@example.com",
            telefono_principal="6561234567",
            direccion_contacto=self.direccion,
        )

        marca = Marca.objects.create(
            nombre="Nissan",
        )

        submarca = SubMarca.objects.create(
            marca=marca,
            nombre="Versa",
        )

        catalogo = VehiculoCatalogo.objects.create(
            marca=marca,
            submarca=submarca,
            anio=2024,
            version="Advance",
        )

        vehiculo = Vehiculo.objects.create(
            cliente=self.cliente,
            catalogo=catalogo,
            marca_texto="Nissan",
            submarca_texto="Versa",
            modelo_anio=2024,
            version="Advance",
        )

        hoy = timezone.localdate()

        self.cotizacion = Cotizacion.objects.create(
            cliente=self.cliente,
            vehiculo=vehiculo,
            flotilla=None,
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=hoy,
            vigencia_hasta=hoy + timedelta(days=365),
            conductor_nombre="Miguel",
            conductor_apellido_paterno="Soto",
            conductor_apellido_materno="Lopez",
            conductor_rfc="SOLM800101ABC",
            conductor_fecha_nacimiento=date(1980, 1, 1),
            conductor_genero=(
                Cotizacion.GeneroConductor.MASCULINO
            ),
            conductor_edad=45,
        )

    def test_construye_person_request(self):
        request = PersonRequestService.build(
            cotizacion=self.cotizacion,
        )

        self.assertEqual(
            request.first_name,
            "Miguel",
        )

        self.assertEqual(
            request.paternal_surname,
            "Soto",
        )

        self.assertEqual(
            request.maternal_surname,
            "Lopez",
        )

        self.assertEqual(
            request.rfc,
            "SOLM800101ABC",
        )

        self.assertEqual(
            request.curp,
            "SOLM800101HCHXXX00",
        )

        self.assertEqual(
            request.gender,
            "MASCULINO",
        )

        self.assertEqual(
            request.email,
            "miguel@example.com",
        )

        self.assertEqual(
            request.phone,
            "6561234567",
        )

        self.assertEqual(
            request.address.neighborhood_code,
            "32500_TECNOLOGICO",
        )

        self.assertIsNone(
            request.address.interior_number,
        )

    def test_rechaza_cliente_sin_direccion_contacto(self):
        self.cliente.direccion_contacto = None
        self.cliente.save(
            update_fields=["direccion_contacto"]
        )

        with self.assertRaisesRegex(
            ValueError,
            "dirección de contacto",
        ):
            PersonRequestService.build(
                cotizacion=self.cotizacion,
            )

    def test_rechaza_cliente_sin_curp(self):
        self.cliente.curp = ""
        self.cliente.save(
            update_fields=["curp"]
        )

        with self.assertRaisesRegex(
            ValueError,
            "CURP",
        ):
            PersonRequestService.build(
                cotizacion=self.cotizacion,
            )

    def test_rechaza_cotizacion_sin_rfc(self):
        self.cotizacion.conductor_rfc = ""
        self.cotizacion.save(
            update_fields=["conductor_rfc"]
        )

        with self.assertRaisesRegex(
            ValueError,
            "RFC",
        ):
            PersonRequestService.build(
                cotizacion=self.cotizacion,
            )

class CotizacionPersonServiceTests(TestCase):

    def setUp(self):
        self.cliente = Cliente.objects.create(
            tipo_cliente=Cliente.TipoCliente.PERSONA,
            nombre="Miguel",
            apellido_paterno="Soto",
            email_principal="miguel@example.com",
        )

        marca = Marca.objects.create(
            nombre="ACURA",
        )

        submarca = SubMarca.objects.create(
            marca=marca,
            nombre="TL",
        )

        vehiculo_catalogo = VehiculoCatalogo.objects.create(
            marca=marca,
            submarca=submarca,
            anio=2015,
            version="SEDAN 3.7L AUT",
        )

        vehiculo = Vehiculo.objects.create(
            cliente=self.cliente,
            catalogo=vehiculo_catalogo,
            marca_texto="ACURA",
            submarca_texto="TL",
            modelo_anio=2015,
            version="SEDAN 3.7L AUT",
            tipo_uso=Vehiculo.TipoUso.PARTICULAR,
        )
        CodigoPostal.objects.create(
            codigo_postal="32500",
            colonia="Centro",
            municipio="Juarez",
            ciudad="Ciudad Juarez",
            estado="Chihuahua",
        )

        hoy = timezone.localdate()

        self.cotizacion = Cotizacion.objects.create(
            cliente=self.cliente,
            vehiculo=vehiculo,
            flotilla=None,
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=hoy,
            vigencia_hasta=hoy + timedelta(days=365),
            conductor_nombre="Miguel",
            conductor_apellido_paterno="Soto",
            conductor_genero=(
                Cotizacion.GeneroConductor.MASCULINO
            ),
            conductor_edad=25,
            estado="CHIHUAHUA",
            ciudad="CIUDAD JUAREZ",
            codigo_postal="32500",
        )

    def test_coordina_request_y_person_service(self):
        configuration = Mock(
            spec=ProviderConfiguration,
        )
        configuration.provider = "CHUBB"

        provider = Mock()
        provider.provider_code = "CHUBB"

        request = Mock(
            spec=PersonRequest,
        )

        request_service = Mock()
        request_service.build.return_value = request

        resultado_esperado = PersonResult(
            provider_code="CHUBB",
            provider_tran_id="57482667",
            provider_person_id="18683522",
            provider_address_id="1410484013",
            raw_response={
                "success": True,
            },
        )

        person_service = Mock()
        person_service.create_one.return_value = resultado_esperado

        person_service_factory = Mock(
            return_value=person_service,
        )

        resultado = CotizacionPersonService.create_one(
            cotizacion=self.cotizacion,
            configuration=configuration,
            provider=provider,
            request_service=request_service,
            person_service_factory=(
                person_service_factory
            ),
        )

        request_service.build.assert_called_once_with(
            cotizacion=self.cotizacion,
        )

        person_service_factory.assert_called_once_with(
            providers=[provider],
        )

        person_service.create_one.assert_called_once_with(
            provider_code="CHUBB",
            request=request,
        )

        self.assertIs(
            resultado,
            resultado_esperado,
        )

    def test_rechaza_provider_que_no_corresponde_a_configuracion(
        self,
    ):
        configuration = Mock(
            spec=ProviderConfiguration,
        )
        configuration.provider = "CHUBB"

        provider = Mock()
        provider.provider_code = "OTRO"

        request_service = Mock()
        person_service_factory = Mock()

        with self.assertRaisesRegex(
            ValueError,
            "no corresponde",
        ):
            CotizacionPersonService.create_one(
                cotizacion=self.cotizacion,
                configuration=configuration,
                provider=provider,
                request_service=request_service,
                person_service_factory=(
                    person_service_factory
                ),
            )

        request_service.build.assert_not_called()
        person_service_factory.assert_not_called()

    def test_create_one_persiste_person_result(self):
        cliente = Cliente.objects.create(
            tipo_cliente=Cliente.TipoCliente.PERSONA,
            nombre="Miguel",
            email_principal="miguel@example.com",
        )

        vehiculo = Vehiculo.objects.create(
            cliente=cliente,
            marca_texto="Nissan",
            submarca_texto="Versa",
            modelo_anio=2024,
        )

        hoy = timezone.localdate()

        cotizacion = Cotizacion.objects.create(
            cliente=cliente,
            vehiculo=vehiculo,
            flotilla=None,
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=hoy,
            vigencia_hasta=hoy + timedelta(days=365),
        )

        configuration = Mock(
            spec=ProviderConfiguration,
        )
        configuration.provider = "CHUBB"

        provider = Mock()
        provider.provider_code = "CHUBB"

        request = Mock(
            spec=PersonRequest,
        )

        result = PersonResult(
            provider_code="CHUBB",
            provider_tran_id="57482667",
            provider_person_id="18683522",
            provider_address_id="1410484013",
            raw_response={
                "success": True,
            },
        )

        request_service = Mock()
        request_service.build.return_value = request

        person_service = Mock()
        person_service.create_one.return_value = result

        person_service_factory = Mock(
            return_value=person_service,
        )

        returned = CotizacionPersonService.create_one(
            cotizacion=cotizacion,
            configuration=configuration,
            provider=provider,
            request_service=request_service,
            person_service_factory=person_service_factory,
        )

        persona = CotizacionProveedorPersona.objects.get(
            cotizacion=cotizacion,
            provider_code="CHUBB",
            rol=CotizacionProveedorPersona.Rol.ASEGURADO,
        )

        self.assertEqual(
            returned,
            result,
        )
        self.assertEqual(
            persona.provider_tran_id,
            "57482667",
        )
        self.assertEqual(
            persona.provider_person_id,
            "18683522",
        )
        self.assertEqual(
            persona.provider_address_id,
            "1410484013",
        )


class PortalPersonApplicationServiceTests(TestCase):

    def setUp(self):
        self.cliente = Cliente.objects.create(
            tipo_cliente=Cliente.TipoCliente.PERSONA,
            nombre="Miguel",
            apellido_paterno="Soto",
            email_principal="miguel@example.com",
        )

        marca = Marca.objects.create(
            nombre="ACURA",
        )

        submarca = SubMarca.objects.create(
            marca=marca,
            nombre="TL",
        )

        vehiculo_catalogo = VehiculoCatalogo.objects.create(
            marca=marca,
            submarca=submarca,
            anio=2015,
            version="SEDAN 3.7L AUT",
        )

        vehiculo = Vehiculo.objects.create(
            cliente=self.cliente,
            catalogo=vehiculo_catalogo,
            marca_texto="ACURA",
            submarca_texto="TL",
            modelo_anio=2015,
            version="SEDAN 3.7L AUT",
            tipo_uso=Vehiculo.TipoUso.PARTICULAR,
        )

        hoy = timezone.localdate()

        self.cotizacion = Cotizacion.objects.create(
            cliente=self.cliente,
            vehiculo=vehiculo,
            flotilla=None,
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=hoy,
            vigencia_hasta=hoy + timedelta(days=365),
            conductor_nombre="Miguel",
            conductor_apellido_paterno="Soto",
            conductor_genero=(
                Cotizacion.GeneroConductor.MASCULINO
            ),
            conductor_edad=25,
            estado="CHIHUAHUA",
            ciudad="CHIHUAHUA",
        )

    def test_coordina_configuracion_resolver_y_person_service(
        self,
    ):
        configuration = Mock(
            spec=ProviderConfiguration,
        )
        configuration.provider = "CHUBB"
        configuration.ambiente = "SIT"
        configuration.ramo = "AUTOS"

        configuration_service = Mock()
        configuration_service.get_active.return_value = (
            configuration
        )

        provider = Mock()
        provider.provider_code = "CHUBB"

        resolver = Mock()
        resolver.build.return_value = provider

        resolver_factory = Mock(
            return_value=resolver
        )

        resultado_esperado = Mock(
            spec=PersonResult,
        )

        person_service = Mock()
        person_service.create_one.return_value = (
            resultado_esperado
        )

        resultado = (
            PortalPersonApplicationService.create_one(
                cotizacion=self.cotizacion,
                provider_code="CHUBB",
                ambiente="SIT",
                ramo="AUTOS",
                configuration_service=(
                    configuration_service
                ),
                resolver_factory=resolver_factory,
                person_service=person_service,
            )
        )

        configuration_service.get_active.assert_called_once_with(
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
        )

        resolver_factory.assert_called_once_with()

        resolver.build.assert_called_once_with(
            provider_code="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
        )

        person_service.create_one.assert_called_once_with(
            cotizacion=self.cotizacion,
            configuration=configuration,
            provider=provider,
        )

        self.assertIs(
            resultado,
            resultado_esperado,
        )

    def test_rechaza_provider_code_vacio(self):
        configuration_service = Mock()
        resolver_factory = Mock()
        person_service = Mock()

        with self.assertRaisesRegex(
            ValueError,
            "provider_code",
        ):
            PortalPersonApplicationService.create_one(
                cotizacion=self.cotizacion,
                provider_code=" ",
                ambiente="SIT",
                ramo="AUTOS",
                configuration_service=(
                    configuration_service
                ),
                resolver_factory=resolver_factory,
                person_service=person_service,
            )

        configuration_service.get_active.assert_not_called()
        resolver_factory.assert_not_called()

    def test_rechaza_ambiente_vacio(self):
        configuration_service = Mock()
        resolver_factory = Mock()

        with self.assertRaisesRegex(
            ValueError,
            "ambiente",
        ):
            PortalPersonApplicationService.create_one(
                cotizacion=self.cotizacion,
                provider_code="CHUBB",
                ambiente="",
                ramo="AUTOS",
                configuration_service=(
                    configuration_service
                ),
                resolver_factory=resolver_factory,
            )

        configuration_service.get_active.assert_not_called()
        resolver_factory.assert_not_called()

    def test_rechaza_ramo_vacio(self):
        configuration_service = Mock()
        resolver_factory = Mock()

        with self.assertRaisesRegex(
            ValueError,
            "ramo",
        ):
            PortalPersonApplicationService.create_one(
                cotizacion=self.cotizacion,
                provider_code="CHUBB",
                ambiente="SIT",
                ramo=" ",
                configuration_service=(
                    configuration_service
                ),
                resolver_factory=resolver_factory,
            )

        configuration_service.get_active.assert_not_called()
        resolver_factory.assert_not_called()


class CotizacionProveedorPersonaTests(TestCase):

    def test_guarda_identidad_externa_de_persona(self):
        cliente = Cliente.objects.create(
            tipo_cliente=Cliente.TipoCliente.PERSONA,
            nombre="Miguel",
            email_principal="miguel@example.com",
        )

        vehiculo = Vehiculo.objects.create(
            cliente=cliente,
            marca_texto="Nissan",
            submarca_texto="Versa",
            modelo_anio=2024,
        )

        hoy = timezone.localdate()

        cotizacion = Cotizacion.objects.create(
            cliente=cliente,
            vehiculo=vehiculo,
            flotilla=None,
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=hoy,
            vigencia_hasta=hoy + timedelta(days=365),
        )

        persona = CotizacionProveedorPersona.objects.create(
            cotizacion=cotizacion,
            provider_code="CHUBB",
            rol=CotizacionProveedorPersona.Rol.ASEGURADO,
            provider_tran_id="57482667",
            provider_person_id="18683522",
            provider_address_id="1410484013",
            raw_response={
                "success": True,
            },
        )

        persona.refresh_from_db()

        self.assertEqual(
            persona.cotizacion,
            cotizacion,
        )
        self.assertEqual(
            persona.provider_code,
            "CHUBB",
        )
        self.assertEqual(
            persona.rol,
            CotizacionProveedorPersona.Rol.ASEGURADO,
        )
        self.assertEqual(
            persona.provider_tran_id,
            "57482667",
        )
        self.assertEqual(
            persona.provider_person_id,
            "18683522",
        )
        self.assertEqual(
            persona.provider_address_id,
            "1410484013",
        )
        self.assertEqual(
            persona.raw_response,
            {
                "success": True,
            },
        )

    def test_no_permite_duplicar_rol_por_cotizacion_y_provider(self):
        cliente = Cliente.objects.create(
            tipo_cliente=Cliente.TipoCliente.PERSONA,
            nombre="Miguel",
            email_principal="miguel@example.com",
        )

        vehiculo = Vehiculo.objects.create(
            cliente=cliente,
            marca_texto="Nissan",
            submarca_texto="Versa",
            modelo_anio=2024,
        )

        hoy = timezone.localdate()

        cotizacion = Cotizacion.objects.create(
            cliente=cliente,
            vehiculo=vehiculo,
            flotilla=None,
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=hoy,
            vigencia_hasta=hoy + timedelta(days=365),
        )

        datos = {
            "cotizacion": cotizacion,
            "provider_code": "CHUBB",
            "rol": CotizacionProveedorPersona.Rol.ASEGURADO,
            "provider_tran_id": "57482667",
            "provider_person_id": "18683522",
            "provider_address_id": "1410484013",
        }

        CotizacionProveedorPersona.objects.create(
            **datos,
        )

        with self.assertRaises(IntegrityError):
            CotizacionProveedorPersona.objects.create(
                **datos,
            )


class PersonPersistenceServiceTests(TestCase):

    def setUp(self):
        self.cliente = Cliente.objects.create(
            tipo_cliente=Cliente.TipoCliente.PERSONA,
            nombre="Miguel",
            email_principal="miguel@example.com",
        )

        self.vehiculo = Vehiculo.objects.create(
            cliente=self.cliente,
            marca_texto="Nissan",
            submarca_texto="Versa",
            modelo_anio=2024,
        )

        hoy = timezone.localdate()

        self.cotizacion = Cotizacion.objects.create(
            cliente=self.cliente,
            vehiculo=self.vehiculo,
            flotilla=None,
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=hoy,
            vigencia_hasta=hoy + timedelta(days=365),
        )

    def test_persiste_person_result(self):
        result = PersonResult(
            provider_code="CHUBB",
            provider_tran_id="57482667",
            provider_person_id="18683522",
            provider_address_id="1410484013",
            raw_response={
                "success": True,
            },
        )

        persona = PersonPersistenceService.save(
            cotizacion=self.cotizacion,
            person_result=result,
            rol=CotizacionProveedorPersona.Rol.ASEGURADO,
        )

        self.assertEqual(
            persona.cotizacion,
            self.cotizacion,
        )
        self.assertEqual(
            persona.provider_code,
            "CHUBB",
        )
        self.assertEqual(
            persona.provider_tran_id,
            "57482667",
        )
        self.assertEqual(
            persona.provider_person_id,
            "18683522",
        )
        self.assertEqual(
            persona.provider_address_id,
            "1410484013",
        )

    def test_actualiza_persona_existente_mismo_provider_y_rol(self):
        primer_resultado = PersonResult(
            provider_code="CHUBB",
            provider_tran_id="100",
            provider_person_id="200",
            provider_address_id="300",
            raw_response={
                "version": 1,
            },
        )

        segundo_resultado = PersonResult(
            provider_code="CHUBB",
            provider_tran_id="101",
            provider_person_id="201",
            provider_address_id="301",
            raw_response={
                "version": 2,
            },
        )

        PersonPersistenceService.save(
            cotizacion=self.cotizacion,
            person_result=primer_resultado,
            rol=CotizacionProveedorPersona.Rol.ASEGURADO,
        )

        persona = PersonPersistenceService.save(
            cotizacion=self.cotizacion,
            person_result=segundo_resultado,
            rol=CotizacionProveedorPersona.Rol.ASEGURADO,
        )

        self.assertEqual(
            CotizacionProveedorPersona.objects.count(),
            1,
        )
        self.assertEqual(
            persona.provider_tran_id,
            "101",
        )
        self.assertEqual(
            persona.provider_person_id,
            "201",
        )
        self.assertEqual(
            persona.provider_address_id,
            "301",
        )
        self.assertEqual(
            persona.raw_response,
            {
                "version": 2,
            },
        )

class IssueRequestServiceTests(TestCase):

    def setUp(self):
        self.cliente = Cliente.objects.create(
            tipo_cliente=Cliente.TipoCliente.PERSONA,
            nombre="Miguel",
            email_principal="miguel@example.com",
        )

        self.vehiculo = Vehiculo.objects.create(
            cliente=self.cliente,
            marca_texto="ACURA",
            submarca_texto="TL",
            modelo_anio=2015,
            version="SEDAN 3.7L AUT",
            placas="TR543",
            vin="JH4KA3277KC007500",
        )

        hoy = timezone.localdate()

        self.cotizacion = Cotizacion.objects.create(
            cliente=self.cliente,
            vehiculo=self.vehiculo,
            flotilla=None,
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=hoy,
            vigencia_hasta=hoy + timedelta(days=365),
            forma_pago_preferida="CONTADO",
        )

        self.provider_quote = (
            CotizacionProveedor.objects.create(
                cotizacion=self.cotizacion,
                provider_code="CHUBB",
                provider_configuration_id=77,
                success=True,
                elapsed_ms=100,
                provider_quote_id="2061261215",
                provider_quote_version_id="2061499999",
                currency="MXN",
                total_premium=Decimal("41582.77"),
            )
        )

        self.provider_risk = (
            CotizacionProveedorRiesgo.objects.create(
                cotizacion_proveedor=self.provider_quote,
                provider_risk_id="2061426582",
                risk_number=1,
                vehicle_key="01010100101",
            )
        )

        self.provider_option = (
            CotizacionProveedorOpcion.objects.create(
                cotizacion_proveedor=self.provider_quote,
                riesgo=self.provider_risk,
                code="1",
                provider_package_id="1",
                name="AMPLIA",
                total_premium=Decimal("41582.77"),
                currency="MXN",
                selected=True,
            )
        )

        aseguradora = Aseguradora.objects.create(
            nombre="Chubb Issue Test",
        )

        producto = ProductoSeguro.objects.create(
            aseguradora=aseguradora,
            nombre_producto="Autos",
            tipo_producto=ProductoSeguro.TipoProducto.AUTO,
            modelo_calculo=ProductoSeguro.ModeloCalculo.SIMPLE,
        )

        self.item = CotizacionItem.objects.create(
            cotizacion=self.cotizacion,
            aseguradora=aseguradora,
            producto=producto,
            provider_option=self.provider_option,
            prima_neta=Decimal("35247.21"),
            derechos=Decimal("600.00"),
            iva=Decimal("5735.56"),
            prima_total=Decimal("41582.77"),
            forma_pago="CONTADO",
            provider="CHUBB",
            provider_quote_id="2061261215",
            paquete_nombre="AMPLIA",
        )

        self.person = (
            CotizacionProveedorPersona.objects.create(
                cotizacion=self.cotizacion,
                provider_code="CHUBB",
                rol=(
                    CotizacionProveedorPersona
                    .Rol
                    .ASEGURADO
                ),
                provider_tran_id="57482667",
                provider_person_id="18683522",
                provider_address_id="1410484013",
                raw_response={
                    "success": True,
                },
            )
        )

    def test_build_creates_internal_issue_request_without_invoice(
        self,
    ):
        result = IssueRequestService.build(
            cotizacion_item=self.item,
        )

        self.assertEqual(
            result.provider_quote_id,
            self.provider_quote.provider_quote_id,
        )
        self.assertEqual(
            result.provider_quote_version_id,
            self.provider_quote.provider_quote_version_id,
        )

        self.assertEqual(
            result.payment_method_code,
            "CONTADO",
        )

        self.assertEqual(
            result.insured.provider_tran_id,
            self.person.provider_tran_id,
        )
        self.assertEqual(
            result.insured.provider_person_id,
            self.person.provider_person_id,
        )
        self.assertEqual(
            result.insured.provider_address_id,
            self.person.provider_address_id,
        )

        self.assertEqual(
            len(result.risks),
            1,
        )

        risk = result.risks[0]

        self.assertEqual(
            risk.risk_number,
            self.provider_risk.risk_number,
        )
        self.assertEqual(
            risk.provider_package_id,
            self.provider_option.provider_package_id,
        )
        self.assertEqual(
            risk.vin,
            self.vehiculo.vin,
        )
        self.assertEqual(
            risk.plate,
            self.vehiculo.placas,
        )
        self.assertEqual(
            risk.reference,
            self.cotizacion.folio,
        )

        self.assertEqual(
            risk.owner,
            result.insured,
        )
        self.assertEqual(
            risk.beneficiary,
            result.insured,
        )

        self.assertIsNone(
            result.invoice,
        )

    def test_build_rejects_missing_vin(self):
        self.vehiculo.vin = ""
        self.vehiculo.save(
            update_fields=["vin"],
        )

        with self.assertRaisesMessage(
            ValueError,
            "El vehículo no tiene VIN.",
        ):
            IssueRequestService.build(
                cotizacion_item=self.item,
            )

    def test_build_rejects_missing_provider_person(self):
        self.person.delete()

        with self.assertRaisesMessage(
            ValueError,
            "No existe la persona persistida para emisión",
        ):
            IssueRequestService.build(
                cotizacion_item=self.item,
            )

    def test_build_rejects_missing_provider_package_id(self):
        self.provider_option.provider_package_id = ""
        self.provider_option.save(
            update_fields=["provider_package_id"],
        )

        with self.assertRaisesMessage(
            ValueError,
            "La opción no tiene provider_package_id.",
        ):
            IssueRequestService.build(
                cotizacion_item=self.item,
            )

class PortalIssueApplicationServiceTests(TestCase):

    def setUp(self):
        self.cliente = Cliente.objects.create(
            tipo_cliente=Cliente.TipoCliente.PERSONA,
            nombre="Miguel",
            email_principal="miguel@example.com",
        )

        self.vehiculo = Vehiculo.objects.create(
            cliente=self.cliente,
            marca_texto="ACURA",
            submarca_texto="TL",
            modelo_anio=2015,
            version="SEDAN 3.7L AUT",
            placas="TR543",
            vin="JH4KA3277KC007500",
        )

        hoy = timezone.localdate()

        self.cotizacion = Cotizacion.objects.create(
            cliente=self.cliente,
            vehiculo=self.vehiculo,
            flotilla=None,
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=hoy,
            vigencia_hasta=hoy + timedelta(days=365),
            forma_pago_preferida="CONTADO",
        )

        self.provider_quote = (
            CotizacionProveedor.objects.create(
                cotizacion=self.cotizacion,
                provider_code="CHUBB",
                provider_configuration_id=77,
                success=True,
                elapsed_ms=100,
                provider_quote_id="2061261215",
                provider_quote_version_id="2061499999",
                currency="MXN",
                total_premium=Decimal("41582.77"),
            )
        )

        self.provider_risk = (
            CotizacionProveedorRiesgo.objects.create(
                cotizacion_proveedor=self.provider_quote,
                provider_risk_id="2061426582",
                risk_number=1,
                vehicle_key="01010100101",
            )
        )

        self.provider_option = (
            CotizacionProveedorOpcion.objects.create(
                cotizacion_proveedor=self.provider_quote,
                riesgo=self.provider_risk,
                code="1",
                provider_package_id="1",
                name="AMPLIA",
                total_premium=Decimal("41582.77"),
                currency="MXN",
                selected=True,
            )
        )

        self.aseguradora = Aseguradora.objects.create(
            nombre="Chubb Issue Application Test",
        )

        self.producto = ProductoSeguro.objects.create(
            aseguradora=self.aseguradora,
            nombre_producto="Autos",
            tipo_producto=ProductoSeguro.TipoProducto.AUTO,
            modelo_calculo=ProductoSeguro.ModeloCalculo.SIMPLE,
        )

        self.item = CotizacionItem.objects.create(
            cotizacion=self.cotizacion,
            aseguradora=self.aseguradora,
            producto=self.producto,
            provider_option=self.provider_option,
            prima_neta=Decimal("35247.21"),
            derechos=Decimal("600.00"),
            iva=Decimal("5735.56"),
            prima_total=Decimal("41582.77"),
            forma_pago="CONTADO",
            provider="CHUBB",
            provider_quote_id="2061261215",
            paquete_nombre="AMPLIA",
        )

        self.person = (
            CotizacionProveedorPersona.objects.create(
                cotizacion=self.cotizacion,
                provider_code="CHUBB",
                rol=(
                    CotizacionProveedorPersona
                    .Rol
                    .ASEGURADO
                ),
                provider_tran_id="57482667",
                provider_person_id="18683522",
                provider_address_id="1410484013",
                raw_response={
                    "success": True,
                },
            )
        )

        self.configuration_service = Mock()

        self.configuration = Mock()
        self.configuration.provider = "CHUBB"
        self.configuration.ambiente = "SIT"
        self.configuration.ramo = "AUTOS"

        self.configuration_service.get_by_id.return_value = (
            self.configuration
        )

        self.resolver_factory = Mock()
        self.resolver = Mock()

        self.provider = Mock()
        self.provider.provider_code = "CHUBB"

        self.resolver_factory.return_value = self.resolver
        self.resolver.build.return_value = self.provider

        self.request_service = Mock()
        self.request = Mock()

        self.request_service.build.return_value = (
            self.request
        )

        self.issue_service_factory = Mock()
        self.issue_service = Mock()

        self.issue_service_factory.return_value = (
            self.issue_service
        )

        self.persistence_service = Mock()
        self.persisted_policy = Mock()

        self.persistence_service.save.return_value = (
            self.persisted_policy
        )
        self.attempt_persistence_service = Mock()

    def test_issue_one_coordinates_complete_issue_flow(
        self,
    ):
        expected_result = Mock()

        attempt = Mock()
        attempt.success = True
        attempt.result = expected_result
        attempt.error = None

        self.issue_service.issue_one.return_value = (
            attempt
        )

        result = PortalIssueApplicationService.issue_one(
            cotizacion_item=self.item,
            configuration_service=(
                self.configuration_service
            ),
            resolver_factory=self.resolver_factory,
            request_service=self.request_service,
            issue_service_factory=(
                self.issue_service_factory
            ),
            persistence_service=self.persistence_service,
            attempt_persistence_service=(
                self.attempt_persistence_service
            ),            
        )

        self.configuration_service.get_by_id.assert_called_once_with(
            77,
        )

        self.resolver_factory.assert_called_once_with(
            configuration_service=(
                self.configuration_service
            ),
        )

        self.resolver.build.assert_called_once_with(
            provider_code="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            configuration=self.configuration,
        )

        self.request_service.build.assert_called_once_with(
            cotizacion_item=self.item,
        )

        self.issue_service_factory.assert_called_once_with(
            providers=[self.provider],
        )

        self.issue_service.issue_one.assert_called_once_with(
            "CHUBB",
            self.request,
        )

        self.attempt_persistence_service.save.assert_called_once_with(
            cotizacion_item=self.item,
            cotizacion_proveedor=self.provider_quote,
            provider_configuration_id=77,
            attempt=attempt,
        )

        self.persistence_service.save.assert_called_once_with(
            cotizacion_item=self.item,
            issue_result=expected_result,
        )

        self.assertIs(
            result,
            self.persisted_policy,
        )


    def test_issue_one_raises_when_issue_attempt_fails(
        self,
    ):
        error = Mock()
        error.message = "Error de emisión."
        error.error_type = "ProviderInvalidResponseError"
        error.retryable = False
        error.outcome_unknown = False

        attempt = Mock()
        attempt.success = False
        attempt.result = None
        attempt.error = error

        self.issue_service.issue_one.return_value = (
            attempt
        )

        with self.assertLogs(
            "cotizador.services.portal_issue_application_service",
            level="ERROR",
        ) as logs:
            with self.assertRaisesRegex(
                ValueError,
                "Error de emisión",
            ):
                PortalIssueApplicationService.issue_one(
                    cotizacion_item=self.item,
                    configuration_service=(
                        self.configuration_service
                    ),
                    resolver_factory=self.resolver_factory,
                    request_service=self.request_service,
                    issue_service_factory=(
                        self.issue_service_factory
                    ),
                    persistence_service=(
                        self.persistence_service
                    ),
                    attempt_persistence_service=(
                        self.attempt_persistence_service
                    ),
                )

        self.persistence_service.save.assert_not_called()
        self.attempt_persistence_service.save.assert_called_once_with(
            cotizacion_item=self.item,
            cotizacion_proveedor=self.provider_quote,
            provider_configuration_id=77,
            attempt=attempt,
        )
        self.assertEqual(len(logs.output), 1)
        self.assertIn(
            "cotizacion_id="
            f"{self.cotizacion.id}",
            logs.output[0],
        )
        self.assertIn(
            "cotizacion_item_id="
            f"{self.item.id}",
            logs.output[0],
        )
        self.assertIn(
            "provider=CHUBB",
            logs.output[0],
        )
        self.assertIn(
            "error_type=ProviderInvalidResponseError",
            logs.output[0],
        )
        self.assertIn(
            "retryable=False",
            logs.output[0],
        )
        self.assertIn(
            "message=Error de emisión.",
            logs.output[0],
        )

    def test_issue_one_identifies_unknown_outcome(
        self,
    ):
        error = Mock()
        error.message = (
            "Chubb excedió el timeout de 30 segundos "
            "para POST /issue."
        )
        error.error_type = "ProviderHttpTimeoutError"
        error.retryable = True
        error.outcome_unknown = True

        attempt = Mock()
        attempt.success = False
        attempt.result = None
        attempt.error = error

        self.issue_service.issue_one.return_value = (
            attempt
        )

        with self.assertLogs(
            "cotizador.services.portal_issue_application_service",
            level="ERROR",
        ) as logs:
            with self.assertRaises(ValueError):
                PortalIssueApplicationService.issue_one(
                    cotizacion_item=self.item,
                    configuration_service=(
                        self.configuration_service
                    ),
                    resolver_factory=self.resolver_factory,
                    request_service=self.request_service,
                    issue_service_factory=(
                        self.issue_service_factory
                    ),
                    persistence_service=(
                        self.persistence_service
                    ),
                    attempt_persistence_service=(
                        self.attempt_persistence_service
                    ),                    
                )

        self.persistence_service.save.assert_not_called()

        self.attempt_persistence_service.save.assert_called_once_with(
            cotizacion_item=self.item,
            cotizacion_proveedor=self.provider_quote,
            provider_configuration_id=77,
            attempt=attempt,
        )

        self.assertEqual(
            len(logs.output),
            1,
        )
        self.assertIn(
            "outcome_unknown=True",
            logs.output[0],
        )

    def test_issue_one_blocks_when_unknown_issue_exists(
        self,
    ):
        CotizacionProveedorEmision.objects.create(
            cotizacion_item=self.item,
            cotizacion_proveedor=self.provider_quote,
            provider_code="CHUBB",
            provider_configuration_id=77,
            estatus=(
                CotizacionProveedorEmision
                .Estatus
                .INDETERMINADA
            ),
            elapsed_ms=30000,
            retryable=True,
            outcome_unknown=True,
            error_type="ProviderHttpTimeoutError",
            error_message="Timeout durante /issue.",
        )

        with self.assertRaisesRegex(
            ValueError,
            "requiere reconciliación",
        ):
            PortalIssueApplicationService.issue_one(
                cotizacion_item=self.item,
                configuration_service=(
                    self.configuration_service
                ),
                resolver_factory=self.resolver_factory,
                request_service=self.request_service,
                issue_service_factory=(
                    self.issue_service_factory
                ),
                persistence_service=(
                    self.persistence_service
                ),
                attempt_persistence_service=(
                    self.attempt_persistence_service
                ),
            )

        self.issue_service.issue_one.assert_not_called()
        self.persistence_service.save.assert_not_called()
        self.attempt_persistence_service.save.assert_not_called()

    def test_issue_one_requires_provider(
        self,
    ):
        self.item.provider = ""

        with self.assertRaisesRegex(
            ValueError,
            "no tiene provider",
        ):
            PortalIssueApplicationService.issue_one(
                cotizacion_item=self.item,
                configuration_service=(
                    self.configuration_service
                ),
                resolver_factory=self.resolver_factory,
                request_service=self.request_service,
                issue_service_factory=(
                    self.issue_service_factory
                ),
                persistence_service=self.persistence_service,
            )

        self.configuration_service.get_by_id.assert_not_called()

    def test_issue_one_requires_provider_configuration_id(
        self,
    ):
        self.provider_quote.provider_configuration_id = None
        self.provider_quote.save(
            update_fields=["provider_configuration_id"],
        )

        with self.assertRaisesRegex(
            ValueError,
            "no tiene provider_configuration_id",
        ):
            PortalIssueApplicationService.issue_one(
                cotizacion_item=self.item,
                configuration_service=(
                    self.configuration_service
                ),
                resolver_factory=self.resolver_factory,
                request_service=self.request_service,
                issue_service_factory=(
                    self.issue_service_factory
                ),
                persistence_service=self.persistence_service,
            )

        self.configuration_service.get_by_id.assert_not_called()

    def test_issue_one_rejects_provider_mismatch(
        self,
    ):
        self.provider_quote.provider_code = "OTRO"
        self.provider_quote.save(
            update_fields=["provider_code"],
        )

        with self.assertRaisesRegex(
            ValueError,
            "no corresponde al provider",
        ):
            PortalIssueApplicationService.issue_one(
                cotizacion_item=self.item,
                configuration_service=(
                    self.configuration_service
                ),
                resolver_factory=self.resolver_factory,
                request_service=self.request_service,
                issue_service_factory=(
                    self.issue_service_factory
                ),
                persistence_service=self.persistence_service,
            )

        self.configuration_service.get_by_id.assert_not_called()

    def test_issue_one_creates_insured_person_when_missing(
        self,
    ):
        self.person.delete()

        person_resolver_factory = Mock()
        person_resolver = Mock()
        person_provider = Mock()
        person_provider.provider_code = "CHUBB"

        person_resolver_factory.return_value = (
            person_resolver
        )
        person_resolver.build.return_value = (
            person_provider
        )

        person_service = Mock()

        expected_result = Mock()

        attempt = Mock()
        attempt.success = True
        attempt.result = expected_result
        attempt.error = None

        self.issue_service.issue_one.return_value = (
            attempt
        )

        PortalIssueApplicationService.issue_one(
            cotizacion_item=self.item,
            configuration_service=(
                self.configuration_service
            ),
            resolver_factory=self.resolver_factory,
            request_service=self.request_service,
            issue_service_factory=(
                self.issue_service_factory
            ),
            persistence_service=self.persistence_service,
            person_resolver_factory=(
                person_resolver_factory
            ),
            person_service=person_service,
            attempt_persistence_service=(
                self.attempt_persistence_service
            ),            
        )

        self.configuration_service.get_by_id.assert_called_once_with(
            77,
        )

        person_resolver_factory.assert_called_once_with()

        person_resolver.build.assert_called_once_with(
            provider_code="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            configuration=self.configuration,
        )

        person_service.create_one.assert_called_once_with(
            cotizacion=self.cotizacion,
            configuration=self.configuration,
            provider=person_provider,
        )

        self.request_service.build.assert_called_once_with(
            cotizacion_item=self.item,
        )

    def test_reconcile_unknown_issue_marks_it_successful(
        self,
    ):
        emision = CotizacionProveedorEmision.objects.create(
            cotizacion_item=self.item,
            cotizacion_proveedor=self.provider_quote,
            provider_code="CHUBB",
            provider_configuration_id=77,
            estatus=(
                CotizacionProveedorEmision
                .Estatus
                .INDETERMINADA
            ),
            elapsed_ms=30000,
            retryable=True,
            outcome_unknown=True,
            error_type="ProviderHttpTimeoutError",
            error_message="Timeout durante /issue.",
        )

        issue_result = IssueResult(
            provider_code="CHUBB",
            provider_policy_id="99007704",
            provider_policy_key="M6",
            policy_number=None,
            currency="MXN",
            net_premium=Decimal("35247.21"),
            fees=Decimal("600.00"),
            surcharge=Decimal("0.00"),
            discount=Decimal("0.00"),
            taxes=Decimal("5735.56"),
            total_premium=Decimal("41582.77"),
            raw_response={
                "reconciled": True,
            },
        )

        persistence_service = Mock()
        expected_policy = Mock()

        persistence_service.save.return_value = (
            expected_policy
        )

        result = IssueReconciliationService.reconcile(
            cotizacion_item=self.item,
            emision=emision,
            issue_result=issue_result,
            persistence_service=persistence_service,
        )

        self.assertIs(
            result,
            expected_policy,
        )

        persistence_service.save.assert_called_once_with(
            cotizacion_item=self.item,
            issue_result=issue_result,
        )

        emision.refresh_from_db()

        self.assertEqual(
            emision.estatus,
            CotizacionProveedorEmision.Estatus.EXITOSA,
        )
        self.assertFalse(
            emision.outcome_unknown
        )
        self.assertFalse(
            emision.retryable
        )
        self.assertEqual(
            emision.provider_policy_id,
            "99007704",
        )
        self.assertEqual(
            emision.provider_policy_key,
            "M6",
        )

    def test_issue_one_blocks_when_successful_issue_exists(self):
        CotizacionProveedorEmision.objects.create(
            cotizacion_item=self.item,
            cotizacion_proveedor=self.provider_quote,
            provider_code="CHUBB",
            provider_configuration_id=77,
            estatus=CotizacionProveedorEmision.Estatus.EXITOSA,
            elapsed_ms=1200,
            provider_policy_id="99007664",
            provider_policy_key="M6",
        )

        with self.assertRaisesRegex(
            ValueError,
            "emisión exitosa",
        ):
            PortalIssueApplicationService.issue_one(
                cotizacion_item=self.item,
                configuration_service=self.configuration_service,
                resolver_factory=self.resolver_factory,
                request_service=self.request_service,
                issue_service_factory=self.issue_service_factory,
                persistence_service=self.persistence_service,
                attempt_persistence_service=self.attempt_persistence_service,
            )

        self.issue_service.issue_one.assert_not_called()
        self.persistence_service.save.assert_not_called()
        self.attempt_persistence_service.save.assert_not_called()

    def test_issue_one_reserves_and_finalizes_attempt(self):
        from unittest.mock import Mock

        expected_result = Mock()

        attempt = Mock()
        attempt.success = True
        attempt.result = expected_result
        attempt.error = None

        self.issue_service.issue_one.return_value = attempt

        reservation = Mock()
        self.attempt_persistence_service.reserve.return_value = (
            reservation
        )

        calls = []

        def reserve_side_effect(**kwargs):
            calls.append("reserve")
            return reservation

        def issue_side_effect(*args, **kwargs):
            calls.append("issue")
            return attempt

        def finalize_side_effect(**kwargs):
            calls.append("finalize")
            return reservation

        def persist_side_effect(**kwargs):
            calls.append("persist")
            return self.persisted_policy

        self.attempt_persistence_service.reserve.side_effect = (
            reserve_side_effect
        )
        self.issue_service.issue_one.side_effect = (
            issue_side_effect
        )
        self.attempt_persistence_service.finalize.side_effect = (
            finalize_side_effect
        )
        self.persistence_service.save.side_effect = (
            persist_side_effect
        )

        result = PortalIssueApplicationService.issue_one(
            cotizacion_item=self.item,
            configuration_service=self.configuration_service,
            resolver_factory=self.resolver_factory,
            request_service=self.request_service,
            issue_service_factory=self.issue_service_factory,
            persistence_service=self.persistence_service,
            attempt_persistence_service=(
                self.attempt_persistence_service
            ),
        )

        self.assertEqual(
            calls,
            ["reserve", "issue", "finalize", "persist"],
        )

        self.attempt_persistence_service.reserve.assert_called_once_with(
            cotizacion_item=self.item,
            cotizacion_proveedor=self.provider_quote,
            provider_configuration_id=77,
            provider_code="CHUBB",
        )

        self.attempt_persistence_service.finalize.assert_called_once_with(
            reservation=reservation,
            attempt=attempt,
        )

        self.attempt_persistence_service.save.assert_not_called()

        self.assertIs(result, self.persisted_policy)


class IssueAttemptPersistenceServiceTests(
    PortalIssueApplicationServiceTests
):

    def test_save_persists_successful_issue_attempt(self):
        from integrations.issues.contracts import (
            IssueAttempt,
            IssueResult,
        )
        from cotizador.services.issue_attempt_persistence_service import (
            IssueAttemptPersistenceService,
        )

        issue_result = IssueResult(
            provider_code="CHUBB",
            provider_policy_id="99007664",
            provider_policy_key="M6",
            policy_number="M699007664",
            currency="MXN",
            net_premium=Decimal("35247.21"),
            fees=Decimal("600.00"),
            surcharge=Decimal("0.00"),
            discount=Decimal("0.00"),
            taxes=Decimal("5735.56"),
            total_premium=Decimal("41582.77"),
            raw_response={"success": True},
        )

        attempt = IssueAttempt(
            provider_code="CHUBB",
            success=True,
            elapsed_ms=1200,
            result=issue_result,
        )

        emission = IssueAttemptPersistenceService.save(
            cotizacion_item=self.item,
            cotizacion_proveedor=self.provider_quote,
            provider_configuration_id=77,
            attempt=attempt,
        )

        self.assertEqual(
            emission.estatus,
            CotizacionProveedorEmision.Estatus.EXITOSA,
        )
        self.assertEqual(
            emission.provider_policy_id,
            "99007664",
        )
        self.assertEqual(
            emission.provider_policy_key,
            "M6",
        )
        self.assertFalse(emission.outcome_unknown)

        self.assertEqual(
            CotizacionProveedorEmision.objects.filter(
                cotizacion_item=self.item,
            ).count(),
            1,
        )

    def test_reserve_creates_in_progress_issue(self):
        from cotizador.services.issue_attempt_persistence_service import (
            IssueAttemptPersistenceService,
        )

        emission = IssueAttemptPersistenceService.reserve(
            cotizacion_item=self.item,
            cotizacion_proveedor=self.provider_quote,
            provider_configuration_id=77,
            provider_code="CHUBB",
        )

        emission.refresh_from_db()

        self.assertEqual(
            emission.estatus,
            CotizacionProveedorEmision.Estatus.EN_PROCESO,
        )

        self.assertEqual(
            emission.cotizacion_item_id,
            self.item.id,
        )

        self.assertEqual(
            emission.cotizacion_proveedor_id,
            self.provider_quote.id,
        )

        self.assertEqual(
            emission.provider_configuration_id,
            77,
        )

        self.assertEqual(
            CotizacionProveedorEmision.objects.filter(
                cotizacion_item=self.item,
            ).count(),
            1,
        )

    def test_reserve_blocks_duplicate_issue(self):
        from cotizador.services.issue_attempt_persistence_service import (
            IssueAttemptPersistenceService,
        )

        params = {
            "cotizacion_item": self.item,
            "cotizacion_proveedor": self.provider_quote,
            "provider_configuration_id": 77,
            "provider_code": "CHUBB",
        }

        first_emission = IssueAttemptPersistenceService.reserve(
            **params
        )

        with self.assertRaisesRegex(
            ValueError,
            "Ya existe una emisión",
        ):
            IssueAttemptPersistenceService.reserve(
                **params
            )

        self.assertEqual(
            first_emission.estatus,
            CotizacionProveedorEmision.Estatus.EN_PROCESO,
        )

        self.assertEqual(
            CotizacionProveedorEmision.objects.filter(
                cotizacion_item=self.item,
            ).count(),
            1,
        )

    def test_finalize_updates_existing_reservation(self):
        from decimal import Decimal

        from cotizador.services.issue_attempt_persistence_service import (
            IssueAttemptPersistenceService,
        )
        from integrations.issues.contracts import (
            IssueAttempt,
            IssueResult,
        )

        reservation = IssueAttemptPersistenceService.reserve(
            cotizacion_item=self.item,
            cotizacion_proveedor=self.provider_quote,
            provider_configuration_id=77,
            provider_code="CHUBB",
        )

        original_id = reservation.id

        result = IssueResult(
            provider_code="CHUBB",
            provider_policy_id="99007664",
            provider_policy_key="M6",
            policy_number="M699007664",
            currency="MXN",
            net_premium=Decimal("35247.21"),
            fees=Decimal("600.00"),
            surcharge=Decimal("0.00"),
            discount=Decimal("0.00"),
            taxes=Decimal("5735.56"),
            total_premium=Decimal("41582.77"),
            raw_response={"success": True},
        )

        attempt = IssueAttempt(
            provider_code="CHUBB",
            success=True,
            elapsed_ms=1200,
            result=result,
        )

        emission = IssueAttemptPersistenceService.finalize(
            reservation=reservation,
            attempt=attempt,
        )

        emission.refresh_from_db()

        self.assertEqual(emission.id, original_id)
        self.assertEqual(
            emission.estatus,
            CotizacionProveedorEmision.Estatus.EXITOSA,
        )
        self.assertEqual(
            emission.provider_policy_id,
            "99007664",
        )
        self.assertEqual(
            emission.provider_policy_key,
            "M6",
        )
        self.assertEqual(emission.elapsed_ms, 1200)
        self.assertFalse(emission.outcome_unknown)

        self.assertEqual(
            CotizacionProveedorEmision.objects.filter(
                cotizacion_item=self.item,
            ).count(),
            1,
        )

    def test_finalize_blocks_second_finalization(self):
        from decimal import Decimal

        from cotizador.services.issue_attempt_persistence_service import (
            IssueAttemptPersistenceService,
        )
        from integrations.issues.contracts import (
            IssueAttempt,
            IssueResult,
        )

        reservation = IssueAttemptPersistenceService.reserve(
            cotizacion_item=self.item,
            cotizacion_proveedor=self.provider_quote,
            provider_configuration_id=77,
            provider_code="CHUBB",
        )

        result = IssueResult(
            provider_code="CHUBB",
            provider_policy_id="99007664",
            provider_policy_key="M6",
            policy_number="M699007664",
            currency="MXN",
            net_premium=Decimal("35247.21"),
            fees=Decimal("600.00"),
            surcharge=Decimal("0.00"),
            discount=Decimal("0.00"),
            taxes=Decimal("5735.56"),
            total_premium=Decimal("41582.77"),
        )

        attempt = IssueAttempt(
            provider_code="CHUBB",
            success=True,
            elapsed_ms=1200,
            result=result,
        )

        IssueAttemptPersistenceService.finalize(
            reservation=reservation,
            attempt=attempt,
        )

        with self.assertRaisesRegex(
            ValueError,
            "La reserva de emisión ya fue finalizada",
        ):
            IssueAttemptPersistenceService.finalize(
                reservation=reservation,
                attempt=attempt,
            )

        reservation.refresh_from_db()

        self.assertEqual(
            reservation.estatus,
            CotizacionProveedorEmision.Estatus.EXITOSA,
        )

        self.assertEqual(
            CotizacionProveedorEmision.objects.filter(
                cotizacion_item=self.item,
            ).count(),
            1,
        )

    def test_finalize_marks_unknown_outcome_as_indeterminate(self):
        from cotizador.services.issue_attempt_persistence_service import (
            IssueAttemptPersistenceService,
        )
        from integrations.issues.contracts import (
            IssueAttempt,
            IssueProviderError,
        )

        reservation = IssueAttemptPersistenceService.reserve(
            cotizacion_item=self.item,
            cotizacion_proveedor=self.provider_quote,
            provider_configuration_id=77,
            provider_code="CHUBB",
        )

        attempt = IssueAttempt(
            provider_code="CHUBB",
            success=False,
            elapsed_ms=30000,
            error=IssueProviderError(
                provider_code="CHUBB",
                message="Timeout esperando respuesta del proveedor",
                error_type="TIMEOUT",
                retryable=True,
                outcome_unknown=True,
            ),
        )

        emission = IssueAttemptPersistenceService.finalize(
            reservation=reservation,
            attempt=attempt,
        )

        self.assertEqual(
            emission.estatus,
            CotizacionProveedorEmision.Estatus.INDETERMINADA,
        )
        self.assertTrue(emission.outcome_unknown)
        self.assertTrue(emission.retryable)
        self.assertEqual(emission.error_type, "TIMEOUT")
        self.assertEqual(emission.elapsed_ms, 30000)

        # No debe permitir reservar otra emisión.
        with self.assertRaisesRegex(
            ValueError,
            "Ya existe una emisión",
        ):
            IssueAttemptPersistenceService.reserve(
                cotizacion_item=self.item,
                cotizacion_proveedor=self.provider_quote,
                provider_configuration_id=77,
                provider_code="CHUBB",
            )

        self.assertEqual(
            CotizacionProveedorEmision.objects.filter(
                cotizacion_item=self.item,
            ).count(),
            1,
        )

    def test_finalize_failed_issue_allows_new_reservation(self):
        from cotizador.services.issue_attempt_persistence_service import (
            IssueAttemptPersistenceService,
        )
        from integrations.issues.contracts import (
            IssueAttempt,
            IssueProviderError,
        )

        params = {
            "cotizacion_item": self.item,
            "cotizacion_proveedor": self.provider_quote,
            "provider_configuration_id": 77,
            "provider_code": "CHUBB",
        }

        reservation = IssueAttemptPersistenceService.reserve(
            **params
        )

        attempt = IssueAttempt(
            provider_code="CHUBB",
            success=False,
            elapsed_ms=850,
            error=IssueProviderError(
                provider_code="CHUBB",
                message="Solicitud de emisión rechazada",
                error_type="VALIDATION_ERROR",
                retryable=False,
                outcome_unknown=False,
            ),
        )

        emission = IssueAttemptPersistenceService.finalize(
            reservation=reservation,
            attempt=attempt,
        )

        self.assertEqual(
            emission.estatus,
            CotizacionProveedorEmision.Estatus.FALLIDA,
        )
        self.assertFalse(emission.outcome_unknown)
        self.assertFalse(emission.retryable)
        self.assertEqual(
            emission.error_type,
            "VALIDATION_ERROR",
        )

        # Una emisión fallida con resultado conocido
        # no bloquea una nueva reserva.
        new_reservation = IssueAttemptPersistenceService.reserve(
            **params
        )

        self.assertNotEqual(
            new_reservation.id,
            reservation.id,
        )

        self.assertEqual(
            new_reservation.estatus,
            CotizacionProveedorEmision.Estatus.EN_PROCESO,
        )

        self.assertEqual(
            CotizacionProveedorEmision.objects.filter(
                cotizacion_item=self.item,
            ).count(),
            2,
        )


class IssuePersistenceServiceTests(TestCase):

    def setUp(self):
        self.cliente = Cliente.objects.create(
            tipo_cliente=Cliente.TipoCliente.PERSONA,
            nombre="Miguel",
            email_principal="miguel@example.com",
        )

        self.vehiculo = Vehiculo.objects.create(
            cliente=self.cliente,
            marca_texto="ACURA",
            submarca_texto="TL",
            modelo_anio=2015,
            version="SEDAN 3.7L AUT",
            placas="TR543",
            vin="JH4KA3277KC007500",
        )

        hoy = timezone.localdate()

        self.cotizacion = Cotizacion.objects.create(
            cliente=self.cliente,
            vehiculo=self.vehiculo,
            flotilla=None,
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=hoy,
            vigencia_hasta=hoy + timedelta(days=365),
            forma_pago_preferida="CONTADO",
        )

        self.aseguradora = Aseguradora.objects.create(
            nombre="Chubb Persistence Test",
        )

        self.producto = ProductoSeguro.objects.create(
            aseguradora=self.aseguradora,
            nombre_producto="Autos",
            tipo_producto=ProductoSeguro.TipoProducto.AUTO,
            modelo_calculo=ProductoSeguro.ModeloCalculo.SIMPLE,
        )

        self.item = CotizacionItem.objects.create(
            cotizacion=self.cotizacion,
            aseguradora=self.aseguradora,
            producto=self.producto,
            prima_neta=Decimal("35000.00"),
            derechos=Decimal("500.00"),
            iva=Decimal("5680.00"),
            prima_total=Decimal("41180.00"),
            forma_pago="CONTADO",
            provider="CHUBB",
            provider_quote_id="2061261215",
            paquete_nombre="AMPLIA",
        )

    def _issue_result(
        self,
        *,
        provider_code="CHUBB",
        provider_policy_id="99007670",
        provider_policy_key="M6",
        policy_number=None,
    ):
        return IssueResult(
            provider_code=provider_code,
            provider_policy_id=provider_policy_id,
            provider_policy_key=provider_policy_key,
            policy_number=policy_number,
            currency="MXN",
            net_premium=Decimal("35247.21"),
            fees=Decimal("600.00"),
            surcharge=Decimal("0.00"),
            discount=Decimal("0.00"),
            taxes=Decimal("5735.56"),
            total_premium=Decimal("41582.77"),
            raw_response={
                "success": True,
                "responseData": [
                    {
                        "quoteKey": "M6 ",
                        "quotePolicyId": 99007670,
                    },
                ],
            },
        )

    def test_save_creates_policy_and_provider_result(
        self,
    ):
        result = self._issue_result()

        poliza = IssuePersistenceService.save(
            cotizacion_item=self.item,
            issue_result=result,
        )

        self.assertEqual(
            Poliza.objects.count(),
            1,
        )
        self.assertEqual(
            PolizaProveedor.objects.count(),
            1,
        )

        self.assertEqual(
            poliza.cotizacion_item,
            self.item,
        )
        self.assertEqual(
            poliza.cliente,
            self.cotizacion.cliente,
        )
        self.assertEqual(
            poliza.vehiculo,
            self.cotizacion.vehiculo,
        )
        self.assertEqual(
            poliza.aseguradora,
            self.item.aseguradora,
        )
        self.assertEqual(
            poliza.producto,
            self.item.producto,
        )

        self.assertEqual(
            poliza.prima_neta,
            Decimal("35247.21"),
        )
        self.assertEqual(
            poliza.gastos_expedicion,
            Decimal("600.00"),
        )
        self.assertEqual(
            poliza.financiamiento,
            Decimal("0.00"),
        )
        self.assertEqual(
            poliza.subtotal,
            Decimal("35847.21"),
        )
        self.assertEqual(
            poliza.iva,
            Decimal("5735.56"),
        )
        self.assertEqual(
            poliza.prima_total,
            Decimal("41582.77"),
        )

        provider_result = poliza.resultado_proveedor

        self.assertEqual(
            provider_result.provider_code,
            "CHUBB",
        )
        self.assertEqual(
            provider_result.provider_policy_id,
            "99007670",
        )
        self.assertEqual(
            provider_result.provider_policy_key,
            "M6",
        )
        self.assertEqual(
            provider_result.currency,
            "MXN",
        )
        self.assertEqual(
            provider_result.raw_response,
            result.raw_response,
        )

    def test_save_completes_prepared_policy_instead_of_creating_another(
        self,
    ):
        prepared = PolicyPreparationService.prepare(
            cotizacion_item=self.item,
        )
        prepared_pk = prepared.pk

        self.assertEqual(
            prepared.estatus,
            Poliza.Estatus.EN_PROCESO,
        )
        self.assertFalse(
            PolizaProveedor.objects.filter(
                poliza=prepared,
            ).exists()
        )

        result = self._issue_result(
            policy_number="M6 99007670",
        )

        poliza = IssuePersistenceService.save(
            cotizacion_item=self.item,
            issue_result=result,
        )

        self.assertEqual(
            poliza.pk,
            prepared_pk,
        )
        self.assertEqual(
            Poliza.objects.filter(
                cotizacion_item=self.item,
            ).count(),
            1,
        )
        self.assertEqual(
            PolizaProveedor.objects.filter(
                poliza=poliza,
            ).count(),
            1,
        )

        poliza.refresh_from_db()

        self.assertEqual(
            poliza.numero_poliza,
            "M6 99007670",
        )
        self.assertIsNotNone(
            poliza.fecha_emision,
        )
        self.assertEqual(
            poliza.estatus,
            Poliza.Estatus.EN_PROCESO,
        )

        self.assertEqual(
            poliza.prima_neta,
            Decimal("35247.21"),
        )
        self.assertEqual(
            poliza.gastos_expedicion,
            Decimal("600.00"),
        )
        self.assertEqual(
            poliza.financiamiento,
            Decimal("0.00"),
        )
        self.assertEqual(
            poliza.subtotal,
            Decimal("35847.21"),
        )
        self.assertEqual(
            poliza.iva,
            Decimal("5735.56"),
        )
        self.assertEqual(
            poliza.prima_total,
            Decimal("41582.77"),
        )

        provider_result = poliza.resultado_proveedor

        self.assertEqual(
            provider_result.provider_code,
            "CHUBB",
        )
        self.assertEqual(
            provider_result.provider_policy_id,
            "99007670",
        )
        self.assertEqual(
            provider_result.provider_policy_key,
            "M6",
        )
        self.assertEqual(
            provider_result.currency,
            "MXN",
        )

        self.cotizacion.refresh_from_db()

        self.assertEqual(
            self.cotizacion.estatus,
            Cotizacion.Estatus.EMITIDA,
        )
        self.assertIsNotNone(
            self.cotizacion.emitida_at,
        )

    def test_save_marks_quote_as_issued(
        self,
    ):
        result = self._issue_result()

        IssuePersistenceService.save(
            cotizacion_item=self.item,
            issue_result=result,
        )

        self.cotizacion.refresh_from_db()

        self.assertEqual(
            self.cotizacion.estatus,
            Cotizacion.Estatus.EMITIDA,
        )
        self.assertIsNotNone(
            self.cotizacion.emitida_at,
        )

    def test_save_uses_policy_number_when_provider_returns_it(
        self,
    ):
        result = self._issue_result(
            policy_number="K6 99454302",
        )

        poliza = IssuePersistenceService.save(
            cotizacion_item=self.item,
            issue_result=result,
        )

        self.assertEqual(
            poliza.numero_poliza,
            "K6 99454302",
        )

    def test_save_is_idempotent_for_same_provider_policy(
        self,
    ):
        result = self._issue_result()

        first = IssuePersistenceService.save(
            cotizacion_item=self.item,
            issue_result=result,
        )

        second = IssuePersistenceService.save(
            cotizacion_item=self.item,
            issue_result=result,
        )

        self.assertEqual(
            first.pk,
            second.pk,
        )
        self.assertEqual(
            Poliza.objects.count(),
            1,
        )
        self.assertEqual(
            PolizaProveedor.objects.count(),
            1,
        )

    def test_save_rejects_result_from_different_provider(
        self,
    ):
        result = self._issue_result(
            provider_code="OTRO",
        )

        with self.assertRaisesRegex(
            ValueError,
            "no corresponde al CotizacionItem",
        ):
            IssuePersistenceService.save(
                cotizacion_item=self.item,
                issue_result=result,
            )

        self.assertEqual(
            Poliza.objects.count(),
            0,
        )
        self.assertEqual(
            PolizaProveedor.objects.count(),
            0,
        )

    def test_save_prepared_policy_logs_number_change_once(
        self,
    ):
        prepared = PolicyPreparationService.prepare(
            cotizacion_item=self.item,
        )

        previous_number = prepared.numero_poliza

        result = self._issue_result(
            policy_number="M6 99007670",
        )

        first = IssuePersistenceService.save(
            cotizacion_item=self.item,
            issue_result=result,
        )

        second = IssuePersistenceService.save(
            cotizacion_item=self.item,
            issue_result=result,
        )

        self.assertEqual(first.pk, second.pk)

        events = PolizaEvento.objects.filter(
            poliza=first,
            tipo=PolizaEvento.Tipo.NUMERO_ACTUALIZADO,
        )

        self.assertEqual(events.count(), 1)

        event = events.get()

        self.assertEqual(
            event.data["numero_anterior"],
            previous_number,
        )
        self.assertEqual(
            event.data["numero_nuevo"],
            "M6 99007670",
        )
#***

class PolicyPreparationServiceTests(TestCase):

    def setUp(self):
        self.cliente = Cliente.objects.create(
            tipo_cliente=Cliente.TipoCliente.PERSONA,
            nombre="Miguel",
            email_principal="miguel@example.com",
        )

        self.vehiculo = Vehiculo.objects.create(
            cliente=self.cliente,
            marca_texto="ACURA",
            submarca_texto="TL",
            modelo_anio=2015,
            version="SEDAN 3.7L AUT",
            placas="TR543",
            vin="JH4KA3277KC007500",
        )

        hoy = timezone.localdate()

        self.cotizacion = Cotizacion.objects.create(
            cliente=self.cliente,
            vehiculo=self.vehiculo,
            flotilla=None,
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=hoy,
            vigencia_hasta=hoy + timedelta(days=365),
            forma_pago_preferida="CONTADO",
        )

        self.aseguradora = Aseguradora.objects.create(
            nombre="Chubb Policy Preparation Test",
        )

        self.producto = ProductoSeguro.objects.create(
            aseguradora=self.aseguradora,
            nombre_producto="Autos",
            tipo_producto=ProductoSeguro.TipoProducto.AUTO,
            modelo_calculo=ProductoSeguro.ModeloCalculo.SIMPLE,
        )

        self.item = CotizacionItem.objects.create(
            cotizacion=self.cotizacion,
            aseguradora=self.aseguradora,
            producto=self.producto,
            prima_neta=Decimal("35000.00"),
            derechos=Decimal("500.00"),
            iva=Decimal("5680.00"),
            prima_total=Decimal("41180.00"),
            forma_pago="CONTADO",
            provider="CHUBB",
            provider_quote_id="2061261215",
            paquete_nombre="AMPLIA",
        )

    def test_prepare_creates_policy_in_process_and_created_event(self):
        poliza = PolicyPreparationService.prepare(
            cotizacion_item=self.item,
        )

        self.assertEqual(
            poliza.estatus,
            Poliza.Estatus.EN_PROCESO,
        )
        self.assertEqual(
            poliza.cotizacion_item,
            self.item,
        )
        self.assertEqual(
            poliza.cliente,
            self.cliente,
        )
        self.assertEqual(
            poliza.vehiculo,
            self.vehiculo,
        )
        self.assertEqual(
            poliza.aseguradora,
            self.aseguradora,
        )
        self.assertEqual(
            poliza.producto,
            self.producto,
        )
        self.assertIsNone(poliza.fecha_emision)

        self.assertTrue(
            poliza.numero_poliza.startswith("PEND-COT-")
        )

        evento = poliza.eventos.get(
            tipo=PolizaEvento.Tipo.CREADA,
        )

        self.assertEqual(
            evento.dedupe_key,
            f"POLIZA_CREADA:{poliza.id}",
        )

    def test_prepare_is_idempotent_for_same_cotizacion_item(self):
        first = PolicyPreparationService.prepare(
            cotizacion_item=self.item,
        )

        second = PolicyPreparationService.prepare(
            cotizacion_item=self.item,
        )

        self.assertEqual(first.id, second.id)

        self.assertEqual(
            Poliza.objects.filter(
                cotizacion_item=self.item,
            ).count(),
            1,
        )

        self.assertEqual(
            PolizaEvento.objects.filter(
                poliza=first,
                tipo=PolizaEvento.Tipo.CREADA,
            ).count(),
            1,
        )

    def test_prepared_policy_can_create_pending_payment(self):
        poliza = PolicyPreparationService.prepare(
            cotizacion_item=self.item,
        )

        created = crear_plan_pagos(
            poliza,
            overwrite=False,
        )

        self.assertEqual(created, 1)

        pago = Pago.objects.get(poliza=poliza)

        self.assertEqual(
            pago.estatus,
            Pago.Estatus.PENDIENTE,
        )
        self.assertEqual(
            pago.cliente,
            self.cliente,
        )
        self.assertEqual(
            pago.monto,
            Decimal("41180.00"),
        )
        self.assertEqual(
            pago.moneda,
            "MXN",
        )

    def test_payment_plan_is_idempotent_for_prepared_policy(self):
        poliza = PolicyPreparationService.prepare(
            cotizacion_item=self.item,
        )

        first_created = crear_plan_pagos(
            poliza,
            overwrite=False,
        )

        second_created = crear_plan_pagos(
            poliza,
            overwrite=False,
        )

        self.assertEqual(first_created, 1)
        self.assertEqual(second_created, 0)

        self.assertEqual(
            Pago.objects.filter(
                poliza=poliza,
            ).count(),
            1,
        )

        pago = Pago.objects.get(poliza=poliza)

        self.assertEqual(
            pago.estatus,
            Pago.Estatus.PENDIENTE,
        )

#**

class PortalDocumentApplicationServiceTests(TestCase):

    def setUp(self):
        self.cliente = Cliente.objects.create(
            tipo_cliente=Cliente.TipoCliente.PERSONA,
            nombre="Miguel",
            email_principal="miguel@example.com",
        )

        self.vehiculo = Vehiculo.objects.create(
            cliente=self.cliente,
            marca_texto="ACURA",
            submarca_texto="TL",
            modelo_anio=2015,
            version="SEDAN 3.7L AUT",
            placas="TR543",
            vin="JH4KA3277KC007500",
        )

        hoy = timezone.localdate()

        self.cotizacion = Cotizacion.objects.create(
            cliente=self.cliente,
            vehiculo=self.vehiculo,
            flotilla=None,
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=hoy,
            vigencia_hasta=hoy + timedelta(days=365),
            forma_pago_preferida="CONTADO",
        )

        self.provider_quote = (
            CotizacionProveedor.objects.create(
                cotizacion=self.cotizacion,
                provider_code="CHUBB",
                provider_configuration_id=77,
                success=True,
                elapsed_ms=100,
                provider_quote_id="2061261215",
                provider_quote_version_id="2061499999",
                currency="MXN",
                total_premium=Decimal("41582.77"),
            )
        )

        self.provider_risk = (
            CotizacionProveedorRiesgo.objects.create(
                cotizacion_proveedor=self.provider_quote,
                provider_risk_id="2061426582",
                risk_number=1,
                vehicle_key="01010100101",
            )
        )

        self.provider_option = (
            CotizacionProveedorOpcion.objects.create(
                cotizacion_proveedor=self.provider_quote,
                riesgo=self.provider_risk,
                code="1",
                provider_package_id="1",
                name="AMPLIA",
                total_premium=Decimal("41582.77"),
                currency="MXN",
                selected=True,
            )
        )

        self.aseguradora = Aseguradora.objects.create(
            nombre="Chubb Document Application Test",
        )

        self.producto = ProductoSeguro.objects.create(
            aseguradora=self.aseguradora,
            nombre_producto="Autos",
            tipo_producto=ProductoSeguro.TipoProducto.AUTO,
            modelo_calculo=ProductoSeguro.ModeloCalculo.SIMPLE,
        )

        self.item = CotizacionItem.objects.create(
            cotizacion=self.cotizacion,
            aseguradora=self.aseguradora,
            producto=self.producto,
            provider_option=self.provider_option,
            prima_total=Decimal("41582.77"),
            forma_pago="CONTADO",
            provider="CHUBB",
            provider_quote_id="2061261215",
            paquete_nombre="AMPLIA",
        )

        self.poliza = Poliza.objects.create(
            cliente=self.cliente,
            vehiculo=self.vehiculo,
            aseguradora=self.aseguradora,
            producto=self.producto,
            cotizacion_item=self.item,
            numero_poliza="PEND-CHUBB-99007704",
            fecha_emision=hoy,
            vigencia_desde=self.cotizacion.vigencia_desde,
            vigencia_hasta=self.cotizacion.vigencia_hasta,
            estatus=Poliza.Estatus.EN_PROCESO,
            prima_total=Decimal("41582.77"),
            forma_pago="CONTADO",
        )

        self.poliza_proveedor = (
            PolizaProveedor.objects.create(
                poliza=self.poliza,
                provider_code="CHUBB",
                provider_policy_id="99007704",
                provider_policy_key="M6",
                currency="MXN",
                raw_response={},
            )
        )

        self.configuration_service = Mock()

        self.configuration = Mock()
        self.configuration.provider = "CHUBB"
        self.configuration.ambiente = "SIT"
        self.configuration.ramo = "AUTOS"

        self.configuration_service.get_by_id.return_value = (
            self.configuration
        )

        self.resolver_factory = Mock()
        self.resolver = Mock()

        self.provider = Mock()
        self.provider.provider_code = "CHUBB"

        self.resolver_factory.return_value = self.resolver
        self.resolver.build.return_value = self.provider

        self.document_service_factory = Mock()
        self.document_service = Mock()

        self.document_service_factory.return_value = (
            self.document_service
        )

    def test_get_policy_documents_coordinates_complete_flow(
        self,
    ):
        expected_result = Mock()

        self.document_service.get_policy_documents.return_value = (
            expected_result
        )

        result = (
            PortalDocumentApplicationService
            .get_policy_documents(
                poliza=self.poliza,
                configuration_service=(
                    self.configuration_service
                ),
                resolver_factory=self.resolver_factory,
                document_service_factory=(
                    self.document_service_factory
                ),
            )
        )

        self.configuration_service.get_by_id.assert_called_once_with(
            77,
        )

        self.resolver_factory.assert_called_once_with(
            configuration_service=(
                self.configuration_service
            ),
        )

        self.resolver.build.assert_called_once_with(
            provider_code="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            configuration=self.configuration,
        )

        self.document_service_factory.assert_called_once_with(
            providers=[self.provider],
        )

        expected_request = PolicyDocumentRequest(
            provider_policy_id="99007704",
            provider_policy_key="M6",
            risk_number=1,
        )

        self.document_service.get_policy_documents.assert_called_once_with(
            "CHUBB",
            expected_request,
        )

        self.assertIs(
            result,
            expected_result,
        )

    def test_get_policy_documents_allows_missing_risk(
        self,
    ):
        self.provider_option.riesgo = None
        self.provider_option.save(
            update_fields=["riesgo"],
        )

        expected_result = Mock()

        self.document_service.get_policy_documents.return_value = (
            expected_result
        )

        PortalDocumentApplicationService.get_policy_documents(
            poliza=self.poliza,
            configuration_service=self.configuration_service,
            resolver_factory=self.resolver_factory,
            document_service_factory=(
                self.document_service_factory
            ),
        )

        expected_request = PolicyDocumentRequest(
            provider_policy_id="99007704",
            provider_policy_key="M6",
            risk_number=None,
        )

        self.document_service.get_policy_documents.assert_called_once_with(
            "CHUBB",
            expected_request,
        )

    def test_get_policy_documents_rejects_provider_mismatch(
        self,
    ):
        self.provider_quote.provider_code = "OTRO"
        self.provider_quote.save(
            update_fields=["provider_code"],
        )

        with self.assertRaisesRegex(
            ValueError,
            "no corresponde",
        ):
            PortalDocumentApplicationService.get_policy_documents(
                poliza=self.poliza,
                configuration_service=(
                    self.configuration_service
                ),
                resolver_factory=self.resolver_factory,
                document_service_factory=(
                    self.document_service_factory
                ),
            )

        self.configuration_service.get_by_id.assert_not_called()

    def test_get_policy_documents_requires_configuration_id(
        self,
    ):
        self.provider_quote.provider_configuration_id = None
        self.provider_quote.save(
            update_fields=["provider_configuration_id"],
        )

        with self.assertRaisesRegex(
            ValueError,
            "no tiene provider_configuration_id",
        ):
            PortalDocumentApplicationService.get_policy_documents(
                poliza=self.poliza,
                configuration_service=(
                    self.configuration_service
                ),
                resolver_factory=self.resolver_factory,
                document_service_factory=(
                    self.document_service_factory
                ),
            )

        self.configuration_service.get_by_id.assert_not_called()

    def test_get_policy_documents_requires_policy_key(
        self,
    ):
        self.poliza_proveedor.provider_policy_key = ""
        self.poliza_proveedor.save(
            update_fields=["provider_policy_key"],
        )

        with self.assertRaisesRegex(
            ValueError,
            "no tiene provider_policy_key",
        ):
            PortalDocumentApplicationService.get_policy_documents(
                poliza=self.poliza,
                configuration_service=(
                    self.configuration_service
                ),
                resolver_factory=self.resolver_factory,
                document_service_factory=(
                    self.document_service_factory
                ),
            )

        self.document_service.get_policy_documents.assert_not_called()

    def test_get_and_persist_policy_document_coordinates_flow(
        self,
    ):
        policy_document = PolicyDocument(
            order_id="1",
            file_name="M699007704_00001.pdf",
            content=b"%PDF-1.4 test",
        )

        expected_result = PolicyDocumentResult(
            provider_code="CHUBB",
            provider_policy_id="99007704",
            provider_policy_key="M6",
            documents=(policy_document,),
        )

        self.document_service.get_policy_documents.return_value = (
            expected_result
        )

        persistence_service = Mock()
        expected_documento = Mock()
        persistence_service.persist.return_value = expected_documento

        result = (
            PortalDocumentApplicationService
            .get_and_persist_policy_document(
                poliza=self.poliza,
                configuration_service=self.configuration_service,
                resolver_factory=self.resolver_factory,
                document_service_factory=(
                    self.document_service_factory
                ),
                persistence_service=persistence_service,
            )
        )

        persistence_service.persist.assert_called_once_with(
            poliza=self.poliza,
            document=policy_document,
            subido_por=None,
        )

        self.assertIs(
            result,
            expected_documento,
        )

    def test_get_and_persist_policy_document_rejects_no_documents(
        self,
    ):
        expected_result = PolicyDocumentResult(
            provider_code="CHUBB",
            provider_policy_id="99007704",
            provider_policy_key="M6",
            documents=(),
        )

        self.document_service.get_policy_documents.return_value = (
            expected_result
        )

        persistence_service = Mock()

        with self.assertRaisesRegex(
            ValueError,
            "no devolvió documentos",
        ):
            (
                PortalDocumentApplicationService
                .get_and_persist_policy_document(
                    poliza=self.poliza,
                    configuration_service=(
                        self.configuration_service
                    ),
                    resolver_factory=self.resolver_factory,
                    document_service_factory=(
                        self.document_service_factory
                    ),
                    persistence_service=persistence_service,
                )
            )

        persistence_service.persist.assert_not_called()

    def test_get_and_persist_policy_document_rejects_multiple_documents(
        self,
    ):
        first = PolicyDocument(
            order_id="1",
            file_name="policy.pdf",
            content=b"%PDF-1.4 policy",
        )

        second = PolicyDocument(
            order_id="2",
            file_name="receipt.pdf",
            content=b"%PDF-1.4 receipt",
        )

        expected_result = PolicyDocumentResult(
            provider_code="CHUBB",
            provider_policy_id="99007704",
            provider_policy_key="M6",
            documents=(first, second),
        )

        self.document_service.get_policy_documents.return_value = (
            expected_result
        )

        persistence_service = Mock()

        with self.assertRaisesRegex(
            ValueError,
            "más de un documento",
        ):
            (
                PortalDocumentApplicationService
                .get_and_persist_policy_document(
                    poliza=self.poliza,
                    configuration_service=(
                        self.configuration_service
                    ),
                    resolver_factory=self.resolver_factory,
                    document_service_factory=(
                        self.document_service_factory
                    ),
                    persistence_service=persistence_service,
                )
            )

        persistence_service.persist.assert_not_called()

    def test_get_and_persist_policy_document_retries_once_on_timeout(
        self,
    ):
        policy_document = PolicyDocument(
            order_id="1",
            file_name="M699007704_00001.pdf",
            content=b"%PDF-1.4 test",
        )

        expected_result = PolicyDocumentResult(
            provider_code="CHUBB",
            provider_policy_id="99007704",
            provider_policy_key="M6",
            documents=(policy_document,),
        )

        self.document_service.get_policy_documents.side_effect = [
            ProviderHttpTimeoutError("timeout"),
            expected_result,
        ]

        persistence_service = Mock()
        expected_documento = Mock()
        persistence_service.persist.return_value = (
            expected_documento
        )

        result = (
            PortalDocumentApplicationService
            .get_and_persist_policy_document(
                poliza=self.poliza,
                configuration_service=self.configuration_service,
                resolver_factory=self.resolver_factory,
                document_service_factory=(
                    self.document_service_factory
                ),
                persistence_service=persistence_service,
            )
        )

        self.assertEqual(
            self.document_service.get_policy_documents.call_count,
            2,
        )

        persistence_service.persist.assert_called_once_with(
            poliza=self.poliza,
            document=policy_document,
            subido_por=None,
        )

        self.assertIs(
            result,
            expected_documento,
        )

    def test_get_and_persist_policy_document_propagates_second_timeout(
        self,
    ):
        self.document_service.get_policy_documents.side_effect = [
            ProviderHttpTimeoutError("timeout 1"),
            ProviderHttpTimeoutError("timeout 2"),
        ]

        persistence_service = Mock()

        with self.assertRaises(ProviderHttpTimeoutError):
            (
                PortalDocumentApplicationService
                .get_and_persist_policy_document(
                    poliza=self.poliza,
                    configuration_service=(
                        self.configuration_service
                    ),
                    resolver_factory=self.resolver_factory,
                    document_service_factory=(
                        self.document_service_factory
                    ),
                    persistence_service=persistence_service,
                )
            )

        self.assertEqual(
            self.document_service.get_policy_documents.call_count,
            2,
        )

        persistence_service.persist.assert_not_called()

    def test_get_and_persist_policy_document_returns_existing_document(
        self,
    ):
        documento = Documento.objects.create(
            nombre_archivo="existing.pdf",
            tipo=Documento.Tipo.PDF,
            file="docs/existing.pdf",
            tamano=100,
            hash="a" * 64,
        )

        self.poliza.documento = documento
        self.poliza.save(
            update_fields=[
                "documento",
                "updated_at",
            ]
        )

        persistence_service = Mock()

        result = (
            PortalDocumentApplicationService
            .get_and_persist_policy_document(
                poliza=self.poliza,
                configuration_service=self.configuration_service,
                resolver_factory=self.resolver_factory,
                document_service_factory=(
                    self.document_service_factory
                ),
                persistence_service=persistence_service,
            )
        )

        self.assertEqual(
            result.id,
            documento.id,
        )

        self.document_service.get_policy_documents.assert_not_called()
        persistence_service.persist.assert_not_called()


class PolicyDocumentPersistenceServiceTests(TestCase):
    def setUp(self):
        super().setUp()

        self.media_root = tempfile.mkdtemp()

        self.cliente = Cliente.objects.create(
            tipo_cliente=Cliente.TipoCliente.PERSONA,
            nombre="Miguel",
            email_principal="miguel@example.com",
        )

        self.vehiculo = Vehiculo.objects.create(
            cliente=self.cliente,
            marca_texto="ACURA",
            submarca_texto="TL",
            modelo_anio=2015,
            version="SEDAN 3.7L AUT",
            placas="TR543",
            vin="JH4KA3277KC007500",
        )

        hoy = timezone.localdate()

        self.cotizacion = Cotizacion.objects.create(
            cliente=self.cliente,
            vehiculo=self.vehiculo,
            flotilla=None,
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=hoy,
            vigencia_hasta=hoy + timedelta(days=365),
            forma_pago_preferida="CONTADO",
        )

        self.aseguradora = Aseguradora.objects.create(
            nombre="Chubb Document Persistence Test",
        )

        self.producto = ProductoSeguro.objects.create(
            aseguradora=self.aseguradora,
            nombre_producto="Autos",
            tipo_producto=ProductoSeguro.TipoProducto.AUTO,
            modelo_calculo=ProductoSeguro.ModeloCalculo.SIMPLE,
        )

        self.item = CotizacionItem.objects.create(
            cotizacion=self.cotizacion,
            aseguradora=self.aseguradora,
            producto=self.producto,
            prima_neta=Decimal("35000.00"),
            derechos=Decimal("500.00"),
            iva=Decimal("5680.00"),
            prima_total=Decimal("41180.00"),
            forma_pago="CONTADO",
            provider="CHUBB",
            provider_quote_id="2061261215",
            paquete_nombre="AMPLIA",
        )

        self.poliza = Poliza.objects.create(
            cliente=self.cliente,
            vehiculo=self.vehiculo,
            aseguradora=self.aseguradora,
            producto=self.producto,
            cotizacion_item=self.item,
            numero_poliza="PEND-CHUBB-99007704",
            vigencia_desde=self.cotizacion.vigencia_desde,
            vigencia_hasta=self.cotizacion.vigencia_hasta,
            estatus=Poliza.Estatus.EN_PROCESO,
            prima_neta=Decimal("35247.21"),
            gastos_expedicion=Decimal("600.00"),
            subtotal=Decimal("35847.21"),
            iva=Decimal("5735.56"),
            prima_total=Decimal("41582.77"),
            forma_pago="CONTADO",
        )

        self.policy_document = PolicyDocument(
            order_id="1",
            file_name="M699007704_00001.pdf",
            content=b"%PDF-1.4 test document",
        )
    
    def tearDown(self):
        shutil.rmtree(
            self.media_root,
            ignore_errors=True,
        )
        super().tearDown()

    def test_persist_creates_document_and_links_policy(self):
        with override_settings(
            MEDIA_ROOT=self.media_root,
        ):
            documento = (
                PolicyDocumentPersistenceService.persist(
                    poliza=self.poliza,
                    document=self.policy_document,
                )
            )

            self.poliza.refresh_from_db()

            self.assertEqual(
                self.poliza.documento_id,
                documento.id,
            )
            self.assertEqual(
                documento.nombre_archivo,
                "M699007704_00001.pdf",
            )
            self.assertEqual(
                documento.tipo,
                Documento.Tipo.PDF,
            )
            self.assertEqual(
                documento.tamano,
                len(self.policy_document.content),
            )
            self.assertEqual(
                documento.hash,
                hashlib.sha256(
                    self.policy_document.content
                ).hexdigest(),
            )

            with documento.file.open("rb") as stored_file:
                self.assertEqual(
                    stored_file.read(),
                    self.policy_document.content,
                )

    def test_persist_rejects_empty_content(self):
        document = PolicyDocument(
            order_id="1",
            file_name="policy.pdf",
            content=b"",
        )

        with self.assertRaisesRegex(
            ValueError,
            "no tiene contenido",
        ):
            PolicyDocumentPersistenceService.persist(
                poliza=self.poliza,
                document=document,
            )

    def test_persist_is_idempotent_for_same_document(self):
        with override_settings(
            MEDIA_ROOT=self.media_root,
        ):
            first = PolicyDocumentPersistenceService.persist(
                poliza=self.poliza,
                document=self.policy_document,
            )

            second = PolicyDocumentPersistenceService.persist(
                poliza=self.poliza,
                document=self.policy_document,
            )

            self.assertEqual(first.id, second.id)
            self.assertEqual(
                Documento.objects.count(),
                1,
            )

            self.poliza.refresh_from_db()

            self.assertEqual(
                self.poliza.documento_id,
                first.id,
            )


    def test_persist_rejects_different_existing_document(self):
        with override_settings(
            MEDIA_ROOT=self.media_root,
        ):
            first = PolicyDocumentPersistenceService.persist(
                poliza=self.poliza,
                document=self.policy_document,
            )

            different_document = PolicyDocument(
                order_id="2",
                file_name="different.pdf",
                content=b"%PDF-1.4 different document",
            )

            with self.assertRaisesRegex(
                ValueError,
                "ya tiene un documento diferente",
            ):
                PolicyDocumentPersistenceService.persist(
                    poliza=self.poliza,
                    document=different_document,
                )

            self.assertEqual(
                Documento.objects.count(),
                1,
            )

            self.poliza.refresh_from_db()

            self.assertEqual(
                self.poliza.documento_id,
                first.id,
            )
