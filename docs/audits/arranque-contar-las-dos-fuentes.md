# Nota de arranque — el medidor cuenta un registro que Tavily no alimenta

Fecha: 2026-08-28. Publicada ANTES del primer cambio de código (ADR-001).

## La cadena de evidencia, entera

1. Pasada 4 del banco: clave de Tavily puesta y llegando (`TAVILY_API_KEY: ***`
   en el `env:`), fuentes idénticas a la pasada sin clave (0,3 de media).
2. Atestado del buscador (preflight run 33138475089): Tavily **USABLE, 3
   resultados**, con la misma llamada que hace la herramienta. La clave está
   bien y el servidor contesta.
3. Leído `skills/researcher.py` de la 0.15.1 instalada,
   `_search_relevant_source_urls`:

   ```python
   if url and raw_content and len(raw_content) > 100:
       prefetched_content.append({"url": url, "raw_content": raw_content})
       self.researcher.add_research_sources([{"url": url}])   # -> research_sources
   elif url:
       new_search_urls.append(url)                            # -> visited_urls (tras raspar)
   ```

   Tavily devuelve `{"href", "body"}` con `body` casi siempre > 100 caracteres:
   sus resultados van por la rama de contenido pre-traído, alimentan la
   investigación de verdad… y **nunca entran en `visited_urls`**.
4. Nuestro medidor cuenta `fuentes = len(get_source_urls())`, y
   `get_source_urls()` devuelve `list(self.visited_urls)`.

Conclusión: **el instrumento cuenta el registro que la vía de Tavily no
alimenta**. Con el buscador POR FIN funcionando, `fuentes` puede seguir a cero y
la regla `fuentes > 0` suspende preguntas investigadas con fuentes reales.
Noveno caso de la enfermedad de la casa, variante nueva: la tubería nueva llena
otro registro y el contador sigue mirando el viejo.

## Lo que se decide construir

`medir_investigador._investigar` cuenta las fuentes como la UNIÓN de los dos
registros de la herramienta: las URL visitadas (`get_source_urls`) y las URL de
los orígenes de investigación (`get_research_sources`, campo `url` de cada
entrada). Deduplicadas: una página raspada Y pre-traída es UNA fuente.

## Las cuatro preguntas

1. ¿La prueba nueva se ve FALLAR antes: un investigador fingido con
   `visited_urls` vacío y `research_sources` llenos da hoy `fuentes=0`?
2. ¿La unión DEDUPLICA? Una URL en los dos registros no puede contar dos veces
   —inflar fuentes es el verde que miente, peor que el rojo.
3. ¿`research_sources` sin campo `url` (o con formas raras) no revienta la
   medición ni cuenta como fuente?
4. ¿Un investigador con TODO vacío sigue dando `fuentes=0` y la medición sigue
   siendo NO fiable? La corrección no puede aflojar la regla `fuentes > 0`.

## Criterio de parada

- (a) Si la unión pudiera dar fuentes > 0 sin que ninguna URL real exista, se
  para: sería desarmar la regla que mató al buscador muerto.
- (b) Regla de las dos rondas (ADR-001) — y OJO: ya llevamos H-24 (contradicción
  leída como divergencia), el 503 leído como muerto, y esto. La familia «el
  instrumento lee el registro equivocado y el rojo miente» tiene ya TRES casos:
  la raíz común queda nombrada en la evidencia y si aparece un cuarto, se para
  todo y se rediseña la medición entera.

## Lo que NO se toca

Ni el banco, ni la regla `fuentes > 0`, ni los buscadores, ni los modelos.
