# ADR-139 — La reconciliación pasa cada hora activa en vez de cada seis

- Estado: RECHAZADO — refutado por los guardianes durante el propio
  intento; el cron queda como estaba (`17 */6 * * *`) y este ADR registra
  por qué no puede ser más denso.
- Fecha: 2026-09-05
- Aprobación: la fusión de la PR que introduce este ADR, por el
  propietario — con su autorización nocturna del 04-09-2026, la ejecuto
  yo si Quality y mi revisión están en verde. Cauce ADR-002, opción 2.

## Contexto y problema

La carrera del verde de Quality: cuando el verde llega mientras la
incidencia está en `sirius:repairing` o `sirius:reviewing`, no se
consume, y la incidencia queda atascada hasta que alguien relanza a
mano. Medido: 4 veces en la ola de criticidad (#508, #514, #520 ×2;
deuda 3 de la bitácora) y varias más el 04-09. El reconciliador
(`reconcile-sirius-states.yml`) cura esos atascos solo, pero pasa cada
6 horas. La propuesta barata del informe de la mina v2 (documentada en
`docs/audits/mina-2026-09-cambios-para-el-propietario.md`): que pase
cada hora. **Esa propuesta es anterior al contador de siete días y nunca
se había chocado contra sus invariantes de hora; este ADR registra el
choque.**

## Criterio de parada (escrito ANTES de decidir)

- Solo el cron y sus comentarios: si hiciera falta tocar la lógica del
  reconciliador o los lectores de crones del motor, parar — eso sería un
  encargo, no este cambio.
- Los guardianes de la hora del contador mandan: cualquier variante que
  los ponga en rojo se descarta, no se debilita. **Este criterio es el
  que acabó rechazando la decisión entera.**

## Opciones consideradas

1. `17 * * * *` — cada hora, la letra de la propuesta original.
2. `17 0,4-23 * * *` — cada hora salvo la ventana de silencio del
   contador, con rango.
3. `17 0,4,…,23 * * *` (una lista con comas) y su variante final de 21
   entradas de `schedule` con horas sueltas.
4. `17 */4 * * *` — cada cuatro horas.

## Decisión

**Ninguna: se rechaza densificar el cron y se conserva `17 */6 * * *`.**
Las cuatro variantes caen, cada una con su rojo visto fallar (abajo), y
la cuarta cae por el mismo teorema que la tercera sin necesidad de
ejecutarla: el derivador de la hora del contador
(`sirius-racha --hora-recomendada`, `seven_day_streak.py:497`) exige que
el mayor hueco libre de disparos programados del día DOBLE la ventana de
tolerancia — hoy 170 min de tolerancia (máximo `timeout-minutes` del
repositorio, 85, por dos), o sea un hueco de ≥340 min. Con pasadas cada
hora el mayor hueco del día ronda los 172 min; con cada 4 horas, 240.
Solo el cada-6 vigente (hueco de 360) cumple. **Bajo el régimen de
tolerancia actual, el ritmo del reconciliador no puede subir; punto.**

Lo que sí puede curar la carrera en ≤1 h es la «opción completa» del
mismo informe: que la ruta de avance acepte también verdes de Quality
para incidencias en `sirius:repairing` cuyo último veredicto del
corrector sea FIXED con el mismo head — lógica del motor, pariente de la
deuda 10 de la bitácora, y merece su encargo con revisión dual.

## Comprobación que la sostiene

Cuatro rojos, los tres primeros vistos fallar y el cuarto derivado del
mismo invariante:

1. `17 * * * *`:
   `test_la_hora_del_contador_deja_pasar_la_ventana_de_tolerancia`
   falla — «el contador dispara a las 03:24 UTC y solo deja 7 min
   tranquilos por delante, cuando la tolerancia vigente es de 170 min».
   La letra de la propuesta habría hecho NO_COMPARABLE cada día.
2. `17 0,4-23 * * *`: los guardianes del contador revientan con
   `ValueError: invalid literal for int() with base 10: '4-23'`
   (`seven_day_streak._expandir_campo`): ese lector entiende `*`, `*/N`
   y comas, no rangos.
3. La lista con comas: Quality (run 33931016125) cazó lo que mi
   validación local no vio por correr solo tests/automation —
   `test_hora_recomendada_atada_al_schedule_real_del_repositorio`
   (tests/engine/test_seven_day_streak.py:521) usa OTRO lector de crones
   que no entiende ni comas. Y su variante de 21 entradas con horas
   sueltas, que ambos lectores digieren, cayó donde ya no hay sintaxis
   que valga: `ValueError: el mayor hueco libre de disparos periódicos
   (172 min) no deja ni su mitad (86 min) por delante de la ventana de
   tolerancia (2:50:00): ninguna hora produciría días verdes con el
   ritmo real del repositorio` (`seven_day_streak.py:497`).
4. `17 */4 * * *`: mismo invariante, sin ejecutar — hueco máximo 240 <
   340. Se registra para que nadie lo intente como «término medio».

Sobre el árbol final (cron revertido, prueba del cron con su comentario
nuevo, este ADR): validaciones obligatorias con código de salida
verificado, citadas en la PR.

## Consecuencias

- El cron no cambia; la cura de la carrera sigue tardando ≤6 h por esta
  vía. La vía real (la «opción completa») queda señalada aquí, en el
  comentario del propio workflow y en la deuda 10.
- El papel del propietario
  (`docs/audits/mina-2026-09-cambios-para-el-propietario.md`) queda
  parcialmente superado: su «opción barata» no debe aplicarse; este ADR
  es la referencia.
- Candidata de limpieza para la lista de deudas: el repositorio tiene
  dos lectores de crones con dos dialectos distintos (el del motor y el
  del test de la hora recomendada); unificarlos evitaría que la próxima
  persona descubra el segundo por un rojo de Quality.

## Alternativas descartadas y por qué

Las cuatro de arriba, cada una con su rojo. Y la de forzarlo bajando los
`timeout-minutes` del repositorio para encoger la tolerancia: tocaría
los presupuestos de los cuatro workflows críticos del motor para
acomodar un cron — la cola meneando al perro.
