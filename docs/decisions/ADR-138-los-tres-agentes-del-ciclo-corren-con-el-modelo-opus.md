# ADR-138 — Los tres agentes del ciclo corren con el modelo opus

- Estado: PROPUESTO
- Fecha: 2026-09-04
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario
- Cauce: ADR-002, opción 2 — cambio sobre `.github/workflows/**` hecho en
  sesión interactiva por decisión explícita del propietario (04-09-2026:
  «el modelo del implementador y de todo eso, opus… pongo opus y listo»),
  con su fusión como aprobación.

## Contexto y problema

Hasta hoy, ninguno de los tres workflows de agentes fijaba modelo: el
implementador (`implement-sirius-work.yml`), el corrector
(`repair-sirius-work.yml`) y el revisor Claude (`review-sirius-work.yml`)
corrían con el que la action trae por defecto. El coste de esa elección
quedó medido el 04-09-2026 en la bitácora del ciclo:

- Entradas 27-28: el bucle de reparación de G2/G3 — rondas de papel
  fabricadas por correcciones estrechas (atacadas por otra vía, ADR-135).
- Entrada 31: C1 necesitó seis rondas porque la semántica de las
  reanudaciones se descubrió a parches en vez de especificarse de una —
  el tipo de trabajo de diseño donde un modelo más capaz en el
  implementador y el corrector rinde más que en ningún otro sitio.

El propietario había aplazado esta palanca por la mañana para medir una
cada vez (primero ADR-135, cuya primera medición sostuvo la predicción:
cero rondas de papel en C1); esta noche decidió aplicarla.

## Criterio de parada (escrito ANTES de decidir)

- Cambiar SOLO el argumento de modelo: si el cambio exigiera tocar
  permisos, gates, prompts o cualquier otra línea de los tres workflows,
  parar y hablarlo.
- Tras la fusión: medir en la bitácora, con el mismo desglose ronda a
  ronda de las entradas 27-31, los dos próximos encargos. Si las rondas
  por encargo no bajan respecto a las de hoy (mediana 4,5 entre #523,
  #526 y #529), la palanca no rinde y se revierte con la misma facilidad
  (una palabra por fichero).

## Opciones consideradas

1. `--model opus` en los tres agentes (implementador, corrector, revisor
   Claude).
2. Solo implementador y corrector (la recomendación de la mañana: los
   revisores no eran el eslabón débil).
3. Mantener el modelo por defecto y esperar más mediciones de ADR-135.

## Decisión

**Opción 1**, por decisión del propietario («el implementador y todo
eso»): una palabra añadida a la línea `claude_args` de cada uno de los
tres workflows — `--model opus`, el alias que la CLI resuelve a la
generación vigente de esa familia, a propósito en vez de un
identificador con versión: no hay que volver a tocar los workflows
cuando la familia avance, y la resolución queda del lado de la cuenta
del propietario. El revisor Codex no es nuestro y no se toca. Ninguna
otra línea cambia.

## Comprobación que la sostiene

- `git diff origin/main` de esta rama: exactamente tres líneas
  cambiadas, una por workflow, todas en `claude_args`, todas añadiendo
  solo `--model opus` (implement-sirius-work.yml:281,
  repair-sirius-work.yml:649, review-sirius-work.yml:304).
- La suite de automation que vigila los workflows y los prompts de rol,
  en verde sobre el árbol final (salida citada en la PR).
- Lo no verificable antes de fusionar: el efecto sobre las rondas. Queda
  fijado arriba como criterio de parada medible sobre los dos próximos
  encargos, con la mediana de hoy (4,5 rondas) como listón.

## Consecuencias

- Surte efecto en el primer run de cada workflow tras la fusión; los
  encargos en vuelo no existen ahora mismo, así que no hay mezcla de
  modelos dentro de un mismo ciclo.
- El coste por ronda sube y la apuesta registrada es que el número de
  rondas baja más que proporcionalmente (entrada 27 de la bitácora:
  cada ronda extra paga dos revisores + corrector + CI).
- La medición de ADR-135 continúa en paralelo: sus dos viñetas del
  prompt aplican igual con cualquier modelo.

## Alternativas descartadas y por qué

- **Solo implementador y corrector (opción 2):** era la recomendación
  técnica de la mañana, pero el propietario eligió cubrir también al
  revisor Claude, y el argumento de coste que la sostenía pesa menos con
  su presupuesto real («no me consumen mucho»); mantener dos modelos
  distintos entre agentes también añade una variable a la medición.
- **Esperar más mediciones (opción 3):** la primera medición de ADR-135
  ya está tomada y C1 (entrada 31) dio el dato que faltaba sobre dónde
  duele el modelo por defecto; retrasarlo solo encarece los siguientes
  encargos.
- **Un identificador de modelo con versión:** obligaría a reabrir los
  tres workflows en cada relevo de la familia; el alias deja esa
  decisión donde debe estar, en la cuenta que ejecuta.
