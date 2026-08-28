# Nota de arranque — H-29: la intención durable antes del efecto externo

Fecha: 2026-08-28. ANTES del primer cambio (ADR-001). Corrección autorizada.

## Afirmación a corregir (verificada en #396)

`dispatch_work_item` crea la incidencia y aplica la etiqueta ANTES de
`journal.record`, y ante cualquier excepción libera la reserva. Una caída entre
el efecto en GitHub y el registro durable deja el diario sin episodio: el
reintento crea una SEGUNDA incidencia para el mismo `work_id`.

## Lo que se decide construir (las dos mitades del informe, combinadas)

1. **Intención durable antes del efecto**: el diario gana
   `record_intencion(work_id)` / `intencion_pendiente(work_id)`, y el
   despachador la graba ANTES de tocar GitHub.
2. **Adopción al reintentar**: si al reservar hay intención pendiente sin
   episodio, el despachador BUSCA la incidencia por su `work_id` (el cuerpo lo
   lleva en `## Work ID`) con un método nuevo del puerto de escritura:
   - encontrada → la ADOPTA: re-aplica la etiqueta (idempotente en GitHub) y
     graba el episodio con ese número;
   - no encontrada → la caída fue antes de crear: se crea con normalidad.

Ventanas cubiertas: caída tras la intención (reintento no encuentra → crea una),
tras crear (encuentra → adopta), tras etiquetar (encuentra → adopta). En todas,
el mismo `work_id` converge a UNA incidencia y UN episodio.

## Las preguntas

1. ¿La prueba nueva se ve FALLAR hoy: caída tras crear → reintento → DOS
   incidencias creadas? (es la reproducción exacta del informe)
2. ¿Las tres ventanas convergen a una incidencia y un episodio, contando las
   ESCRITURAS del escritor falso, no leyendo el código?
3. ¿La adopción exige coincidencia de `work_id`? Adoptar la incidencia
   equivocada sería peor que duplicar.
4. ¿El camino feliz no cambia de forma observable (mismos verbos, mismo orden
   de efectos en GitHub)?

## Criterio de parada

- (a) Si la búsqueda de adopción fallara (red), el reintento NO crea: se para
  con error reintentable. Ante la duda, ninguna incidencia nueva.
- (b) La intención no sustituye a la reserva (concurrencia intra-proceso) ni a
  la concurrencia del workflow (entre procesos): se añade, no se reemplaza.
- (c) Dos rondas (ADR-001).
