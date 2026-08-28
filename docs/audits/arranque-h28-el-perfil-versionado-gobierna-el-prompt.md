# Nota de arranque — H-28: la versión del perfil gobierna el prompt

Fecha: 2026-08-28. ANTES del primer cambio (ADR-001). Corrección autorizada.

## Afirmación a corregir (verificada en #396, F-3.2-01)

`implement-sirius-work.yml` y `review-sirius-work.yml` extraen el rol del
campo `Perfil: rol@N` TIRANDO la versión (`sed` con `@.*`), y `cat` lee el
prompt vigente de main. `implementer@1` puede significar dos textos distintos
en dos Runs: la versión se registra pero no gobierna nada.

## Lo que se decide construir (decidido ahora, antes de ver resultados)

Un manifiesto versionado (`scripts/automation/prompts/manifiesto.json`, JSON
para que el runner lo lea con stdlib, sin instalar nada) con dos carriles:
`ejecucion` (rol@N del ejecutor → su prompt) y `revision` (rol@N del ejecutor
→ el prompt de su revisor, porque quien revisa depende de quién implementó).
Cada fila: fichero + sha256 de sus bytes. Un resolver
(`scripts/automation/resolver_prompt.py`, función importable + CLI, la misma
lógica que corre en producción — lección de H-14) que:

- parsea `Perfil:` con `sirius_engine.profile_field` (una sola verdad, vía
  `sys.path` a `src/`, sin instalar el paquete);
- resuelve rol@N EXACTO en el carril pedido; clave desconocida → ROJO;
- verifica el sha256 del fichero contra la fila ANTES de entregarlo; texto
  movido sin registrar versión nueva → ROJO (fail-closed: convierte «texto
  distinto en silencio» en «parada que se ve»).

Los dos workflows sustituyen su `sed`+`case` por una llamada al resolver.
Filas iniciales: ejecución implementer@1 y documentalista@1; revisión
implementer@1→reviewer, documentalista@1→revisor-documental,
investigador@1→revisor-documental (las únicas llaves que la TABLA_PERFILES
puede proyectar hacia estos dos workflows hoy).

## Las preguntas

1. ¿`Perfil: implementer@99` (rol conocido, versión desconocida) se ve
   FALLAR? Hoy la versión se tira y resolvería el prompt vigente; el test
   nuevo debe estar en ROJO antes del arreglo y en verde después.
2. ¿El manifiesto no puede pudrirse? Cada fila: fichero existente y sha256
   igual a los bytes reales — visto FALLAR alterando una fila.
3. ¿Los workflows llaman al resolver DE VERDAD? Invocación contada en líneas
   de código del bloque `run:` (no comentarios — receta de la familia vacua),
   y el `sed`+`case` viejo desaparece de los dos.
4. ¿Editar un prompt sin registrar la versión nueva pone el sistema en ROJO?
   sha256 discrepante → salida ≠ 0 con mensaje que nombra el remedio.

## Criterio de parada

- (a) Si el resolver necesitara CUALQUIER dependencia fuera de stdlib en el
  runner (el job del implementador no instala nada): parar y decidir delante.
- (b) Si algún guardián existente (expresiones de workflow, estructural)
  choca con el cambio: traerlo aquí antes de romperlo.
- (c) Nada de claves nuevas; `CLAVES_QUE_OBLIGAN_A_PARAR` no aplica.
- (d) Dos rondas con defectos de la misma familia → parar y buscar la raíz
  (ADR-001).
