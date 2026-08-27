# Evidencia — El lazo que faltaba entre atestiguar y medir

Rama `banco-atestigua-en-su-pasada`, 27-08-2026. Sin ADR: cierra el cableado que
ADR-095 decidió.

## Afirmación

El guardián de ADR-095 **existía y no servía para nada**.

El atestado que el comparador exige lo escribía el preflight **en su propio
runner**, y allí moría: se subía como artefacto y el fichero versionado del
repositorio se quedaba con lo que hubiera la última vez. Comprobado:

```
uv run python -c "... modelos_sin_atestado(configuraciones)"
  -> ['gemini-3.5-flash', 'models/gemini-embedding-001',
      'nvidia/llama-nemotron-embed-vl-1b-v2', 'nvidia/nemotron-3-nano-30b-a3b']
```

**Los cuatro sin atestiguar**, incluidos los cuatro que ya se había medido que
responden. Con eso el banco se habría negado a medir **siempre** —correcto pero
inútil— o, si alguien hubiera confirmado un atestado a mano, habría medido con
uno viejo.

Es la misma familia de siempre, y van seis: una pieza correcta que nadie llama.
Aquí el guardián estaba escrito, probado y **desconectado de su fuente de datos**.

## El arreglo

El banco genera su propio atestado **en la misma pasada**, antes de medir.

Es más fuerte que confirmarlo en el repositorio, y por dos razones:

- **no puede estar caducado** — se escribe segundos antes de usarse;
- **no puede pertenecer a otra cuenta** — lo escribe la misma corrida, con las
  mismas claves.

Lo que se mide y lo que se atestigua son la misma corrida.

## Mutación

| mutación | prueba que cae |
|---|---|
| el banco deja de atestiguar | `test_el_banco_atestigua_en_su_propia_pasada` |
| atestigua **después** de medir | la misma |

La segunda importa tanto como la primera: atestiguar al final es atestiguar
cuando la cuota ya se gastó.

## Lo que NO hace

No mide calidad: eso es la pasada. Y el fichero versionado
`modelos_atestiguados.yml` sigue en el repositorio como **registro de la última
comprobación**, no como fuente para el guardián — el guardián usa el que la
propia pasada acaba de escribir.

## Validaciones

```
ruff format --check .    -> 0
ruff check .             -> 0
mypy src tests           -> 0
pytest tests/automation  -> 854 passed, 5 skipped
git diff --check         -> 0
```
