# Evidencia — El banco vuelve a tener botón, y ya no puede medir un cadáver

Rama `banco-con-atestado`, 27-08-2026. Sin ADR: aplica lo que ADR-095 decidió.

## Afirmación

El disparador del banco estaba desactivado con una condición escrita para
reponerlo:

> «Se repone cuando la prueba de vida exista y el veredicto dependa de evidencia
> observada.»

**Las dos se cumplen y están medidas**, así que se repone. Dejarlo apagado sería
tan deshonesto como haberlo encendido antes.

## Comprobación de las dos condiciones

**1. La prueba de vida existe y usa los modelos de verdad.** No lee catálogos:
llama. Encontró lo que ninguna lista podía decir:

```
NO RESPONDE gemini-2.5-flash  ->  404 "This model is no longer available"
NO RESPONDE nvidia/llama-3.1-nemotron-70b  ->  404 "Not found for account"
CANDIDATO OK models/gemini-3.5-flash, nvidia/nemotron-3-nano-30b-a3b
```

**2. El veredicto depende de evidencia observada**, por partida doble:

- sin fuentes no hay acierto (`fuentes > 0`), medido: buscador muerto pasa de
  100 % a 0 % y código 3;
- y ahora, además, cada modelo tiene que constar `usable` en el atestado.
  Comprobado con el atestado vacío: el comparador **se niega**, código 5, y tres
  pruebas del banco caen.

## Lo que cambia aquí

- **El botón vuelve** (`workflow_dispatch`). Sigue siendo solo a mano: cada pasada
  gasta cuota de dos APIs del propietario, y un reloj que gasta su dinero
  mientras duerme no es automatización, es una fuga.
- **El banco pasa el atestado al comparador** (`--atestado`). Sin esto el
  guardián de ADR-095 existía y no lo llamaba nadie — que es el sexto caso de
  «pieza correcta sin llamante» de este repositorio, y no iba a ser el sexto.
- **El preflight escribe el atestado y lo publica** como artefacto, para que el
  banco pueda exigirlo.

## El orden de uso, que ahora está cerrado

```
1. preflight --atestiguar   -> escribe qué modelos responden HOY
2. medir-investigador       -> se niega si alguno no consta, y si no, mide
```

## Lo que NO hace

No mide calidad todavía: eso es la pasada. Y no impide que el atestado sea viejo
—caduca a los siete días, y entonces vuelve a negarse—.

## Validaciones

```
ruff format --check .    -> 0
ruff check .             -> 0
mypy src tests           -> 0
pytest tests/automation  -> 841 passed, 5 skipped
git diff --check         -> 0
```
