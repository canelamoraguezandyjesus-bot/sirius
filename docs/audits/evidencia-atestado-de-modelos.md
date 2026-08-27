# Evidencia — La raíz de las cuatro rondas, y el arreglo que la hace imposible

Rama `atestado-de-modelos`, 27-08-2026. La decisión va en **ADR-095**; esto es la
medición que la sostiene.

## La raíz, verificada a mano antes de aceptarla

Un diagnóstico adversarial la nombró así:

> Cada ronda se contestó la pregunta más barata que se podía responder sin llamar
> al proveedor, se declaró por escrito la pregunta que faltaba, y se entregó
> igual. El apartado «lo que esto NO garantiza» funcionó como **permiso de
> entrega** en vez de como freno.

**No se aceptó de palabra.** Las cuatro afirmaciones que la sostienen, comprobadas
por ejecución:

```
grep -rln preflight tests/                          -> vacío       (CERO guardianes)
grep -c preflight .github/workflows/medir-...yml    -> 0           (el banco no depende de él)
ADR escritos en la noche del 26-08                  -> 0
_candidatos(google, catalogo, 'gemini', 4)          -> 3 de 4 de la generación 2.5,
                                                       ya declarada muerta
```

Las cuatro ciertas. El instrumento del que colgaba todo no tenía ni una prueba, el
banco podía medir un cadáver, y lo único que merecía guardarse —la escalera de
cuatro preguntas— no estaba escrito en ninguna parte.

## El arreglo, y por qué es imposible y no improbable

**1. El atestado** (`modelos_atestiguados.yml`, escrito solo por
`preflight --atestiguar`). Hasta hoy el resultado de cada llamada moría en la cola
de un log: **ningún programa podía leerlo**, así que ningún guardián podía
exigirlo. Ahora es un dato con fecha.

**2. El guardián.** `comparar_investigadores.py` sale con código 5 si un modelo
configurado no consta usable y reciente. Comprobado por ejecución:

```
sin fichero de atestado -> ['gemini-3.5-flash', 'models/gemini-embedding-001']
atestado vacío          -> el comparador se niega; 3 pruebas del banco caen
```

**3. La memoria.** `_candidatos` deja de proponer lo que el atestado ya da por
muerto, y ordena por generación en vez de por alfabeto:

```
antes: ['gemini-2.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.5-pro', 'gemini-3-flash']
ahora: ['gemini-3.7-flash', 'gemini-3.5-flash', 'gemini-3-flash']
```

**4. Doce guardianes** donde había cero.

## Mutación: las cinco propiedades, vistas caer

| mutación | prueba que cae |
|---|---|
| el instrumento pierde la memoria | `test_no_vuelve_a_proponer_un_modelo_que_ya_dijo_que_no_sirve` |
| vuelve el orden alfabético | `test_lo_nuevo_va_antes_que_lo_viejo` |
| el guardián deja de exigir atestado | `test_sin_atestado_no_se_mide` |
| el atestado deja de caducar | `test_un_atestado_caducado_no_vale` |
| «existir» basta, sin `usable` | `test_un_modelo_que_existe_pero_no_responde_no_deja_medir` |

Con sus anti-vacuas en el otro sentido: un atestado fresco **sí** deja medir, y no
saber **no** es lo mismo que saber que está muerto.

## El tercer guardián vacuo de la noche, y por qué importa

La primera versión de la prueba de la memoria **pasó la mutación en verde**.
Comprobaba que `_muertos_conocidos` existiera y devolviera lo correcto, pero no
que `_candidatos` **la usara**: sustituir la llamada real por `muertos = set()`
la dejaba impasible.

Es el tercer guardián así en la misma noche —los otros dos fueron el de `ddgs` y
el de H-14—, y los tres son la misma raíz con otro traje: **probar la pieza en vez
del cable**. Queda escrito dentro del propio fichero para que la próxima versión
no lo repita.

## Lo que esto NO arregla

No impide que vuelva a escribir «lo que esto no garantiza» y entregue igual. Eso
es conducta, y no hay guardián que la compruebe —igual que ADR-091—. Lo único que
se puede hacer es quitarle el sitio: por eso el arreglo no es una promesa, es un
fichero que un programa lee y del que un código de salida depende.

## Validaciones

```
uv run ruff format --check .    -> 0
uv run ruff check .             -> 0
uv run mypy src tests           -> 0
uv run pytest tests/automation  -> 841 passed, 5 skipped
uv run pytest tests/engine      -> 941 passed, 1 skipped
git diff --check                -> 0
```
