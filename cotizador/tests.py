import json
from decimal import Decimal
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from unittest.mock import Mock

from autos.models import Vehiculo, VehiculoCatalogo, Marca, SubMarca
from crm.models import Cliente

from cotizador.models import (
    Cotizacion,
    CotizacionProveedor,
    CotizacionProveedorCobertura,
    CotizacionProveedorOpcion,
    CotizacionProveedorRiesgo,
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
            ciudad="CHIHUAHUA",
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
                "CHIHUAHUA",
            ): "369",
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
            "369",
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
            ("MUNICIPALITY", "CHIHUAHUA"): "369",
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
            estado="CHIHUAHUA",
            ciudad="CHIHUAHUA",
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
                "CHIHUAHUA",
                "Chihuahua",
                "369",
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
            369,
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

