# 02 - Domain Model

# Historial del Documento

| Versión | Fecha | Autor | Descripción |
|---------|-------|--------|-------------|
| 1.0 | Julio 2026 | Miguel Soto / ChatGPT | Versión inicial del Modelo de Dominio del Switchh Insurance Engine. |

---

# Objetivo

El Modelo de Dominio define el lenguaje común utilizado por el Switchh Insurance Engine (SIE).

Todos los componentes del Broker intercambian información utilizando estos contratos.

El objetivo es desacoplar completamente el ERP de las APIs de las aseguradoras.

Ningún contrato depende de Chubb, Quálitas, GNP o cualquier otro proveedor.

---

# Principios

El Modelo de Dominio cumple las siguientes reglas:

- Es independiente del ERP.
- Es independiente de las aseguradoras.
- Representa conceptos propios del negocio de seguros.
- Es estable en el tiempo.
- Constituye el lenguaje oficial del Motor Broker.

---

# Flujo del Modelo de Dominio

```
ERP (Django Models)

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

Insurance Providers

        │

        ▼

APIs Externas
```

---

# Contratos del Broker

Actualmente el Engine define los siguientes contratos.

```
BrokerCustomerData

BrokerVehicleData

BrokerQuoteRequest

BrokerQuoteOption

BrokerQuoteResult

BrokerIssueRequest

BrokerIssuedPolicy

BrokerPolicyDocument

BrokerPaymentLink
```

Cada uno representa un concepto del negocio del Broker.

---

# BrokerCustomerData

Representa la información del cliente necesaria para operar una cotización o póliza.

## Responsabilidad

Contener únicamente los datos del cliente requeridos por el Engine.

## Origen

CRM de Clientes.

## Destino

Insurance Providers.

## Campos

| Campo | Tipo |
|--------|------|
| tipo_cliente | str |
| nombre | str |
| email | str |
| telefono | str |
| codigo_postal | str |
| ciudad | str |
| estado | str |
| nombre_comercial | str |

---

# BrokerVehicleData

Representa el vehículo objeto del seguro.

## Responsabilidad

Proporcionar una representación uniforme del vehículo.

## Origen

Catálogo de Vehículos.

## Destino

Insurance Providers.

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

Es el contrato más importante del proceso de cotización.

## Origen

BrokerQuoteRequestMapper.

## Consumido por

InsuranceBroker.

## Contiene

- Cliente.
- Vehículo.
- Vigencias.
- Forma de pago.
- Notas.

---

# BrokerQuoteOption

Representa una propuesta de una aseguradora.

Cada aseguradora genera una o más opciones.

## Ejemplo

```
Chubb

↓

Premium Plus

↓

$12,450
```

---

## Información

- Producto
- Paquete
- Prima
- Coberturas
- Deducibles
- Vigencia

---

# BrokerQuoteResult

Representa el resultado consolidado de una cotización.

Puede contener:

- Una opción.
- Varias opciones.
- Errores.

## Responsabilidad

Convertirse en el único resultado del proceso de cotización.

---

# BrokerIssueRequest

Representa la solicitud de emisión.

Contiene la información necesaria para convertir una cotización en una póliza.

---

# BrokerIssuedPolicy

Representa la póliza emitida por una aseguradora.

No representa el modelo Django Poliza.

Representa únicamente la respuesta del Broker.

---

# BrokerPolicyDocument

Representa un documento generado por una aseguradora.

Ejemplos:

- Póliza PDF
- Carátula
- Condiciones Generales
- Recibo de Pago

---

# BrokerPaymentLink

Representa un enlace de pago generado por una aseguradora.

Puede utilizarse para procesos de cobro en línea.

---

# Objetos Auxiliares

Actualmente existen dos objetos auxiliares.

## Coverage

Representa una cobertura.

Ejemplos:

- Daños Materiales
- Robo Total
- Responsabilidad Civil

---

## Deductible

Representa un deducible asociado a una cobertura.

---

# Relaciones

```
BrokerQuoteRequest

│

├── BrokerCustomerData

└── BrokerVehicleData

        │

        ▼

Insurance Broker

        │

        ▼

BrokerQuoteResult

        │

        ├── BrokerQuoteOption

        ├── Coverage

        └── Deductible
```

---

# Responsabilidades

El Modelo de Dominio debe mantenerse completamente independiente de:

- Django
- Modelos ORM
- Chubb
- Quálitas
- GNP
- AXA
- Requests
- HTTP
- JSON

Su única responsabilidad es representar conceptos del negocio del Broker.

---

# Beneficios

Esta arquitectura proporciona:

- Bajo acoplamiento.
- Reutilización.
- Escalabilidad.
- Integración uniforme.
- Incorporación sencilla de nuevas aseguradoras.
- Independencia entre el ERP y los Providers.

---

# Regla Fundamental

Los contratos definidos en este documento constituyen el lenguaje oficial del Switchh Insurance Engine.

Toda comunicación entre el ERP y los Providers deberá realizarse exclusivamente mediante estos contratos.

Ningún Provider podrá depender de modelos Django.

Ningún módulo del ERP podrá depender de estructuras JSON específicas de una aseguradora.

El Modelo de Dominio es la única fuente de verdad para el intercambio de información dentro del Switchh Insurance Engine.
