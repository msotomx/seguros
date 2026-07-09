Hay un documento que no debería faltar y que casi nunca se hace en proyectos de software:
11-architecture-decisions.md

Es un registro de decisiones arquitectónicas (similar a un ADR, Architecture Decision Record).

Cada vez que tomemos una decisión importante, la documentamos brevemente.

# Principio Fundamental

Toda decisión arquitectónica del Switchh Insurance Engine deberá favorecer:

1. Bajo acoplamiento.

2. Alta cohesión.

3. Escalabilidad.

4. Independencia entre el ERP y las aseguradoras.

5. Reutilización de componentes.

6. Incorporación de nuevas aseguradoras sin modificar el núcleo del Broker.


ADR-001

Decisión: El Broker nunca conocerá modelos de Django.

Motivo: Mantener el Motor Broker desacoplado del ERP.

ADR-002

Decisión: Todo Provider debe implementar la interfaz InsuranceProvider.

Motivo: Garantizar intercambiabilidad entre aseguradoras.

ADR-003

Decisión: Se utilizan Builders para solicitudes y Mappers para respuestas.

Motivo: Separar claramente la transformación de entrada y salida de cada API.

ADR-004

Decisión: El ProviderRegistry es el único componente que conoce qué aseguradoras están activas.

Motivo: Evitar que el ERP decida qué proveedores consultar y centralizar la configuración.
