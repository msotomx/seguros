# 📘 Documentación de Modelos – Sistema de Seguros

Este documento describe la función y responsabilidad de cada **app** y **modelo** del sistema de Seguros, desarrollado con **Django 5.2 + PostgreSQL**, usando una arquitectura modular y escalable.

---

## 🧱 core
Modelos base reutilizables por todo el sistema.  
**No generan tablas propias** (modelos abstractos).

### Modelos
- **TimeStampedModel (abstracto)**  
  Agrega `created_at` y `updated_at` a los modelos que lo heredan.  
  Usado para auditoría, ordenamiento y trazabilidad.

- **SoftDeleteModel (abstracto)**  
  Agrega `is_active` para borrado lógico sin eliminar registros físicamente.

- **MoneyMixin (abstracto)**  
  Agrega el campo `moneda` (por defecto MXN) para estandarizar operaciones financieras.

---

## 👤 accounts
Gestión de usuarios, roles y permisos del sistema.

### Modelos
- **UserProfile**  
  Extiende al usuario de Django con:
  - Rol (Admin, Agente, Operador, Lectura)
  - Estatus activo/inactivo
  - Teléfono y notas
  - Aseguradoras permitidas (restricción opcional)
  
  Centraliza permisos de negocio como:
  - Cotizar
  - Emitir/cancelar pólizas
  - Administrar tarifas
  - Ver o administrar finanzas

---

## 📎 documentos
Gestión centralizada de archivos y adjuntos.

### Modelos
- **Documento**  
  Almacena archivos (PDF, imagen, XML, etc.) con:
  - Metadatos (tipo, tamaño, hash)
  - Usuario que lo subió  
  Se reutiliza en pólizas, pagos, siniestros, mensajes e incidentes.

---

## 📚 catalogos
Catálogos transversales usados por múltiples módulos.

### Modelos
- **Aseguradora**  
  Catálogo de compañías aseguradoras (datos básicos y estatus).

- **AseguradoraContacto**  
  Contactos asociados a una aseguradora (ejecutivos, soporte, siniestros).

- **ProductoSeguro**  
  Planes/productos por aseguradora (Auto, Flotilla, etc.).  
  Define el tipo de cálculo:
  - SIMPLE: captura externa
  - REGLAS: motor interno (B)

- **CoberturaCatalogo**  
  Catálogo estándar de coberturas (RC, DM, RT, etc.) con tipo de valor.

- **ProductoCobertura**  
  Relación producto–cobertura, define qué coberturas incluye cada producto y valores por defecto.

---

## 🤝 crm
Gestión comercial y relación con clientes.

### Modelos
- **Direccion**  
  Direcciones reutilizables (fiscal o contacto).

- **Cliente**  
  Cliente persona o empresa.  
  Incluye datos fiscales, contacto principal, estatus, origen y **owner** para asignación por usuario (cartera).

- **ClienteContacto**  
  Contactos adicionales por cliente (empresas o familiares).

- **Conversacion**  
  Hilo de comunicación con el cliente (asunto, canal, estatus).  
  Puede relacionarse a cotizaciones, pólizas o siniestros.

- **Mensaje**  
  Mensajes individuales (entrantes/salientes), canal, usuario que atendió, adjuntos y metadata.

---

## 🚗 autos
Información de vehículos, conductores y flotillas.

### Modelos
- **Marca**  
  Catálogo de marcas de vehículos.

- **SubMarca**  
  Submarcas/modelos asociados a una marca.

- **VehiculoCatalogo**  
  Catálogo técnico (año, tipo, clave AMIS opcional, valor de referencia) usado por tarifas.

- **Vehiculo**  
  Vehículo asegurado.  
  Incluye uso, datos técnicos, valor comercial y relación con cliente.

- **Conductor**  
  Conductores asociados a un cliente (licencia, contacto).

- **Flotilla**  
  Agrupación de vehículos para empresas.

- **FlotillaVehiculo**  
  Relación flotilla–vehículo, permite altas/bajas históricas.

---

## 🧠 tarifas (Motor B)
Motor interno de cálculo de primas mediante reglas.

### Modelos
- **ZonaTarifa**  
  Define zonas de riesgo (Z1, Z2, etc.).

- **ZonaTarifaDetalle**  
  Asocia estados/ciudades o rangos de CP a una z
