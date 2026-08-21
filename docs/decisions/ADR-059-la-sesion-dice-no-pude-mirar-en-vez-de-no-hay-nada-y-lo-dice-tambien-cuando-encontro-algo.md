# ADR-059 — La sesión dice «no pude mirar» en vez de «no hay nada», y lo dice también cuando sí encontró algo

- Estado: APROBADO
- Fecha: 2026-08-21
- Aprobación: la fusión de la PR por el propietario
- Contexto: defecto **H-9**, incidencia [#224](https://github.com/canelamoraguezandyjesus-bot/sirius/issues/224), `docs/audits/registro_defectos.yml`
- Relacionadas: ADR-036 (una lectura caída no es una ausencia y el llamador tiene que poder distinguirlas), ADR-050 (los tres proveedores de contexto tienen la misma firma y reportan su fallo — este defecto es su §«Hallazgo adyacente»), ADR-034, ADR-047 (un defecto encontrado se registra y no se borra), ADR-001 (disciplina de evidencia)

## Contexto y problema

`_resumir_contexto` (`src/sirius_engine/session.py`) es la **única** función que
convierte un `ContextoRecuperado` en la frase que lee una persona. En
`origin/main` (`3f9773a`) no miraba `proveedores_fallidos` en ningún caso:

```
$ git show origin/main:src/sirius_engine/session.py | grep -c "proveedores_fallidos"
0
```

Su rama de cero referencias era, literalmente, una línea:

```python
if not contexto.referencias:
    return f"No encontré referencias para {contexto.consulta!r}."
```

Con las tres fuentes caídas, esa línea le decía al humano **«No encontré
referencias para X»** cuando la verdad era **«no pude mirar»**.

Es la familia de ADR-036 —«una lectura caída no es una ausencia»— pero **un
nivel por encima de H-5**, y peor que él por a quién se lo dice:

| | H-5 (ADR-050) | H-9 (este) |
|---|---|---|
| dónde se perdía el dato | dentro de `ContextoRecuperado` | en el texto final |
| quién lo recibía | un programa | **una persona** |
| ¿se podía notar? | sí, comparando campos | **no**: es una frase en su idioma que suena a respuesta comprobada |

ADR-050 arregló que el motor supiera distinguir «vacío» de «roto». H-9 es que,
sabiéndolo, **no se lo contaba a quien preguntaba**. Lo encontró el agente de
H-5, decidió no ampliar alcance de madrugada y lo dejó escrito en ADR-050
§«Hallazgo adyacente»; ADR-047 es lo que impidió que se evaporase ahí.

## Criterio de parada (escrito ANTES de decidir)

Publicado en la incidencia #224 ([comentario del
21-08](https://github.com/canelamoraguezandyjesus-bot/sirius/issues/224#issuecomment-5372769883)),
antes de tocar código y antes de ver ningún resultado. Se para y se consulta al
propietario si:

1. Cerrar esto exige **tocar `context_recall.py`** o cambiar cualquier firma
   pública: la incidencia lo plantea como un arreglo de la capa de texto, y si
   no lo es, la premisa está mal.
2. La mutación **«quitar la mención de los fallidos»** no hace caer la prueba
   nueva → prueba vacua, se arregla antes de seguir.
3. La mutación **«avisar siempre»** no hace caer nada → el requisito 2 no lo
   fija ninguna prueba, se añade antes de seguir.
4. El **caso mixto** no se puede montar sin inventar un proveedor falso.
5. Para conseguir verde hiciera falta relajar, saltar, `xfail` o borrar
   cualquier prueba existente.
6. Dos defectos de la misma familia durante el trabajo → regla de las dos rondas.

**Ninguna se disparó.** Punto 1: el diff de `src/` toca un solo fichero,
`session.py`, y ninguna firma pública (`_resumir_contexto` y `_citar` son
privadas; `RespuestaTurno`, `SesionCLI` y `ContextoRecuperarConfig` quedan
intactas). Puntos 2 y 3: mutaciones (a) y (c) de la tabla, ambas matan pruebas.
Punto 4: el caso mixto se monta con un fichero real en `tmp_path` y una
`LecturaHistorialGit(NO_DISPONIBLE)`, sin dobles nuevos. Punto 5: no se relajó,
saltó ni borró ninguna prueba; las cinco existentes de `test_session.py` siguen
con todas sus aserciones y el helper `_sesion` solo ganó dos parámetros con
valores por defecto que preservan su comportamiento anterior.

En la misma nota se declaró qué NO garantiza esto, y se mantiene:

- **No** arregla ningún otro punto que hable con un humano: arregla el único
  que hoy existe para `contexto.recuperar`.
- **No** dice *por qué* falló cada lectura: el motivo vive en `Lectura*.error`
  (ADR-050) y no entra en el identificador, que es grueso a propósito para no
  romper el determinismo (requisito 5 de A3).
- **No** traduce los identificadores a nombres de andar por casa (ver §Decisión).
- **No** reintenta ni degrada nada. Solo informa.
- **No** impide mentir: quien construya a mano un `ContextoRecuperado` con
  `proveedores_fallidos=()` tras un fallo sigue pudiendo hacerlo.

## Opciones consideradas

1. **Añadir el aviso solo a la rama de cero referencias.** Es el «está a una
   línea» que estimó quien encontró el defecto, y satisface los requisitos 1 y
   2 de la incidencia tal como estaban escritos.
2. **Anteponer el aviso y conservar detrás la frase de siempre**, del estilo
   «Aviso: … No encontré referencias para X».
3. **Frase propia para cada una de las tres situaciones**, y una tabla en
   `session.py` que traduzca `historial_git` → «el historial de cambios»,
   `arbol:<ruta>` → «el fichero `<ruta>`», etc.
4. **Frase propia para cada una de las tres situaciones**, citando los
   identificadores tal como llegan y recortando la lista como ya se recortan
   las referencias encontradas.

## Decisión

**La opción 4.** `_resumir_contexto` distingue tres situaciones, y las dos que
ya existían se dicen **byte a byte igual que antes**:

| situación | lo que lee la persona |
|---|---|
| se pudo mirar en todo, no había nada | `No encontré referencias para 'X'.` *(sin cambios)* |
| se pudo mirar en todo, había | `Encontré N referencia(s) para 'X': …` *(sin cambios)* |
| quedaron sitios sin leer, nada encontrado | `No pude mirar en todos los sitios, así que no puedo decirte si hay algo sobre 'X': 3 sitio(s) no se dejaron leer (incidencia:404:cuerpo; incidencia:404:comentarios; historial_git). En los que sí pude mirar no había nada.` |
| quedaron sitios sin leer **y** se encontró algo | `Encontré 1 referencia(s) para 'X': fichero:NOTAS.md:1. Aviso: puede que no sea todo, porque 1 sitio(s) no se dejaron leer (historial_git); ahí no he podido mirar.` |

Tres decisiones dentro de la decisión, que son la parte que había que pensar:

**a) El caso mixto avisa igual.** El propietario lo añadió al encargo y tiene
razón: avisar solo cuando no se encontró nada deja media mentira. Una respuesta
parcial que se lee como completa engaña exactamente igual, y encima con
hallazgos delante que la hacen más creíble. Por eso el aviso cuelga de
`proveedores_fallidos`, no de «no encontré nada».

**b) Cuando no se pudo mirar, la frase NO empieza por «No encontré».** La
opción 2 —aviso delante, frase de siempre detrás— habría sido más barata y
pasaría los mismos requisitos, pero deja en el texto una oración que afirma una
ausencia que nadie comprobó. La gente lee frases, no párrafos. Si no se pudo
mirar, la frase entera tiene que decir eso.

**c) Los identificadores se citan sin traducir, y la frase que los envuelve es
la que tiene que entenderse.** La opción 3 leería mejor, y se descartó a
conciencia: una tabla de traducción en `session.py` se queda **muda en
silencio** el día que aparezca un proveedor nuevo o cambie un formato de
identificador, y cambiar un mensaje impreciso por uno incompleto es un mal
negocio en un ADR que trata precisamente de no afirmar de más. Los
identificadores son **citas**, igual que las de las referencias encontradas,
que tampoco se traducen (`fichero:NOTAS.md:1`); lo que carga el significado es
la frase: *«no pude mirar en todos los sitios»*, *«N sitio(s) no se dejaron
leer»*. Ninguna de las dos exige saber qué es un «proveedor».

**Y el recorte.** Las lecturas fallidas del árbol y de incidencias son **una por
fichero y dos por incidencia**: siete incidencias caídas son catorce
identificadores. Volcárselos a una persona en una línea es ilegible, así que se
citan como ya se citan las referencias: los cinco primeros y `y N más`. El
número que se anuncia es **siempre el total**, nunca el de la lista recortada —
recortar la cita es una comodidad, recortar el recuento sería volver a mentir.
La constante `_MAXIMO_CITADO = 5` sustituye al `5` que ya estaba escrito a mano
en la línea de las referencias, para que ambas listas se recorten igual.

### Un defecto de esta misma familia, en el primer borrador

Merece quedar escrito porque es exactamente lo que este ADR combate. El primer
borrador del caso mixto decía **«Aviso: esto no es todo lo que hay»**. Eso
*afirma* que hay más, que es tan poco comprobado como decir que no hay nada: de
un sitio que no se pudo leer no se sabe si tiene algo. Corregido a «puede que
no sea todo … ahí no he podido mirar» antes del primer commit. Es una sola
aparición, no dos rondas, así que la regla de las dos rondas no se disparó;
queda anotado porque la lección es que la frase engañosa se escribe sola, y en
la dirección que menos se espera.

Las pruebas **no cambiaron** al corregir la redacción: fijan que el aviso está
y qué sitios cita, no las palabras exactas. Solo las dos frases que la
incidencia exige preservar se comprueban con igualdad literal.

## Comprobación que la sostiene

### 1. La prueba, vista fallar antes del arreglo

Cinco pruebas nuevas en `tests/engine/test_session.py`, sobre `procesar_turno`
—lo que de verdad ve una persona—, no sobre la función privada. Contra
`session.py` **sin tocar**:

```
$ uv run pytest tests/engine/test_session.py -q
>       assert "No encontré referencias" not in mensaje
E       assert 'No encontré referencias' not in "No encontré...oque B12e?'."
E
E         'No encontré referencias' is contained here:
E           No encontré referencias para '¿qué pasó con el bloque B12e?'.
E         ? +++++++++++++++++++++++

tests/engine/test_session.py:171: AssertionError
=========================== short test summary info ============================
FAILED tests/engine/test_session.py::test_la_sesion_dice_que_no_pudo_mirar_en_vez_de_que_no_hay_nada
FAILED tests/engine/test_session.py::test_la_sesion_ensena_lo_encontrado_y_ademas_el_hueco
FAILED tests/engine/test_session.py::test_la_sesion_no_le_vuelca_a_una_persona_una_lista_interminable_de_sitios
3 failed, 7 passed in 1.07s
```

Esa primera aserción **es** el defecto H-9: las tres fuentes caídas y la sesión
respondiendo con una ausencia que nadie comprobó.

Que solo caigan tres de las cinco es en sí una comprobación: las dos que fijan
«esto se sigue diciendo igual que hoy» pasaban ya contra el código viejo, que es
justo lo que tienen que hacer.

Tras el arreglo:

```
$ uv run pytest tests/engine/test_session.py -q
10 passed in 0.07s
```

### 2. Pruebas por mutación

Cada mutación se sembró reescribiendo el fichero desde una copia del texto
original guardada **en una variable de Python**, nunca con `git checkout --`, y
se revirtió desde esa misma copia. Línea base antes de empezar: 0 fallos;
comprobado que el árbol vuelve limpio al terminar: 0 fallos.

| # | Mutación sembrada | Resultado | Prueba(s) que caen |
|---|---|---|---|
| a | Quitar la mención de los huecos en la rama de cero referencias — el defecto H-9 original, y la mutación exigida por la incidencia | **CAE** 2 | `..._dice_que_no_pudo_mirar_en_vez_de_que_no_hay_nada`, `..._no_le_vuelca_a_una_persona_una_lista_interminable_de_sitios` |
| b | Avisar solo cuando no se encontró nada: el caso mixto pierde el hueco — la segunda mutación exigida | **CAE** 1 | `..._ensena_lo_encontrado_y_ademas_el_hueco` |
| c | Avisar **siempre**, hubiera huecos o no (el arreglo tramposo) | **CAE** 2 | `..._sigue_diciendo_igual_que_hoy_que_miro_y_no_habia_nada`, `..._no_avisa_de_huecos_cuando_pudo_leerlo_todo` |
| d | Citar todos los sitios sin recortar | **CAE** 1 | `..._no_le_vuelca_a_una_persona_una_lista_interminable_de_sitios` |
| e | Anunciar el número de los citados en vez del total sin leer | **CAE** 1 | `..._no_le_vuelca_a_una_persona_una_lista_interminable_de_sitios` |

**Ninguna resultó equivalente.** La (a) y la (b) son las dos que exige el
encargo: (a) devuelve la frase engañosa, (b) comprueba que el caso mixto no se
pierde. La (c) es la que impide el arreglo tramposo de avisar siempre, que
satisfaría el requisito 1 mientras rompe el 2. La (e) es la más fina: recortar
la lista está bien, recortar el recuento sería volver a mentir con otro número.

### 3. Validaciones

Las cuatro de `AGENTS.md`. **La batería completa no se ejecuta aquí a
propósito**: un intento anterior de esta tanda murió con `exit 137` (OOM) por
correr varias baterías completas en paralelo en el mismo contenedor. La valida
Quality en la PR.

```
$ uv run ruff format --check .   → 442 files already formatted
$ uv run ruff check .            → All checks passed!
$ uv run mypy src tests          → Success: no issues found in 420 source files
$ uv run pytest tests/engine/test_session.py tests/engine/test_context_recall.py \
      tests/engine/test_cli_entrypoint.py tests/engine/test_cli_notification.py \
      tests/engine/test_boundary.py -q
                                 → 47 passed in 0.61s
$ git diff --check               → (sin salida)
```

`test_context_recall.py` y los dos de la CLI se incluyen aunque no se tocan
porque son los vecinos que consumen `session`; `test_boundary.py` porque la
frontera es lo que ningún cambio puede romper en silencio.

## Consecuencias

- Quien pregunte «¿qué pasó con X?» y no se pueda mirar, **se entera**. Es el
  último tramo de la familia ADR-036 para `contexto.recuperar`: el motor ya
  sabía distinguir «vacío» de «roto» desde ADR-050, y ahora lo dice.
- **Ninguna firma pública cambia.** `_resumir_contexto` y `_citar` son privadas;
  `SesionCLI`, `RespuestaTurno` y `ContextoRecuperarConfig` quedan idénticas. El
  único llamador, `sirius_engine.cli`, no se toca y sus pruebas siguen verdes.
- **Sí cambia el texto que se ve** en dos situaciones nuevas. Cualquier
  automatismo que hoy hiciera coincidencia exacta sobre el mensaje de un turno
  de consulta seguiría funcionando en las dos situaciones antiguas, y no
  reconocería las dos nuevas. No existe ninguno hoy:
  `grep -rn "No encontré referencias"` fuera de `session.py` solo encuentra las
  pruebas nuevas.
- `test_session.py::_sesion` gana dos parámetros opcionales para tirar fuentes
  por separado; las cinco pruebas que ya lo usaban no cambian ni una aserción.
- Queda **sin cerrar** lo declarado en la nota: si mañana aparece una segunda
  función que renderice un `ContextoRecuperado` a texto, puede nacer torcida
  igual. Hoy no existe.

## Alternativas descartadas y por qué

- **Opción 1 (avisar solo cuando no se encontró nada).** Es la lectura literal
  de los requisitos 1 y 2 de #224 y habría sido de verdad «una línea». Se
  descarta porque deja el caso mixto mintiendo: encontrar tres cosas de cinco
  sitios y presentarlas como la respuesta es la misma ausencia no comprobada,
  con hallazgos delante que la hacen más creíble. La mutación (b) existe para
  que esto no pueda volver por descuido.
- **Opción 2 (aviso delante, «No encontré referencias» detrás).** Satisface los
  requisitos y conserva una oración que afirma lo que nadie comprobó. Un texto
  no se lee entero: se lee la primera frase.
- **Opción 3 (tabla de traducción de identificadores).** Leería mejor y se
  quedaría muda en silencio ante un proveedor nuevo. Cambia impreciso por
  incompleto, y el fallo nuevo sería del tipo que nadie nota. Si el propietario
  quiere nombres legibles, el sitio correcto es que el **identificador nazca
  legible** en `context_recall.py`, donde se sabe qué es cada cosa —y eso es
  tocar una firma pública con otro bloque en vuelo, así que sería otra
  incidencia y otro ADR.
- **Hacer el fallo imposible en vez de improbable** (que el tipo impidiera
  llegar a `referencias` sin resolver antes `proveedores_fallidos`). Es
  rediseñar la capa de presentación del repositorio entero por un defecto de
  gravedad media, exactamente el «ampliar alcance por iniciativa propia» que
  ADR-050 tuvo el buen criterio de no hacer. Se declaró en la nota de arranque
  que no se iba a hacer, antes de empezar, en vez de descubrirlo después. Lo
  que sí se hace: la renderización sigue concentrada en **una sola** función, y
  la propiedad queda fijada con prueba en las cuatro situaciones, de modo que
  una regresión sale como una prueba roja y no como una frase que suena a
  respuesta.
