# ADR-220 — La cola regenera las vistas de la memoria al traer la base, y resuelve sola el conflicto que solo está en ellas

- Estado: APROBADO
- Fecha: 2026-10-01
- Aprobación: la fusión de la PR por el motor con aprobación dual (ADR-205).
- Nota de arranque:
  `docs/audits/arranque-2026-10-01-la-cola-regenera-las-vistas-al-traer-la-base.md`,
  publicada en el commit `bb8e10bd` (01-10-2026, 07:32 UTC), antes del primer
  commit de arreglo.

## Contexto y problema

Desde ADR-200 la cola trae `main` a la rama que espera revisión: el paso
«Fusionar la base y empujar» de `advance-sirius-after-quality.yml` hace
`git merge --no-ff` de la base y empuja la combinación para que Quality la
pruebe de verdad. Lo que no hacía es **regenerar las vistas de la memoria**
—`MEMORIA.md` (ADR-171) y, desde ADR-218, `docs/audits/INDICE.md`— después de
traerla. Son vistas generadas del árbol, vigiladas por
`test_la_memoria_confirmada_en_este_arbol_esta_al_dia`: si `main` trajo un ADR
o un documento, la combinación tiene la vista vieja y Quality cae por la
memoria. Y si las dos partes la regeneraron —lo normal: **43 de las 44 fusiones
de `main` entre el 11-09 y el 30-09 cambiaron `MEMORIA.md`**, medido con
`git log --first-parent -- MEMORIA.md`—, `git merge` da conflicto en un fichero
que nadie debería resolver a mano, y el paso lo deshacía y pedía una persona.

Medido en la bitácora del ciclo (entrada 146; deuda 48): en #653 costó una
vuelta del corrector, 25 minutos. Es un caso, demasiado pequeño para una tasa,
pero el mecanismo es determinista: toda rama que espere en la cola mientras
`main` avanza con un ADR sale con la vista vieja, sin excepción.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque: ningún permiso ni secreto nuevo; un conflicto que
alcance un fichero que no sea una vista generada se trata exactamente como hoy
(deshacer y avisar); la prueba ejecuta el bash del paso de verdad sobre un
repositorio con remoto y dobles de `uv` y `gh`, por los tres caminos; tres
mutaciones vistas caer.

## Opciones consideradas

1. **Que Quality regenere la vista cuando la encuentre vieja.** Rechazada:
   Quality comprueba, no escribe; una comprobación que corrige lo que comprueba
   deja de comprobar.
2. **`git merge -X ours` (o `theirs`) para las vistas.** Rechazada: elige una
   de las dos vistas viejas en vez de la única correcta, la del árbol
   combinado; Quality caería igual.
3. **Regenerar tras la fusión limpia, y nada más.** Insuficiente: con 43 de 44
   fusiones tocando la vista, el caso frecuente es el conflicto, no la fusión
   limpia.
4. **Regenerar tras la fusión limpia y, cuando el conflicto esté SOLO en las
   vistas generadas, regenerar del árbol combinado y terminar la fusión. Esta.**

## Decisión

En el paso «Fusionar la base y empujar», con el entorno preparado por dos pasos
nuevos (`astral-sh/setup-uv` y `uv sync --locked --all-groups`, la misma
versión fijada que `reflejar-desenlace.yml`, condicionados a la misma puesta al
día):

1. **Fusión limpia**: `uv run sirius-memoria conocimiento` regenera las dos
   vistas del árbol combinado; si cambiaron, se confirman en un commit propio
   («Regenera las vistas de la memoria tras traer `main` (ADR-220)») y se
   empuja. Nunca se reescribe la historia: es un commit más.
2. **Conflicto solo en las vistas** (`git diff --name-only --diff-filter=U` no
   lista nada fuera de `MEMORIA.md` y `docs/audits/INDICE.md`): se regeneran
   del árbol combinado, se añaden **solo ellas** y la fusión termina con
   `git commit --no-edit`, con el mensaje que ya tenía; se empuja.
3. **Cualquier otro conflicto**: ni se regenera ni se toca el árbol; se deshace
   y se avisa en la incidencia, exactamente como hasta ahora (ADR-200).
4. **Frontera de credenciales** (ronda 1 de Codex en la PR #667, P1: «no
   ejecutes código controlado por la rama con el PAT del bot»). Desde ese
   checkout se ejecuta código DE LA RAMA (`uv sync` y el generador), que no
   ha pasado necesariamente la revisión dual; si el PAT estuviera en
   `.git/config` o en su entorno, ese código podría leerlo y empujar lo que
   quisiera. Por eso el checkout de la rama no persiste credenciales
   (`persist-credentials: false`), el paso no exporta `GH_TOKEN`, el generador
   corre con `env -u SIRIUS_BOT_TOKEN -u GH_TOKEN`, y el PAT aparece solo en
   las dos operaciones fijas que lo necesitan: el `git push`, por una URL
   `https://x-access-token:…@github.com/…` construida en el propio paso y que
   no se guarda en ningún sitio (`SIRIUS_PUSH_URL` es la costura de las
   pruebas), y el `gh issue comment` del aviso de conflicto, con el token
   inline. Lo que el código de la rama puede hacer en este paso es lo mismo
   que ya podía hacer en Quality: nada con el PAT.

Defensa en profundidad: aunque la puerta de «solo vistas» fallara, `git add`
añade únicamente las vistas y `git commit` se niega a confirmar con rutas sin
fusionar; la puerta existe para que el generador no se ejecute sobre un árbol
con conflictos ajenos, no como única barrera.

## Comprobación que la sostiene

`tests/automation/test_cola.py` gana cinco pruebas y endurece una. Tres ejecutan el bash del
paso **de verdad** —extraído del YAML— sobre un repositorio de prueba con su
remoto, con dobles de `uv` (escribe las vistas a partir de `git ls-files`, como
el generador real escribe a partir del árbol) y de `gh` (apunta lo que
publicaría), con el `PATH`, el `ISSUE`, la `RAMA` y la `BASE` que el workflow
pasa:

- `test_la_puesta_al_dia_regenera_las_vistas_y_las_confirma_antes_de_empujar`:
  fusión limpia con la vista vieja → la punta de la rama en el remoto es el
  commit de regeneración sobre la fusión, y la vista es la del árbol combinado.
- `test_un_conflicto_solo_en_las_vistas_generadas_se_resuelve_regenerando`:
  las dos partes cambiaron `MEMORIA.md` → la rama avanza con la fusión, la
  vista no lleva marcas de conflicto y no se avisa a nadie.
- `test_un_conflicto_fuera_de_las_vistas_sigue_siendo_cosa_de_una_persona`:
  conflicto en `otro.txt` → la rama no se mueve, la fusión queda deshecha, se
  publica el aviso de conflicto y **el generador no llega a ejecutarse**.
- `test_la_puesta_al_dia_tiene_con_que_regenerar`: los dos pasos de entorno
  existen, van antes del de fusión y llevan la misma condición.
- `test_el_codigo_de_la_rama_corre_sin_el_pat_al_alcance` (punto 4): el
  checkout de la rama no persiste el PAT, el generador va con `env -u`, ningún
  paso exporta el PAT como `GH_TOKEN`, y el push va por la URL del paso y no
  por `origin`. Y las tres pruebas de comportamiento lo miden de verdad: el
  doble de `uv` apunta si vio `SIRIUS_BOT_TOKEN` o `GH_TOKEN` en su entorno
  (la fusión limpia exige que no), y el clon del runner tiene el remoto
  `origin` sin camino de empuje, como en el runner sin credenciales: solo la
  URL con el PAT llega al remoto.
- `test_la_puesta_al_dia_no_empuja_con_el_token_del_workflow` (endurecida):
  el push lleva el PAT (con `GITHUB_TOKEN` Quality no volvería a correr,
  ADR-183) y nunca `--force`.

**Mutaciones, cada una aplicada sobre el workflow, la batería de `test_cola.py`
ejecutada y el fichero restaurado:**

| | Mutación | Resultado |
|---|---|---|
| M1 | no regenerar tras la fusión limpia | cae `regenera_las_vistas_y_las_confirma` |
| M2 | quitar la puerta «solo vistas» (tratar cualquier conflicto como de vistas) | cae `un_conflicto_fuera_de_las_vistas…`: el generador se ejecutó sobre un árbol con conflicto ajeno |
| M3 | empujar sin confirmar la vista regenerada | cae `regenera_las_vistas_y_las_confirma` |
| M4 | persistir el PAT en el checkout de la rama (`persist-credentials: true`) | cae `el_codigo_de_la_rama_corre_sin_el_pat_al_alcance` |
| M5 | ejecutar el generador con el PAT en su entorno (sin `env -u`) | cae `el_codigo_de_la_rama_corre_sin_el_pat_al_alcance`, `la_puesta_al_dia_regenera_las_vistas_y_las_confirma_antes_de_empujar` |
| M6 | exportar el PAT como `GH_TOKEN` a todo el paso | cae `el_codigo_de_la_rama_corre_sin_el_pat_al_alcance` |
| M7 | empujar por `origin` en vez de por la URL con el PAT | cae `el_codigo_de_la_rama_corre_sin_el_pat_al_alcance`, `la_puesta_al_dia_regenera_las_vistas_y_las_confirma_antes_de_empujar`, `un_conflicto_solo_en_las_vistas_generadas_se_resuelve_regenerando` |

Una mutación anunciada en la nota **no cayó**, y se dice: «resolver añadiendo
todo» (`git add -A` en vez de solo las vistas) no cambia el resultado del caso
C porque la puerta impide llegar ahí; es la razón de la prueba y la mutación
M2 de arriba, que miden la puerta directamente.

- Las 30 pruebas de `test_cola.py` en verde; `ruff`, `mypy` sobre la prueba;
  el YAML carga. Batería entera: en la PR.

## Consecuencias

- Una rama que espere en la cola sale con las vistas al día; el caso de #653
  (25 minutos del corrector) deja de poder repetirse por esta causa.
- El job instala `uv` solo cuando hay puesta al día (unos dos minutos); el
  resto de runs no cambian.
- El conflicto en `docs/audits/registro_defectos.yml` —dos PR que añaden una
  entrada H en el mismo sitio— sigue siendo cosa de una persona: no es una
  vista generada y una unión a ciegas podría duplicar identificadores.

## Alternativas descartadas y por qué

Las de «Opciones consideradas».

## La lección

- familia: `regla-que-depende-de-que-alguien-se-acuerde`
- sin esto se repetiría: automatizar la mitad de un gesto (traer la base) y dejar la otra mitad (regenerar lo generado) a que alguien se acuerde, con Quality como único aviso y 25 minutos después.
- lo hace cumplir: `tests/automation/test_cola.py`
