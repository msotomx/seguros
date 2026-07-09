# 05 - Provider Registry

# Historial del Documento

| Versión | Fecha | Autor | Descripción |
|---------|-------|--------|-------------|
| 1.0 | Julio 2026 | Miguel Soto / ChatGPT | Definición del Provider Registry del Switchh Insurance Engine. |

---

# Objetivo

El **Provider Registry** es el componente responsable de descubrir, registrar y proporcionar los Providers disponibles dentro del Switchh Insurance Engine (SIE).

Su función es desacoplar completamente el Insurance Broker de las implementaciones específicas de cada aseguradora.

El Broker nunca conoce qué aseguradoras existen.

Únicamente consulta al Provider Registry.

---

# Responsabilidad

El Provider Registry es responsable de:

- Registrar Providers disponibles.
- Determinar qué Providers están activos.
- Filtrar Providers por ramo.
- Definir el orden de ejecución.
- Exponer Providers al Insurance Broker.

---

# Arquitectura

```
Insurance Broker

        │

        ▼

Provider Registry

        │

 ┌──────┼──────────┐

 ▼      ▼          ▼

CHUBB QUALITAS    GNP

 ▼      ▼          ▼

Provider Provider Provider
```

---

# Filosofía

El Broker nunca ejecuta código como:

```
if aseguradora == "CHUBB":
```

o

```
if provider == "QUALITAS":
```

Todas las decisiones relacionadas con aseguradoras pertenecen exclusivamente al Provider Registry.

---

# Componentes

Actualmente el Registry utiliza dos componentes.

```
ProviderRegistry

↓

ProviderRegistration

↓

ProviderFactory
```

---

# ProviderRegistration

Representa la definición de un Provider.

## Propiedades

| Campo | Descripción |
|--------|-------------|
| code | Código único del Provider |
| name | Nombre comercial |
| ramo | Ramo soportado |
| active | Indica si está habilitado |
| priority | Prioridad de ejecución |
| supports_quote | Soporta cotización |
| supports_issue | Soporta emisión |
| supports_documents | Soporta documentos |

---

# ProviderRegistry

Representa el catálogo central de Providers.

Actualmente mantiene una lista en memoria.

Ejemplo:

```
CHUBB

priority = 1

quote = True
```

En versiones futuras esta información será obtenida desde la base de datos.

---

# ProviderFactory

El Registry nunca crea Providers directamente.

Toda creación de instancias ocurre mediante:

```
ProviderFactory
```

Ejemplo:

```
Provider Code

↓

CHUBB

↓

ProviderFactory

↓

ChubbProvider()
```

---

# Flujo General

```
BrokerQuoteRequest

↓

InsuranceBroker

↓

ProviderRegistry

↓

ProviderFactory

↓

InsuranceProvider
```

---

# Flujo de Cotización

```
InsuranceBroker

↓

ProviderRegistry.quote_providers()

↓

[
    CHUBB,
    QUALITAS,
    GNP
]

↓

ProviderFactory

↓

Providers
```

---

# Prioridad

Los Providers pueden ejecutarse en un orden específico.

Ejemplo

| Provider | Prioridad |
|-----------|-----------|
| CHUBB | 1 |
| QUALITAS | 2 |
| GNP | 3 |

El Registry siempre devolverá los Providers ordenados por prioridad.

---

# Ramo

Cada Provider puede soportar diferentes ramos.

Ejemplo

| Provider | Autos | Hogar | Vida |
|-----------|--------|--------|------|
| CHUBB | ✓ | ✓ | ✓ |
| QUALITAS | ✓ | ✗ | ✗ |
| GNP | ✓ | ✓ | ✓ |

El Broker únicamente solicitará Providers compatibles con el ramo solicitado.

---

# Capacidades

Cada Provider declara qué operaciones soporta.

Ejemplo

| Operación | CHUBB |
|-----------|--------|
| Cotizar | ✓ |
| Emitir | ✓ |
| Documentos | ✓ |
| Endosos | Futuro |
| Renovaciones | Futuro |

Esto permite incorporar funcionalidades gradualmente.

---

# Evolución

Actualmente el Registry utiliza una lista en memoria.

```
ProviderRegistration(...)
```

En una siguiente etapa utilizará el modelo:

```
AseguradoraConfiguracion
```

La información será obtenida desde la base de datos.

---

# Modelo Futuro

```
AseguradoraConfiguracion

↓

ProviderRegistry

↓

InsuranceBroker
```

Esto permitirá activar o desactivar aseguradoras sin modificar el código fuente.

---

# Beneficios

Esta arquitectura proporciona:

- Incorporación sencilla de nuevas aseguradoras.
- Configuración centralizada.
- Menor acoplamiento.
- Alta escalabilidad.
- Orden de ejecución configurable.
- Habilitación por ambiente.
- Habilitación por ramo.

---

# Reglas Arquitectónicas

## Regla 1

El Insurance Broker nunca conoce Providers concretos.

---

## Regla 2

Toda selección de Providers ocurre mediante el Registry.

---

## Regla 3

Toda creación de Providers ocurre mediante el ProviderFactory.

---

## Regla 4

Los Providers deben ser intercambiables.

---

## Regla 5

Agregar una nueva aseguradora no requiere modificar el Insurance Broker.

Únicamente:

- Crear el Provider.
- Registrarlo.
- Activarlo.

---

# Ejemplo

Actualmente

```
Registry

↓

CHUBB
```

En el futuro

```
Registry

↓

CHUBB

QUALITAS

GNP

AXA

HDI

MAPFRE
```

El Broker continuará ejecutando exactamente el mismo flujo.

No será necesario modificar su código.

---

# Roadmap

## Versión 1

- Registro en memoria.
- Prioridad.
- Filtrado por ramo.

---

## Versión 2

- Configuración desde base de datos.
- Activación por ambiente.
- Configuración por aseguradora.

---

## Versión 3

- Descubrimiento dinámico de Providers.
- Métricas de disponibilidad.
- Balanceo por prioridad.
- Monitoreo de salud.

---

# Conclusión

El Provider Registry constituye el punto único de descubrimiento de aseguradoras dentro del Switchh Insurance Engine.

Gracias a este componente, el Insurance Broker permanece completamente independiente de las implementaciones específicas de cada Provider.

Esta separación permite que el Engine crezca mediante la incorporación de nuevas aseguradoras sin afectar el núcleo del sistema.
