# ADR-213 — Escribir las tres reglas de septiembre del propietario, dar proporción a la cadena de comprobación y fechar en las transcripciones las reglas del 20-09

- Estado: APROBADO
- Fecha: 2026-09-20
- Aprobación: la sesión, por ADR-204 (es orden y método, no producto, dinero ni
  salud); el propietario, al fusionar la PR de esta rama

## Contexto y problema

El paso 5 de la auditoría de la forma de trabajar leyó 28 transcripciones de
sesiones de Claude Code en la nube que el paso 4 no había podido ver
(`docs/audits/AUDITORIA_FORMA_DE_TRABAJO_2026-09.md`, sección «Paso 5»). Tres
cosas salieron de ahí que son decisión de la sesión y no del propietario:

1. **Tres reglas de conversación que él dijo en septiembre y no estaban
   escritas**: contestar primero cuando habla mientras la sesión encadena
   esperas (14-09 11:04), el parte de la mañana con «qué hiciste, qué no
   hiciste y por qué, qué queda» (14-09 11:06, 20:53, 22:48) y acumular lo del
   ordenador para dárselo en lote (11-09 20:19). Las tres se violaron después
   de dichas; la primera, en esta misma sesión el 20-09. Es la familia
   `regla-del-propietario-que-solo-vive-en-una-conversacion`, que ADR-204 y
   ADR-208 ya nombraron. El paso 5 midió la distancia entre regla dicha y regla
   escrita: 41 días para ADR-204, 8 para ADR-205, 0 para ADR-191, 6 para
   ADR-206. Las reglas del motor se escriben el día que las dice; las de
   conversación, semanas después.
2. **La cadena de comprobación no sabía cuándo sobra.** Dos sesiones que
   recibieron «copia tu transcripción y no modifiques nada más» cargaron la
   skill, corrieron doce minutos de batería y regeneraron `MEMORIA.md` para un
   commit que solo añadía un `.jsonl` (20-09; hallazgo T-08 del paso 5). No
   comprobaron nada y tocaron lo que la orden excluía.
3. **Las reglas del 20-09 tienen fecha de origen en su boca, y ADR-204, 205 y
   206 no la tenían**: se escribieron con las palabras del 20-09 como si
   hubieran nacido ese día. La tabla del hallazgo T-02 del paso 5 las fecha
   (10-08 21:06 la primera de ADR-204; 12-09 00:27 la de ADR-205; 13-09 08:19 y
   14-09 00:42 la cola). Los ADR aprobados no se editan (ADR-209, ADR-190); el
   puntero queda aquí.

## Criterio de parada (escrito ANTES de decidir)

La parada de la lectura es la de las adendas 4 y 5 de
`docs/audits/arranque-auditoria-forma-de-trabajo.md`, publicadas el 20-09 a
las 23:05 y a las 23:27 UTC, antes de abrir ningún extracto: revisadas
C-01…C-03, N-03 y E-01…E-06 con lo que las fuentes añadan o desmientan y
escrita la sección «paso 5»; o extractos agotados; o regla de las dos rondas
disparada por una familia nueva. Estado al cerrar: la sección está escrita, los
extractos de las 28 se agotaron, y la regla de las dos rondas se disparó por
una familia **repetida**, no nueva, cuya raíz ya tenía nombre y arreglo
empezado (ADR-208, ADR-211); este ADR es lo que faltaba de ese arreglo.

Para lo que este ADR cambia, la parada propia, fijada antes de tocar nada:
cada regla nueva tiene una guarda que falla al quitarla; la cadena entera vuelve
verde salvo la única prueba que por diseño espera al segundo commit —la lección
sin su defecto, ADR-182—; y ningún documento tocado tiene citas rotas.

## Opciones consideradas

- **Dejar las tres reglas solo en la skill.** La skill se carga cuando el
  modelo decide cargarla; `AGENTS.md` se lee siempre. ADR-208 puso las diez en
  `AGENTS.md` por esa razón, y las tres nuevas son de la misma naturaleza.
- **Escribirlas sin guarda.** Es la familia de ADR-211: prosa que nadie vuelve
  a comprobar. La guarda existente de ADR-204 ya sabe vigilar frases de
  `AGENTS.md`; ampliarla cuesta doce líneas.
- **Bajar la batería para commits de datos con un hook.** Una puerta más, y
  ADR-001 retiró la última tras quince defectos. La proporción es juicio del que
  ejecuta; se escribe donde lo lee, en la skill que ya lo guía.
- **Editar ADR-204, 205 y 206 para añadirles la fecha de origen.** Un ADR
  fusionado está aprobado (ADR-209) y sus citas están medidas (ADR-190). El
  puntero vive aquí y en el paso 5, que es donde está la evidencia.

## Decisión

1. **`AGENTS.md`**, sección «Cómo conversa el propietario, y qué espera
   (ADR-208)», gana las reglas 11, 12 y 13, con sus palabras y su fecha:
   *contesta primero, trabaja después*; *el parte de la mañana tiene tres
   partes: qué hiciste, qué no y por qué, y qué le toca a él*; *lo del
   ordenador, en lote*. `tests/automation/test_reglas_de_agents.py` las vigila
   igual que vigila las tres categorías de ADR-204.
2. **La skill `hablar-con-el-propietario`** gana la sección «Tres reglas más,
   de septiembre» con la forma operativa de cada una, y un dato más de su
   máquina: la ruta del repositorio, que él no sabe de memoria y lo dijo el
   11-09 a las 21:17.
3. **La skill `cadena-de-comprobacion`** gana la sección «Cuándo la cadena
   entera sobra» y su descripción lo anuncia: un cambio que no toca código,
   pruebas, documentos ni registros no necesita la batería; basta
   `git diff --check` y el comprobador de documentos si tocó algún `.md`.
4. **Las fechas de origen** de ADR-171, 191, 195, 204, 205 y 206 quedan en la
   tabla T-02 del paso 5 y en el contexto de este ADR; los seis ADR no se
   tocan.
5. **El registro de ideas**: I-007 pasa a promovida, porque la quinta vía
   funcionó y no la tenía la sesión sino el propietario; nace I-008, el
   contador de rondas para la revisión externa traída a mano, aparcada con su
   disparador, porque construirlo es tocar el motor y una auditoría no
   construye.
6. **Las ramas `transcripciones/*` las borra el propietario** con el comando
   que se le da: `.claude/settings.json` prohíbe a las sesiones
   `git push --delete`, y rodear una prohibición suya no es una opción. El
   compromiso de la adenda 4 se cumple dejando la hora del borrado en el paso 5
   cuando lo haga.

## Comprobación que la sostiene

| Qué se afirma | Comando | Resultado |
|---|---|---|
| La guarda de `AGENTS.md` pasa con las tres reglas | `uv run --no-sync pytest tests/automation/test_reglas_de_agents.py -q` | 9 pruebas en verde (las 6 de ADR-204 y las 3 nuevas) |
| La guarda no es vacua | quitar cada una de las tres reglas de `AGENTS.md`, una a una, y correr la guarda; restaurar desde copia | **3 de 3 cazadas**: cada regla quitada → «1 failed, 8 passed»; `AGENTS.md` restaurado y su diff intacto (17 líneas añadidas) |
| Las skills pasan su guarda con las secciones nuevas | `uv run --no-sync pytest tests/automation/test_skills.py -q` | en verde dentro de las 806 pruebas de las seis guardas juntas, 3,0 s |
| El registro de ideas acepta I-007 promovida e I-008 aparcada | `uv run --no-sync pytest tests/automation/test_registro_de_ideas.py -q` | en verde (mismo lote) |
| Los ADR siguen bien formados y este es único | `uv run --no-sync pytest tests/automation/test_estado_de_los_adr.py tests/automation/test_registro_de_decisiones.py tests/automation/test_citas_de_los_adr.py -q` | en verde (mismo lote) |
| Documentos sin citas rotas | `scripts/automation/sirius_check_docs.py` sobre los nueve `.md` tocados | «Sin defectos documentales en los ficheros comprobados» |
| Formato, estilo y tipos | `ruff format --check .`, `ruff check .`, `mypy src tests` | limpio tras partir una línea larga del fichero de pruebas; mypy: 606 ficheros sin errores |
| La batería entera | `uv run --no-sync pytest` | **7 309 en verde, 17 saltadas, 2 xfailed y 1 roja, 13 min 58 s**; la roja es `test_todo_adr_que_declara_un_defecto_deja_su_entrada_en_el_registro` para ADR-213, que por diseño espera al commit siguiente (ADR-182) |
| `MEMORIA.md` al día | `uv run --no-sync sirius-memoria conocimiento` | regenerada en el mismo commit (ADR-171) |

## Consecuencias

- Una sesión que lea `AGENTS.md` sabe que contesta antes de seguir, cómo rinde
  cuentas por la mañana y que lo del ordenador va en lote.
- Un commit de datos ya no arrastra doce minutos de batería ni una
  regeneración de `MEMORIA.md` que la orden prohibía.
- Lo que sigue sin guarda: que alguien conteste tarde de todos modos. Es
  conducta; la guarda solo impide que la regla desaparezca de donde se lee.
- El registro de defectos recibe H-213 en el commit siguiente, con el sha de
  este arreglo (ADR-182, ADR-192): es el orden que la skill
  `registro-de-defectos` describe, y por eso la batería de este commit tiene
  una prueba roja por diseño.

## Alternativas descartadas y por qué

- **Una skill nueva para el parte de la mañana.** Tres párrafos no son una
  skill; la forma operativa cabe en la que ya existe, y las tres condiciones de
  ADR-211 piden fricción medida, que aquí es de una sesión.
- **Contar las rondas de la revisión externa desde esta rama.** El hallazgo
  T-04 lo pide, pero el contador viviría en el motor o en la PR de sesión, y
  eso es diseño del motor: va a I-008 con su disparador.
- **Borrar las ramas con `git push origin :refs/heads/…`** para no chocar con
  la regla textual del `deny`. Es la misma acción con otras palabras; la regla
  es suya y se respeta, y el borrado lo hace él.

## La lección

- familia: `regla-del-propietario-que-solo-vive-en-una-conversacion`
- sin esto se repetiría: que una regla que él dijo el 14-09 («que me contestes
  primero») se vuelva a violar el 20-09 porque no está donde la sesión lee, y
  que una orden de «no toques nada más» dispare doce minutos de batería y una
  regeneración de `MEMORIA.md`
- lo hace cumplir: `tests/automation/test_reglas_de_agents.py`
