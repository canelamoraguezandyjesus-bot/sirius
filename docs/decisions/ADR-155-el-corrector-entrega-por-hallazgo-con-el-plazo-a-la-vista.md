# ADR-155 — El corrector entrega por hallazgo, con el plazo a la vista

- Estado: PROPUESTO
- Fecha: 2026-09-06
- Aprobación: decisión del propietario del 06-09-2026 a las 14:12 UTC
  («Ficha deuda 8 y luego continua»), y la fusión de esta PR (toca
  `.github/**`: ficha del operador).

Esta es también la nota de arranque de la rama
`claude/adr-155-entrega-por-hallazgo`, publicada antes del primer cambio, con
las cuatro preguntas de la disciplina de evidencia (ADR-001).

## Contexto y problema

El corrector tiene 36 minutos por ronda (ADR-150), y no puede tener más: el
contador de siete días prohíbe cualquier job por encima de 85 minutos. Dentro
de esos 36 tiene que corregir todos los hallazgos de la ronda y ejecutar una
sola vez la cadena completa (ADR-145), que tarda entre 9 y 15 minutos en el
runner. Cuando la ronda trae varios hallazgos de fondo, no cabe, y el modo de
fallo es el peor posible: **el paso muere y no queda nada**, porque el
corrector solo empuja al final.

Los datos, los dos en #545:

- Ronda 1 (run 33998592213, 05-09): murió a los 30:00 con `pwsh`, `uv` y
  `pytest` vivos; había corregido tres hallazgos y estaba validando. Sin push.
  ADR-150 subió el tope a 36 y dejó escrito su criterio de refutación: «una
  segunda muerte por tiempo desmiente el ADR y señala a la deuda 8».
- Ronda 4 (run 34036357352, 06-09, 13:32 → 14:08): murió a los 36:12 con
  cuatro hallazgos (dos P1 de `reflect.py`, un P2 y un P3). Sin push. Treinta
  y seis minutos de trabajo perdidos enteros, y la incidencia en
  `failed-safely` por segunda vez en el día.

La deuda 8 de la bitácora del ciclo lo tenía nombrado desde el 02-09
(entradas 9 y 16): «presupuesto o un commit por hallazgo cuando la ronda
trae varios». No es un problema de minutos —no hay más— sino de la forma de
la ronda: el corrector trabaja a ciegas respecto a su plazo y entrega todo o
nada.

## Nota de arranque (cuatro preguntas, ADR-001)

1. **¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo
   observar el fallo?** Vive en dos sitios: el corrector no sabe cuándo muere
   (el workflow lo sabe y no se lo dice) y no empuja hasta el final (su prompt
   no se lo pide). El arreglo va a los dos: el paso que prepara el prompt
   calcula la hora a la que muere el paso del corrector y la hora límite para
   arrancar la validación, y las escribe en el contexto; el prompt exige
   corregir por orden de severidad, empujar tras cada hallazgo y, llegada la
   hora límite, validar lo hecho, empujar y declarar lo que falta. Se observa
   en el log del run (los commits intermedios) y en el veredicto (la lista de
   corregidos y no corregidos).
2. **¿Qué NO garantiza esto?** No garantiza que una ronda corrija todos sus
   hallazgos: garantiza que lo corregido no se pierda y que lo que falta quede
   dicho. No cambia el tope de 36 ni el de 85. No cambia el criterio de
   convergencia: una ronda parcial con menos pendientes es progreso por la
   regla vigente; una ronda parcial sin ningún hallazgo corregido no lo es, y
   el freno seguirá parando. No garantiza que el corrector obedezca el plazo:
   si lo ignora y muere, la diferencia respecto a hoy son los pushes
   intermedios, que sí sobreviven.
3. **Criterio de parada (decidido antes de ver ningún resultado).** Los
   guardianes nuevos ven FALLAR el workflow y el prompt vigentes (sin plazo en
   el contexto, sin regla de entrega por hallazgo, y el `FIXED` que presupone
   todo corregido) y pasan con el cambio; el número de minutos del plazo que
   el prompt recibe es el mismo `timeout-minutes` del paso del corrector,
   sujetado por guardián; la cadena completa termina en 0. En vivo: la
   siguiente ronda de #545 (cuatro hallazgos) deja al menos un push antes de
   la hora límite y termina en `FIXED` con su lista de corregidos y no
   corregidos, o muere por tiempo con la rama ya avanzada; en cualquiera de
   los dos casos la revisión siguiente cuenta menos pendientes que cuatro.
   Una tercera muerte por tiempo SIN ningún push intermedio desmiente este
   ADR.
4. **¿Qué hace esto imposible, en vez de improbable?** Que un paso muerto por
   tiempo se lleve todo el trabajo de la ronda: el trabajo empujado ya está
   en la rama cuando el runner muere. Y que el corrector no pueda saber cuánto
   le queda: la hora la calcula el workflow con el mismo número que gobierna
   el tope, y un guardián prohíbe que los dos números se separen.

## Criterio de parada (escrito ANTES de decidir)

Ver punto 3 de la nota de arranque.

## Opciones consideradas

1. **Plazo a la vista, corrección por severidad y push por hallazgo, en el
   prompt y en el contexto** (elegida). Cabe en el presupuesto actual, no toca
   la máquina de estados ni el aplicador del veredicto, y convierte la muerte
   por tiempo en una ronda parcial en vez de en una ronda perdida.
2. **Sacar la cadena del presupuesto del agente** (opción 4 de ADR-150: el
   workflow ejecuta `check.ps1` después del agente). No cabe hoy: con el job
   en 85 y la suma de pasos en 80, un paso de cadena de 10-15 minutos obliga a
   recortar otros pasos por debajo de lo medido (Quality tardó 15 min esta
   tarde), y el agente empuja por su cuenta, así que un rojo posterior no
   impediría el push. Sigue siendo la salida de fondo para cuando el
   presupuesto cambie; no sustituye a esta.
3. **Subir el tope.** Imposible sin romper la geometría del contador
   (ADR-150).
4. **Un veredicto nuevo (`FIXED_PARTIAL`).** Descartada: obligaría a tocar el
   aplicador, el agregador y sus guardianes para decir lo que `FIXED` con un
   resumen honesto ya dice; la revisión siguiente vuelve a levantar lo que
   falte, que es exactamente el camino que ya existe.

## Decisión

- `repair-sirius-work.yml`, paso «Preparar instrucciones para Claude Code»:
  calcula con `date -u` la hora a la que muere el paso del corrector
  (`PLAZO_MIN`, el mismo número que su `timeout-minutes`) y la hora límite
  para arrancar la validación final (`PLAZO_MIN − 16`, la reserva medida
  para una cadena de 9-15 minutos más el push), y las escribe en la sección
  «Contexto de esta ejecución» del prompt.
- `scripts/automation/prompts/corrector.md` (in situ, como ADR-135/145/154):
  corregir de mayor a menor severidad; commit y push tras cada hallazgo
  corregido con su prueba (el push intermedio no necesita la cadena
  completa); llegada la hora límite, dejar de corregir, validar lo hecho una
  sola vez, empujar y escribir `FIXED` nombrando por identificador los
  hallazgos corregidos y los no corregidos. La definición de `FIXED` pasa a
  admitir esa entrega parcial declarada.
- Guardianes: el número de minutos del plazo que escribe el paso de prompt
  coincide con el `timeout-minutes` del paso del corrector; el contexto lleva
  las dos horas; el prompt lleva las tres reglas (severidad, push por
  hallazgo, plazo) y el `FIXED` parcial declarado.

## Comprobación que la sostiene

- Guardianes vistos fallar contra el workflow y el prompt de `main`, y en
  verde con el cambio; guardianes existentes del workflow del corrector
  intactos: transcritos en el cuerpo de la PR.
- Cadena completa como una sola invocación, anclada a su árbol (ADR-154):
  transcrita en el cuerpo de la PR.
- Lo que NO se ha medido: el caso en vivo (criterio 3), que mide la
  reanudación de #545.

## Consecuencias

- Una ronda del corrector ya no es todo o nada: lo corregido queda en la
  rama y lo que falta queda escrito. El coste de una muerte por tiempo baja
  de «la ronda entera» a «lo que no cupo».
- Las rondas con muchos hallazgos pueden necesitar más de una vuelta; cada
  vuelta cuenta menos pendientes, que es lo que la política de convergencia
  llama progreso.
- La deuda 8 queda saldada en su mitad de presupuesto por hallazgo; la
  cancelación cuando el propietario corrige a mano (entrada 17) sigue
  abierta.

## Alternativas descartadas y por qué

Ver «Opciones consideradas».
