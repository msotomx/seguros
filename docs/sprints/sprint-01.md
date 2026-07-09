# Sprint 01

# Primera Cotización End-to-End

## Objetivo

Construir la primera versión funcional del Switchh Insurance Engine (SIE), validando la arquitectura completa del Motor Broker antes de integrar aseguradoras reales.

---

# Resultado

## Arquitectura

- ✅ Insurance Broker
- ✅ Provider Registry
- ✅ Provider Factory
- ✅ Broker Contracts
- ✅ Broker Mappers
- ✅ Chubb Provider
- ✅ Quote Builder
- ✅ Quote Service
- ✅ API Client
- ✅ Quote Mapper
- ✅ Quote Result Mapper

---

## Flujo Validado

```
Cotizacion

↓

BrokerQuoteRequestMapper

↓

BrokerQuoteRequest

↓

InsuranceBroker

↓

ProviderFactory

↓

ChubbProvider

↓

ChubbQuoteService

↓

ChubbQuoteBuilder

↓

FakeChubbApiClient

↓

ChubbQuoteMapper

↓

BrokerQuoteResult

↓

BrokerQuoteResultMapper

↓

CotizacionItem
```

---

## Pruebas

- ✅ check
- ✅ chubb_test
- ✅ provider_test
- ✅ broker_test
- ✅ chubb_quote_chain_test
- ✅ broker_save_mock_quote_test
- ✅ broker_quote_mock_full_test

---

## Documentación

- ✅ docs/architecture
- ✅ docs/development/testing.md

---

## Estado de Chubb

### Funcionando

- OAuth
- Health
- Arquitectura
- Payload Builder
- Mock End-to-End

### Pendiente

Autorización de:

- Business Profiles
- Agents
- Rates
- Groupings
- Packages
- Vehicles

---

## Conclusión

El Sprint 1 concluye con una arquitectura estable, desacoplada y preparada para incorporar múltiples aseguradoras sin modificar el núcleo del Insurance Broker.
