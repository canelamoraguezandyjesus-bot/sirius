# ADR-072 — REPARAR tiene dos entradas, porque el ciclo real tiene dos

- Estado: PROPUESTO
- Fecha: 2026-08-22
- Aprobación: la fusión de la PR de esta rama por el propietario
- Nota de arranque de esta rama: este ADR. Publicado antes del primer commit.

## Contexto y problema

La máquina de fases del motor solo permitía entrar en REPARAR desde REVISAR:

```python
self._require_phase(frozenset({WorkItemPhase.REVISAR}), "request_repair")
```

**El ciclo real tiene dos entradas.** Cuando Quality falla,
`advance-sirius-after-quality.yml` pasa de `sirius:ci-pending` a
`sirius:repair-requested` **sin pasar por revisión** — y con razón: no hay nada
que revisar de un cambio que no compila.

En fases del motor eso es **COMPROBAR → REPARAR**, y esa arista no existía.

### Qué provocaba, y no es hipotético

El motor tenía dos salidas y las dos malas:

1. **Inventar una fase REVISAR que nunca ocurrió**, para poder llegar a REPARAR
   por el único camino legal. Un estado falso en el almacén canónico.
2. **Quedarse en COMPROBAR** mientras la incidencia decía REPARAR: una
   divergencia **permanente** entre las dos fuentes, no una ventana transitoria.

Lo encontró el diseño del verificador de proyección de D1 (incidencia #250,
hallazgo H-D): entre los cuatro falsos rojos estructurales, dos venían de que
**las dos máquinas de estados no son el mismo grafo**. Esta arista era uno de
ellos. Un verificador honesto habría dado rojo en cada CI roja, sin que hubiera
ningún defecto.

La arquitectura tampoco lo decía: su §3.4 dibuja
`… COMPROBAR → REVISAR → (REPARAR → COMPROBAR → REVISAR)* → ENTREGAR` y **no
dice qué pasa cuando COMPROBAR falla**. No era un desacuerdo entre documento y
código: era un hueco en los dos.

## Criterio de parada (escrito ANTES de decidir)

Si cerrar el hueco exigiera **una operación nueva del dominio** —un
`request_repair_from_check` aparte— se para y se piensa: dos operaciones para el
mismo destino multiplican las guardas y las tablas exhaustivas que este
repositorio mantiene a mano, y esa multiplicación es su propia fuente de
defectos. No se activó: una fase más en la guarda existente basta.

Y si al añadirla alguna transición ilegal pasara a ser legal sin quererlo, se
para. Tampoco: hay control negativo para las tres fases que siguen sin poder
reparar.

## Decisión

`request_repair` acepta **REVISAR o COMPROBAR**. Nada más cambia: sigue
exigiendo estado ACTIVE, sigue llevando a REPARAR, y `resume_after_repair` sigue
devolviendo a COMPROBAR — así el bucle cierra igual por las dos entradas.

Se corrige también la arquitectura §3.4, que es donde faltaba escrito.

## Consecuencias

- El motor puede representar el camino de la CI roja, que es el más frecuente
  del ciclo después del camino feliz.
- Desaparece uno de los cuatro falsos rojos estructurales que bloqueaban D1.
  **Quedan tres**: el instante del despacho, la ventana de tolerancia y la otra
  arista que falta (`* → DELIVERED` al fusionar).
- La tabla exhaustiva de `test_work_item_transitions.py` gana una entrada. Esa
  tabla está escrita a mano **a propósito**, como oráculo independiente de la
  implementación; que haya que tocarla es la señal de que el cambio es real.

## Lo que esto NO hace

- **No desbloquea D1.** Es una de cuatro.
- **No añade la arista `* → DELIVERED`.** Al fusionar, el ciclo aplica
  `sirius:completed` desde donde esté, y `deliver` exige fase ENTREGAR. Ese
  desajuste sigue vivo y es más delicado: tocarlo significa decidir si el motor
  acepta entregar desde cualquier fase, y eso sí es una decisión de diseño.
- **No cambia quién dispara la reparación.** Sigue siendo el ciclo por su
  etiqueta; esto solo permite que el motor lo represente.

## Comprobación que la sostiene

- **Mutación vista fallar**: quitada COMPROBAR de la guarda, caen seis pruebas
  —la nueva del camino de CI roja y el control negativo, en las dos
  implementaciones del almacén—.
- No regresión: REVISAR → REPARAR sigue funcionando, con su prueba.
- Controles negativos: REPARAR no puede volver a entrar en REPARAR, y PREPARAR y
  EJECUTAR siguen sin poder reparar.
- Suite de `tests/engine` completa en verde con las dos implementaciones del
  almacén, incluida la tabla exhaustiva de fases.
