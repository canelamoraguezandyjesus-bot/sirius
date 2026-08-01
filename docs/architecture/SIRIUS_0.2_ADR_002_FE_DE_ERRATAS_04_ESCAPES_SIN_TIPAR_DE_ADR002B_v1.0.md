# SIRIUS 0.2 — ADR-002 · Fe de erratas 04 y adenda preinscrita: escapes sin tipar de `ADR002-B`

**Versión:** 1.0
**Estado:** ERRATA RECONOCIDA + ADENDA PREINSCRITA al paquete de corrección 04
**Fecha:** 1 de agosto de 2026
**Rama:** `evidence/adr001-spikes`
**Ficha afectada:** `ADR002-B` v4 (huella `5c9eab540e74b4290635dc7c6d0b79daf76d86aa`), congelada en `ec6fb70`
**Ámbito exclusivo:** `experiments/adr002/candidates/adr002_b/`, sus pruebas, su ficha sucesora y esta documentación

## 0. Qué declara esta errata

La auditoría adversarial ejecutada sobre el HEAD `51095e7` —posterior a congelar
la ficha `ADR002-B` v4— encontró defectos que **falsifican una declaración
congelada** de esa ficha. Se reconocen aquí sin reescribir la v4, se preinscribe
su corrección, y se aplica el mecanismo que el propio paquete 04 dejó escrito:

> «Si tras congelar la v4 hubiera que modificar una fuente incluida en su
> huella, se conservaría la v4 y se emitiría la v5, congelada antes de repetir
> las pruebas, sin reutilizar evidencia anterior.»

**La ficha v4 no se reescribe.** Se conservará marcada `SUSTITUIDA`, con su
contenido normativo íntegro en el historial, y la v5 declarará la verdad
corregida.

## 1. La declaración falsificada

La ficha v4 —y antes la v3, y el módulo desde el paquete 12— declara:

> «Indice inexistente, corrupto —física o lógicamente—, desfasado o que cite
> identidades que el canon no contiene → **fallo cerrado tipado**, sin
> degradación silenciosa.»

Esa afirmación es **falsa en cuatro caminos reproducibles**. Todos se han
reproducido sobre sidecars construidos por el constructor real y manipulados
por SQL, es decir, ficheros que superan `quick_check`, tablas, versiones y
parámetros.

## 2. Los defectos, uno a uno

### 2.1 `D1` — conteo de metadatos con más de 4 300 dígitos (`ValueError`)

`LectorVectorial.__init__` valida que los conteos `elementos` y `terminos`
sean cadenas ASCII de dígitos sin ceros iniciales, pero **no acota su
longitud**. `int(declarado)` topa entonces con el límite de CPython
(`sys.get_int_max_str_digits()`, 4 300 por omisión) y lanza `ValueError`, que
no es subtipo de `IndiceNoUtilizableError`.

Además, ese punto es **posterior** a las ramas que cierran la conexión y está
fuera de todo `try`: el descriptor del sidecar queda abierto.

Reproducido: `UPDATE metadatos SET valor = '9'*5000 WHERE clave = 'elementos'`
→ `ValueError: Exceeds the limit (4300 digits) for integer string conversion`.
El mensaje de CPython además revela el **número de dígitos** de la celda.

### 2.2 `D2` — JSON con anidamiento profundo (`RecursionError`)

`_pares_de_vector_validados` traduce `ValueError` —con el comentario correcto
de que `JSONDecodeError` es su subtipo—, pero el decodificador de `json`
lanza **`RecursionError`** ante anidamiento profundo, y `RecursionError` no es
subtipo de `ValueError`. Atraviesa `_consultar_validando` y **los dos `except`
de `consultar`**, de modo que tampoco se ejecuta el cierre de conexión que esa
ruta promete.

Reproducido sobre `vectores_de_termino.dimensiones` y sobre
`vectores_de_elemento.dimensiones` con 100 000 corchetes anidados (≈ 200 KB,
muy por debajo del techo de 32 MiB) → `RecursionError: Stack overflow while
decoding a JSON array`.

### 2.3 `D3` — identidad persistida con entero no representable (`OverflowError`)

`_FORMATO_DE_IDENTIDAD_PERSISTIDA` es `(CLASE):([1-9][0-9]*)` **sin cota de
longitud**. Una identidad `MEMORIA:` seguida de 4 000 nueves pasa la
validación del lector, llega a `por_identificadores` del puerto común, y
SQLite no puede almacenar ese entero: `OverflowError: Python int too large to
convert to SQLite INTEGER`. La defensa de frontera del candidato captura
**solo** `IdentificadorInvalidoError`, de modo que el `OverflowError` escapa
sin tipar desde `E3`.

Reproducido de extremo a extremo con `engine.recuperar`.

### 2.4 `D4` — recomputación del canon fuera de todo `try` (fuga de conexión)

`huella_del_canon(ruta_canon)` se invoca en `__init__` fuera de cualquier
`try`. Si el canon no responde al esquema, la `sqlite3.OperationalError` sale
sin traducirse **y sin cerrar la conexión del sidecar**.

El **escape sin tipar** de esta ruta es la **limitación 2 ya declarada** de la
fe de erratas 03 («canon ilegible que puede escapar sin el error tipado
específico del índice») y **se conserva declarada, no se corrige aquí**. Lo
que sí se corrige es la **fuga de conexión**, que no estaba declarada y
contradice la regla de cierre del §6 del paquete 04.

### 2.5 `D5` — dos inexactitudes en el texto de la ficha v4

1. La v4 afirma, en dos declaraciones ampliadas respecto de la v3, que
   **«ningún mensaje reproduce celdas»**, en términos universales. No es
   exacto: `IndiceInconsistenteError` reproduce los identificadores ausentes,
   **por su contrato explícito de la corrección 02**, que esta misión ordenó
   no tocar. La afirmación correcta es la acotada: los mensajes de
   **corrupción y apertura** no reproducen celdas; el de inconsistencia
   reproduce identidades canónicas acotadas y ningún otro contenido.
2. El §8 del paquete 04 enumeró el **cierre de conexión** entre lo que la
   ficha debía declarar, y la v4 no lo declara explícitamente.

## 3. Corrección preinscrita (antes de tocar código)

| # | Corrección | Dónde |
|---|---|---|
| C1 | acotar la longitud de los conteos antes de `int()`: máximo `_DIGITOS_MAXIMOS_DE_ENTERO = 19` (los de un entero con signo de 64 bits); una celda más larga es corrupción tipada, con mensaje minimizado que **no** revela ni la celda ni su longitud | `vectores.py`, apertura |
| C2 | mover la conversión de conteos y la recomputación de la huella dentro de una región que **cierra la conexión** ante cualquier excepción; el escape sin tipar del canon ilegible se conserva **tal cual** (limitación 2), solo deja de filtrar el descriptor | `vectores.py`, apertura |
| C3 | acotar la longitud de la celda de vector **antes** de deserializar (`_LONGITUD_MAXIMA_DE_VECTOR = 16384`, holgura sobre el máximo posible de ≈ 4 700 caracteres para 256 pares) y traducir además `RecursionError` junto a `ValueError` | `vectores.py`, validador central |
| C4 | acotar la identidad persistida a `[1-9][0-9]{0,18}` **y** exigir que su número sea ≤ 2⁶³−1, de modo que toda identidad que el lector acepta es representable por el puerto | `vectores.py`, validador de identidad |
| C5 | corregir en la **ficha v5** las dos inexactitudes de `D5`: acotar la afirmación sobre los mensajes y declarar el cierre de conexión | ficha `ADR002-B` v5 |

**Ninguna corrección toca `common/` ni `adr002_a/`.** El bound de identidad
vive en el lector de B, no en el puerto común: B no puede entregar al puerto
lo que el puerto no puede representar, y esa es responsabilidad del derivado.

## 4. Límites — revisión

Todas las correcciones son **comprobaciones de cota sobre datos ya leídos**:
una comparación de longitud antes de `int()`, una comparación de longitud
antes de `json.loads` —que además **evita** el trabajo de deserializar celdas
patológicas—, y una comparación numérica en un `fullmatch` ya existente.
Ninguna sentencia SQL nueva, ningún dato adicional leído. **Los seis límites
por etapa, el almacenamiento, la construcción, la reconstrucción y el borrado
se conservan**, con el mismo fundamento estático que la v4, reforzado: el
camino patológico ahora hace **menos** trabajo, no más. Ninguna cifra procede
de medición.

## 5. Consecuencia de custodia

1. `ficha_ADR002-B_v4.json` se conserva y se marca `SUSTITUIDA`;
2. se emite `ficha_ADR002-B_v5.json` — versión 5, sustituye a 4, `CONGELADA`,
   con el motivo exacto de esta errata;
3. **todas** las pruebas de B se repiten bajo la v5; ninguna evidencia
   anterior se reutiliza;
4. ninguna ficha ni acta de `ADR002-A` se modifica; `ADR002-A` v3 sigue
   PREPARADO PARA BENCHMARK e intacto;
5. `ADR002-B` sigue **PENDIENTE DE APROBACIÓN**: esta errata no lo aprueba.

## 6. Limitaciones que siguen declaradas

Las ocho de la fe de erratas 03 permanecen, **incluida la 2** (canon ilegible
que puede escapar sin el error tipado específico), que esta errata reconoce
expresamente como **no corregida**: solo se le retira la fuga de conexión.

## 7. Honestidad del hallazgo

Estos defectos **no los encontró el usuario ni un revisor externo**: los
encontró la auditoría adversarial que este mismo trabajo ejecutó sobre su
propio resultado, y se verificaron reproduciéndolos uno a uno antes de
escribir esta errata. Se registran aquí íntegros, con su reproducción, porque
la evidencia publicada no se reescribe: se corrige mediante fe de erratas y
documento sucesor.
