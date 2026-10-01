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

La puesta al día pasa a **dos jobs** nuevos, `regenerar` y `empujar`, que arrancan
con las salidas del paso «Advance matching Sirius work item» (`ponerse_al_dia`,
`rama`, `base`, `incidencia`):

1. **`regenerar`, sin ningún secreto y de solo lectura** (`permissions:
   contents: read`). Trae la rama (sin persistir credenciales, historia entera),
   trae la base y la fusiona **sin empujar**; publica como salidas el resultado
   y las dos puntas exactas (`cabeza_rama`, `cabeza_base`). Si la fusión es
   limpia o el conflicto está **solo en las vistas** (`git diff --name-only
   --diff-filter=U` no lista nada fuera de `MEMORIA.md` y
   `docs/audits/INDICE.md`), prepara el entorno (`astral-sh/setup-uv` y `uv
   sync --locked --all-groups`, la misma versión fijada que
   `reflejar-desenlace.yml`, con plazo propio de 20 min por ADR-224), ejecuta
   `uv run sirius-memoria conocimiento` sobre el árbol combinado y entrega las
   dos vistas como artefacto (`vistas-regeneradas-<run>`, un día de retención).
   Con cualquier otro conflicto deshace la fusión y dice `conflicto`, sin
   gastar un `uv sync`.
2. **`empujar`, código fijo con el PAT** (git y gh; ningún `uv`, ningún
   `python`), en otra máquina y solo si `regenerar` terminó bien. Trae la rama
   (sin persistir credenciales), trae la base y comprueba que las puntas son
   **las mismas** sobre las que se regeneraron las vistas; si alguien empujó
   entre medias, no aplica datos de otro árbol y lo deja para el próximo run.
   Repite la misma fusión: si es limpia, copia las dos vistas del artefacto y,
   si cambiaron, las confirma en un commit propio («Regenera las vistas de la
   memoria tras traer `main` (ADR-220)»); si el conflicto está solo en las
   vistas, las copia, añade **solo ellas** y termina la fusión con `git commit
   --no-edit`, con el mensaje que ya tenía. Empuja por una URL
   `https://x-access-token:…@github.com/…` construida en el propio paso
   (`SIRIUS_PUSH_URL` es la costura de las pruebas). Nunca reescribe la
   historia: es un commit más. Y escribe las vistas **solo sobre ficheros
   regulares, por rutas sin ningún enlace simbólico**, comprobado después de
   fusionar y sobre el artefacto también: si la rama hubiera convertido
   `MEMORIA.md` (o `docs/audits`) en un enlace a `.git/config`, el `cp` lo
   seguiría y el `git add` siguiente ejecutaría lo que ese config dijera
   (`core.fsmonitor`) con el PAT en el entorno (ronda 3 de Codex en la PR
   #667). Con un enlace, no se toca nada y el run falla.
3. **Cualquier otro conflicto**: la rama no se toca y `empujar` publica el aviso
   en la incidencia con el PAT, exactamente como hasta ahora (ADR-200).
4. **La frontera de credenciales** (rondas 1 y 2 de Codex en la PR #667, las
   dos P1). El código de la rama corre en un job que no recibe ningún secreto,
   ni en su entorno ni en el de ningún proceso de su máquina: un `env -u` no
   bastaba, porque el hijo lee `/proc/<padre>/environ`, y un proceso que la
   rama dejara en segundo plano leería el de cualquier paso posterior del
   mismo runner. Las vistas cruzan al job de confianza como datos, atadas a
   las dos puntas sobre las que se calcularon. Lo que el código de la rama
   puede hacer en esta cola es lo mismo que ya podía hacer en Quality: nada
   con el PAT.

Defensa en profundidad: aunque la puerta de «solo vistas» fallara, `git add`
añade únicamente las vistas y `git commit` se niega a confirmar con rutas sin
fusionar; la puerta existe para que el generador no se ejecute sobre un árbol
con conflictos ajenos, no como única barrera.

## Comprobación que la sostiene

`tests/automation/test_cola.py` gana siete pruebas y endurece una. Cinco
ejecutan el bash de los pasos **de verdad** —extraído del YAML—, cada job en su
propio clon (como en dos máquinas), con **exactamente el entorno que el YAML
declara para cada paso** (las expresiones `${{ }}` se sustituyen y no se añade
ni una variable: un secreto que el YAML diera al job que regenera lo vería el
doble), sobre un repositorio de prueba con su remoto y con dobles de `uv`
(escribe las vistas a partir de `git ls-files`, como el generador real escribe
a partir del árbol, y apunta si tuvo un token en su entorno o en el del proceso
que lo lanzó, leyendo `/proc/$PPID/environ`) y de `gh` (apunta lo que
publicaría); el clon de cada runner tiene `origin` sin camino de empuje, como el
runner sin credenciales:

- `test_la_puesta_al_dia_regenera_las_vistas_y_las_confirma_antes_de_empujar`:
  fusión limpia con la vista vieja → la punta de la rama en el remoto es el
  commit de regeneración sobre la fusión, y la vista es la del árbol combinado.
- `test_un_conflicto_solo_en_las_vistas_generadas_se_resuelve_regenerando`:
  las dos partes cambiaron `MEMORIA.md` → la rama avanza con la fusión, la
  vista no lleva marcas de conflicto y no se avisa a nadie.
- `test_un_conflicto_fuera_de_las_vistas_sigue_siendo_cosa_de_una_persona`:
  conflicto en `otro.txt` → la rama no se mueve, la fusión queda deshecha, se
  publica el aviso de conflicto y **el generador no llega a ejecutarse**.
- `test_si_las_puntas_cambian_entre_los_dos_jobs_no_se_aplican_vistas_de_otro_arbol`:
  alguien empuja a la rama entre `regenerar` y `empujar` → el job que empuja lo
  ve, no aplica las vistas y la rama queda como la dejó quien empujó.
- `test_la_puesta_al_dia_tiene_con_que_regenerar`: `setup-uv`, `uv sync` y la
  entrega del artefacto existen en `regenerar`, condicionados a la fusión y en
  ese orden; `empujar` recoge el mismo artefacto antes de aplicarlo.
- `test_el_codigo_de_la_rama_corre_en_un_job_sin_ningun_secreto` (punto 4): de
  los jobs que traen la rama, solo `regenerar` ejecuta código; ese job no
  contiene un solo `secrets.` y solo puede leer; ningún checkout persiste
  credenciales; `empujar` depende de que `regenerar` haya terminado bien y
  comprueba las dos puntas.
- `test_una_vista_que_la_rama_convirtio_en_enlace_simbolico_no_se_pisa_con_el_pat`:
  la rama hace de `MEMORIA.md` un enlace a `.git/config` → el job que empuja
  falla, el `.git/config` de su runner queda intacto y la rama no se mueve.
- `test_la_puesta_al_dia_no_empuja_con_el_token_del_workflow` (endurecida): el
  paso que empuja recibe el PAT (con `GITHUB_TOKEN` Quality no volvería a
  correr, ADR-183), lo usa por la URL del paso y no por `origin`, y nunca
  `--force`.

**Mutaciones, cada una aplicada sobre el workflow, la batería de `test_cola.py`
ejecutada y el fichero restaurado:**

| | Mutación | Resultado |
|---|---|---|
| M1 | no regenerar tras la fusión limpia | cae `regenera_las_vistas_y_las_confirma` |
| M2 | quitar la puerta «solo vistas» (tratar cualquier conflicto como de vistas) | cae `un_conflicto_fuera_de_las_vistas…`: el generador se ejecutó sobre un árbol con conflicto ajeno |
| M3 | empujar sin confirmar la vista regenerada | cae `regenera_las_vistas_y_las_confirma` |
| M4 | el checkout del job que regenera persiste credenciales | cae `el_codigo_de_la_rama_corre_en_un_job_sin_ningun_secreto` |
| M5 | el paso que regenera recibe el PAT en su entorno | cae `el_codigo_de_la_rama_corre_en_un_job_sin_ningun_secreto`, `la_puesta_al_dia_regenera_las_vistas_y_las_confirma_antes_de_empujar` (el doble lo vio) |
| M6 | el job que empuja ejecuta el generador (código de la rama con el PAT) | cae `el_codigo_de_la_rama_corre_en_un_job_sin_ningun_secreto`, `la_puesta_al_dia_regenera_las_vistas_y_las_confirma_antes_de_empujar`, `un_conflicto_solo_en_las_vistas_generadas_se_resuelve_regenerando` |
| M7 | empujar por `origin` en vez de por la URL con el PAT | cae `la_puesta_al_dia_no_empuja_con_el_token_del_workflow`, `la_puesta_al_dia_regenera_las_vistas_y_las_confirma_antes_de_empujar`, `un_conflicto_solo_en_las_vistas_generadas_se_resuelve_regenerando` |
| M8 | no comprobar que las puntas son las mismas | cae `el_codigo_de_la_rama_corre_en_un_job_sin_ningun_secreto`, `si_las_puntas_cambian_entre_los_dos_jobs_no_se_aplican_vistas_de_otro_arbol` |
| M9 | empujar aunque la regeneración haya fallado | cae `el_codigo_de_la_rama_corre_en_un_job_sin_ningun_secreto` |
| M10 | escribir las vistas sin comprobar enlaces ni ficheros regulares | cae `una_vista_que_la_rama_convirtio_en_enlace_simbolico_no_se_pisa_con_el_pat` |

Una mutación anunciada en la nota **no cayó**, y se dice: «resolver añadiendo
todo» (`git add -A` en vez de solo las vistas) no cambia el resultado del caso
C porque la puerta impide llegar ahí; es la razón de la prueba y la mutación
M2 de arriba, que miden la puerta directamente.

- Las 32 pruebas de `test_cola.py` en verde; `ruff`, `mypy` sobre la prueba;
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
