# 09 - Policy Issue Flow

# Historial del Documento

| Versión | Fecha | Autor | Descripción |
|---------|-------|--------|-------------|
| 1.0 | Julio 2026 | Miguel Soto / ChatGPT | Flujo completo del proceso de emisión de pólizas del Switchh Insurance Engine. |

---

# Objetivo

Este documento describe el flujo completo de emisión de una póliza dentro del **Switchh Insurance Engine (SIE)**.

La emisión comienza cuando el usuario selecciona una cotización previamente obtenida y solicita convertirla en una póliza.

---

# Alcance

Este documento cubre únicamente el proceso de:

```
Emisión de Póliza
```

No incluye:

- Cotización
- Documentos
- Endosos
- Renovaciones
- Cancelaciones

---

# Flujo General

```
ERP

↓

BrokerIssueRequestMapper

↓

BrokerIssueRequest

↓

InsuranceBroker

↓

ProviderRegistry

↓

ProviderFactory

↓

InsuranceProvider

↓

IssueService

↓

IssueBuilder

↓

API Client

↓

REST API

↓

Policy Mapper

↓

BrokerIssuedPolicy

↓

BrokerIssuedPolicyMapper

↓

Poliza
```

---

# Precondición

Debe existir una cotización válida.

```
Cotización

↓

Cliente selecciona opción

↓

Emitir
```

La cotización contiene:

- Provider
- Producto
- Prima
- Vigencia
- Provider Quote Id

---

# Paso 1

## Selección de la Cotización

El usuario selecciona una opción.

Ejemplo:

```
CHUBB

Premium Plus

$12,450
```

El ERP identifica:

- Provider
- Provider Quote Id

---

# Paso 2

## BrokerIssueRequestMapper

El ERP transforma la información en un contrato del Broker.

```
CotizacionItem

↓

BrokerIssueRequest
```

---

# Paso 3

## InsuranceBroker

El Broker recibe la solicitud.

Responsabilidades:

- Validar la petición.
- Localizar el Provider.
- Ejecutar el proceso de emisión.

---

# Paso 4

## Provider Registry

El Registry localiza el Provider.

```
Provider = CHUBB

↓

ChubbProvider
```

---

# Paso 5

## Provider Factory

Se crea la instancia correspondiente.

```
CHUBB

↓

ProviderFactory

↓

ChubbProvider
```

---

# Paso 6

## ChubbProvider

El Provider únicamente delega.

```
BrokerIssueRequest

↓

IssueService
```

---

# Paso 7

## Issue Service

Coordina el proceso.

Responsabilidades:

- Builder
- API Client
- Mapper

No construye JSON.

No interpreta respuestas.

---

# Paso 8

## Issue Builder

Construye el payload requerido por la aseguradora.

```
BrokerIssueRequest

↓

JSON
```

Ejemplo conceptual

```
Provider Quote Id

↓

Payload de Emisión
```

---

# Paso 9

## API Client

Realiza la comunicación HTTP.

Responsabilidades:

- OAuth
- Headers
- Endpoint
- POST
- Timeout
- Retries

---

# Paso 10

## REST API

La aseguradora procesa la emisión.

Respuesta esperada

```
Número de póliza

Vigencias

Prima

Identificador interno
```

---

# Paso 11

## Policy Mapper

Transforma la respuesta.

```
JSON

↓

BrokerIssuedPolicy
```

---

# Paso 12

## InsuranceBroker

Recibe la póliza emitida.

No realiza modificaciones.

Simplemente entrega el resultado al ERP.

---

# Paso 13

## BrokerIssuedPolicyMapper

Convierte el contrato del Broker al modelo Django.

```
BrokerIssuedPolicy

↓

Poliza
```

La póliza queda almacenada.

---

# Resultado Final

```
CotizacionItem

↓

BrokerIssueRequest

↓

InsuranceBroker

↓

Provider

↓

IssueService

↓

IssueBuilder

↓

REST API

↓

PolicyMapper

↓

BrokerIssuedPolicy

↓

Poliza
```

---

# Responsabilidades por Capa

| Componente | Responsabilidad |
|------------|-----------------|
| ERP | Solicitar emisión |
| IssueRequestMapper | Crear contrato |
| InsuranceBroker | Orquestar |
| ProviderRegistry | Descubrir Provider |
| ProviderFactory | Crear instancia |
| Provider | Delegar |
| IssueService | Coordinar |
| IssueBuilder | Construir payload |
| API Client | Comunicación HTTP |
| REST API | Emitir póliza |
| PolicyMapper | Interpretar respuesta |
| IssuedPolicyMapper | Persistir en ERP |

---

# Manejo de Errores

Errores posibles:

## Builder

- Datos incompletos.
- Validaciones.

---

## API Client

- Timeout.
- OAuth.
- SSL.
- HTTP.

---

## Provider

Errores propios de la aseguradora.

Ejemplo

```
Quote Expirada

Producto inválido

Prima modificada
```

---

## Broker

El Broker traduce los errores al modelo común del Engine.

---

# Contratos Utilizados

```
BrokerIssueRequest

↓

BrokerIssuedPolicy
```

Estos contratos son independientes de cualquier aseguradora.

---

# Flujo Simplificado

```
BrokerIssueRequest

↓

InsuranceBroker

↓

InsuranceProvider

↓

IssueService

↓

IssueBuilder

↓

API Client

↓

REST API

↓

PolicyMapper

↓

BrokerIssuedPolicy

↓

Poliza
```

---

# Beneficios

La arquitectura proporciona:

- Emisión uniforme.
- Bajo acoplamiento.
- Reutilización.
- Escalabilidad.
- Fácil incorporación de nuevas aseguradoras.

---

# Principios Arquitectónicos

Durante el proceso se mantienen las siguientes reglas:

- El ERP nunca conoce APIs.
- El Broker nunca construye JSON.
- El Provider nunca conoce Django.
- Los Builders únicamente construyen solicitudes.
- Los Mappers únicamente interpretan respuestas.
- El API Client únicamente comunica con la aseguradora.

---

# Escenario Futuro

Cuando existan múltiples aseguradoras:

```
BrokerIssueRequest

↓

InsuranceBroker

↓

ProviderRegistry

↓

ProviderFactory

↓

CHUBB

QUALITAS

GNP

↓

Provider correspondiente

↓

BrokerIssuedPolicy
```

El flujo permanecerá idéntico.

La única diferencia será el Provider seleccionado.

---

# Resultado Esperado

Una emisión exitosa produce:

- Número de póliza.
- Vigencia.
- Prima.
- Identificador del Provider.
- Documento de póliza (cuando aplique).

Toda esta información queda encapsulada dentro del contrato:

```
BrokerIssuedPolicy
```

Posteriormente el ERP decide cómo almacenarla.

---

# Conclusión

La emisión de pólizas constituye el segundo proceso principal del Switchh Insurance Engine.

El flujo mantiene la misma filosofía utilizada durante la cotización:

- Un único modelo de dominio.
- Una única interfaz para el ERP.
- Providers intercambiables.
- Separación estricta de responsabilidades.

Esta consistencia permitirá incorporar nuevas aseguradoras sin modificar el Insurance Broker ni el ERP, garantizando una arquitectura escalable y preparada para la evolución del negocio.
