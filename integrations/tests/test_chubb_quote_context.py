from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase

from integrations.catalog.contracts import (
    ProviderCatalogValue,
)
from integrations.providers.chubb.context import (
    ChubbQuoteContextResolver,
)
from integrations.providers.contracts import (
    QuoteInsured,
    QuoteRequest,
    QuoteVehicle,
)
from integrations.providers.exceptions import (
    ProviderQuoteContextError,
)


class ChubbQuoteContextResolverTest(SimpleTestCase):
    def setUp(self):
        self.configuration = SimpleNamespace(
            id=1,
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            settings={
                "PRODUCT_ID": 1,
                "BUSINESS_PROFILE_ID": 7190,
                "AGENT_ID": 93300,
                "CONDUIT_ID": 0,
                "GROUPING_ID": 353796,
                "RATE_ID": 453,
                "CALCULATION_TYPE_ID": 2,
                "CURRENCY_ID": 1,
                "INSURED_AMOUNT_TYPE_ID": 1,
                "DEDUCTIBLE_TYPE_ID": 1,
                "SOURCE_APPLICATION": 23,
            },
        )

        self.configuration_service = Mock()
        self.configuration_service.get_active.return_value = (
            self.configuration
        )

        self.catalog_service = Mock()

        mappings = {
            ("VEHICLE", "ADVANCE"): self._mapping(
                catalog="VEHICLE",
                internal="ADVANCE",
                external="01140300301",
                metadata={"vehicle_id": 1146},
            ),
            ("VEHICLE_USE", "PARTICULAR"): self._mapping(
                catalog="VEHICLE_USE",
                internal="PARTICULAR",
                external="1",
            ),
            ("PAYMENT_FREQUENCY", "ANNUAL"): self._mapping(
                catalog="PAYMENT_FREQUENCY",
                internal="ANNUAL",
                external="12",
            ),
            (
                "COVERAGE_PACKAGE",
                "COMPREHENSIVE",
            ): self._mapping(
                catalog="COVERAGE_PACKAGE",
                internal="COMPREHENSIVE",
                external="1",
            ),
            ("STATE", "CHH"): self._mapping(
                catalog="STATE",
                internal="CHH",
                external="1",
            ),
            ("MUNICIPALITY", "CHIHUAHUA"): self._mapping(
                catalog="MUNICIPALITY",
                internal="CHIHUAHUA",
                external="42",
            ),
        }

        self.catalog_service.to_provider.side_effect = (
            lambda provider_id, catalog_code, internal_code:
            mappings[(catalog_code, internal_code)]
        )

        self.resolver = ChubbQuoteContextResolver(
            provider_id=1,
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            configuration_service=self.configuration_service,
            catalog_service=self.catalog_service,
        )

        self.request = QuoteRequest(
            provider_id=1,
            vehicle=QuoteVehicle(
                year=2024,
                brand_code="NISSAN",
                model_code="VERSA",
                version_code="ADVANCE",
                use_code="PARTICULAR",
                postal_code="31000",
            ),
            insured=QuoteInsured(
                person_type="INDIVIDUAL",
                first_name="Miguel",
                last_name="Soto",
            ),
            start_date=date(2026, 7, 11),
            end_date=date(2027, 7, 11),
            payment_frequency_code="ANNUAL",
            coverage_code="COMPREHENSIVE",
            metadata={
                "state_code": "CHH",
                "municipality_code": "CHIHUAHUA",
            },
        )

    @staticmethod
    def _mapping(
        *,
        catalog,
        internal,
        external,
        metadata=None,
    ):
        return ProviderCatalogValue(
            provider_id=1,
            catalog_code=catalog,
            internal_code=internal,
            internal_name=internal,
            external_code=external,
            external_name=internal,
            metadata=metadata or {},
        )

    def test_resolves_context(self):
        context = self.resolver.resolve(
            request=self.request,
        )

        self.assertEqual(context.product_id, 1)
        self.assertEqual(
            context.business_profile_id,
            7190,
        )
        self.assertEqual(context.vehicle_key, "01140300301")
        self.assertEqual(context.vehicle_id, 1146)
        self.assertEqual(context.vehicle_use_id, 1)
        self.assertEqual(context.payment_type_id, 12)
        self.assertEqual(context.package_id, 1)
        self.assertEqual(context.country_subdivision_id, 1)
        self.assertEqual(context.municipality_id, 42)
        self.assertEqual(context.source_application, 23)
        self.assertEqual(
            context.prospect_name,
            "Miguel Soto",
        )

    def test_loads_active_configuration(self):
        self.resolver.resolve(
            request=self.request,
        )

        self.configuration_service.get_active.assert_called_once_with(
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
        )

    def test_rejects_missing_location_metadata(self):
        request = QuoteRequest(
            provider_id=1,
            vehicle=self.request.vehicle,
            insured=self.request.insured,
            start_date=self.request.start_date,
            end_date=self.request.end_date,
            payment_frequency_code="ANNUAL",
            coverage_code="COMPREHENSIVE",
            metadata={},
        )

        with self.assertRaises(
            ProviderQuoteContextError
        ):
            self.resolver.resolve(
                request=request,
            )

    def test_rejects_missing_required_setting(self):
        del self.configuration.settings["RATE_ID"]

        with self.assertRaises(
            ProviderQuoteContextError
        ):
            self.resolver.resolve(
                request=self.request,
            )

    def test_rejects_configuration_for_another_id(self):
        self.configuration.id = 99

        with self.assertRaises(
            ProviderQuoteContextError
        ):
            self.resolver.resolve(
                request=self.request,
            )

    def test_rejects_vehicle_without_vehicle_id_metadata(self):
        self.catalog_service.to_provider.side_effect = None
        self.catalog_service.to_provider.return_value = (
            self._mapping(
                catalog="VEHICLE",
                internal="ADVANCE",
                external="01140300301",
                metadata={},
            )
        )

        with self.assertRaises(
            ProviderQuoteContextError
        ):
            self.resolver.resolve(
                request=self.request,
            )
            