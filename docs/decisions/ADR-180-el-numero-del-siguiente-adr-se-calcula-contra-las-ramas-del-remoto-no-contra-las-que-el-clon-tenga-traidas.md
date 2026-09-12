# ADR-180 — El numero del siguiente ADR se calcula contra las ramas del remoto, no contra las que el clon tenga traidas

- Estado: PROPUESTO
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

*(Pendiente: esta versión es la nota de arranque, confirmada antes del primer
cambio de código, como manda ADR-001.)*

## Criterio de parada (escrito ANTES de decidir)

El del apartado 3 de la nota de arranque.

## Opciones consideradas

*(Pendiente, al terminar.)*

## Decisión

Pendiente: esta versión es la nota de arranque. Lo que se propone: que
`scripts/siguiente_adr.py` traiga las cabezas del remoto antes de calcular el
número, degradando sin abortar cuando no haya red, y que diga cuál de las dos
cosas hizo.

## Comprobación que la sostiene

*(Pendiente: comandos y resultados, al terminar.)*

## Consecuencias

*(Pendiente, al terminar.)*

## Alternativas descartadas y por qué

*(Pendiente, al terminar.)*

## La lección

- familia: `medir-lo-que-se-tiene-en-vez-de-lo-que-hay`
- sin esto se repetiría: preguntarle a la copia local por un hecho que vive fuera -las ramas traídas en vez de las que existen- y creer que la respuesta cubre el caso; aquí el guion veía el 3,4% de las ramas y repartió el mismo número tres veces en un día.
- lo hace cumplir: `tests/automation/test_registro_de_decisiones.py`
