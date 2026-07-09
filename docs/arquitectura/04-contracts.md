# 04 - Broker Contracts

# Historial del Documento

| Versión | Fecha | Autor | Descripción |
|---------|-------|--------|-------------|
| 1.0 | Julio 2026 | Miguel Soto / ChatGPT | Especificación de los contratos del Switchh Insurance Engine. |

---

# Objetivo

Los **Broker Contracts** constituyen el lenguaje oficial utilizado por el Switchh Insurance Engine (SIE).

Todos los componentes internos del Engine intercambian información utilizando estos contratos.

Los contratos son independientes de:

- Django
- Base de datos
- APIs REST
- JSON
- Chubb
- Quálitas
- GNP
- AXA

Su propósito es representar únicamente conceptos del negocio de seguros.

---

# Principios

Todo contrato deberá cumplir las siguientes reglas:

- Representar un concepto del negocio.
- No contener lógica de negocio.
- Ser independiente de cualquier Provider.
- Ser reutilizable.
- Mantener compatibilidad hacia atrás cuando sea posible.

---

# Flujo General

```
ERP

↓

Broker Request Mapper

↓

Broker Contracts

↓

Insurance Broker

↓

Providers

↓

APIs
```

---

# Contratos Disponibles

Actualmente el Engine define los siguientes contratos.

| Contrato | Propósito |
|-----------|-----------|
| BrokerCustomerData | Información del cliente |
| BrokerVehicleData | Información del vehículo |
| BrokerQuoteRequest | Solicitud de cotización |
| BrokerQuoteOption | Opción de cotización |
| BrokerQuoteResult | Resultado consolidado |
| BrokerIssueRequest | Solicitud de emisión |
| BrokerIssuedPolicy | Póliza emitida |
| BrokerPolicyDocument | Documento |
| BrokerPaymentLink | Enlace de pago |
| Coverage | Cobertura |
| Deductible | Deducible |

---

# BrokerCustomerData

Representa al cliente asegurado.

## Responsabilidad

Contener únicamente la información del cliente requerida por el Broker.

## Campos

| Campo | Tipo | Descripción |
|--------|------|-------------|
| tipo_cliente | str | Individual o Empresa |
| nombre | str | Nombre completo |
| email | str | Correo electrónico |
| telefono | str | Teléfono |
| codigo_postal | str | Código Postal |
| ciudad | str | Ciudad |
| estado | str | Estado |
| nombre_comercial | str | Empresa |

---

# BrokerVehicleData

Representa el vehículo asegurado.

## Campos

| Campo | Tipo |
|--------|------|
| tipo_uso | str |
| anio | int |
| marca | str |
| submarca | str |
| version | str |
| placas | str |
| vin | str |
| codigo_postal | str |

---

# BrokerQuoteRequest

Representa una solicitud de cotización.

## Relaciones

```
BrokerQuoteRequest

│

├── BrokerCustomerData

└── BrokerVehicleData
```

## Campos

| Campo | Tipo |
|--------|------|
| cotizacion_id | int |
| cliente | BrokerCustomerData |
| vehiculo | BrokerVehicleData |
| vigencia_desde | date |
| vigencia_hasta | date |
| forma_pago | str |
| notas | str |
| raw | dict |

---

# Coverage

Representa una cobertura.

## Campos

| Campo | Tipo |
|--------|------|
| name | str |
| insured_amount | Decimal |
| deductible | str |

---

# Deductible

Representa un deducible.

## Campos

| Campo | Tipo |
|--------|------|
| coverage | str |
| value | str |

---

# BrokerQuoteOption

Representa una propuesta generada por un Provider.

## Campos

| Campo | Tipo |
|--------|------|
| provider | str |
| provider_quote_id | str |
| product_name | str |
| package_name | str |
| currency | str |
| prima_total | Decimal |
| prima_neta | Decimal |
| derechos | Decimal |
| iva | Decimal |
| recargos | Decimal |
| payment_type | str |
| valid_until | date |
| coverages | list[Coverage] |
| deductibles | list[Deductible] |
| raw_response | dict |

---

# BrokerQuoteResult

Resultado consolidado de una cotización.

## Relaciones

```
BrokerQuoteResult

│

├── BrokerQuoteOption

└── Errors
```

## Campos

| Campo | Tipo |
|--------|------|
| request | BrokerQuoteRequest |
| options | list[BrokerQuoteOption] |
| errors | list |

## Propiedad

```
ok
```

Indica si la cotización contiene al menos una opción válida.

---

# BrokerIssueRequest

Representa la solicitud de emisión.

## Campos

| Campo | Tipo |
|--------|------|
| provider | str |
| provider_quote_id | str |
| cotizacion_item_id | int |
| cliente_id | int |
| vehiculo_id | int |
| payment_type | str |
| raw | dict |

---

# BrokerIssuedPolicy

Representa una póliza emitida.

## Campos

| Campo | Tipo |
|--------|------|
| provider | str |
| policy_number | str |
| provider_policy_id | str |
| issued_at | datetime |
| vigencia_desde | date |
| vigencia_hasta | date |
| prima_total | Decimal |
| raw_response | dict |

---

# BrokerPolicyDocument

Representa un documento emitido por una aseguradora.

## Ejemplos

- Póliza PDF
- Carátula
- Condiciones Generales
- Recibo

## Campos

| Campo | Tipo |
|--------|------|
| provider | str |
| policy_number | str |
| document_type | str |
| filename | str |
| content_type | str |
| content_base64 | str |
| download_url | str |
| raw_response | dict |

---

# BrokerPaymentLink

Representa un enlace de pago.

## Campos

| Campo | Tipo |
|--------|------|
| provider | str |
| provider_quote_id | str |
| provider_policy_id | str |
| url | str |
| expires_at | datetime |
| raw_response | dict |

---

# Convenciones

Todos los contratos deberán seguir las siguientes reglas.

## Sin lógica

Los contratos nunca contienen reglas de negocio.

---

## Sin llamadas HTTP

Los contratos nunca realizan llamadas a APIs.

---

## Sin acceso a base de datos

Los contratos nunca conocen Django ORM.

---

## Sin dependencias de Providers

No contienen información específica de Chubb, Quálitas o cualquier otra aseguradora.

---

## Inmutabilidad lógica

Una vez construido un contrato, deberá representar fielmente el estado de una operación.

---

# Evolución

Cuando el Engine incorpore nuevas funcionalidades podrán agregarse nuevos contratos.

Ejemplos:

```
BrokerEndorsementRequest

BrokerEndorsementResult

BrokerRenewRequest

BrokerRenewResult

BrokerClaimRequest

BrokerClaimResult
```

Siempre manteniendo compatibilidad con los contratos existentes.

---

# Conclusión

Los Broker Contracts representan el núcleo del lenguaje utilizado por el Switchh Insurance Engine.

Toda comunicación entre el ERP y los Providers deberá realizarse utilizando exclusivamente estos contratos.

La estabilidad de estos contratos garantiza la independencia entre el negocio, el ERP y las aseguradoras integradas.
