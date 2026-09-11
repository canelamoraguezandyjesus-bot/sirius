<!-- Encargo LANZADO el 11-09-2026 como #582. Manda el cuerpo de la incidencia; esto es la copia auditada. -->

## Work ID

WI-20260911-H5

## Bloque

ENCARGO

Perfil: implementer@2

## Objetivo

Que una decisión de lista cerrada entre cuando el ámbito de la petición es miembro de la lista: portar la pertenencia que el origen declara y que `G4` decida por pertenencia, no por contención

## Contexto

Es el **hueco H5**, que ADR-148 no nombra: se contaba dentro de los cinco de H1, y H1 (ADR-168) demostró midiendo que no era de vigencia sino de **ámbito**. El propietario decidió el 11-09-2026 las dos mitades: **restaurar la pertenencia** y **pasar `G4` a pertenencia**.

**El caso**: `B04-CA-22` («¿Qué decisiones eran válidas entre enero y marzo?», ámbito `PRJ-BETA`) espera seis decisiones; tras H1 entran cinco y **falta `DEC-001`**. Medido sobre `main` (`5fc5fdc`): falta **en las dos configuraciones**, con ejes del corpus y sin ellos, así que no es el problema de «los ejes no se persisten» de la palanca 2. Son dos capas, y hay que resolver las dos.

### Capa 1: el dato no llega, y existe

`DEC-001` es **el único** ítem `MULTI_PROYECTO_CERRADO` de los 97 (`project: LISTA-CERRADA-AB`, `ejes_p2.ambito: MULTI_PROYECTO_CERRADO`). La fixture del banco **no declara miembros**: ninguna clave con «miembro» existe en ningún ítem, y el cargador lo dice en su propia nota (`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`, `_ejes_declarados`, ≈765-790: `miembros_de_ambito=()`, con el comentario «el corpus portado no declara la membresía de listas cerradas»). `G4` recibe una lista sin miembros y se niega, con la razón correcta: **«lista cerrada sin miembros resueltos: la duda no abre ámbito»**. La puerta está bien; le falta el dato.

**Y el dato existe, estructurado, en el origen que la fixture cita** (`fuente.commit` = `dfdcdaff04dcba10939cc0b0569c55b6a636296f`, rama `evidence/adr001-spikes`):

```python
# experiments/adr002/benchmark/build_corpus.py:82-88
{
    "id": "LISTA-CERRADA-AB",
    "nombre": "Lista cerrada Alfa+Beta v1",
    "tipo": "MULTI_PROYECTO_CERRADO",
    "miembros_lista_cerrada": ["PRJ-ALFA", "PRJ-BETA"],
},
```

Y la adjudicación del origen lo usa así: «pertenece a LISTA-CERRADA-AB; **Gamma no es miembro y no hereda**» (`cases_v0_5.json`, CA-03, donde `DEC-001` es señuelo fuera de ámbito). La semántica del origen es deliberada: **la lista tiene miembros, y un ámbito entra si es uno de ellos.** Lo que se perdió fue al portar a JSON: la nota de la fixture dice que `experiments/adr002/projection/build.py` «no la expone como JSON». **Portar es restaurar, no inventar.**

### Capa 2: aunque el dato llegara, `G4` lo excluiría

La rama multiproyecto de `_g4` (`src/sirius/domain/staged_engine_gates.py`) decide con `all(peticion.ambito.autoriza(m) for m in miembros)`: **contención** —«todos los miembros de la lista caben en tu ámbito»—. Lo que el origen describe es **pertenencia** —«tu ámbito es uno de los miembros»—. Simulado con los miembros del origen y `Ambito.autoriza` (`staged_engine_contracts.py:138-149`):

| caso | `all()` | `any()` | lo que el origen adjudica |
|---|---|---|---|
| `B04-CA-22`, ámbito `PRJ-BETA` | **False** | **True** | debe entrar |
| ámbito Gamma (CA-03 del origen) | False | False | no debe entrar |

**`any` reproduce la adjudicación en los dos sentidos; `all` falla el positivo.** Y `all` no es un descuido: es una postura de confidencialidad, coherente con «la duda no abre ámbito». Por eso cambiarlo fue decisión del propietario y no del ciclo.

### Lo que este encargo NO cierra, y hay que decirlo antes de medir (deuda 24)

**El puerto real entrega todo ítem con `ejes=SIN_EJES`** (`src/sirius/adapters/persistence/staged_engine_port.py:29`). Sin ejes, `G4` toma la rama `ambito is None` y comprueba `autoriza(item.project_id)` con `project_id = 'LISTA-CERRADA-AB'`, que no es ningún proyecto del ámbito: **excluido**. O sea: **en producción `DEC-001` no entra con este encargo**, y no entrará hasta que los ejes se persistan (decisión del propietario del 11-09, por el Rector). Lo que este encargo cierra es **el techo del laboratorio** (`--ejes --peticion`) y **la semántica de `G4`** para cuando los ejes existan. Afirmar más sería repetir el error de H1.

## Qué hacer

1. **Portar la pertenencia a la fixture**: que `DEC-001` declare sus miembros, tomados **verbatim** de `build_corpus.py:87` en `dfdcdaff`, con la procedencia escrita en la nota de la fixture (`fuente.nota_incidencia_457` o una nota nueva al lado). Es el **único** cambio permitido en el corpus: ni `resultado_esperado`, ni adjudicaciones, ni ningún otro ítem.
2. **Que el cargador lo lea** (`_ejes_declarados`) en vez de fijar `miembros_de_ambito=()`, y que su comentario deje de decir lo que ya no es cierto (deuda 28).
3. **Que `G4` decida por pertenencia**: `any` en vez de `all`, con el docstring y **la cadena de razón** («lista cerrada con miembros fuera del ámbito») reescritos para que digan lo que la puerta hace ahora —esa cadena llega a la explicación que ve el usuario, y una razón que describe la regla vieja es la familia de `CLAUDE-R3-001` en ADR-168—.

## Casos de aceptación

- **Una prueba de `G4`, vista fallar antes del cambio**: con miembros `{A, B}` y ámbito `B`, entra; con ámbito Gamma, no entra; **sin miembros resueltos, sigue sin entrar** («la duda no abre ámbito» se conserva).
- **`B04-CA-22` recupera las seis** en la configuración con ejes, y se comprueba que `DEC-001` entra por `G4` con pertenencia y no por otro camino.
- **Predicción publicada ANTES de medir** (ADR-001), sobre la línea base **medida al empezar** con `scripts/diagnosticar_busqueda_del_banco.py` (referencia sobre `main` en `5fc5fdc`: `--peticion` = `17/47; 162; 78/81; 0`; `--ejes --peticion` = `21/47; 144; 78/81; 0`):
  - `--ejes --peticion`: **`78/81 → 79/81`** hallados y **`21/47 → 22/47`** exactas (`B04-CA-22` tiene `extras=0` y pasa a exacta), **0 críticas perdidas** (`DEC-001` no es crítica: `nivel=None`).
  - `--peticion`: **no se mueve** (`SIN_EJES`, ver arriba). Si se mueve, algo más ha cambiado y hay que explicarlo.
  - **«De más» sin listón a propósito**, pero transcritas antes y después: `DEC-001` con pertenencia puede aparecer en casos de `PRJ-ALFA`/`PRJ-BETA` que no lo esperan si la búsqueda lo alcanza. Si aparece, se dice en cuáles y por qué, y se razona si es ruido del filtro o del ámbito.
- Si el número no llega, **se para y se registra caso a caso**; no se ajusta el criterio al resultado.

## Reglas de evidencia que este encargo hereda del ciclo

- **Ninguna afirmación sin la comprobación al lado; manda el árbol** (deuda 19).
- **Cada cifra dice de qué medición sale y qué está desactivado en ella**: hay cuatro mediciones del banco y no se comparan entre sí (bitácora del ciclo, entradas 82-83). Aquí la que decide es `--ejes --peticion`, y se dice por qué.
- **Contra-medición que aísle el arnés** (deuda 21), ítem a ítem: en particular, que `DEC-001` entra por `G4` y no porque el cargador haya cambiado otra cosa.
- **Ninguna cifra apoyada en `created_at` sin su condición** (deuda 27): el banco escribe `valid_from` en `created_at`. Este encargo no toca fechas; si aparece una, la condición viaja con ella.
- **Toda prosa que el cambio deje falsa se corrige en el mismo trabajo** (deuda 28): el comentario del cargador, el docstring de `_g4`, la cadena de razón, y las pruebas que hoy referencian la rama de lista cerrada (`tests/unit/test_staged_engine.py`, `tests/engine/test_escalation.py`, `tests/acceptance/staged_engine_category_and_relevance.py`). Ninguna se relaja para conseguir verde.
- **La sección de validación del ADR** con terna, código de salida y ancla «sobre el árbol de `<sha>`», actualizada en CADA corrección (ADR-145, ADR-154, forma de ADR-159).

## Requisitos y pruebas de aceptación

Validaciones obligatorias en verde con UNA SOLA invocación de `scripts/check.ps1`, y **al menos una prueba determinista vista FALLAR antes del cambio** (ADR-001), con su mutación transcrita. Como mínimo:

1. Prueba de `G4`, vista fallar: pertenencia admite al miembro, excluye al no miembro, y **sin miembros sigue excluyendo**.
2. Prueba del cargador: `DEC-001` llega al motor con `miembros_de_ambito == ("PRJ-ALFA", "PRJ-BETA")`, leídos de la fixture y no fijados en código.
3. Prueba de que `B04-CA-22` recupera las seis con ejes, y de que `--peticion` no cambia.
4. Prueba que fije las **0 omisiones críticas**.
5. Recuento del banco antes y después, con la predicción publicada antes de medir.

Todas deterministas: sin Ollama en CI.

## Límites

- **El único cambio al corpus es añadir la pertenencia de `DEC-001`, portada verbatim del origen**; `resultado_esperado`, adjudicaciones y todos los demás ítems quedan intactos, y la procedencia se escribe en la fixture.
- **Nunca se lee ni se indexa `criticidad.razon_segura`.**
- **Ninguna crítica puede perderse**: las 0 omisiones críticas se fijan con prueba.
- **La puerta `category_matching_enabled` NO se abre.** Los ejes **no se persisten** aquí: eso es otra decisión y va por el Rector.
- Ni `.github/**` ni ningún workflow cambian.
- ADR con nota de arranque antes del primer commit; `siguiente_adr.py` re-ejecutado tras `git fetch` justo antes de abrir la PR (hay ramas en vuelo: #576 y H4; la numeración se pisa: deuda 18); si se renumera, cambiar también el TÍTULO de la PR.

## Base y dependencias

ADR-148, ADR-168 (H1, que aisló este hueco y lo midió ítem a ítem), y la decisión del propietario del 11-09-2026 (`docs/audits/decisiones-pendientes-de-la-linea-de-memoria.md`, rama de auditoría). **No depende de H4 ni de los ejes**, aunque su efecto en producción sí. Referencias autorizadas: sesion-cli.

## Alcance permitido

La pertenencia de `DEC-001` en la fixture y su lectura en el cargador; la rama multiproyecto de `G4`; sus pruebas; su ADR. Nada más.

## Fuera de alcance

Persistir los ejes; los huecos H3 y H4; abrir la puerta de la memoria; cualquier otro ítem del corpus; y cualquier cosa no descrita arriba.

## Validaciones obligatorias

- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run mypy src tests`
- `uv run pytest`
- `git diff --check <base> <head>` — **con las dos revisiones**, no a secas (deuda 25). Se transcribe el comando y su código de salida.

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
