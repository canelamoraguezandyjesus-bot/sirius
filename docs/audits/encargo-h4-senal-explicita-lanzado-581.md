<!-- Encargo LANZADO el 11-09-2026 como #581. Manda el cuerpo de la incidencia; esto es la copia auditada. -->

## Work ID

WI-20260911-H4

## Bloque

ENCARGO

Perfil: implementer@2

## Objetivo

Que la ampliación por categoría (M14) se active por una señal explícita de la petición, y no porque un texto libre contenga la subcadena «contexto»

## Contexto

Es el **hueco H4 de ADR-148**, y no es de ranking como ADR-148 supone: es una decisión de producto que el propietario **tomó el 11-09-2026** —señal explícita en vez de subcadena—. Este encargo la ejecuta.

**El mecanismo, trazado desde donde se declara hasta donde se consume** (deuda 24: «el dato está declarado» no es «el dato llega»):

- `PROPOSITO_DE_CONTEXTO: Final = "contexto"` (`src/sirius/domain/relevance.py:156`) y `pide_contexto(proposito)` (`relevance.py:345-354`), que devuelve `PROPOSITO_DE_CONTEXTO in proposito.casefold()`. **Una comprobación de subcadena sobre un texto libre.**
- **Un solo consumidor**: `src/sirius/application/rank_relevant_knowledge.py:539`, `if self._category_matching_enabled and pide_contexto(peticion.proposito):`. Ahí se enciende **un camino de recuperación entero** (la ampliación por categoría y criticidad, M14/M19a).
- `Peticion.proposito: str` (`src/sirius/domain/staged_engine_contracts.py:180`), que lo rellena quien construye la petición: el intérprete (`src/sirius/application/interpret_query_request.py`) o la política uniforme.

**Los dos hechos que hacen que hoy el resultado dependa de una casualidad de redacción, medidos y no supuestos:**

1. **La política uniforme SIEMPRE activa la ampliación**: `PROPOSITO_RECUPERACION_ORDINARIA = "recuperacion de contexto relevante (B6b)"` (`interpret_query_request.py:77`) contiene «contexto». O sea: con la puerta cerrada —el estado por defecto de producción— la ampliación se enciende para toda petición, y **nadie lo decidió así**: es un efecto de que el literal lleve esa palabra.
2. **Las peticiones reales del banco la activan en 2 de 47.** Los propósitos declarados en `peticion_p2` son siete: `responder_al_usuario` (27), `planificar_entrega` (5), `revisar_historial` (5), `verificar_fuente` (4), `planificar_viaje` (3), `ensamblar_contexto_b05` (2) y `revisar_conflicto` (1). **Solo `ensamblar_contexto_b05` contiene «contexto»**: `B04-CA-33` y `B04-CA-34`.

**El caso que lo destapa**: `B04-CA-30` (ámbito `PRJ-ALFA`, propósito `responder_al_usuario`) espera `DEC-003`, `MEM-001` y `MEM-016`; entran dos y **falta `MEM-001`**, que solo puede llegar por la ampliación. Medido en el diagnóstico de H4 (08-09): sustituyendo **solo el propósito** de ese caso por uno que contenga «contexto», `MEM-001` entra (`faltan=[]`, con 2 extras más). **Toda la diferencia es la subcadena.**

**Lo que NO se decide aquí y hay que dejar claro desde el principio** (deuda 24, otra vez): la ampliación exige además `category_matching_enabled`, que en producción está **cerrada** y es la decisión final de la línea. Este encargo **no la abre**. Su efecto se mide en el laboratorio —el arnés del banco la abre— y en producción queda preparado para cuando se abra. Decir que «H4 cierra el hueco en producción» sería afirmar más de lo que el árbol sostiene.

## Qué hacer

Que la activación de M14 dependa de **una señal explícita** de la `Peticion` —no de una subcadena—, y que esa señal la fije **quien construye la petición**, con criterio declarado: el intérprete a partir de la intención inferida y las reglas del producto, y la política uniforme con un valor decidido, no heredado del texto de un literal.

**Decide con medida, no de antemano**, dónde vive la señal y qué la enciende, y déjalo razonado en el ADR. Dos preguntas que el ADR tiene que contestar con el árbol delante:

1. ¿Qué peticiones deben activar la ampliación? El corpus adjudica que `B04-CA-30` (`responder_al_usuario`) espera `MEM-001`; eso es un dato sobre qué debe encenderla, y hay que decir si la regla elegida lo satisface y por qué, sin ajustar la regla al caso.
2. ¿Qué hace la política uniforme? Hoy la enciende siempre por accidente. Con la señal explícita, ese «siempre» pasa a ser una decisión escrita, y hay que escribirla.

## Casos de aceptación

- **Una prueba, vista fallar antes del cambio**, de que la ampliación **no** se activa por la presencia de la subcadena en un propósito arbitrario, y **sí** por la señal explícita.
- **`B04-CA-30` recupera `MEM-001`** por la ampliación, con la señal encendida por la regla elegida y no por un ajuste al caso.
- **`B04-CA-33` y `B04-CA-34` siguen recuperando lo que hoy recuperan**: son los dos casos que hoy activan la ampliación por su propósito, y la señal nueva no puede perderlos.
- **Predicción publicada ANTES de medir** (ADR-001), sobre la línea base **medida al empezar** con `scripts/diagnosticar_busqueda_del_banco.py --peticion` (referencia, medida sobre `main` en `5fc5fdc`: `17/47; 162; 78/81; 0`): cuántos hallados gana, cuántos elementos de más trae `B04-CA-30` —el diagnóstico de H4 midió **+2**—, y **0 críticas perdidas**. La predicción se escribe con la regla elegida delante; si el número no llega, se para y se registra caso a caso.
- **Ninguna otra columna del banco empeora** en ninguna de las cuatro configuraciones del diagnóstico.

## Reglas de evidencia que este encargo hereda del ciclo

- **Ninguna afirmación sin la comprobación al lado**, y **manda el árbol**: si algo de arriba no cuadra, se registra la diferencia en vez de acomodarse (deuda 19).
- **Cada cifra dice de qué medición sale y qué está desactivado en ella.** Hay cuatro mediciones distintas del banco (etapa de búsqueda sin filtro, arnés de examen, paquete de producción con filtro inerte, y Ollama real en la máquina del propietario) y **no se comparan entre sí**. El diagnóstico `--peticion` es la etapa de búsqueda: mide si `MEM-001` **entra**, no lo que el sistema entrega (bitácora del ciclo, entradas 82-83).
- **La contra-medición que aísla el arnés** (deuda 21) va con la medición que decide, ítem a ítem y no con una constante.
- **Toda prosa que el cambio deje falsa se corrige en el mismo trabajo** (deuda 28): `pide_contexto` está citada en docstrings de `relevance.py` (≈205) y `rank_relevant_knowledge.py` (≈360), y **25 referencias en pruebas** la fijan (`tests/unit/test_relevance_domain.py`: 14; `tests/unit/test_peticion_ordinaria.py`: 7; `tests/integration/test_rank_relevant_knowledge.py`: 4). Se revisan todas; ninguna se relaja para conseguir verde.
- **La sección de validación del ADR** lleva terna, código de salida y ancla al árbol —«sobre el árbol de `<sha>`»—, actualizada en CADA corrección (ADR-145, ADR-154, forma de ADR-159).

## Requisitos y pruebas de aceptación

Validaciones obligatorias en verde con UNA SOLA invocación de `scripts/check.ps1`, y **al menos una prueba determinista vista FALLAR antes del cambio** (ADR-001), con su mutación transcrita en el ADR. Como mínimo:

1. Prueba, vista fallar, de que un propósito que contiene «contexto» **sin** la señal explícita **no** activa la ampliación.
2. Prueba, vista fallar, de que la señal explícita **sí** la activa, sea cual sea el texto del propósito.
3. Prueba de que `B04-CA-30` recupera `MEM-001` y de que `B04-CA-33`/`B04-CA-34` no pierden nada.
4. Prueba que fije las **0 omisiones críticas**, no solo medirlas.
5. Recuento del banco transcrito antes y después, con la predicción publicada antes de medir.

Todas deterministas, con dobles: sin Ollama en CI.

## Límites

- No se toca el corpus, `resultado_esperado` ni ninguna adjudicación del banco.
- **Nunca se lee ni se indexa `criticidad.razon_segura`.**
- **La puerta `category_matching_enabled` NO se abre.**
- El adaptador del modelo local sigue localhost-only y fail-open; ni `.github/**` ni ningún workflow cambian.
- ADR con nota de arranque antes del primer commit; `siguiente_adr.py` re-ejecutado tras `git fetch` justo antes de abrir la PR (hay otra rama en vuelo, #576, y la numeración se pisa: deuda 18); si se renumera, cambiar también el TÍTULO de la PR.

## Base y dependencias

ADR-148 (hueco H4), ADR-164 (P1: el intérprete que construye la `Peticion`), y la decisión del propietario del 11-09-2026 registrada en `docs/audits/decisiones-pendientes-de-la-linea-de-memoria.md` de la rama de auditoría. **No depende de H5 ni de los ejes.** Referencias autorizadas: sesion-cli.

## Alcance permitido

La señal explícita, quién la fija, su consumo en la ampliación, sus pruebas y su ADR. Nada más.

## Fuera de alcance

Abrir la puerta de la memoria; los huecos H3 y H5; los ejes; cualquier cambio de ranking; y cualquier cosa no descrita arriba.

## Validaciones obligatorias

- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run mypy src tests`
- `uv run pytest`
- `git diff --check <base> <head>` — **con las dos revisiones**, no a secas: sin argumentos compara el árbol contra el índice y no demuestra nada (deuda 25). Se transcribe el comando y su código de salida.

## Rama base

main

## Condiciones de parada

- `READY_FOR_REVIEW`
- `BLOCKED_BY_DECISION`
- `FAILED_SAFELY`
- `USAGE_LIMIT_REACHED`
- Merge automático prohibido.

## Salvaguardas

- No cambiar Producto, Arquitectura Técnica, ATD ni documentos canónicos sin decisión explícita.
- No hacer push directo a `main`.
- No reducir, saltar ni falsear ninguna prueba para conseguir verde.
- No hacer merge automático: el merge sigue siendo un gesto explícito del propietario (contrato §8, sin cambios).
