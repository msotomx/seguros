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
