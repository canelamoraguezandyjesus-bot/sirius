---
name: cadena-de-comprobacion
description: >-
  La cadena completa que hay que pasar ANTES de confirmar y empujar cualquier
  cambio de este repositorio, en el orden que no desperdicia los once minutos y
  medio de la batería, con los dos pasos que `scripts/check.ps1` NO hace y que
  son los que muerden: el comprobador de documentos y la regeneración de
  `MEMORIA.md`. Cárgala siempre que vayas a confirmar, a empujar, a decir que
  algo está verde, o cuando la batería o el comprobador te hayan rechazado algo
  y no sepas por qué.
---

# La cadena de comprobación

**Regla única: verde no es «pasó pytest». Verde es la cadena entera, y la
cadena es más larga que `scripts/check.ps1`.**

## El orden, y por qué es este

De lo más barato a lo más caro. La batería tarda **11 min 30 s** (7 179
pruebas medidas el 20-09-2026): lanzarla antes que `ruff` significa descubrir
un espacio en blanco al final de once minutos y medio.

```bash
uv run --no-sync ruff format --check .      # segundos
uv run --no-sync ruff check .               # segundos
uv run --no-sync mypy src tests             # ~1 min
uv run --no-sync python scripts/automation/sirius_check_docs.py <ficheros .md tocados>
uv run --no-sync sirius-memoria conocimiento   # solo si tocaste docs/ o un registro
uv run --no-sync pytest                     # ~11 min 30 s: lánzala en segundo plano
```

En Windows, los cuatro primeros pasos de `check.ps1` son los mismos y se
detiene en el primer rojo (ADR-153). **Lo que `check.ps1` no hace son los dos
del medio.** No los hace por diseño —el comprobador de documentos solo mira los
ficheros que le pasas— y son los dos que rechazan trabajo ya terminado.

## Los dos pasos que no están en el guion

**1. El comprobador de documentos.** Solo mira **los ficheros que le pasas por
argumento**, nunca `docs/**` entero. Si tocaste cinco documentos y le pasas
cuatro, dice «sin defectos» y miente por omisión. Su trampa cara:

> Una cita a un fichero que **solo vive en otra rama** se acepta únicamente si
> la palabra **«rama»** aparece en los **40 caracteres anteriores** a la cita
> (`_VENTANA_RAMA`, `scripts/automation/sirius_check_docs.py`). No basta con
> decirlo en la frase anterior ni al final de la misma frase: cuarenta
> caracteres, delante.

**2. `MEMORIA.md` es generada, no escrita.** No se edita a mano nunca. Si el
cambio toca `docs/` o cualquier registro, se regenera **en el mismo commit**
(ADR-171): `tests/engine/test_memoria.py` compara el fichero con lo que el
árbol produce y falla si alguien la editó o si se quedó atrás. Regenerarla en
el commit siguiente deja un commit rojo en la historia.

## Mientras corre la batería

Once minutos y medio son para leer el diff, no para tocar el árbol. Dos cosas
que ya salieron caras:

- **Nunca `git checkout -- <fichero>` sobre trabajo sin confirmar.** El 20-09
  ese comando, usado para deshacer una mutación, borró la edición entera de
  `src/sirius_engine/memoria.py` y hubo que rehacerla. Para deshacer una
  mutación, guarda una copia antes o aplica la mutación desde un fichero
  aparte.
- **Una mutación que no se aplicó no prueba nada.** Si mutas con `sed` o con
  un `python -c` dentro de comillas, comprueba con `git diff` que el árbol
  cambió de verdad antes de creerte el «16 passed». El escapado de la consola
  se ha comido una mutación entera, y las pruebas pasaron sin haber sido
  probadas.

## Antes de decir que está verde

Di las cifras, no el adjetivo: cuántas pruebas pasaron, cuántas se saltaron,
cuánto tardó, y qué ficheros le pasaste al comprobador de documentos. «Todo
verde» sin cifras es exactamente la afirmación que ADR-001 prohíbe.

## Qué NO hace esta cadena

- **No comprueba Windows.** `quality-windows.yml` no ha corrido nunca; la
  validación en Windows real es manual (PROC-008 de la auditoría).
- **No sustituye la prueba por mutación.** Verde con una prueba vacua es
  verde. La mutación es obligatoria y vive en la skill `disciplina-evidencia`.
- **No mira los documentos que no le pasas.** Ver arriba.
- **No garantiza que el commit sea coherente.** Que pase la cadena no
  significa que el registro de defectos, el ADR y el código digan lo mismo.
