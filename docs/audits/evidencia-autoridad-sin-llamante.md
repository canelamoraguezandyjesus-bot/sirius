# Evidencia — La quinta pieza sin llamante era la salida de emergencia

Rama `autoridad-sin-llamante`, 27-08-2026. Sin ADR: la decisión ya está tomada en
el contrato §11.4. Esto es cablearla y vigilar que no se descablee.

## Afirmación

`authority_reversion` (D1c) llevaba **desde que se escribió sin un solo
llamante**. Comprobado:

```
grep -rl authority_reversion src/ scripts/ .github/  ->  solo su propio .pyc
grep -rn authority_reversion src/ --include=*.py     ->  nada fuera del módulo
```

Es la **quinta** pieza así de este repositorio, y la peor de las cinco: es lo
único que devolvería el mando a la vía GitHub si el motor se porta mal con una
clase ya conmutada.

**Una salida de emergencia que nadie invoca no es una salvaguarda: es un adorno
que se cita en un contrato.**

## Dónde se cableó, y por qué ahí

En la pasada diaria (`sirius-racha`), no en un reloj propio. El §11.4 dice que
una sola divergencia real basta y que *«no se espera a un patrón ni a una segunda
ocurrencia»*. La pasada diaria es el único sitio donde esas divergencias se leen
recién medidas; un reloj aparte añadiría un retardo entre ver la divergencia y
actuar sobre ella, **y ese retardo es exactamente lo que el contrato prohíbe**.

Y solo revierte. **No conmuta hacia el motor**, que sigue siendo un acto explícito
del propietario (§11.3). Es la dirección segura: devolver el mando nunca puede dar
autoridad a nadie.

## Mutación

| mutación | prueba que cae |
|---|---|
| quitar el `import` y el bloque de reversión | `test_cada_pieza_tiene_quien_la_llame[authority_reversion]` |

## El cuarto guardián vacuo de la noche, y por qué lo nombro aparte

La primera versión de este guardián usaba `grep -rl` y **dio por bueno un fichero
que solo nombraba el módulo en un comentario** — y el comentario era el mío, el
que explica que la pieza estaba sin llamante. Quitar el `import` real la dejaba
impasible.

Van cuatro en la misma noche: el de H-14, el de `ddgs`, el de la memoria del
preflight y éste. **Los cuatro son el mismo defecto**, y merece la pena nombrarlo
de una vez:

> Un guardián que se conforma con que algo esté **NOMBRADO** no comprueba que
> esté **LLAMADO**.

Es la raíz de ADR-095 aplicada a las pruebas: comprobar la declaración en vez del
hecho. Queda escrito dentro del fichero.

## Lo que NO hace

No revierte nada hoy: no hay ninguna clase conmutada al motor todavía, así que la
pasada dirá «ninguna clase requiere reversión». Eso es correcto y hay que leerlo
como lo que es — la salvaguarda está **conectada**, no ejercitada. Se ejercitará
el día que haga falta, que es el único día en que importa que estuviera puesta.

## Validaciones

```
ruff format --check .    -> 0
ruff check .             -> 0
mypy src tests           -> 0
pytest tests/automation  -> 849 passed, 5 skipped
pytest tests/engine      -> 941 passed, 1 skipped
git diff --check         -> 0
```
