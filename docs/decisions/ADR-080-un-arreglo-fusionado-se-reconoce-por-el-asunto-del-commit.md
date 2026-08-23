# ADR-080 — Un arreglo fusionado se reconoce por el asunto del commit, y por eso la guarda ve poco pero no se equivoca

- Estado: APROBADO
- Fecha: 2026-08-23
- Aprobación: fusión de la PR por el propietario
- Contexto: tercera pieza de mecanizar el método, incidencia #267
- Relacionadas: ADR-001 (disciplina de evidencia: medir antes de fijar el
  criterio), ADR-075 (el registro versionado es la fuente autoritativa del
  estado de un defecto, no la incidencia de GitHub), ADR-078 y ADR-079 (los
  dos precedentes: elegir un criterio midiendo y escribir su precio),
  incidencia #267 (mecanizar el método)

## Contexto y problema

Dos veces en doce horas, un defecto arreglado y fusionado se quedó marcado
como `abierto` en `docs/audits/registro_defectos.yml`:

- **H-11**, arreglado en `18b4f2a` (#248) el 22-08. La entrada siguió
  `abierto` hasta que se corrigió a mano casi un día después.
- **H-13**, arreglado en `87163d9` (#283) de madrugada. La entrada siguió
  `abierto` hasta la mañana siguiente.

La segunda la cometió **la misma sesión que había corregido la primera**, y
sobre un defecto que ella misma había dado de alta unas horas antes. Eso
descarta la explicación cómoda: no es descuido, es que cerrar la entrada
dependía de que alguien se acordara.

Importa porque ADR-075 fijó que **el registro es la fuente autoritativa**. Si
su exactitud depende de la memoria de quien fusiona, la autoridad es nominal:
el 23-08 por la mañana el registro decía «un defecto abierto» y el defecto que
nombraba estaba arreglado desde hacía siete horas.

El guardián que ya existía —`tests/automation/test_registro_de_defectos.py`—
comprobaba seis cosas y ninguna era esta: que un defecto abierto no tuviera ya
su arreglo dentro.

## Criterio de parada (escrito ANTES de decidir)

1. **Si la señal produce falsos positivos, no entra tal cual.** Aquí un falso
   positivo no es ruido inocente: empuja a cerrar un defecto que sigue vivo,
   que es peor que no avisar. El listón es más alto que en una guarda normal.
2. **Si reconocer un arreglo exige red**, se para: el guardián del registro es
   determinista y barato a propósito, y tiene que seguir siéndolo el día en que
   lo ejecute un modelo pequeño.
3. **Si la guarda puede quedarse sin entradas y pasar en verde sin comprobar
   nada**, no entra sin su anti-vacua. Es el falso verde que este repositorio
   ya ha medido tres veces.

## Opciones consideradas

1. **Comparar contra el estado de la incidencia de GitHub.** Un defecto
   `abierto` cuya incidencia está cerrada es una contradicción. Descartada por
   el criterio de parada 2: exige red, y además ADR-075 dice que la incidencia
   no es la autoridad, así que la contradicción no diría en qué dirección
   corregir.
2. **Cualquier commit de `main` que NOMBRE el identificador.** Descartada tras
   medir: da un falso positivo inmediato (ver abajo).
3. **Un commit de `main` cuyo ASUNTO empiece por el identificador y dos
   puntos.** Es la opción elegida.

## Decisión

Opción 3. Un arreglo se reconoce cuando el asunto de un commit de `main`
empieza por el identificador del defecto seguido de dos puntos —`H-13: el
motor deja de necesitar el árbol de código`—, que es la convención que este
repositorio ya venía usando sin haberla escrito.

Si un defecto marcado `abierto` tiene un commit así en `main`, la batería se
rompe y dice cuál es.

Se lee con `git log`, sin red, como el resto del guardián.

## Comprobación que la sostiene

Medido el 23-08-2026 sobre los **14 defectos** del registro.

**La opción 2, ingenua**, produce un falso positivo inmediato:

```
H-14   abierto   2 commits nombran el identificador   <-- SEÑALARÍA
```

H-14 sigue abierto de verdad —el corrector no puede arreglar un fallo de
Quality, y arreglarlo necesita permiso sobre `.github/`—. Los commits que lo
nombran lo **describen**, no lo arreglan: uno lo da de alta en el registro y
otro explica por qué un bloque se quedó parado por su causa. Un identificador
mencionado no es un identificador resuelto.

**La opción 3, elegida**:

| | resultado |
|---|---|
| Falsos positivos sobre los 14 defectos | **0** |
| Casos reales que habría cazado | **2 de 2** (H-11 y H-13) |
| Defectos cerrados cuyo arreglo sigue la convención | **4 de 13** |

Los dos casos que motivan este ADR tienen commits que empiezan por su
identificador —`H-11: diario del despachador durable…` y `H-13: el motor deja
de necesitar el árbol…`—, así que la guarda los habría roto el mismo día.

**Dos mutaciones vistas fallar (ADR-001):**

1. Marcando H-13 como `abierto` —literalmente lo que ocurrió— cae
   `test_ningun_defecto_abierto_tiene_ya_su_arreglo_en_main`.
2. Sustituyendo el criterio por el ingenuo de la opción 2 cae
   `test_el_criterio_reconoce_el_arreglo_y_no_la_mera_mencion`, y lo dice
   nombrando el asunto: «el criterio confunde nombrar con arreglar: *Cerrar
   H-13 en el registro y dar de alta H-14 (#286)*».

Con el árbol correcto, 22 passed.

Y una tercera, **intentada y descartada por inútil**, que merece quedar escrita
porque estuvo a punto de colarse como evidencia: aflojar el patrón *o* cambiar
`match` por `search`, **por separado**, no rompe nada. `match` ya ancla al
principio, así que cada mitad por su cuenta es un cambio sin efecto. Una
mutación que no cambia el comportamiento no demuestra nada: la prueba de que la
prueba muerde son las dos mitades juntas, que es el criterio ingenuo entero.

## Consecuencias

**El alcance es corto y es deliberado.** Solo 4 de los 13 defectos cerrados
tienen un commit que siga la convención; los otros nueve se arreglaron con
asuntos que no empiezan por el identificador, y a esos **esta guarda no los
ve**. No es un descuido pendiente de arreglar: es el precio de no equivocarse.

La asimetría está elegida a conciencia. Un falso negativo deja una entrada
vieja, que es lo que ya pasaba antes de esta guarda. Un falso positivo
empujaría a marcar como cerrado un defecto vivo, y eso rompe la propiedad que
ADR-075 protege. Ante la duda, callar.

**Efecto lateral esperado, y bienvenido:** la guarda premia la convención. Un
arreglo cuyo asunto empiece por el identificador queda vigilado; uno que no,
no. Si con el tiempo la convención se generaliza, el alcance sube solo, sin
tocar el criterio.

**Dónde corre, y dónde no.** Medido el 23-08-2026 sobre la ejecución
32633782403: en Quality esta guarda **no corre**. Quality clona con
`actions/checkout` y la profundidad por defecto, y en una PR eso deja un árbol
sin `origin/main`; `git log origin/main` sale con código 128. La primera versión
de la guarda se estrelló ahí y puso la PR en rojo por un motivo de entorno, no
por un defecto del registro.

La salida elegida es **saltar y decir por qué**, no apañarse con lo que haya. La
tentación era caer a `HEAD`, que sí resuelve: leería una historia de UN commit,
no encontraría ningún arreglo y pasaría en verde sin haber comprobado nada. Se
descarta por el criterio de parada 3 — es exactamente el falso verde que este
repositorio ya ha pagado tres veces. Por el mismo motivo se salta también cuando
la referencia resuelve pero no deja ver ni un commit de la convención, que es lo
que pasaría en un `push` a `main` con el clon por defecto.

Un salto declarado deja la guarda sin dientes en CI, así que la parte que sí
puede correr en cualquier árbol se separó en una prueba propia: el criterio se
comprueba contra asuntos reales del repositorio —dos que arreglan y dos que solo
nombran— sin tocar el historial. Así, lo que el entorno se lleva es el alcance,
no la garantía de que el criterio siga mordiendo.

**Lo que lo cambiaría** es una línea, `fetch-depth: 0` en el checkout de Quality,
y no se hace aquí por dos motivos: ADR-002 prohíbe que la automatización edite
`.github/**`, y encarecer cada ejecución del ciclo para una sola guarda es una
decisión del propietario, no de este bloque. Queda anotado, no ejecutado.

**Lo que sigue sin mecanizar:** que la entrada se cierre *sola*. Esta guarda
avisa de la contradicción; cerrarla sigue siendo un acto humano. Se avisa
antes de que el registro mienta, que es lo que faltaba.

## Alternativas descartadas y por qué

- **Consultar la API de GitHub** para comparar con el estado de la incidencia:
  descartada por el criterio de parada 2 (exige red) y porque ADR-075 ya
  establece que la incidencia no es la autoridad.
- **Cualquier mención del identificador**: descartada tras medir, con el falso
  positivo de H-14 como evidencia.
- **Caer a `HEAD` cuando `origin/main` no resuelve**, para que la guarda
  «corra igualmente» en Quality: descartada por el criterio de parada 3. En ese
  árbol `HEAD` trae un commit, así que la guarda pasaría en verde sin comprobar
  nada. Un verde falso es peor que un salto declarado.
- **Exigir la convención `H-N:` a todo commit que arregle un defecto**, para
  subir el alcance: sería una regla nueva sobre cómo escribir commits, fuera
  del alcance de una guarda del registro, y con el riesgo conocido de que una
  regla que nadie comprueba se incumple. Si algún día se quiere, es su propia
  decisión.
