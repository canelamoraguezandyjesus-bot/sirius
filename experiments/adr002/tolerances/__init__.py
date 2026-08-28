"""Medición experimental aislada de la línea base FTS5 para ADR-002.

Paquete de trabajo 02: `docs/architecture/
SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_02_TOLERANCIAS_Y_MEDICION_v0.1.md`.

Este paquete NO es código productivo y NO se convierte automáticamente en
diseño ni en implementación (ADR-001 §5.10 aplicado por analogía). Solo
mide, sobre bases SQLite temporales creadas con la cadena canónica de
Alembic, el comportamiento real del código de recuperación de Sirius 0.1,
que se usa **sin modificarlo**.

Restricciones que este paquete respeta y que sus pruebas verifican:

- sin red, sin API, sin embeddings, sin modelos externos;
- sin datos reales de usuario y sin secretos;
- sin escribir fuera de ``experiments/adr002/`` y ``artifacts/adr002_tolerances/``;
- sin ejecutar ninguna de las realizaciones técnicas T1-T4.
"""
