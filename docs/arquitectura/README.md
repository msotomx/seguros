# Switchh Insurance Engine (SIE)

Documentación de arquitectura del Motor Broker de Switchh Seguros.

---

## Objetivo

Esta documentación describe la arquitectura, principios de diseño y funcionamiento interno del Switchh Insurance Engine (SIE).

El objetivo es servir como referencia para desarrolladores, arquitectos e integradores que participen en la evolución del Motor Broker.

---

## Índice

| Documento | Descripción |
|------------|-------------|
| 00 | Principios del Engine |
| 01 | Visión General |
| 02 | Modelo de Dominio |
| 03 | Motor Broker |
| 04 | Contratos |
| 05 | Provider Registry |
| 06 | Providers |
| 07 | Builders y Mappers |
| 08 | Flujo de Cotización |
| 09 | Flujo de Emisión |
| 10 | Roadmap |
| 11 | Decisiones Arquitectónicas |

---

## Diagramas

Los diagramas utilizados por la documentación se encuentran en:

docs/architecture/diagrams/

---

## Convenciones

Durante toda la documentación se utilizan las siguientes convenciones.

Broker

: Componentes propios del Switchh Insurance Engine.

Provider

: Adaptador hacia una aseguradora.

Builder

: Convierte contratos del Broker al formato requerido por una aseguradora.

Mapper

: Convierte respuestas de una aseguradora a contratos del Broker.

Contract

: Modelo de datos independiente utilizado por el Engine.

---

## Estado

Versión Arquitectura:

**v1.0**

Última actualización:

Julio 2026
