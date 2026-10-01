# ADR-222 — Un defecto cerrado lleva la PR que lo fusionó: la referencia que un clon de `main` puede seguir
| M4 | H-218 con `pr: 652` (una PR fusionada, pero no la que añadió ADR-218) | cae `…es_una_pr_fusionada_en_main_cuando_hay_historia`: el commit que añadió ADR-218 es «… (#664)» |

- Estado: APROBADO
- Fecha: 2026-10-01
- Aprobación: la fusión de la PR por el motor con aprobación dual (ADR-205).
- Nota de arranque:
  `docs/audits/arranque-2026-10-01-la-referencia-de-cierre-de-un-defecto-se-sigue-desde-main.md`,
  publicada en el commit `5d24fb1a` (01-10-2026, 08:04 UTC), antes del primer
  commit de arreglo.

## Contexto y problema

La skill `registro-de-defectos` cierra un defecto con `cerrado_por: <sha de 40
caracteres del commit que lo arregló>`, en dos commits (el arreglo; después, la
entrada con su sha). La convención nació cuando las ramas entraban en `main`
con commit de mezcla y el sha seguía siendo antepasado de `main`. Desde que las
PR entran **aplastadas** (ADR-205, 20-09-2026; y las de sesión desde antes),
ese sha vive en la rama de origen —que no se borra, ADR-195— y **no está en
`main`**: quien clona `main`, abre el registro y quiere ver el arreglo, no
llega.

Codex lo cazó en la PR #664 sobre H-217. La mina de septiembre (PR #665) lo
midió con su guion de `cerrado_por` inalcanzables, que entra en `main` con esa
PR (clon entero; `git cat-file -e` y
`git merge-base --is-ancestor` contra `origin/main`): **29 de 68** defectos
cerrados citan un commit que `main` no contiene: los 14 cerrados desde el
20-09, todos; 13 anteriores que viven solo en su rama; y 2 con un sha corto
(H-7, H-9). La primera cuenta a mano de esa edición dijo 19 de 49; la del guion
es la que vale.

Lo que sí se puede seguir desde `main`: **la PR**. El commit aplastado lleva
«(#N)» en su título, así que `git log --first-parent --grep="(#N)" origin/main`
lo encuentra; y el ADR del defecto, cuando lo hay, entra en ese mismo commit.
La correspondencia de las 29 se obtuvo de la API (`GET /commits/{sha}/pulls`),
las dos de sha corto resolviendo primero el sha entero (H-7 → `7fedb39c…` →
#220; H-9 → `41df5e26…` → #234).

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque: no se reescribe ningún `cerrado_por` (el sha sigue
siendo dato); la frontera es el número de este ADR y las anteriores se rellenan
solo donde se midió; la guarda no sale a la red; tres mutaciones vistas caer.

## Opciones consideradas

1. **Cambiar `cerrado_por` por el commit de `main`.** Rechazada: no se conoce
   hasta después de fusionar, así que la entrada no podría ir en la misma PR
   que el arreglo; y reescribir los 68 existentes es tocar lo que ADR-195
   manda conservar.
2. **Fusionar con commit de mezcla para conservar el sha.** Rechazada: deshace
   ADR-205 y la historia lineal que el reflector y la cola leen.
3. **Añadir la referencia que falta —la PR— sin quitar la que hay. Esta.**

## Decisión

1. Desde este ADR, un defecto `cerrado` lleva, además de `cerrado_por`, **`pr:
   <número de la PR que lo fusiona>`**; si lo cerró un encargo del motor, cuya
   PR la abre el workflow al terminar el run, basta `incidencia: <número>`, que
   ya es un campo del registro y se conoce desde el principio.
2. El orden de dos commits gana un paso: el commit 1 (arreglo y ADR), **empujar
   y abrir la PR** para conocer su número, y el commit 2 (la entrada, con el
   sha del commit 1 y el número de la PR). La skill lo dice así.
3. Las 29 entradas medidas reciben su `pr:` con la correspondencia de la API;
   las 39 cuyo sha sí está en `main` no se tocan: no se rellena lo que no se
   midió, y para ellas el sha basta.
4. La guarda (`test_registro_de_defectos.py`) exige la forma siempre —desde la
   frontera, `pr` o `incidencia` enteros; todo `pr`, un entero positivo— y la
   existencia solo donde el clon tiene historia de `origin/main`: en Quality,
   que clona con profundidad 1, esa prueba se salta diciendo por qué; en la
   cadena de comprobación local corre y comprueba que cada `pr` corresponde a
   un título «(#N)» de la primera línea de `main`. Un defecto cuyo ADR aún no
   está en `main` va en vuelo y no se le exige hasta que entre.

## Comprobación que la sostiene

- `test_todo_defecto_cerrado_desde_la_frontera_lleva_una_referencia_que_main_contiene`,
  `test_la_frontera_de_la_referencia_se_ejercita_de_verdad` (anti-vacua: sin un
  cerrado desde la frontera la regla pasaría sola; H-222 es el primero),
  `test_toda_referencia_pr_es_un_numero_de_pr` y
  `test_cada_referencia_pr_es_una_pr_fusionada_en_main_cuando_hay_historia`.
- Sobre este árbol, con historia: las 29 referencias rellenadas corresponden a
  una PR fusionada en `main`, y las 14 que tienen su ADR en `main` (H-204 a
  H-215, H-217 y H-218) apuntan **exactamente** al commit de primer padre que
  añadió ese ADR (`git log --first-parent --diff-filter=A -- <ADR>`): buscar
  el número en cualquier asunto de la historia dejaba pasar una PR equivocada
  (ronda 1 de Codex en la PR #668). Las 15 anteriores a la frontera no tienen
  `adr:` y solo pueden comprobarse por existencia; la prueba exige además que
  la comprobación fuerte se haya ejercitado sobre todos los que la admiten.
- **Mutaciones** (cada una aplicada sobre el registro o la prueba, la batería
  del fichero ejecutada, el fichero restaurado):

| | Mutación | Resultado |
|---|---|---|
| M1 | H-222 sin `pr` ni `incidencia` | cae `…lleva_una_referencia_que_main_contiene` |
| M2 | `pr: "664"` como texto en H-217 | cae `toda_referencia_pr_es_un_numero_de_pr` |
| M3 | H-1 con `pr: 999` (una PR que no existe en `main`) | cae `…es_una_pr_fusionada_en_main_cuando_hay_historia` |

- Batería entera, `ruff`, `mypy`, comprobador de documentos: en la PR.

## Consecuencias

- Desde un clon de `main`, cada defecto cerrado desde aquí —y los 29 medidos—
  lleva a su PR, y de la PR al commit de `main` con un `git log`.
- Cerrar un defecto en una rama de sesión exige abrir la PR antes del segundo
  commit. Es lo que ya hacía la práctica (la PR se abre al primer push).
- Las 39 entradas antiguas con sha en `main` no cambian; si alguna vez se
  midiera su PR, se rellenaría igual, con la medida al lado.

## Alternativas descartadas y por qué

Las de «Opciones consideradas».

## La lección

- familia: `regla-que-depende-de-que-alguien-se-acuerde`
- sin esto se repetiría: una convención de registro escrita para un modo de fusión (con commit de mezcla) que sobrevive al cambio de modo (aplastado) sin que nadie la relea, con la batería en verde y 29 referencias que no llevan a ninguna parte.
- lo hace cumplir: `tests/automation/test_registro_de_defectos.py`
