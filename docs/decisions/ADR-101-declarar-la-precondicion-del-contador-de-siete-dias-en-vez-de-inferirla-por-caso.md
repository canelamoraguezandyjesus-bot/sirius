# ADR-101 — Declarar la precondicion del contador de siete dias en vez de inferirla por caso

- Estado: APROBADO
- Fecha: 2026-08-28
- Aprobación: el propietario ordenó rematar lo pendiente el 28-08; la fusión
  de la PR lo confirma. Resuelve H-25 (#376) por su propia recomendación:
  «(A o B) ahora y (C) como bloque propio» — aquí se hace (B).

## Contexto y problema

H-25: el contador de los siete días (D1a/D1b) corre cada noche comparando el
estado del motor con el de la incidencia para clases cuyo estado el motor
todavía NO mantiene — nada escribe el desenlace de GitHub en su almacén, y los
seis WorkItems reales de la única pasada tienen exactamente dos sucesos
(creado y activado). El §11.2 pone la precondición literal: «el contador no
puede empezar antes de que el motor lleve el estado por sí mismo». Cada rojo
significa «esta etapa no ha empezado» y se lee «el motor se equivocó».

Es la segunda ronda de la familia de H-24 (regla de las dos rondas, ADR-001):
el verificador mete en DIVERGENCIA todo lo que no coincide, y cada caso nuevo
se venía tapando con una «ventana» más. La siguiente habría sido la 5.

## Criterio de parada (escrito ANTES de decidir)

- Si algún test existente dependiera de comparar sin declarar jurisdicción de
  forma que el cambio le cambiara el SIGNIFICADO, traerlo delante y decidir
  con él (ocurrió: el test del día verde del CLI; ver Comprobación).
- Si `authority_reversion` reaccionara a las líneas NO_COMPARABLE de forma
  inesperada, parar: la salida de emergencia no se toca a la ligera.
- Dos rondas con defectos de la misma familia → parar y nombrar la raíz.

## Opciones consideradas

Las tres de #376: **(A)** no registrar línea para una clase sin estado propio;
**(B)** registrar la línea como NO_COMPARABLE con motivo explícito; **(C)**
cablear el retorno del desenlace de GitHub al almacén (lo que de verdad
desbloquea D1). Y, ortogonal: inferir la precondición por caso (mirar si el
WorkItem tiene solo los sucesos del despacho) o declararla como hecho.

## Decisión

**(B), con la precondición como HECHO DECLARADO**, no como quinta ventana ni
como heurística por item:

- `projection_verifier.CLASES_CON_ESTADO_PROPIO: frozenset[WorkItemClass]` —
  vacío hoy, porque hoy es la verdad. Una clase entra SOLO desde el bloque
  que cablee el retorno del desenlace (la (C) de #376), con su evidencia,
  editando a conciencia `test_h25_el_conjunto_declarado_esta_vacio_hoy`.
- `verificar_dia` exige `clases_con_estado_propio` como parámetro obligatorio
  sin valor por defecto: nadie compara sin declarar jurisdicción (la misma
  lección que la tercera guarda del supervisor, C1-P3).
- Clase fuera del conjunto → los DOS ejes `NO_COMPARABLE` con motivo que cita
  el §11.2 y dice que la etapa no ha empezado. Manda sobre todas las ventanas,
  incluida la 0: las ventanas son tolerancias DE una comparación; esto dice si
  hay comparación que hacer. El día sigue sin ser verde: D1 sigue bloqueado,
  que es la verdad, pero el registro deja de acusar al motor.

Contra la heurística por item (solo-sucesos-de-despacho): parecería más
automática, pero una vez exista (C) un item al que (C) no le escribiera por un
fallo REAL quedaría «no comparable» para siempre — la heurística taparía
exactamente el defecto que el instrumento existe para ver. El hecho declarado
no puede tapar nada: o la clase está cableada y se compara entero, o no lo
está y se dice.

## Comprobación que la sostiene

`tests/engine/test_projection_verifier.py` (sección H-25, 4 pruebas nuevas
vistas FALLAR primero) y `test_h25_declarar_una_clase_devuelve_la_comparacion
_real_por_el_cli` (extremo a extremo: declarar la clase — lo que hará (C) —
devuelve el día verde por el CLI real). Cuatro mutaciones vistas caer: tratar
toda clase como declarada; tratar toda clase como no declarada; el CLI
puenteando la constante; las ventanas mandando sobre la precondición. El
criterio de parada (a) se materializó: el test del CLI que afirmaba
`es_verde is True` para PROGRAMACION cambió a la verdad nueva (línea
registrada, NO_COMPARABLE §11.2, día no verde) con el porqué en su cuerpo.
Detalle en `docs/audits/evidencia-h25-el-contador-declara-su-precondicion.md`.

## Consecuencias

- La pasada nocturna deja de escribir acusaciones falsas; escribe el hecho:
  «esta etapa no ha empezado». La racha sigue sin poder avanzar — correcto,
  el contrato dice que no hay nada que medir todavía.
- (C) tiene ahora un contrato de llegada claro: cablear el retorno del
  desenlace Y declarar la clase en el conjunto, con la prueba del conjunto
  editada a la vez. Queda como bloque propio, a la orden del propietario.
- `authority_reversion` no cambia: NO_COMPARABLE no es divergencia y no
  dispara reversión (ya probado en su suite, re-ejecutada aquí).

## Alternativas descartadas y por qué

- **(A) sin línea**: pierde la traza de que la pasada corrió; (B) la conserva
  sin acusar, y es la misma forma que ya usa la familia (ADR-096).
- **Ventana 5**: seguir parcheando la raíz que la regla de las dos rondas
  obligaba a nombrar.
- **Heurística por item**: ver Decisión — taparía defectos reales de (C).
- **(C) ahora**: alcance nuevo; #376 ya lo separa como bloque propio.
