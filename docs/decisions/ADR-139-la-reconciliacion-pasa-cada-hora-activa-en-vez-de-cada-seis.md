# ADR-139 — La reconciliación pasa cada hora activa en vez de cada seis

- Estado: PROPUESTO
- Fecha: 2026-09-04
- Aprobación: la fusión de la PR que introduce este ADR, por el
  propietario — con su autorización nocturna del 04-09-2026 («haz las
  cuatro cosas… te doy la libertad de fusionar cuando hayan pasado por
  revisión y tú los hayas revisado»), la ejecuto yo si Quality y mi
  revisión están en verde. Cauce ADR-002, opción 2.

## Contexto y problema

La carrera del verde de Quality: cuando el verde llega mientras la
incidencia está en `sirius:repairing` o `sirius:reviewing`, no se
consume, y la incidencia queda atascada hasta que alguien relanza a
mano. Medido: 4 veces en la ola de criticidad (#508, #514, #520 ×2;
deuda 3 de la bitácora) y varias más el 04-09. El reconciliador
(`reconcile-sirius-states.yml`) cura esos atascos solo, pero pasaba cada
6 horas (`17 */6 * * *`): atasco curado en ≤6 h. La propuesta barata del
informe de la mina v2 (documentada en
`docs/audits/mina-2026-09-cambios-para-el-propietario.md`): que pase
cada hora.

## Criterio de parada (escrito ANTES de decidir)

- Solo el cron y sus comentarios: si hiciera falta tocar la lógica del
  reconciliador o el lector de crones del motor, parar — eso sería un
  encargo, no este cambio.
- Los guardianes de la hora del contador mandan: cualquier variante que
  los ponga en rojo se descarta, no se debilita.

## Opciones consideradas

1. `17 * * * *` — cada hora, la letra de la propuesta original.
2. `17 0,4-23 * * *` — cada hora salvo la ventana de silencio del
   contador, con rango.
3. `17 0,4,5,…,23 * * *` — lo mismo, con lista explícita de horas.
4. `17 */4 * * *` — cada cuatro horas (mejora sin acercarse a la
   ventana).

## Decisión

**Opción 3.** Cada hora activa (las 00 y de 04 a 23, siempre al minuto
:17), saltándose la madrugada 01-03. Las dos primeras opciones cayeron
por sus rojos, los dos vistos fallar y citados abajo; la cuarta curaría
en ≤4 h lo que la elegida cura en ≤1 h durante todo el horario en que el
ciclo trabaja de verdad. El hueco de madrugada es el único momento sin
cobertura horaria, y es exactamente cuando no hay ciclos activos que
generen la carrera; en el peor caso un atasco de las 00:30 espera a las
04:17.

## Comprobación que la sostiene

Dos rojos previos, vistos fallar (ADR-001):

1. Con `17 * * * *`,
   `test_la_hora_del_contador_deja_pasar_la_ventana_de_tolerancia`
   falla: «el contador dispara a las 03:24 UTC y solo deja 7 min
   tranquilos por delante, cuando la tolerancia vigente es de 170 min»
   — la letra de la propuesta original habría hecho NO_COMPARABLE cada
   día, igual que el cron que el mismo guardián me tumbó en ADR-137.
2. Con `17 0,4-23 * * *`, los guardianes del contador revientan con
   `ValueError: invalid literal for int() with base 10: '4-23'`
   (`seven_day_streak._expandir_campo`): el lector de crones del motor
   entiende `*`, `*/N` y comas, no rangos — y extenderlo sería tocar el
   motor, fuera del alcance de este cambio (criterio de parada).

Con la lista explícita: `tests/automation/test_contador_de_siete_dias.py`
9/9 en verde; la suite de automation completa en verde sobre el árbol
final (salida en la PR). El diff toca un único fichero
(`.github/workflows/reconcile-sirius-states.yml`): el cron y sus
comentarios.

## Consecuencias

- Un atasco por la carrera del verde se cura solo en ≤1 h en horario
  activo (antes ≤6 h); la intervención manual que hoy hacía yo (relanzar
  el run verde) deja de ser necesaria salvo de madrugada.
- Más pasadas del reconciliador: es de lectura y reetiquetado
  condicional, idempotente por diseño (su propio encabezado lo explica),
  así que el coste es cuota de API, no riesgo.
- Si alguien cambia la hora del contador o la tolerancia, este cron está
  en la lista de los que hay que rederivar (los comentarios del fichero
  lo dicen; el guardián lo exige).

## Alternativas descartadas y por qué

- **Cada hora a secas / con rango:** los dos rojos de arriba.
- **Cada 4 horas (`*/4`):** pasa los guardianes, pero cura en ≤4 h lo
  que la elegida cura en ≤1 h; la única ventaja sería la estética del
  cron, y este fichero se lee una vez al año.
- **La «opción completa» del informe (que la ruta de avance acepte
  también `repairing` con head coincidente):** sigue siendo mejor de
  raíz y sigue pendiente — es lógica del motor y merece su encargo con
  revisión dual, no un cambio nocturno de cron (relacionada con la
  deuda 10).
