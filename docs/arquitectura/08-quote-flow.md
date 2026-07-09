# 08 - Quote Flow

# Historial del Documento

| Versión | Fecha | Autor | Descripción |
|---------|-------|--------|-------------|
| 1.0 | Julio 2026 | Miguel Soto / ChatGPT | Flujo completo del proceso de cotización del Switchh Insurance Engine. |

---

# Objetivo

Este documento describe el flujo completo de una cotización dentro del **Switchh Insurance Engine (SIE)**.

El objetivo es mostrar cómo una solicitud realizada desde el ERP es transformada, enviada a una aseguradora y convertida nuevamente al modelo de negocio del Broker.

---

# Alcance

Este documento cubre únicamente el proceso de:

```
Cotización de Seguro
```

No incluye:

- Emisión
- Documentos
- Endosos
- Renovaciones
- Cancelaciones

---

# Flujo General

```
ERP

↓

BrokerQuoteRequestMapper

↓

BrokerQuoteRequest

↓

InsuranceBroker

↓

ProviderRegistry

↓

ProviderFactory

↓

ChubbProvider

↓

ChubbQuoteService

↓

ChubbQuoteBuilder

↓

ChubbApiClient

↓

Chubb REST API

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

# Paso 1

## Usuario solicita una cotización

El proceso inicia desde el ERP.

Ejemplo:

```
Portal

↓

Cotizador

↓

Nueva Cotización
```

La información capturada pertenece al dominio del ERP.

Todavía no existen Broker Contracts.

---

# Paso 2

## BrokerQuoteRequestMapper

El ERP convierte sus modelos en un contrato del Broker.

```
Cotizacion

↓

BrokerQuoteRequest
```

El resultado es un objeto completamente independiente del ERP.

---

# Paso 3

## InsuranceBroker

El Broker recibe el BrokerQuoteRequest.

Su responsabilidad consiste en:

- Validar la solicitud.
- Consultar el Provider Registry.
- Ejecutar Providers.
- Consolidar respuestas.

El Broker no conoce aseguradoras específicas.

---

# Paso 4

## Provider Registry

El Registry determina qué Providers pueden atender la solicitud.

Ejemplo:

```
BrokerQuoteRequest

↓

ProviderRegistry

↓

CHUBB
```

En el futuro:

```
CHUBB

QUALITAS

GNP
```

---

# Paso 5

## Provider Factory

El Registry solicita la creación del Provider correspondiente.

```
CHUBB

↓

ProviderFactory

↓

ChubbProvider
```

---

# Paso 6

## Chubb Provider

El Provider representa la interfaz pública de la integración.

Su única responsabilidad consiste en delegar la operación.

```
Broker

↓

ChubbProvider

↓

ChubbQuoteService
```

---

# Paso 7

## Chubb Quote Service

El Service coordina el proceso de cotización.

Responsabilidades:

- Invocar Builder.
- Invocar API Client.
- Invocar Mapper.

No construye JSON.

No interpreta respuestas.

---

# Paso 8

## Chubb Quote Builder

El Builder transforma el contrato del Broker al formato requerido por Chubb.

```
BrokerQuoteRequest

↓

Payload JSON
```

Ejemplo conceptual:

```
Broker Contract

↓

Quote Builder

↓

{
    ...
}
```

---

# Paso 9

## Chubb API Client

El API Client realiza la comunicación HTTP.

Responsabilidades:

- Obtener OAuth Token.
- Configurar Headers.
- Configurar Endpoints.
- Ejecutar POST.
- Manejar Timeouts.
- Manejar Errores HTTP.

No interpreta respuestas.

---

# Paso 10

## Chubb REST API

La aseguradora procesa la solicitud.

Respuesta:

```
JSON
```

---

# Paso 11

## Chubb Quote Mapper

El Mapper interpreta la respuesta.

```
JSON Chubb

↓

BrokerQuoteResult
```

Toda la información queda convertida al lenguaje del Broker.

---

# Paso 12

## Insurance Broker

El Broker recibe uno o varios BrokerQuoteResult.

Si existen múltiples aseguradoras:

```
CHUBB

↓

BrokerQuoteOption

QUALITAS

↓

BrokerQuoteOption

GNP

↓

BrokerQuoteOption
```

El Broker consolida todas las respuestas.

---

# Paso 13

## BrokerQuoteResultMapper

El resultado vuelve al ERP.

```
BrokerQuoteResult

↓

CotizacionItem
```

Ahora el ERP puede almacenar la información en su modelo de datos.

---

# Resultado Final

```
Cliente

↓

Cotización

↓

ERP

↓

Broker

↓

Provider

↓

API

↓

Provider

↓

Broker

↓

ERP

↓

CotizacionItem
```

---

# Flujo Simplificado

```
Cotizacion

↓

BrokerQuoteRequest

↓

InsuranceBroker

↓

ChubbProvider

↓

QuoteService

↓

QuoteBuilder

↓

API Client

↓

REST API

↓

QuoteMapper

↓

BrokerQuoteResult

↓

CotizacionItem
```

---

# Responsabilidades por Capa

| Componente | Responsabilidad |
|------------|-----------------|
| ERP | Capturar información |
| Broker Request Mapper | Convertir a Broker Contracts |
| Insurance Broker | Orquestar |
| Provider Registry | Descubrir Providers |
| Provider Factory | Crear Provider |
| Provider | Delegar |
| Quote Service | Coordinar |
| Quote Builder | Construir payload |
| API Client | Comunicación HTTP |
| REST API | Procesar solicitud |
| Quote Mapper | Interpretar respuesta |
| Broker Result Mapper | Convertir al ERP |

---

# Manejo de Errores

Los errores pueden ocurrir en diferentes niveles.

## Builder

Errores de validación.

---

## API Client

Errores de comunicación.

- Timeout.
- HTTP 500.
- OAuth.
- SSL.

---

## Provider

Errores específicos de la aseguradora.

---

## Broker

Consolida errores provenientes de múltiples Providers.

---

# Escenario Multiaseguradora

```
BrokerQuoteRequest

↓

InsuranceBroker

↓

ProviderRegistry

↓

┌──────────────┬──────────────┬──────────────┐

▼              ▼              ▼

CHUBB      QUALITAS        GNP

▼              ▼              ▼

Quote         Quote         Quote

▼              ▼              ▼

BrokerQuoteOption

BrokerQuoteOption

BrokerQuoteOption

└──────────────┬──────────────┘

↓

BrokerQuoteResult
```

El ERP continúa utilizando exactamente la misma interfaz.

---

# Beneficios

Este flujo proporciona:

- Desacoplamiento entre ERP y aseguradoras.
- Incorporación sencilla de nuevos Providers.
- Un único modelo de negocio.
- Reutilización del Engine.
- Bajo acoplamiento.
- Alta mantenibilidad.

---

# Principios Arquitectónicos

Durante todo el proceso se respetan las siguientes reglas:

- El ERP nunca conoce APIs.
- El Broker nunca conoce JSON.
- Los Providers nunca conocen Django.
- Los Builders únicamente construyen solicitudes.
- Los Mappers únicamente interpretan respuestas.
- El API Client únicamente realiza comunicación HTTP.

---

# Conclusión

El proceso de cotización constituye el principal caso de uso del Switchh Insurance Engine.

Gracias a la separación entre Broker, Providers, Builders, API Client y Mappers, el sistema puede integrar múltiples aseguradoras utilizando una arquitectura uniforme y un único modelo de negocio.

Esta arquitectura permite incorporar nuevas aseguradoras sin modificar el ERP ni el núcleo del Insurance Broker.
