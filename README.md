# Switchh Seguros

Sistema ERP para la administración de un Broker de Seguros desarrollado por Switchh Sistemas.

## Características

- CRM de Clientes
- Cotizador Multiaseguradora
- Administración de Pólizas
- Pagos en Línea
- Comisiones
- Portal del Cliente
- Motor Broker (Switchh Insurance Engine)

---

## Arquitectura General

```
ERP

↓

Switchh Insurance Engine (SIE)

↓

Providers

↓

Aseguradoras
```

---

## Estructura del Proyecto

```
accounts/
autos/
cotizador/
crm/
finanzas/
integrations/
polizas/
portal/
ui/

docs/
```

---

## Documentación

Toda la documentación del proyecto se encuentra en:

docs/

- Arquitectura
- API
- Desarrollo
- Deployment

---

## Tecnologías

- Python 3.12
- Django 5.2
- MySQL
- Docker
- Nginx
- Gunicorn
- MercadoPago
- Chubb APIs

---

## Estado del Proyecto

En desarrollo activo.

Actualmente el Motor Broker soporta la integración base con Chubb y está preparado para incorporar nuevas aseguradoras.

## Estado del proyecto 2026-07-09

**Versión:** 1.0.0

### Sprint 1
- Arquitectura del Motor Broker
- Integración base Chubb
- Flujo completo de cotización (Mock)
- Persistencia de resultados
- Documentación técnica

### Sprint 2 (Próximo)
- Integración real con Chubb
- Provider Configuration
- Catálogos
- Comparador de cotizaciones
- Emisión de pólizas
