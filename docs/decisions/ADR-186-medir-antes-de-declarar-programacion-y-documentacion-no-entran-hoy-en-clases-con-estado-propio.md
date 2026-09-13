# ADR-186 — Medir antes de declarar: programacion y documentacion no entran hoy en CLASES_CON_ESTADO_PROPIO

- Estado: PROPUESTO
- Fecha: 2026-09-13
- Aprobación: el propietario, fusionando la PR de la incidencia #605 (`WI-20260913-072231`)

## Contexto y problema

El contador de los siete días (contrato §11.2) lleva desde el 26-08-2026
escribiendo en `docs/operations/racha_siete_dias.jsonl` y **no ha contado ni un
solo día**. La causa está declarada y es honesta: `CLASES_CON_ESTADO_PROPIO`
(`src/sirius_engine/projection_verifier.py:86`) está vacío, así que
`precondicion_estado_propio` declara los dos ejes `NO_COMPARABLE` diciendo que
la etapa que el contador mide **no ha empezado** (H-25, ADR-101, #376).

Eso era verdad cuando se escribió. Desde el 04-09-2026 ya no lo es del todo:
C1 (ADR-136, ADR-137, ADR-173, #529) cableó el reflejo del desenlace de GitHub
al almacén, `reflejar-desenlace.yml` corre tras cada cambio de etiqueta y el
diario del motor tiene hoy 83 WorkItems con desenlace real. ADR-136 dejó C2
—declarar las clases— explícitamente **«para después de observar al menos una
pasada real»**. Ya van nueve días, y la incidencia #605 encarga cerrar ese
punto: medir primero, declarar solo si la medida lo sostiene.

El registro tiene hoy 356 líneas: 342 `no_comparable` por esta precondición y
14 `divergencia` anteriores a H-25 (26, 27 y 28-08-2026, todas de la forma
`motor=<WorkItemPhase.PREPARAR> incidencia=None`).

## Criterio de parada (escrito ANTES de decidir)

No es mío: lo publicó el propietario en el cuerpo de la incidencia #605, antes
de que nadie midiera nada, y no se ha tocado. Literal:

> Si lo que sale es DIVERGENCIA SISTEMATICA -no una ventana ni un caso
> suelto-, PARA con BLOCKED_BY_DECISION, explica que diverge y por que, y NO
> declares: declarar para que el contador acuse al motor de un defecto que es
> del reflejo seria peor que el silencio de hoy.

Y el subordinado que añade la nota de arranque
(`docs/audits/arranque-c2-medir-antes-de-declarar-la-precondicion.md`), más
estricto y nunca más laxo: **una clase sin ninguna línea comparable hoy tampoco
se declara**, porque declarar sin medida es justo lo que ADR-136 aplazó.

## Opciones consideradas

1. **Declarar las dos clases** (`programacion`, `documentacion`), reescribir
   `test_h25_el_conjunto_declarado_esta_vacio_hoy` y añadir la prueba que fija
   que una línea declarada ya no sale `no_comparable`. Es el camino (c) del
   encargo.
2. **No declarar ninguna** y dejar escrita la medida con el nombre exacto de lo
   que lo impide. Es el camino (b) del encargo.
3. **Declarar solo `documentacion`**, que es la clase sin líneas rojas.
4. **Declarar y, a la vez, abrir una ventana nueva** para el hueco que la
   medida destapa.

## Decisión

**Opción 2: hoy no entra ninguna de las dos.** La medida no sostiene la
declaración, y el encargo manda parar con `BLOCKED_BY_DECISION` en ese caso.
`CLASES_CON_ESTADO_PROPIO` sigue vacío y
`test_h25_el_conjunto_declarado_esta_vacio_hoy` sigue afirmándolo intacto.

Lo que se entrega es la medida —el paso (a) del encargo—, la decisión que
bloquea, y **una prueba de caracterización** que convierte el motivo del
bloqueo en algo que se rompe solo cuando alguien lo arregle:
`test_h25_una_parada_publicada_saldria_divergencia_en_fase_si_se_declarase`, en
`tests/engine/test_projection_verifier.py`.

Lo que falta decidir, y no es mío (por eso el bloqueo):

- **Decisión 1 — el eje `fase` frente a los dos estados detenidos.**
  `sirius:blocked-decision` y `sirius:failed-safely` proyectan `fase=None` por
  diseño (`_LABEL_STATE`, `src/sirius_engine/mirror_projection.py:352-353`): el
  vocabulario de etiquetas **no tiene fase** para los dos estados detenidos, y
  el propio módulo lo dice («estado cubre lo que fase no puede:
  `NEEDS_DECISION`, `FAILED_SAFELY`, los terminales»). Pero `_comparar` no lo
  sabe: compara `fase` contra `None` y lo llama `DIVERGENCIA`. Hace falta
  decidir si eso es una ventana nueva —la simétrica de la ventana 2, que ya
  exime al eje `estado` cuando «el vocabulario de etiquetas no puede
  expresarlo»—, si se cambia el vocabulario, o si se acepta. Las ventanas de
  este módulo son «medidas, no inventadas» y hoy son cinco; abrir la sexta no
  cabe en el alcance de #605, que además deja el §11.3 fuera de alcance duro.
- **Decisión 2 — el reflejo ante `failed-safely → blocked-decision`.** La
  regla 3 de `reflejar_desenlace` (`src/sirius_engine/reflect.py`) solo sale de
  una parada cuando el espejo deja de proyectarla Y hay marcador de reanudación
  publicado, y hacia `ACTIVE`/`PLANNED`/`DELIVERED`. De parada a **otra**
  parada no hay camino, así que el motor se queda en `FAILED_SAFELY` mientras
  la incidencia dice `NEEDS_DECISION`, y la divergencia es permanente. Tocar el
  reflejo está fuera de alcance duro en #605.

## Comprobación que la sostiene

Todo lo de abajo es **solo lectura**: copias en `/tmp` de `diario.jsonl` y
`diario-despacho.jsonl` de la rama `estado-del-motor` y lecturas `gh` del
espejo. No se escribió en esa rama ni en ningún registro.

```bash
git fetch origin estado-del-motor --depth=1
git show origin/estado-del-motor:diario.jsonl          > /tmp/medida/diario.jsonl
git show origin/estado-del-motor:diario-despacho.jsonl > /tmp/medida/diario-despacho.jsonl
git show origin/estado-del-motor:racha_siete_dias.jsonl > /tmp/medida/racha.jsonl
```

El guion de medida ejecuta la MISMA `verificar_dia` de producción dos veces por
WorkItem —con el conjunto vacío (hoy) y con `{PROGRAMACION, DOCUMENTACION}`
declaradas (C2)— reproduciendo el filtro exacto de la pasada real
(`src/sirius_engine/seven_day_streak_cli.py:280-322`: se compara solo lo no
terminal y con autoridad `INCIDENCIA`):

```python
linea = verificar_dia(
    motor=item,
    espejo=leer_y_proyectar_work_item(
        GitHubCliMirrorReader(), repo=episodio.repo,
        numero=episodio.numero_incidencia, ahora=ahora
    ),
    contexto=ContextoEjesDiarios(edad_etiqueta_maquina=None),
    ventana_tolerancia=ventana_tolerancia_etiqueta_maquina(Path(".github/workflows")),
    instante=ahora,
    clases_con_estado_propio=frozenset({WorkItemClass.PROGRAMACION, WorkItemClass.DOCUMENTACION}),
)
```

### Medida 1 — lo que la pasada de HOY escribiría (13-09-2026, 07:5xZ)

Los seis WorkItems no terminales con autoridad `INCIDENCIA`. «Hoy» es con el
conjunto vacío; «C2» es con las dos clases declaradas:

| WorkItem | clase | incidencia | hoy | C2 |
|---|---|---|---|---|
| `WI-20260913-042508` | programacion | #601 | `no_comparable` ×2 | **`fase=coincide` `estado=coincide`** |
| `WI-20260913-072231` | programacion | #605 | `no_comparable` ×2 | **`fase=coincide` `estado=coincide`** |
| `WI-20260913-000235` | programacion | #597 | `no_comparable` ×2 | **`fase=DIVERGENCIA`** `estado=coincide` |
| `WI-20260913-003150` | programacion | #599 | `no_comparable` ×2 | **`fase=DIVERGENCIA` `estado=DIVERGENCIA`** |
| `WI-20260828-122242` | investigacion | #392 | `no_comparable` ×2 | `no_comparable` ×2 (no se declara) |
| tres `needs_decision` sin despachar | programacion | — | sin línea | sin línea |

`documentacion`: **cero líneas**. Sus diez WorkItems (8 `delivered`, 2
`cancelled`) son todos terminales, así que la pasada real no los mira, y el
registro no tiene ni ha tenido nunca una línea de esa clase.

Los dos motivos exactos de las dos líneas rojas:

- #597 — `fase: motor=<WorkItemPhase.REVISAR: 'revisar'> incidencia=None`.
  La incidencia lleva `sirius:blocked-decision`, que proyecta
  `(NEEDS_DECISION, None)`. El eje `estado` **coincide**.
- #599 — `fase: motor=<WorkItemPhase.REVISAR: 'revisar'> incidencia=None;`
  `estado: motor=<WorkItemState.FAILED_SAFELY: 'failed_safely'> incidencia=<WorkItemState.NEEDS_DECISION: 'needs_decision'>`.

### Medida 2 — el mismo verificador contradice al reflejo

Sobre los mismos dos pares, `reflejar_desenlace` (el instrumento que C1 usa
para mantener el estado) dice:

```
WI-20260913-000235 #597 motor=needs_decision/revisar | espejo=needs_decision/None
   pasos=[]  divergencia=(ninguna)
WI-20260913-003150 #599 motor=failed_safely/revisar  | espejo=needs_decision/None
   pasos=[]  divergencia=«el motor está en estado=failed_safely fase=revisar y la
             incidencia proyecta estado=needs_decision fase=None; no hay camino
             hacia delante, no se toca nada»
```

Esto es lo decisivo, y es lo que convierte «dos líneas rojas» en «no declarar»:

- En **#597 los dos instrumentos se contradicen sobre el mismo dato**. El
  reflejo dice que el motor está exactamente donde la incidencia dice —cero
  pasos, cero divergencia— y el verificador, con la clase declarada, acusaría
  al motor de divergir en `fase`. No es el motor el que se equivoca: es que el
  eje `fase` compara contra un `None` que el vocabulario nunca podía llenar.
- En **#599 el que diverge es el reflejo**, y lo dice él mismo: no sabe seguir
  a la incidencia de una parada a otra. Declarar haría que el contador
  escribiera esa divergencia **a nombre del motor**, que es literalmente el
  caso que el criterio de parada prohíbe.

### Medida 3 — ¿es sistemático o es un caso suelto?

Contrafactual sobre los 70 WorkItems **terminales** de las dos clases (la
pasada real no los compara; se miden aquí para tener muestra, no seis líneas):

| clase | estado del motor | resultado con C2 declarado | n |
|---|---|---|---|
| programacion | `delivered` | `fase=coincide` `estado=coincide` | **46 / 46** |
| documentacion | `delivered` | `fase=coincide` `estado=coincide` | **8 / 8** |
| programacion | `cancelled` | `estado=no_comparable` (ventana 2); `fase` diverge | 9 de 14 |
| documentacion | `cancelled` | `estado=no_comparable` (ventana 2); `fase` diverge | 2 de 2 |

Las dos lecturas que salen de aquí, y son opuestas:

- **El camino feliz está sano.** 54 de 54 entregados coinciden en los dos ejes.
  El reflejo de C1 hace su trabajo; el bloqueo no es «C1 no funciona».
- **El hueco del eje `fase` no es un caso suelto.** Aparece en todos los
  WorkItems detenidos o cancelados —11 de 14 cancelados y 2 de 2 vivos
  detenidos—, porque es estructural: el vocabulario no tiene fase para ellos.
  Y basta uno para dejar el día rojo, porque `evaluar_racha`
  (`src/sirius_engine/seven_day_streak.py:416-426`) exige que **todas** las
  líneas del día coincidan. Con un solo trabajo parado en el diario —hoy hay
  cinco: cuatro `needs_decision` y uno `failed_safely`— la clase no puede
  encadenar siete días, y ninguno de esos rojos sería culpa del motor.

Dicho de otra forma: declarar hoy no cambiaría «cero días verdes» por «algunos
días verdes». Cambiaría **un silencio honesto por una acusación falsa, y
seguiría dando cero**.

### La prueba nueva, vista fallar

`test_h25_una_parada_publicada_saldria_divergencia_en_fase_si_se_declarase`
fija el motivo 1 del bloqueo sobre el caso exacto de #597. Mutación aplicada
para verla caer —la que será el arreglo del día de mañana—: en `_comparar`
(`src/sirius_engine/projection_verifier.py`), tratar `espejo is None` como no
comparable.

```
$ uv run pytest tests/engine/test_projection_verifier.py -k parada_publicada   # con la mutación
FAILED ... AssertionError: el eje fase ya no acusa al motor: revisa ADR-186 y reabre C2
$ uv run pytest tests/engine/test_projection_verifier.py -k parada_publicada   # sin la mutación
1 passed
```

## Consecuencias

- El contador sigue sin contar, y sigue diciendo por qué en cada línea. D1
  sigue bloqueado; nada se conmuta (§11.3 intacto, fuera de alcance).
- `CLASES_CON_ESTADO_PROPIO` sigue vacío y su guardián sigue entero: nadie
  puede declarar una clase sin tocar `test_h25_el_conjunto_declarado_esta_vacio_hoy`.
- Queda un rojo **útil**: la prueba nueva se romperá el día en que alguien
  arregle el eje `fase`, y el mensaje de ese fallo manda releer este ADR y
  reabrir C2. El bloqueo deja de depender de que alguien se acuerde.
- Las dos decisiones que faltan son pequeñas y están acotadas, con sus ficheros
  señalados. C2 es reintentable en cuanto se tomen: la medida de arriba se
  vuelve a correr en un minuto.
- Aviso para quien las tome: arreglar solo la decisión 1 deja `programacion`
  con tres de cuatro líneas verdes y #599 en rojo permanente. Hacen falta las
  dos.

## Alternativas descartadas y por qué

- **Declarar las dos (opción 1).** La medida no lo sostiene: dos de las cuatro
  líneas comparables de hoy salen en rojo por causas que no son del motor, y
  una de ellas es la que el criterio de parada nombra literalmente.
- **Declarar solo `documentacion` (opción 3).** Sería el único movimiento que
  no empeora nada hoy, y por eso mismo es el peor: no cambia una sola línea del
  registro —esa clase no tiene ningún trabajo vivo— y **gasta el gesto**. El
  conjunto pasaría a estar «no vacío» sin una sola medida detrás, que es
  exactamente lo que ADR-101 escribió que no se hiciera («jamás a mano para
  poner el día verde») y lo que ADR-136 aplazó hasta observar una pasada real.
  Tres de sus ocho entregados coinciden hoy en el contrafactual, sí, pero el
  contrafactual mide WorkItems que la pasada real **nunca** compara.
- **Declarar y abrir la ventana a la vez (opción 4).** Es probablemente el
  arreglo bueno, y sigue sin ser mío: #605 deja fuera de alcance duro el §11.3
  y el reflejo, las ventanas de este módulo son «medidas, no inventadas», y una
  sexta ventana cambia qué cuenta como día verde en el contrato. Además no
  bastaría sola: no arregla #599.
- **Parchear el reflejo para que siga `failed-safely → blocked-decision`.**
  Fuera de alcance duro y, encima, es la segunda ronda de la misma familia —el
  eje que no sabe distinguir «no hay dato» de «no coinciden»—, donde ADR-001
  prohíbe seguir parcheando y manda buscar la raíz.

## La lección

- familia: `medir-lo-que-se-tiene-en-vez-de-lo-que-hay`
- sin esto se repetiría: dar por buena una precondición porque la pieza que la bloqueaba ya existe -C1 lleva nueve días corriendo- en vez de ejecutar el verificador sobre los datos reales y leer lo que sale; aquí eso habría escrito dos acusaciones falsas al motor en la primera pasada, una de ellas contradiciendo al reflejo sobre el mismo dato.
- lo hace cumplir: `tests/engine/test_projection_verifier.py`
