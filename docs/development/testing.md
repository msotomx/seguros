# Switchh Insurance Engine (SIE)

# Development Testing Guide

Este documento describe los comandos de prueba internos utilizados durante el desarrollo del **Switchh Insurance Engine**, permitiendo validar cada componente de manera aislada antes de realizar integraciones con APIs reales.

---

# Objetivos

Los comandos de prueba tienen como propósito:

- Validar componentes individuales.
- Verificar la comunicación entre capas.
- Detectar errores antes de consumir APIs reales.
- Facilitar el desarrollo incremental.
- Mantener una arquitectura desacoplada.

---

# Pruebas Disponibles

## 1. Chubb Health Check

Verifica la conectividad básica con Chubb.

### Comando

```bash
python manage.py chubb_test
```

### Valida

- OAuth
- Endpoint Health
- Comunicación HTTPS

### Resultado esperado

```text
Health OK
```

---

## 2. Provider Test

Prueba la creación del Provider mediante el Factory.

### Comando

```bash
python manage.py provider_test --provider CHUBB
```

### Flujo

```
ProviderFactory

↓

ChubbProvider

↓

Health()
```

### Resultado esperado

```
Health OK
```

---

## 3. Broker Test

Prueba el Insurance Broker.

### Comando

```bash
python manage.py broker_test
```

### Flujo

```
InsuranceBroker

↓

ProviderFactory

↓

InsuranceProvider
```

### Objetivo

Validar que el Broker localiza correctamente el Provider.

---

## 4. Chubb Quote Chain Test

Prueba la cadena completa de cotización utilizando un API Client simulado.

### Comando

```bash
python manage.py chubb_quote_chain_test
```

### Flujo

```
BrokerQuoteRequest

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
```

### Objetivo

Validar toda la arquitectura del Provider sin depender de Chubb.

### Resultado esperado

```
OK: True
Opciones: 1
Errores: 0
```

---

## 5. Chubb Quote Real Test

Realiza una llamada real al endpoint **POST /quote** de Chubb.

### Comando

```bash
python manage.py chubb_quote_real_test
```

### Flujo

```
InsuranceBroker

↓

ProviderFactory

↓

ChubbProvider

↓

POST /quote
```

### Objetivo

Validar la integración real.

### Estado actual

Actualmente depende de que Chubb habilite correctamente:

- Business Profiles
- Agents
- Rates
- Groupings
- Packages
- Vehicles

Mientras dichos catálogos no estén autorizados, el endpoint puede responder con errores HTTP 400 o 500.

---

## 6. Broker Save Mock Quote Test

Guarda un BrokerQuoteResult simulado dentro del ERP.

### Comando

```bash
python manage.py broker_save_mock_quote_test <cotizacion_id>
```

Ejemplo

```bash
python manage.py broker_save_mock_quote_test 5
```

### Flujo

```
BrokerQuoteResult

↓

BrokerQuoteResultMapper

↓

CotizacionItem
```

### Objetivo

Validar el proceso de persistencia de resultados sin utilizar Chubb.

### Resultado esperado

```
Items creados/actualizados: 1
```

---

## 7. Broker Quote Mock Full Test

Prueba el flujo completo del Switchh Insurance Engine utilizando una cotización real del ERP y una respuesta simulada de Chubb.

### Comando

```bash
python manage.py broker_quote_mock_full_test <cotizacion_id>
```

Ejemplo

```bash
python manage.py broker_quote_mock_full_test 5
```

### Flujo

```
Cotizacion

↓

BrokerQuoteRequestMapper

↓

BrokerQuoteRequest

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

### Objetivo

Validar la integración completa entre el ERP y el Insurance Broker sin depender de la API real.

### Resultado esperado

```
=== BROKER QUOTE MOCK FULL TEST ===

OK            : True

Opciones      : 1

Errores       : 0

Items guardados: 1
```

---

# Orden Recomendado de Ejecución

Durante el desarrollo, las pruebas deben ejecutarse en el siguiente orden:

```text
1. python manage.py check

↓

2. python manage.py chubb_test

↓

3. python manage.py provider_test --provider CHUBB

↓

4. python manage.py broker_test

↓

5. python manage.py chubb_quote_chain_test

↓

6. python manage.py broker_save_mock_quote_test

↓

7. python manage.py broker_quote_mock_full_test

↓

8. python manage.py chubb_quote_real_test
```

Este orden permite validar la arquitectura de manera incremental, detectando errores en cada capa antes de avanzar hacia la siguiente.

---

# Buenas Prácticas

Durante el desarrollo del Switchh Insurance Engine:

- Validar primero con pruebas Mock.
- Consumir APIs reales únicamente cuando la arquitectura esté estable.
- No modificar los Builders para adaptarlos a datos de prueba.
- Mantener separados los comandos Mock y los comandos de integración real.
- Ejecutar `python manage.py check` antes de cualquier prueba.

---

# Estado Actual del Sprint 1

## Arquitectura

- ✅ Insurance Broker
- ✅ Provider Factory
- ✅ Provider Registry
- ✅ Broker Contracts
- ✅ Broker Mappers
- ✅ Quote Builder
- ✅ Quote Service
- ✅ API Client
- ✅ Quote Mapper
- ✅ Resultado → CotizacionItem

## Integración Chubb

- ✅ OAuth
- ✅ Health Check
- ✅ Builder funcional
- ✅ Arquitectura validada
- ✅ Flujo Mock completo
- ⏳ Catálogos pendientes de autorización por parte de Chubb.
- ⏳ Cotización real pendiente de IDs oficiales.

---

# Conclusión

Las pruebas descritas en este documento permiten validar el funcionamiento del Switchh Insurance Engine de forma incremental, desacoplada y repetible.

Gracias a estos comandos, es posible desarrollar y verificar la arquitectura completa del Broker antes de depender de servicios externos, reduciendo el tiempo de diagnóstico y facilitando la incorporación de nuevas aseguradoras.
