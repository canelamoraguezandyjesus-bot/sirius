# Medición de los tres guardianes predichos, hecha por el propietario (contraste)

Fecha: 2026-09-04 01:57 UTC. Árbol: `origin/main` en `dc731d4`. Comandos literales; nada estimado.

## (a) Suelo de prueba que no puede fallar

`grep -rnE '^_MINIMO_[A-Z_]* *: *Final\[int\] *= *0\b|assert [a-z_.]+ >= 0$' tests/acceptance`

- `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py:258` → `_MINIMO_ACIERTOS_EXACTOS_PAQUETE_COMPLETO: Final[int] = 0`
- `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py:2335` → `assert paquete_completo.elementos_de_mas >= 0`

Coincidencias: 2. Las dos son guardas muertas reales (la primera es el caso de
M20/#516 CODEX-001, hoy acompañada por dos suelos vivos; la segunda es una
aserción vacua que sobrevivió a esa corrección). Falsos positivos: 0.
Defectos reales de la muestra que habría cazado: 1 (#516 CODEX-001 / observación
del propietario del 03-09 11:56 UTC).

## (b) Adaptador de Ollama sin `think: false` o sin URL absoluta

Por fichero en `src/sirius/adapters/ollama_*.py`: presencia de `"think"`, de
`post("/api…` (ruta relativa), de `post(f"{_OLLAMA_LOCAL_BASE_URL}…` (absoluta) y
de `follow_redirects=False`:

| adaptador | think | ruta relativa | ruta absoluta | follow_redirects=False |
|---|---|---|---|---|
| ollama_category_classifier.py | 0 | 0 | 0 | 0 |
| ollama_criticality_classifier.py | 1 | 0 | 0 | 3 |
| ollama_relevance_filter.py | 1 | 0 | 0 | 2 |

Nota: el grep de «ruta absoluta» da 0 en los dos adaptadores corregidos porque
la llamada está partida en varias líneas (`post(` en una línea y la f-string en
la siguiente); la comprobación mecánica debe buscar `_OLLAMA_LOCAL_BASE_URL}/api`
en cualquier línea, no en la de `post(`. Con esa corrección: el clasificador de
categoría es el único sin `think`, sin URL absoluta y sin `follow_redirects=False`.
Coincidencias: 1 (deuda ya registrada en ADR-130 y en la bitácora). Falsos
positivos: 0. Defectos reales de la muestra que habría cazado: 2 (#518 CODEX-001
P1 y la observación del propietario / CLAUDE-M21A-001 sobre ruta relativa y
redirecciones).

## (c) Orden que dice «calcado de X» sin enumerar guardas

Sobre las órdenes guardadas en el scratchpad de la sesión (los cuerpos de las
incidencias en GitHub son el mismo texto): `grep -ci calcad` y `grep -ci guarda`.

| orden | «calcad» | «guarda» |
|---|---|---|
| orden_m18b.md | 2 | 0 |
| orden_m19a.md | 0 | 1 |
| orden_m19b.md | 0 | 0 |
| orden_m20.md / orden_m20_v3.txt | 1 | 0 / 1 |
| orden_m21a.txt | 2 | 0 |
| orden_m21b.txt | 2 | 0 |
| orden_c1.txt (borrador, no despachado) | 0 | 0 |

Dispararía en M18b, M21a y M21b (y en el primer borrador de M20). Defectos
reales de la muestra explicados por «calcado sin guardas»: M21a (#518, ruta
relativa y redirecciones heredadas del clasificador de categoría) y M21b (#520,
ronda 1: guarda de restauración de copias no exigida). En M18b no hubo hallazgo
de esa familia: 1 falso positivo. Neto sobre la muestra: 2 − 1 = 1. Es una regla
de redacción de órdenes (proceso), no un guardián de código.
