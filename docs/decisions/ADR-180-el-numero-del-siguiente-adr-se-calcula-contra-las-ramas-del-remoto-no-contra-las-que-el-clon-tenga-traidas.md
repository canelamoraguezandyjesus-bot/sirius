# ADR-180 — El numero del siguiente ADR se calcula contra las ramas del remoto, no contra las que el clon tenga traidas

- Estado: APROBADO
- Fecha: 2026-09-12
- Aprobación: la fusión de la PR por el propietario


## Nota de arranque (escrita ANTES de tocar una línea de código)

### Lo medido antes de escribir esta nota (12-09-2026, sobre este clon y el remoto)

| | |
|---|---|
| Ramas remotas que el clon tenía traídas | **14** |
| Ramas que hay en el remoto (`git ls-remote --heads`) | **409** |
| Cobertura del guion | **3,4 %** |
| Coste de traerlas todas (`git fetch` de las cabezas) | **4 segundos** |
| Número máximo de ADR que el guion veía con 14 ramas | 176 |
| Número máximo con las 409 | **179** |

Y lo que ese hueco produjo, hoy mismo: **tres ADR-177 distintos**, cada uno en
su rama abierta y ninguno en `main` -la ampliación por categoría (PR #590), la
autoridad por clase (PR #591) y la guarda de piezas sin llamante (PR #593)-.
Dos hubo que renumerarlos a mano, a 178 y 179. Es la misma forma en que
nacieron los dos ADR-016 que ADR-032 conserva, y la que ADR-044 creyó cerrar.

**ADR-044 arregló la mitad correcta del problema y dejó la otra escrita.** Su
propio docstring lo dice: «el guion solo ve las ramas **traídas**. Un
`git fetch` incompleto vuelve a dejar el hueco abierto». Lo que hoy se ve es
que ese límite no es teórico: en una sesión remota, el clon nace con las ramas
del arranque y nadie trae las demás, así que la cobertura real fue del 3,4 %.

### 1. ¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo OBSERVAR el fallo?

El fallo vive en `scripts/siguiente_adr.py`, en que pregunta «¿qué números usan
las ramas que tengo?» cuando la pregunta que importa es «¿qué números usan las
ramas que hay?». El arreglo va al mismo sitio: traer las cabezas del remoto
antes de calcular. Sí observa el fallo -el guion sabe cuántas ramas consultó, y
tras el arreglo esa cuenta pasa de 14 a 409- y cuesta 4 segundos medidos.

### 2. ¿Qué NO va a garantizar esto?

- **No cierra la ventana de carrera.** Dos sesiones que pidan número a la vez,
  antes de que ninguna haya empujado, seguirán recibiendo el mismo: el remoto
  no puede decir lo que aún no le han contado. Eso solo lo cierra una puerta al
  fusionar, y esa puerta ya existe -`tests/automation/test_registro_de_decisiones.py`
  falla en `main` con dos números iguales-. Lo que este cambio hace es que el
  caso frecuente -ramas abiertas desde hace horas o días- deje de ocurrir.
- **No es una puerta.** Sigue siendo un ayudante, como declara su propio
  docstring, y nada impide crear un ADR a mano con otro número.
- **No renumera nada del pasado** ni toca los dos ADR-016.
- **No hace obligatoria la red.** Sin red, el guion tiene que seguir
  funcionando exactamente como hoy, degradando a las ramas del clon, y decirlo.

### 3. Criterio de parada (decidido ANTES de ver ningún resultado)

- (a) El guion trae las cabezas del remoto antes de calcular y, sobre este
  clon, la cuenta de ramas consultadas pasa de 14 a 409.
- (b) Sin red, o con `git` ausente, o fuera de un repositorio, el guion sigue
  dando un número y **dice** que no pudo traer; nunca aborta.
- (c) El aviso que imprime distingue las dos situaciones, porque hoy dice
  «consultadas N ramas» sin decir si esa N es toda la verdad o un trozo.
- (d) Mutaciones vistas caer: que el guion vuelva a no traer; que el fallo del
  fetch se propague y aborte; que la cuenta de ramas no distinga traído de no
  traído.
- (e) `ruff`, `mypy` y la batería entera en verde.

Parada anticipada: si traer las cabezas del remoto resultara caro -más de unos
segundos- se para y se busca otra vía, porque un guion que tarda deja de usarse
y eso es peor que el fallo que arregla. **Medido antes de escribir esto: 4
segundos.**

### 4. ¿Qué haría el fallo IMPOSIBLE en vez de improbable?

Que el número no lo elija quien crea el ADR, sino que se asigne al fusionar
-un número que solo existe en `main`-. Eso cambia el convenio del registro
entero, rompe las citas de los ADR abiertos y es una decisión mucho más ancha
que esta. Queda dicho y no se hace aquí: lo de aquí hace el fallo **raro**, y la
puerta que ya existe en `main` lo hace **visible** cuando ocurra.

## Contexto y problema

El de la nota de arranque, medido: el guion veía el **3,4 %** de las ramas y
repartió el mismo número, 177, a tres ramas abiertas el mismo día.

## Criterio de parada (escrito ANTES de decidir)

El del apartado 3 de la nota de arranque.

## Opciones consideradas

1. **Avisar más fuerte y dejar que quien lo use haga `git fetch`.** Es lo que
   ya hacía -el aviso estaba ahí- y no evitó nada: quien pide un número no
   sabe que su clon está corto. Descartada.
2. **Consultar la API de GitHub** en vez de git. Añade una dependencia de red
   autenticada a un guion que hoy funciona sin credenciales, y dejaría de
   servir en un clon sin remoto de GitHub. Descartada.
3. **Traer las cabezas del remoto antes de calcular, degradando sin abortar.**
   Elegida; cuesta 4 segundos medidos y no añade ninguna dependencia nueva.
4. **Que el número se asigne al fusionar, no al crear.** Haría el fallo
   imposible en vez de raro, pero cambia el convenio del registro entero y
   rompe las citas de los ADR abiertos. Descartada aquí y dicha en la nota.

## Decisión

`scripts/siguiente_adr.py` trae las cabezas del remoto antes de calcular el número, con el refspec explícito `+refs/heads/*:refs/remotes/origin/*` para que un clon estrecho -el de una sesión remota, que clona una sola rama- también las reciba; si no puede traer -sin red, sin git, fuera de un repositorio- no aborta: calcula con lo que el clon tenga, como antes, y **lo dice con otra frase**, porque un número calculado sobre el 3,4 % de las ramas y uno calculado sobre todas no merecen la misma confianza.

En concreto:

- `_git` se parte en dos: `_correr_git` devuelve `(funcionó, salida)` y `_git`
  sigue devolviendo solo el texto para los lectores. La razón no es estética:
  `git fetch --quiet` **no imprime nada cuando va bien**, así que con la forma
  anterior «trajo» y «no pudo traer» eran la misma cadena vacía.
- `traer_las_cabezas` hace el fetch y devuelve si lo consiguió.
- `_como_se_consulto` produce el aviso, distinto en cada caso, y el de fallo
  dice qué hacer.
- `--sin-traer` conserva el comportamiento anterior para quien lo quiera.

## Comprobación que la sostiene

- Medición previa, sobre este clon: **14** refs remotas frente a **409** en el
  remoto; traerlas, **4 segundos**; máximo de ADR visto, **176 antes** y
  **179 después**.
- En vivo, tras el cambio: `traidas las cabezas del remoto; consultadas 308
  ramas con ADR`, y con `--sin-traer`, el aviso de cobertura parcial.
- `ruff format --check`, `ruff check scripts tests` y `mypy` en verde.
- Batería entera: **5.457 en verde** (17 omitidas, 2 xfail, 9 min 35 s).

**Seis mutaciones sembradas, y la sexta es la que enseña algo:**

| Mutación | Prueba que cae |
|---|---|
| El guion vuelve a no traer | la de traer antes de calcular |
| Se trae DESPUÉS de calcular, que es no traer | la misma |
| Refspec estrecho (`git fetch origin` a secas) | la del refspec explícito |
| El fallo del fetch se propaga y aborta | la de degradar sin abortar |
| El aviso deja de distinguir las dos situaciones | la del aviso |
| `_correr_git` vuelve a no distinguir fallo de salida vacía | **ninguna, al principio** |

La sexta pasó en verde con las once pruebas puestas, y el hueco era real: todas
inyectaban un git de mentira, así que nadie comprobaba que el booleano del que
cuelga todo lo demás valiera algo. Con la prueba que ejercita git **de verdad**
-una invocación que funciona y otra que falla-, la mutación cae. Es la cuarta
forma de prueba vacua del catálogo, encontrada por su mutación y no por mí.

## Consecuencias

- **Crear un ADR cuesta 4 segundos más**, y los paga quien lo crea.
- **Sin red el guion sigue funcionando**, y ahora se sabe cuándo fue así.
- La ventana de carrera -dos sesiones pidiendo a la vez- **sigue abierta**, y
  la caza la puerta que ya existe en `main` al fusionar. Hacerla imposible es
  la opción 4, que es otra decisión.
- Los dos ADR-016 históricos y los tres ADR-177 de hoy no se tocan: ADR-177 se
  queda en la PR #590, y los otros dos ya son 178 y 179.

## Alternativas descartadas y por qué

Las cuatro opciones de arriba, con su razón cada una.

## La lección

- familia: `medir-lo-que-se-tiene-en-vez-de-lo-que-hay`
- sin esto se repetiría: preguntarle a la copia local por un hecho que vive fuera -las ramas traídas en vez de las que existen- y creer que la respuesta cubre el caso; aquí el guion veía el 3,4% de las ramas y repartió el mismo número tres veces en un día.
- lo hace cumplir: `tests/automation/test_registro_de_decisiones.py`
