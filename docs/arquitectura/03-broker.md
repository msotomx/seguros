# 03 - Insurance Broker

# Historial del Documento

| Versión | Fecha | Autor | Descripción |
|---------|-------|--------|-------------|
| 1.0 | Julio 2026 | Miguel Soto / ChatGPT | Definición del núcleo del Switchh Insurance Engine. |

---

# Objetivo

El **Insurance Broker** es el componente central del Switchh Insurance Engine (SIE).

Su responsabilidad es orquestar la comunicación entre el ERP de Switchh Seguros y los diferentes Providers de aseguradoras.

El Broker constituye el único punto de entrada para todos los procesos relacionados con seguros.

---

# Filosofía

El Broker **no conoce aseguradoras**.

No conoce:

- Chubb
- Quálitas
- GNP
- AXA

El Broker únicamente conoce el concepto de:

```
Insurance Provider
```

y trabaja utilizando contratos del dominio definidos por el Engine.

---

# Responsabilidades

El Broker es responsable de:

- Descubrir Providers disponibles.
- Ejecutar reglas del negocio.
- Coordinar Providers.
- Consolidar resultados.
- Administrar errores.
- Exponer una interfaz única al ERP.

---

# No es responsabilidad del Broker

El Broker nunca deberá:

- Consumir directamente una API.
- Construir JSON.
- Interpretar respuestas HTTP.
- Conocer modelos Django.
- Implementar autenticación OAuth.
- Conocer detalles técnicos de una aseguradora.

Estas responsabilidades pertenecen exclusivamente a los Providers.

---

# Arquitectura

```
               ERP

                │

                ▼

      Broker Request Mapper

                │

                ▼

        Insurance Broker

                │

                ▼

       Provider Registry

                │

     ┌──────────┼──────────┐

     ▼          ▼          ▼

 Chubb     Qualitas      GNP

     ▼          ▼          ▼

  Providers   Providers  Providers
```

---

# Componentes

Actualmente el Broker está compuesto por los siguientes módulos.

```
broker/

broker.py

factory.py

registry.py

contracts.py

exceptions.py

mappers/
```

Cada componente tiene una única responsabilidad.

---

# InsuranceBroker

Representa el núcleo del Engine.

Responsabilidades:

- Recibir solicitudes.
- Seleccionar Providers.
- Ejecutar Providers.
- Consolidar respuestas.
- Regresar un único resultado.

El Broker nunca conoce implementaciones específicas.

---

# ProviderRegistry

El Provider Registry mantiene el catálogo de aseguradoras disponibles.

Actualmente define:

- Providers activos.
- Prioridad.
- Ramos soportados.
- Capacidades.

En el futuro obtendrá esta información desde el modelo:

```
AseguradoraConfiguracion
```

---

# ProviderFactory

El Factory crea instancias de Providers.

Ejemplo:

```
CHUBB

↓

ChubbProvider
```

El Broker nunca instancia Providers directamente.

---

# Broker Contracts

Toda comunicación se realiza mediante contratos.

Ejemplo:

```
BrokerQuoteRequest

↓

InsuranceBroker

↓

BrokerQuoteResult
```

El Broker nunca recibe modelos Django.

---

# Broker Mappers

Los Broker Mappers convierten los modelos del ERP a contratos del Engine.

Ejemplo:

```
Cotizacion

↓

BrokerQuoteRequest
```

y posteriormente:

```
BrokerIssuedPolicy

↓

Poliza
```

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

InsuranceProvider

↓

BrokerQuoteResult

↓

ERP
```

---

# Casos de Uso

El Broker soportará los siguientes procesos.

## Cotización

```
quote()
```

---

## Emisión

```
issue()
```

---

## Documentos

```
documents()
```

---

## Endosos

```
endorse()
```

---

## Renovaciones

```
renew()
```

---

## Cancelaciones

```
cancel()
```

Cada proceso mantiene el mismo patrón de arquitectura.

---

# Flujo de Cotización

```
BrokerQuoteRequest

↓

InsuranceBroker

↓

ProviderRegistry

↓

ChubbProvider

↓

BrokerQuoteResult
```

Cuando existan múltiples aseguradoras:

```
BrokerQuoteRequest

↓

InsuranceBroker

↓

ProviderRegistry

↓

┌───────────────┬───────────────┬───────────────┐

▼               ▼               ▼

Chubb      Qualitas        GNP

▼               ▼               ▼

BrokerQuoteOption

BrokerQuoteOption

BrokerQuoteOption

└───────────────┬───────────────┘

↓

BrokerQuoteResult
```

---

# Reglas Arquitectónicas

El Broker deberá cumplir permanentemente las siguientes reglas.

## Regla 1

El Broker nunca conoce APIs externas.

---

## Regla 2

El Broker nunca construye JSON.

---

## Regla 3

El Broker nunca interpreta respuestas HTTP.

---

## Regla 4

El Broker nunca conoce modelos Django.

---

## Regla 5

Toda comunicación ocurre mediante contratos.

---

## Regla 6

Los Providers son completamente intercambiables.

---

## Regla 7

Agregar una nueva aseguradora no requiere modificar el Broker.

---

# Beneficios

Esta arquitectura proporciona:

- Bajo acoplamiento.
- Alta cohesión.
- Escalabilidad.
- Facilidad para pruebas.
- Incorporación sencilla de nuevas aseguradoras.
- Independencia tecnológica.

---

# Ejemplo

El ERP solicita una cotización.

```
BrokerQuoteRequest

↓

InsuranceBroker

↓

ProviderRegistry

↓

CHUBB

↓

BrokerQuoteResult
```

Meses después se incorpora Quálitas.

El ERP continúa ejecutando exactamente el mismo código.

```
BrokerQuoteRequest

↓

InsuranceBroker

↓

ProviderRegistry

↓

CHUBB

QUALITAS

↓

BrokerQuoteResult
```

No fue necesario modificar el ERP.

No fue necesario modificar el Broker.

Únicamente se desarrolló un nuevo Provider.

---

# Objetivo Final

El Insurance Broker constituye el núcleo del Switchh Insurance Engine.

Toda integración con aseguradoras deberá realizarse exclusivamente mediante este componente.

Su objetivo es proporcionar una única interfaz para operar múltiples aseguradoras utilizando un único modelo de negocio, garantizando independencia tecnológica, escalabilidad y mantenibilidad del sistema.
