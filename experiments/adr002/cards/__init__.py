"""Ficha de candidato obligatoria (ADR002-TOL-210, paquete 09).

`ADR002-TOL-210` exige que **todo candidato disponga de una ficha propia,
versionada y comprometida en el repositorio antes de su primera ejecución**, y
que **cada ejecución la referencie** por ID, versión y huella.

Hasta este paquete esa exigencia era una **declaración que nadie comprobaba**:
exactamente el defecto que la propia fila denuncia de la v0.3 del Registro,
donde la regla «señalaba a un contenedor que no podía alojarla, y su
cumplimiento no era auditable».

Este paquete la hace **ejecutable**:

- ``card_protocol`` fija las reglas vinculantes y las propiedades comprobables;
- ``schema_card_v0_1`` valida una ficha contra el contenido mínimo, con todos
  los conjuntos de campos **cerrados**;
- ``verify_cards`` comprueba contra Git la **anterioridad** de la congelación
  y la correspondencia entre una ejecución y la ficha que cita.

No mide, no ejecuta candidatos y no autoriza ninguna ejecución.
"""
