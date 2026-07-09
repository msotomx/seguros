# 06 - Insurance Providers

# Historial del Documento

| Versión | Fecha | Autor | Descripción |
|---------|-------|--------|-------------|
| 1.0 | Julio 2026 | Miguel Soto / ChatGPT | Definición de la arquitectura de Insurance Providers. |

---

# Objetivo

Los **Insurance Providers** son los componentes responsables de integrar el Switchh Insurance Engine (SIE) con las APIs de las aseguradoras.

Cada Provider encapsula completamente las particularidades técnicas de una aseguradora.

Desde la perspectiva del Insurance Broker, todos los Providers funcionan exactamente igual.

---

# Filosofía

El Broker nunca conoce:

- Endpoints REST
- JSON
- OAuth
- Tokens
- Headers HTTP
- Formatos de respuesta
- Códigos de error

Todo ese conocimiento pertenece exclusivamente al Provider.

---

# Arquitectura

```
Insurance Broker

        │

        ▼

Insurance Provider

        │

        ▼

Quote Service

        │

        ▼

Quote Builder

        │

        ▼

API Client

        │

        ▼

REST API
```

Respuesta

```
REST API

        │

        ▼

API Client

        │

        ▼

Quote Mapper

        │

        ▼

Quote Service

        │

        ▼

Insurance Provider

        │

        ▼

Insurance Broker
```

---

# Responsabilidad

Cada Provider es responsable de:

- Autenticación.
- Construcción de solicitudes.
- Consumo de APIs.
- Interpretación de respuestas.
- Conversión al Modelo de Dominio.
- Manejo de errores propios del proveedor.

---

# No es responsabilidad del Provider

El Provider nunca deberá:

- Conocer modelos Django.
- Conocer el ORM.
- Tomar decisiones de negocio.
- Seleccionar aseguradoras.
- Comparar cotizaciones.
- Persistir información.

Estas responsabilidades pertenecen al Broker y al ERP.

---

# Estructura

Cada aseguradora implementará exactamente la misma estructura.

```
providers/

    insurance/

        chubb/

            auth.py

            api_client.py

            endpoints.py

            exceptions.py

            provider.py

            builders/

                quote_builder.py

                issue_builder.py

                ...

            mappers/

                quote_mapper.py

                policy_mapper.py

                ...

            services/

                quote_service.py

                issue_service.py

                ...
```

---

# Provider

Representa la implementación pública de la aseguradora.

Ejemplo

```
ChubbProvider
```

Responsabilidades:

- Exponer la interfaz del Provider.
- Delegar la operación al Service correspondiente.
- No contener lógica de integración.

Ejemplo conceptual

```
Broker

↓

ChubbProvider

↓

QuoteService
```

---

# Services

Cada Service representa un caso de uso.

Ejemplos

```
QuoteService

IssueService

DocumentService

CatalogService
```

Un Service coordina:

- Builder
- API Client
- Mapper

No construye JSON.

No interpreta respuestas.

---

# Builders

Los Builders convierten los contratos del Broker al formato esperado por la aseguradora.

Ejemplo

```
BrokerQuoteRequest

↓

ChubbQuoteBuilder

↓

JSON Chubb
```

Responsabilidad única:

Construir solicitudes.

---

# API Client

El API Client realiza exclusivamente la comunicación HTTP.

Responsabilidades:

- OAuth.
- Tokens.
- Headers.
- Requests.
- Timeouts.
- Retries.
- Manejo HTTP.

Nunca interpreta respuestas del negocio.

---

# Mappers

Los Mappers convierten las respuestas de la aseguradora en contratos del Broker.

Ejemplo

```
JSON Chubb

↓

ChubbQuoteMapper

↓

BrokerQuoteResult
```

Responsabilidad única:

Interpretar respuestas.

---

# Exceptions

Cada Provider define sus propias excepciones.

Ejemplo

```
ChubbProviderError

ChubbAuthenticationError

ChubbAuthorizationError

ChubbApiError

ChubbTimeoutError
```

Estas excepciones son posteriormente traducidas por el Broker a errores comunes.

---

# Flujo de Cotización

```
BrokerQuoteRequest

↓

Insurance Broker

↓

ChubbProvider

↓

QuoteService

↓

QuoteBuilder

↓

API Client

↓

POST /quote

↓

JSON

↓

QuoteMapper

↓

BrokerQuoteResult
```

---

# Flujo de Emisión

```
BrokerIssueRequest

↓

Insurance Broker

↓

ChubbProvider

↓

IssueService

↓

IssueBuilder

↓

API Client

↓

POST /issue

↓

PolicyMapper

↓

BrokerIssuedPolicy
```

---

# Agregar una Nueva Aseguradora

Para incorporar una nueva aseguradora se deberá:

1. Crear un nuevo Provider.

```
qualitas/
```

2. Implementar la interfaz InsuranceProvider.

3. Crear:

- Builders
- Services
- API Client
- Mappers
- Exceptions

4. Registrar el Provider en el Provider Registry.

No será necesario modificar:

- Insurance Broker
- ERP
- Contratos

---

# Ejemplo

```
providers/

    insurance/

        qualitas/

            provider.py

            api_client.py

            builders/

            mappers/

            services/
```

El Broker continuará funcionando exactamente igual.

---

# Beneficios

Esta arquitectura proporciona:

- Desacoplamiento.
- Reutilización.
- Fácil mantenimiento.
- Integraciones independientes.
- Incorporación sencilla de nuevas aseguradoras.
- Pruebas unitarias aisladas.

---

# Reglas Arquitectónicas

## Regla 1

Un Provider representa exactamente una aseguradora.

---

## Regla 2

Un Provider nunca conoce modelos Django.

---

## Regla 3

Un Provider únicamente trabaja con Broker Contracts.

---

## Regla 4

Los Builders únicamente construyen solicitudes.

---

## Regla 5

Los Mappers únicamente interpretan respuestas.

---

## Regla 6

El API Client únicamente realiza comunicación HTTP.

---

## Regla 7

Toda lógica específica de una aseguradora permanece encapsulada dentro del Provider.

---

# Evolución

Actualmente el primer Provider implementado es:

```
ChubbProvider
```

En futuras versiones se incorporarán:

- Quálitas
- GNP
- AXA
- HDI
- MAPFRE

Todos siguiendo exactamente la misma arquitectura.

---

# Objetivo Final

Los Insurance Providers permiten que el Switchh Insurance Engine se comunique con múltiples aseguradoras utilizando una arquitectura uniforme.

Cada Provider encapsula completamente la complejidad técnica de una integración específica, permitiendo que el Insurance Broker opere utilizando un único modelo de negocio y una interfaz común para todas las aseguradoras.

La incorporación de nuevos Providers deberá realizarse sin modificar el núcleo del Engine, garantizando una arquitectura escalable, mantenible y preparada para el crecimiento del ecosistema Switchh.
