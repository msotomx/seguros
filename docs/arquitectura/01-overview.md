# Historial del Documento

| Versión | Fecha      | Autor                 | Descripción |
|---------|------------|--------               |-------------|
| 1.0     | 2026-07-02 | Miguel Soto / ChatGPT | Versión inicial de la arquitectura del Switchh Insurance Engine. |

# Arquitectural Vision

Switchh Insurance Engine (SIE) nace con el objetivo de convertirse en una plataforma independiente para la integración de aseguradoras.

El Engine no pertenece a una aseguradora específica, ni está diseñado para resolver únicamente la emisión de pólizas. Su propósito es abstraer la complejidad técnica de los diferentes proveedores y ofrecer al ERP de Switchh un único modelo de negocio para operar seguros.

Desde la perspectiva del ERP, todas las aseguradoras funcionan exactamente igual.

Desde la perspectiva de cada aseguradora, el Engine actúa como un adaptador especializado que conoce sus reglas, formatos y procesos particulares.

Esta arquitectura permite que el crecimiento del sistema ocurra mediante la incorporación de nuevos Providers, sin modificar el núcleo del ERP ni afectar las integraciones existentes.

El objetivo a largo plazo es que Switchh Insurance Engine pueda operar como un componente reutilizable, capaz de integrarse con diferentes productos de Switchh o incluso con sistemas externos.

# Principios Arquitectónicos

## 1. El ERP nunca conoce una API de aseguradora.

Toda comunicación con proveedores externos debe realizarse exclusivamente a través del Insurance Broker.

---

## 2. Todo Provider implementa el mismo contrato.

Cada aseguradora deberá implementar la interfaz InsuranceProvider.

---

## 3. Los contratos del Broker son independientes de cualquier aseguradora.

BrokerQuoteRequest

BrokerQuoteResult

BrokerIssueRequest

BrokerIssuedPolicy

nunca deberán contener campos específicos de un proveedor.

---

## 4. Los Providers nunca conocen modelos Django.

Los Providers únicamente trabajan con los contratos del Broker.

---

## 5. Los Builders únicamente construyen solicitudes.

Nunca interpretan respuestas.

---

## 6. Los Mappers únicamente interpretan respuestas.

Nunca generan solicitudes.

---

## 7. Toda nueva aseguradora debe implementarse sin modificar el Broker.

El Broker permanece estable.

El crecimiento del sistema ocurre mediante nuevos Providers.

---

## 8. Toda integración debe ser intercambiable.

La sustitución de una aseguradora por otra no debe requerir cambios en el ERP.

# Que es Switchh Insurance Engine

Objetivo
Problema que resuelve
Principios de diseño
Capas
Diagrama general
Casos de uso
Beneficios

# Objetivo Final

El objetivo de Switchh Insurance Engine es convertirse en el núcleo tecnológico de Switchh Seguros.

El Engine deberá proporcionar una única interfaz para operar cualquier aseguradora soportada por la plataforma.

En el futuro permitirá:

- Cotizar simultáneamente con múltiples aseguradoras.
- Emitir pólizas desde un único flujo.
- Administrar documentos.
- Gestionar endosos.
- Renovar pólizas.
- Cancelar pólizas.
- Consultar estados.
- Integrar nuevos productos de seguros.
- Exponer APIs para terceros.
- Operar múltiples ramos de seguros.

Todo ello manteniendo un único modelo de negocio y una arquitectura desacoplada.

# Switchh Insurance Engine (SIE)

## 1. Visión General

**Switchh Insurance Engine (SIE)** es el motor de integración de aseguradoras desarrollado por Switchh Sistemas.

Su objetivo es proporcionar una plataforma desacoplada que permita cotizar, emitir, administrar y operar pólizas de seguros con múltiples aseguradoras utilizando un modelo de negocio único e independiente de cada proveedor.

El Engine actúa como una capa de abstracción entre el ERP de Switchh Seguros y las APIs de las aseguradoras, permitiendo que el resto del sistema trabaje con un único modelo de datos sin conocer las diferencias técnicas de cada integración.

---

# Objetivos

Los objetivos principales del Switchh Insurance Engine son:

- Integrar múltiples aseguradoras bajo una única interfaz.
- Eliminar el acoplamiento entre el ERP y las APIs de cada aseguradora.
- Facilitar la incorporación de nuevas aseguradoras.
- Reutilizar el mismo motor desde diferentes aplicaciones.
- Centralizar las reglas de negocio del Broker.
- Mantener una arquitectura escalable y mantenible.

---

# Problema que resuelve

Cada aseguradora implementa APIs diferentes.

Por ejemplo:

- Diferentes métodos de autenticación.
- Diferentes nombres de campos.
- Diferentes procesos de emisión.
- Diferentes estructuras JSON.
- Diferentes catálogos.
- Diferentes reglas de negocio.

Sin una capa de abstracción, el ERP tendría que conocer todas esas diferencias.

Esto provocaría:

- Alto acoplamiento.
- Código duplicado.
- Difícil mantenimiento.
- Difícil incorporación de nuevas aseguradoras.

Switchh Insurance Engine elimina ese problema convirtiéndose en el único componente que conoce cómo comunicarse con cada proveedor.

---

# Principios de Diseño

El diseño del Engine está basado en los siguientes principios.

## Desacoplamiento

El ERP nunca conoce las APIs de las aseguradoras.

El ERP únicamente trabaja con contratos del Broker.

---

## Arquitectura por Capas

Cada capa tiene una única responsabilidad.

```
ERP

↓

Broker Mappers

↓

Broker Contracts

↓

Insurance Broker

↓

Insurance Providers

↓

APIs Externas
```

---

## Modelo de Dominio Único

Todos los proveedores trabajan utilizando el mismo modelo de negocio.

Ejemplo:

```
BrokerQuoteRequest

BrokerQuoteResult

BrokerIssueRequest

BrokerIssuedPolicy

BrokerPolicyDocument
```

Estos contratos representan conceptos del negocio de seguros y no dependen de ninguna aseguradora.

---

## Patrón Adapter

Cada aseguradora implementa un Provider independiente.

Ejemplo:

```
InsuranceProvider

↓

ChubbProvider

↓

QualitasProvider

↓

GnpProvider
```

Cada Provider traduce los contratos del Broker al formato requerido por su API.

---

## Patrón Builder

Los Builders convierten los contratos del Broker en solicitudes específicas para cada aseguradora.

Ejemplo:

```
BrokerQuoteRequest

↓

ChubbQuoteBuilder

↓

JSON Chubb
```

---

## Patrón Mapper

Los Mappers convierten las respuestas de cada aseguradora en contratos del Broker.

Ejemplo:

```
JSON Chubb

↓

ChubbQuoteMapper

↓

BrokerQuoteResult
```

---

# Arquitectura General

```
                         SWITCHH SEGUROS

                                │

                                ▼

                       Modelos Django

                                │

                                ▼

                 Broker Request Mappers

                                │

                                ▼

                    Broker Contracts

                                │

                                ▼

                     Switchh Insurance Engine

                                │

                                ▼

                      Provider Registry

        ┌──────────────────┼──────────────────┐

        ▼                  ▼                  ▼

   ChubbProvider     QualitasProvider     GnpProvider

        │                  │                  │

        ▼                  ▼                  ▼

      Chubb API        Qualitas API        GNP API

        │                  │                  │

        └──────────────────┼──────────────────┘

                                ▼

                    Broker Response Contracts

                                │

                                ▼

                Broker Response Mappers

                                │

                                ▼

                     Modelos Django
```

---

# Capas del Sistema

## 1. ERP

Contiene los módulos funcionales.

- CRM
- Clientes
- Cotizador
- Pólizas
- Pagos
- Comisiones
- Portal del Cliente

---

## 2. Broker Mappers

Responsables de convertir los modelos del ERP en contratos del Broker y viceversa.

Ejemplo:

```
Cotizacion

↓

BrokerQuoteRequest
```

---

## 3. Broker Contracts

Representan el lenguaje común del Motor Broker.

Ningún contrato depende de una aseguradora específica.

---

## 4. Insurance Broker

Es el cerebro del Engine.

Responsabilidades:

- Orquestar cotizaciones.
- Seleccionar Providers.
- Ejecutar reglas de negocio.
- Consolidar respuestas.
- Manejar errores.
- Exponer una interfaz única al ERP.

---

## 5. Provider Registry

Mantiene el catálogo de proveedores disponibles.

Determina:

- Qué aseguradoras están activas.
- Qué ramos soportan.
- Prioridad.
- Ambiente.
- Capacidades.

---

## 6. Providers

Cada Provider implementa la integración con una aseguradora.

Ejemplo:

- Chubb
- Quálitas
- GNP
- AXA

---

## 7. APIs Externas

Representan los servicios reales de las aseguradoras.

---

# Casos de Uso

El Engine soportará los siguientes procesos:

- Cotización.
- Emisión de pólizas.
- Descarga de documentos.
- Endosos.
- Cancelaciones.
- Renovaciones.
- Consulta de pólizas.
- Consulta de pagos.
- Integración con cobranza.

---

# Beneficios

La arquitectura proporciona los siguientes beneficios.

## Escalabilidad

Agregar una nueva aseguradora únicamente requiere desarrollar un nuevo Provider.

No es necesario modificar el ERP.

---

## Reutilización

El mismo Engine puede ser utilizado por:

- Portal Web.
- Aplicación móvil.
- API pública.
- Sistemas de terceros.
- ERP de Switchh.

---

## Bajo Acoplamiento

El ERP nunca depende de las APIs de las aseguradoras.

Las diferencias técnicas permanecen encapsuladas dentro de los Providers.

---

## Mantenibilidad

Cada componente tiene una única responsabilidad.

Esto reduce significativamente la complejidad del mantenimiento.

---

## Extensibilidad

La arquitectura permite incorporar nuevas funcionalidades sin afectar las integraciones existentes.

---

# Filosofía del Proyecto

Switchh Insurance Engine no es una integración con una aseguradora.

Es una plataforma diseñada para operar como el núcleo tecnológico de un Broker Digital de Seguros.

Toda nueva funcionalidad deberá respetar los principios definidos en este documento, priorizando el desacoplamiento, la reutilización, la escalabilidad y la independencia entre el ERP y los proveedores externos.
