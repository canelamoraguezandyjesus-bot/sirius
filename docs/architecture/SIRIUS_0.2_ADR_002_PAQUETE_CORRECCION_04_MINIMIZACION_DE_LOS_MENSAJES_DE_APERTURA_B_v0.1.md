# SIRIUS 0.2 — ADR-002 · Paquete de corrección 04: minimización de los mensajes de apertura de `ADR002-B`

**Versión:** 0.1
**Estado:** PREINSCRITO — fija el contrato antes de tocar código
**Fecha:** 1 de agosto de 2026
**Rama:** `evidence/adr001-spikes`
**HEAD de partida verificado:** `308f99f21e2849a1b58aac9b2470a01dac27305d`
**Ámbito exclusivo:** `experiments/adr002/candidates/adr002_b/`, sus pruebas, su ficha sucesora y esta documentación de gobierno

Este paquete cierra la última fuga de datos del sidecar en los mensajes de
apertura de `ADR002-B` y nada más. No toca `common/`, no toca `adr002_a/`, no
toca ninguna ficha ni acta de `ADR002-A`, no toca la reaprobación de
`ADR002-A` v3, no toca Sirius 0.1 productivo, no aprueba a B, no autoriza
benchmark ni medición, y el PR #117 permanece abierto y sin fusionar.

## 1. Diagnóstico exacto

La ficha `ADR002-B` v3 (huella `ef2bfb137c5d67450e7ade7b4a934e0a42744800`)
declara que toda corrupción lógica del sidecar produce un mensaje minimizado
compuesto únicamente por **tabla, tipo de defecto y posición o conteo**,
«jamás la celda». La corrección 03 lo cumplió en `consultar` y en los
validadores, pero **`LectorVectorial.__init__` quedó fuera de esa auditoría**
y conserva dos incumplimientos.

### 1.1 Defecto 1 — la celda de huella se reproduce literalmente

```python
actual = huella_del_canon(ruta_canon)
if metadatos.get("huella_del_canon") != actual:
    self._conexion.close()
    msg = (
        "el canon cambio desde que se construyo el indice: "
        f"{metadatos.get('huella_del_canon')} != {actual}"
    )
    raise IndiceDesfasadoError(msg)
```

`metadatos.huella_del_canon` es **una celda del sidecar** y se interpola sin
validación previa de formato. Un sidecar manipulado puede almacenar en esa
celda texto protegido, saltos de línea, contenido arbitrario o una cadena
extremadamente larga, y todo ello aparecería íntegro en la excepción. Se
interpola además `actual`, la huella recomputada del canon vigente, que
tampoco tiene por qué salir.

Hay un segundo problema de **tipificación** escondido en la misma rama: hoy
una celda de huella *sintácticamente imposible* (una cadena vacía, un texto
largo) produce `IndiceDesfasadoError` —«el canon cambió»— cuando lo cierto es
que **el índice está corrupto**, no desfasado. Las dos causas deben ser
distinguibles por tipo.

### 1.2 Defecto 2 — el texto del error físico se incorpora al mensaje externo

```python
except sqlite3.DatabaseError as error:
    self._conexion.close()
    msg = f"el sidecar no es una base legible: {error}"
    raise IndiceCorruptoError(msg) from error
```

El texto de la excepción interna de SQLite se copia al mensaje externo. La
causa ya se conserva con `from error` —que es el mecanismo correcto y
suficiente para diagnosticar—, de modo que la interpolación solo añade
superficie de fuga: el texto de un `DatabaseError` puede incluir fragmentos
del contenido de la base.

### 1.3 La prueba estática vigente no cubre estas rutas

`test_los_conteos_de_metadatos_no_interpolan_la_celda` comprueba únicamente
que la celda de los **conteos** no se interpola. Ninguna prueba cubre la
huella ni el texto del error físico. La cobertura estática se extiende en la
fase 3.

## 2. Formato canónico de la huella persistida

`metadatos.huella_del_canon` es el hexdigest de un SHA-256 producido por
`huella_del_canon`. Su formato canónico es **exactamente**:

- tipo `str` (tipo exacto, no subtipo ni valor adaptado);
- **64** caracteres;
- solo `[0-9a-f]`;
- minúsculas;
- sin espacios, sin saltos de línea, sin prefijos, sin contenido adicional.

Se comprueba con `re.fullmatch` sobre una expresión cerrada
(`[0-9a-f]{64}`), sin anclas: un salto de línea final invalida, sin la
ambigüedad de `$`.

**Orden de comprobación.** La validación de formato precede a la
recomputación de la huella del canon. Además de ser lo correcto —no se puede
comparar contra un valor que no es una huella—, evita leer el canon entero
cuando el sidecar ya es inservible: solo **reduce** trabajo respecto del
camino vigente.

## 3. Jerarquía: corrupción frente a desfase

| Estado de la celda | Tipo | Significado |
|---|---|---|
| No cumple el formato canónico de §2 | **`IndiceCorruptoError`** | el derivado está corrupto: esa celda no es una huella |
| SHA-256 canónico pero distinto del actual | **`IndiceDesfasadoError`** | el canon cambió desde que se construyó el índice |

Ningún tipo nuevo. `IndiceInconsistenteError` conserva intacto su contrato de
la corrección 02 —identidad canónica válida que el canon no contiene, con
identificadores minimizados— y queda **fuera del alcance** de este paquete:
esos identificadores ya pasan por la validación de identidad del lector, de
modo que son canónicos por construcción y no pueden portar contenido.

## 4. Política de mensajes y preservación de causas

1. **Mensaje externo literal o estructural genérico.** Ninguna celda del
   sidecar, ni recortada, ni transformada para mostrarla, ni resumida.
2. **Ningún texto de excepción interna** en el mensaje externo.
3. **Causa siempre preservada** con `raise … from error` cuando existe una
   excepción originaria: el diagnóstico vive en la cadena de causas, no en el
   texto.
4. **Sin capturas indiscriminadas** de excepciones de programación.
5. Las únicas interpolaciones admitidas en un mensaje externo son: literales
   propios, nombres fijos de metadato, posiciones ordinales y conteos
   derivados de constantes propias.

## 5. Auditoría completa de interpolaciones (clasificación previa)

Todas las construcciones de excepción de `vectores.py`, clasificadas antes de
tocar nada:

### 5.1 `LectorVectorial.__init__`

| Interpolación | Clasificación | Decisión |
|---|---|---|
| `{ruta_sidecar}` en «no existe el indice vectorial» | **dato del entorno**, argumento del propio llamante | **se elimina** (§5.3) |
| «no supera la comprobacion de integridad» | literal | se conserva |
| `{faltan}` en «no contiene las tablas esperadas» | **literal propio**: es `set(TABLAS_DEL_SIDECAR) − presentes`, luego solo puede contener nombres de nuestra propia constante | se conserva y se fija con prueba |
| `{error}` en «no es una base legible» | **texto de excepción interna** | **se elimina**; la causa se conserva con `from error` |
| «versiones incompatibles» | literal | se conserva |
| «otros parametros congelados» | literal | se conserva |
| `{clave_de_conteo!r}` | **literal propio** del bucle `("elementos", "terminos")` | se conserva |
| «el conteo 'terminos' excede el vocabulario maximo» | literal | se conserva |
| `{metadatos.get('huella_del_canon')}` | **celda del sidecar** | **se elimina** |
| `{actual}` | huella recomputada del canon | **se elimina** |

### 5.2 `LectorVectorial.consultar` y validadores

Auditados y **conformes ya** desde la corrección 03: `{tabla}` y `{defecto}`
son literales propios, `{posicion}` es una posición ordinal, `{marcas}` son
marcadores SQL; «el sidecar fallo fisicamente durante la consulta» es literal
y conserva la causa con `from error`. Ninguna celda, ningún texto de
excepción. No se modifican.

### 5.3 Por qué se elimina también la ruta del sidecar

No es una celda del sidecar —el fichero ni siquiera existe cuando ese error
se lanza—, de modo que no puede portar contenido canónico; pero **es un dato
del entorno** y su valor diagnóstico es **nulo**: quien construye el lector le
pasó esa misma ruta y ya la tiene, y el sitio de la llamada sigue visible en
el rastreo. Eliminarla deja un invariante mucho más fuerte y comprobable:
**ninguna interpolación de `__init__` procede de una celda, de una excepción
interna ni del entorno**. Se registra aquí como decisión explícita y
reversible.

## 6. Cierre de conexión

Toda detección durante la apertura cierra la conexión **antes** de propagar, y
ningún lector parcialmente inicializado escapa: cuando `__init__` lanza, no
existe instancia. Las dos rutas nuevas (formato de huella inválido y desfase)
cierran igual que las vigentes. Las pruebas posteriores a la ficha lo
demuestran vigilando las conexiones realmente abiertas, no declarándolo.

## 7. Límites afectados — revisión uno a uno, sin conservación automática

| Límite | Decisión | Fundamento estático |
|---|---|---|
| E3 (20 ms, límite local) | **CONSERVADO** | ninguna sentencia nueva; se añade un `fullmatch` sobre una cadena de 64 caracteres, trabajo O(64) constante, en la ruta de apertura ya amortizada |
| Apertura amortizada en E3 | **CONSERVADO** | la validación precede a `huella_del_canon`, de modo que en el caso corrupto **evita** leer el canon: el trabajo máximo no crece y el del caso corrupto disminuye |
| Consulta (3 sentencias dirigidas, ≤ 4096 filas) | **CONSERVADO · sin cambio** | `consultar` no se toca en este paquete |
| Materialización por identidad (≤ 2 sentencias) | **CONSERVADO · sin cambio** | no se toca |
| Construcción / reconstrucción / borrado | **CONSERVADO · sin cambio** | no se tocan |
| Almacenamiento (32 MiB techo) | **CONSERVADO · sin cambio** | no se persiste ni un byte nuevo |

Ninguna cifra procede de medición: no existe ninguna.

## 8. Consecuencia de custodia: ficha `ADR002-B` v4

Modificar `vectores.py` cambia la huella de `ADR002-B`. Por la regla de
sustitución (TOL-210, regla 3):

1. `ficha_ADR002-B_v3.json` se conserva y se marca `SUSTITUIDA` (cambio de
   estado únicamente, con la huella que se recomputa de él);
2. se emite `ficha_ADR002-B_v4.json` — versión 4, sustituye a 3, estado
   `CONGELADA`, motivo exacto: **exposición del valor persistido de huella y
   del texto interno de SQLite en los mensajes de apertura**; declara la
   validación canónica del SHA-256 persistido, la diferencia entre corrupción
   y desfase, los mensajes genéricos, las causas preservadas, el cierre de
   conexión, el **mismo árbol común** (`a83539e3…`), el **mismo árbol de A**
   (`2d90b551…`), el nuevo árbol propio de B, los límites revisados de §7,
   ninguna medición, ningún resultado observado y las limitaciones restantes
   intactas;
3. **todas** las pruebas de B se repiten después de congelar la v4; ninguna
   ejecución previa se reutiliza;
4. ninguna ficha ni acta de `ADR002-A` se modifica.

Si tras congelar la v4 hubiera que modificar una fuente incluida en su
huella, se conservaría la v4 y se emitiría la v5, congelada antes de repetir
las pruebas, sin reutilizar evidencia anterior.

## 9. Orden preinscrito de commits

| # | Contenido | Regla que respeta |
|---|---|---|
| 1 | este paquete (preinscripción) | contrato antes que código |
| 2 | validador canónico de huella, corrupción frente a desfase, mensajes literales, causas preservadas, eliminación de la ruta del entorno, pruebas **exclusivamente estáticas** y suspensión declarada de las suites funcionales de B | corrección estática sin ejecutar B |
| 3 | ficha B v4 congelada; B v3 → `SUSTITUIDA`; custodia e inventario | ficha antes que ejecución |
| 4 | pruebas posteriores a la ficha: huella malformada, huella válida distinta, error físico con centinela, auditoría de las ocho aperturas, regresión completa de B, A intacta por árboles y blobs | anterioridad estricta |

## 10. Limitaciones que este paquete NO corrige (se conservan declaradas)

Siguen vigentes y no se presentan como corregidas: la ventana de 4 096
elementos examinados antes de las exclusiones; el canon ilegible que puede
escapar sin el error tipado específico del índice; la ventana concurrente
entre las lecturas de `construir` (TOCTOU); el techo de almacenamiento
declarado pero no autoimpuesto; las diferencias potenciales de `libm` entre
entornos; la creación de un fichero vacío por `sqlite3.connect` en utilidades
mal invocadas; la ausencia de cierre explícito del lector durante la vida
normal; y `S7` sin camino de adjudicación en el motor común.

## 11. Lo que este paquete no autoriza

Ni benchmark, ni corpus oficial, ni casos oficiales, ni medición alguna de
rendimiento; ni aprobación de B (que quedará **técnicamente preparado,
PENDIENTE DE APROBACIÓN**); ni modificación de `common/`, `adr002_a/`, las
fichas o actas de A, la reaprobación de A v3, o Sirius 0.1; ni `ADR002-C`/
`ADR002-D`; ni `EJE-1`/`EJE-2`; ni elección de ganador; ni fusión del PR #117.
