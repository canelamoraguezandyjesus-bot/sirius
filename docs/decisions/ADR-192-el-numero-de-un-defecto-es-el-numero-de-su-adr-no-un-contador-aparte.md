# ADR-192 — El numero de un defecto es el numero de su ADR, no un contador aparte

- Estado: APROBADO
- Fecha: 2026-09-14
- Aprobación: el propietario, fusionando la PR de esta rama. La decisión de fondo
  —que el `H-N` deje de escribirse a mano— la tomó él el 14-09-2026 de madrugada.

## Contexto y problema

El identificador de un defecto se elegía leyendo el máximo que había en el
registro y sumando uno. Dos ramas abiertas a la vez leen cada una **su propio
árbol**, las dos aciertan, y las dos escriben el mismo número. No hay descuido:
el dato que se consulta no incluye lo que la otra rama está haciendo.

**Tres colisiones en una sola noche:**

| Cuándo | Quién chocó con quién | Cómo se vio |
|---|---|---|
| 13-09 ~16:28 | `H-38`: ADR-184 (#602) y ADR-185 (#604) | al traer `main` a la rama de #602 |
| 13-09 ~16:28 | `H-39`: ADR-184 (#602) y ADR-187 (#611) | **`main` en rojo** tras la segunda fusión |
| 14-09 ~03:30 | `H-43`: ADR-191 (#622) y ADR-190 (#620) | la segunda rama aún sin fusionar |

La tercera ocurrió **mientras se escribía ADR-191**, que es otra cosa: la cola
pone las ramas en fila para fusionar, pero dos ramas pueden coger el mismo número
aunque se fusionen una detrás de otra. Hacen falta los dos arreglos.

Es el mismo modo en que nacieron los **dos ADR-016** del registro de decisiones,
que la skill `adr` describe como lo que su guion **no** cierra.

## Criterio de parada (escrito ANTES de decidir)

Publicado en `docs/audits/arranque-el-identificador-de-defecto-no-se-escribe-a-mano.md`,
antes del primer commit de código. En resumen: la colisión tiene que quedar
imposible y no solo improbable; no se rompe ninguna cita existente; no se renumera
el pasado; la guarda de ADR-182 sigue en pie; y **si la medida contradice la
suposición de la nota, se dice y se replantea**.

Se replanteó dos veces, y las dos por lo que dijo la medida.

## Opciones consideradas

1. **Derivar de la incidencia.** Era la primera propuesta de la nota de arranque.
   **La medida la descartó**: siete entradas —`H-26` a `H-32`— declaran la misma
   incidencia (#396), y `H-40` y `H-43` declaran las dos la #608. Lejos de
   resolver la colisión, `H-<incidencia>` la **provoca** donde hoy no la hay.
   Además `H-35` no tiene incidencia, así que tampoco está siempre.
2. **Un identificador opaco** (resumen del contenido). Imposible de colisionar,
   pero ilegible: `H-a3f9c1` no se puede citar en una conversación ni en el
   mensaje de un commit, que es justo lo que hoy se hace (`H-13: ...`).
3. **Mirar mejor antes de elegir.** Es lo que ADR-180 hizo para los ADR. Estrecha
   la ventana, no la cierra: entre mirar y escribir sigue habiendo un hueco.
4. **El número del defecto ES el de su ADR.** Elegida.

## Decisión

**Uno. El número de un defecto nuevo es el número de su ADR.** `H-192` para el
defecto que declara ADR-192. Nadie elige nada: se copia un dato que la entrada ya
está obligada a declarar desde ADR-182.

**Dos. Se pasa de dos sistemas de numeración a uno**, y el que queda es el único
que tiene guion que lo coordina entre ramas (`scripts/siguiente_adr.py`,
ADR-180) y guarda que caza los repetidos (`test_registro_de_decisiones.py`).

**Tres. La frontera es UNA constante y no crece.** `PRIMER_ADR_CON_ID_DERIVADO`,
hermana de `PRIMER_ADR_CON_LECCION`, que resolvió lo mismo para ADR-174. Vive con
la guarda y no en `src/`: aquella la usa el generador de `MEMORIA.md`, esta no la
usa nadie en producción porque la regla **es** una guarda. Puesta en `src/`, la
guarda de ADR-179 la señaló como pieza sin llamante —y tenía razón—. La regla
vale para toda entrada cuyo `adr` sea mayor o igual que ella. **No es una lista de
excepciones** —la familia `lista-a-mano`, que este arreglo no puede reproducir—:
es un número que se escribe una vez y no se vuelve a tocar.

**Cuatro. Los defectos anteriores conservan su número.** Renumerarlos rompería el
vínculo con su commit de cierre, cuyo mensaje empieza por `H-N: ` y que la guarda
de ADR-080 lee. Y no hace falta un formato doble: los identificadores históricos
llegan a `H-43` y los ADR van por el 192, así que `H-<adr>` no puede chocar con
ninguno viejo.

**Cinco. Lo que esto NO es.** No es «imposible», es **coordinado**. Los dos
ADR-016 demuestran que ese número ha chocado. Lo que cambia es que pasa a haber
**un solo sitio donde puede chocar** en vez de dos, y ese sitio es el que sí está
defendido. El criterio de parada pedía imposible; esto no lo es, y no se vende
como si lo fuera.

## Comprobación que la sostiene

Las tres medidas, en `docs/audits/evidencia-el-identificador-de-defecto-no-se-escribe-a-mano.md`:

| | |
|---|---|
| Entradas del registro | 43 |
| Con `incidencia` | 30 — pero **siete comparten la #396** |
| Con `adr` | 11 — **las once desde `H-33`**, que es cuando ADR-182 lo exigió |
| Sin ninguno de los dos | 12, todas anteriores a que el motor creara incidencias |
| ADR con más de una entrada | **ninguno**: 11 ADR, 11 entradas |

**Tres guardas nuevas, y las dos últimas existen porque la primera sola sería
vacua por los dos lados:**

- `test_el_numero_de_un_defecto_nuevo_es_el_de_su_adr` — la regla.
- `test_la_frontera_deja_fuera_a_los_defectos_de_antes` — que **no** se aplique
  hacia atrás. Sin ella, mover la frontera a 0 pasaría inadvertido hasta que
  alguien renumerara once entradas y rompiera sus commits de cierre.
- `test_la_regla_del_identificador_se_ejercita_de_verdad` — que la frontera no se
  pueda mover hacia **delante**. Esta se añadió al ver que M2 sobrevivía: con la
  frontera en 9999 la primera prueba pasa sin mirar nada y la regla deja de
  existir en silencio.

**Tres mutaciones sembradas y vistas caer:**

| | Mutación | Resultado |
|---|---|---|
| M1 | frontera a 0 | 2 pruebas caen |
| M2 | frontera a 9999 | **sobrevivía**; con la tercera guarda, 1 cae |
| M3 | renumerar `H-192` a `H-44` | 1 prueba cae |

Y una cuarta comprobación que no vino de una mutación sino de una guarda ajena:
**ADR-179 señaló la constante como pieza sin llamante** cuando estaba en `src/`.
Se movió a la guarda, que es donde se usa.

## Consecuencias

- Quien da de alta un defecto ya no elige número: lo copia del ADR. Un paso menos
  y una decisión menos.
- Si dos ADR llegaran a chocar, los defectos chocarían con ellos. Es un solo
  fallo en vez de dos independientes, y tiene guion y guarda.
- `H-43`, dado de alta anoche con `adr: 191`, queda por debajo de la frontera y
  **no se renumera**. Es el último que se eligió a mano.

## Alternativas descartadas y por qué

Las cuatro de arriba, con su motivo. La que más cuesta descartar es la 3 —mirar
mejor—: es barata y ya está hecha para los ADR, pero estrechar una ventana no es
cerrarla, y el problema es que haya dos ventanas, no que una sea ancha.

## La lección

- familia: `regla-que-depende-de-que-alguien-se-acuerde`
- sin esto se repetiría: elegir a mano un identificador leyendo el máximo del
  propio árbol, cuando otra rama abierta a la vez lee el suyo y elige el mismo; el
  13 y el 14 de septiembre pasó tres veces en doce horas y una de ellas dejó
  `main` en rojo.
- lo hace cumplir: `tests/automation/test_registro_de_defectos.py`
