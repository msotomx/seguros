# 07 - Mappers & Builders

# Historial del Documento

| Versión | Fecha | Autor | Descripción |
|---------|-------|--------|-------------|
| 1.0 | Julio 2026 | Miguel Soto / ChatGPT | Arquitectura de Mappers y Builders del Switchh Insurance Engine. |

---

# Objetivo

Este documento define la responsabilidad de los **Broker Mappers**, **Provider Builders** y **Provider Mappers**.

Estos tres componentes constituyen la capa de transformación de datos del Switchh Insurance Engine (SIE).

Su objetivo es mantener completamente desacoplados:

- El ERP de Switchh Seguros.
- El Motor Broker.
- Las APIs de las aseguradoras.

---

# Filosofía

Todo dato que entra o sale del Engine debe pasar por un componente especializado.

Nunca debe existir código que mezcle:

- Modelos Django
- Contratos del Broker
- JSON de una aseguradora

Cada transformación tiene un responsable claramente definido.

---

# Arquitectura General

```
                 ERP Django

                     │

                     ▼

        Broker Request Mapper

                     │

                     ▼

          Broker Contracts

                     │

                     ▼

           Insurance Broker

                     │

                     ▼

          Provider Builder

                     │

                     ▼

          JSON Aseguradora

                     │

                     ▼

               API REST

                     │

                     ▼

          JSON Aseguradora

                     │

                     ▼

           Provider Mapper

                     │

                     ▼

          Broker Contracts

                     │

                     ▼

       Broker Response Mapper

                     │

                     ▼

              ERP Django
```

---

# Capas de Transformación

El Engine define tres tipos de transformaciones.

| Componente | Transforma |
|------------|------------|
| Broker Mapper | Django ⇄ Broker Contracts |
| Provider Builder | Broker Contracts → Provider |
| Provider Mapper | Provider → Broker Contracts |

Cada una tiene una responsabilidad distinta.

---

# Broker Mappers

## Objetivo

Transformar modelos del ERP en contratos del Broker y viceversa.

## Ubicación

```
integrations/
└── broker/
    └── mappers/
```

---

## Flujo

```
Cotizacion

↓

BrokerQuoteRequest
```

o

```
BrokerIssuedPolicy

↓

Poliza
```

---

## Responsabilidades

Los Broker Mappers:

- Conocen Django.
- Conocen los modelos del ERP.
- Conocen los Broker Contracts.
- No conocen aseguradoras.
- No conocen JSON.
- No realizan llamadas HTTP.

---

## Ejemplos

```
BrokerQuoteRequestMapper

BrokerQuoteResultMapper

BrokerIssueRequestMapper

BrokerIssuedPolicyMapper

BrokerPaymentMapper

BrokerEndorsementMapper
```

---

# Provider Builders

## Objetivo

Construir el payload requerido por una aseguradora.

## Ubicación

```
integrations/
└── providers/
    └── insurance/
        └── chubb/
            └── builders/
```

---

## Flujo

```
BrokerQuoteRequest

↓

ChubbQuoteBuilder

↓

JSON Chubb
```

---

## Responsabilidades

Los Builders:

- Conocen la API de la aseguradora.
- Conocen Broker Contracts.
- Construyen payloads.
- No conocen Django.
- No realizan llamadas HTTP.
- No interpretan respuestas.

---

## Ejemplos

```
ChubbQuoteBuilder

ChubbIssueBuilder

ChubbDocumentBuilder
```

---

# Provider Mappers

## Objetivo

Interpretar respuestas de una aseguradora.

## Ubicación

```
integrations/
└── providers/
    └── insurance/
        └── chubb/
            └── mappers/
```

---

## Flujo

```
JSON Chubb

↓

ChubbQuoteMapper

↓

BrokerQuoteResult
```

---

## Responsabilidades

Los Provider Mappers:

- Conocen el formato de respuesta del Provider.
- Conocen Broker Contracts.
- No conocen Django.
- No realizan llamadas HTTP.
- No construyen payloads.

---

## Ejemplos

```
ChubbQuoteMapper

ChubbPolicyMapper

ChubbDocumentMapper
```

---

# Diferencias

| Característica | Broker Mapper | Provider Builder | Provider Mapper |
|---------------|---------------|------------------|-----------------|
| Conoce Django | Sí | No | No |
| Conoce Broker Contracts | Sí | Sí | Sí |
| Conoce Provider | No | Sí | Sí |
| Construye JSON | No | Sí | No |
| Interpreta JSON | No | No | Sí |
| Llama APIs | No | No | No |

---

# Flujo Completo de Cotización

```
Cotizacion (Django)

↓

BrokerQuoteRequestMapper

↓

BrokerQuoteRequest

↓

InsuranceBroker

↓

ChubbProvider

↓

ChubbQuoteService

↓

ChubbQuoteBuilder

↓

Payload JSON

↓

ChubbApiClient

↓

POST /quote

↓

JSON Response

↓

ChubbQuoteMapper

↓

BrokerQuoteResult

↓

BrokerQuoteResultMapper

↓

CotizacionItem (Django)
```

---

# Flujo Completo de Emisión

```
CotizacionItem

↓

BrokerIssueRequestMapper

↓

BrokerIssueRequest

↓

InsuranceBroker

↓

ChubbProvider

↓

ChubbIssueService

↓

ChubbIssueBuilder

↓

Payload JSON

↓

ChubbApiClient

↓

POST /issue

↓

JSON Response

↓

ChubbPolicyMapper

↓

BrokerIssuedPolicy

↓

BrokerIssuedPolicyMapper

↓

Poliza
```

---

# Ejemplo Correcto

## Builder

```python
class ChubbQuoteBuilder:

    def build(self, request: BrokerQuoteRequest) -> dict:

        return {
            "vehicle": {
                "brand": request.vehiculo.marca,
                "model": request.vehiculo.submarca
            }
        }
```

---

## Mapper

```python
class ChubbQuoteMapper:

    def map(self, response) -> BrokerQuoteResult:

        ...
```

---

## Service

```python
class ChubbQuoteService:

    def create_quote(self, request):

        payload = self.builder.build(request)

        response = self.client.post_quote(payload)

        return self.mapper.map(response)
```

---

# Ejemplo Incorrecto

```python
class ChubbQuoteService:

    def create_quote(self, request):

        payload = {
            ...
        }

        response = requests.post(...)

        return BrokerQuoteResult(...)
```

Este código mezcla responsabilidades:

- Construcción del payload.
- Comunicación HTTP.
- Interpretación de respuesta.

Debe evitarse.

---

# Convenciones

## Broker Mappers

```
BrokerQuoteRequestMapper

BrokerQuoteResultMapper

BrokerIssueRequestMapper

BrokerIssuedPolicyMapper
```

---

## Provider Builders

```
ChubbQuoteBuilder

QualitasQuoteBuilder

GnpQuoteBuilder

AxaQuoteBuilder
```

---

## Provider Mappers

```
ChubbQuoteMapper

QualitasQuoteMapper

GnpQuoteMapper

AxaQuoteMapper
```

---

# Reglas Arquitectónicas

## Regla 1

Los Broker Mappers únicamente conectan el ERP con el Broker.

---

## Regla 2

Los Builders únicamente construyen solicitudes.

---

## Regla 3

Los Provider Mappers únicamente interpretan respuestas.

---

## Regla 4

Los Services únicamente orquestan.

---

## Regla 5

El API Client únicamente comunica con la API.

---

## Regla 6

Ningún componente debe asumir responsabilidades de otro.

---

# Beneficios

Esta arquitectura proporciona:

- Separación clara de responsabilidades.
- Fácil mantenimiento.
- Bajo acoplamiento.
- Reutilización.
- Pruebas unitarias sencillas.
- Integración uniforme entre aseguradoras.

---

# Conclusión

La separación entre Broker Mappers, Provider Builders y Provider Mappers constituye uno de los pilares fundamentales del Switchh Insurance Engine.

Gracias a esta arquitectura, el Engine puede integrar múltiples aseguradoras manteniendo un único modelo de negocio, permitiendo que el ERP permanezca completamente independiente de las particularidades técnicas de cada proveedor.
