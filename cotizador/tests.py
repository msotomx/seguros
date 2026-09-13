import json
from decimal import Decimal
from datetime import timedelta, date
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from unittest.mock import Mock

from autos.models import Vehiculo, VehiculoCatalogo, Marca, SubMarca
from crm.models import Cliente

from cotizador.models import (
    Cotizacion,
    CotizacionItem,
    CotizacionProveedor,
    CotizacionProveedorCobertura,
    CotizacionProveedorOpcion,
    CotizacionProveedorRiesgo,
    CotizacionProveedorPersona,
)
from cotizador.services.quote_persistence_service import (
    QuotePersistenceService,
)
from cotizador.services.provider_quote_service import (
    CotizacionProviderService,
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
            message="Timeout consultando proveedor.",
            error_type="TimeoutError",
            retryable=True,
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
            "Timeout consultando proveedor.",
        )
        self.assertEqual(
            registro.error_type,
            "TimeoutError",
        )
        self.assertTrue(
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
            request_json=request_json,
        )

        quote_service.quote_one.assert_called_once_with(
            "CHUBB",
            self.request,
        )

        persistence_service.persist.assert_called_once_with(
            cotizacion=self.cotizacion,
            attempt=attempt,
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
