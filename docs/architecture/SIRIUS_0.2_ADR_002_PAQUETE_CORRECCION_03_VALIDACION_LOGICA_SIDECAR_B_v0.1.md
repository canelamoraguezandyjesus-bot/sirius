# SIRIUS 0.2 — ADR-002 · Paquete de corrección 03: validación lógica y minimización ante corrupción del sidecar de `ADR002-B`

**Versión:** 0.1
**Estado:** PREINSCRITO — fija el contrato antes de tocar código
**Fecha:** 1 de agosto de 2026
**Rama:** `evidence/adr001-spikes`
**HEAD de partida verificado:** `e17694abc2c7eebd8da7c5012924d3c7c2857e37`
**Ámbito exclusivo:** `experiments/adr002/candidates/adr002_b/`, sus pruebas, su ficha sucesora y esta documentación de gobierno

Este paquete corrige un defecto bloqueante de `ADR002-B` v2 y nada más. No
toca `common/`, no toca `adr002_a/`, no toca ninguna ficha ni acta de
`ADR002-A`, no aprueba a B, no autoriza benchmark ni medición, y el PR #117
permanece abierto y sin fusionar. La reaprobación vigente de `ADR002-A` v3
permanece intacta.

## 1. Diagnóstico exacto del defecto

### 1.1 Lo que el lector comprueba hoy

`LectorVectorial.__init__` (blob vigente de `vectores.py`:
`3999497c27e64858172e3f7d0c6d3561e3d6931f`) comprueba, en este orden:
existencia del fichero; `PRAGMA quick_check`; presencia de las cinco tablas;
versiones de algoritmo y tokenización; parámetros congelados; y huella
SHA-256 del canon de origen. Todo fallo de esas comprobaciones es cerrado y
tipado (`IndiceInexistenteError`, `IndiceCorruptoError`,
`IndiceDesfasadoError`).

### 1.2 Lo que `consultar` consume sin validar

Durante `consultar`, el lector consume directamente valores lógicos
almacenados en SQLite **sin validación alguna**:

| Dato consumido | Uso directo | Escape posible |
|---|---|---|
| `vocabulario.dimension` | `int(fila[0])` | `ValueError` (texto no numérico), valores fuera de rango aceptados |
| `vectores_de_termino.dimensiones` | `for dimension, valor in json.loads(...)` | `json.JSONDecodeError`, `TypeError`, `ValueError` |
| `vectores_de_elemento.dimensiones` | `pares = json.loads(...)` y aritmética sobre los pares | `json.JSONDecodeError`, `TypeError` |
| `vectores_de_elemento.norma_cuadrada` | `math.sqrt(norma_cuadrada)` y división | `TypeError`, `ValueError` (raíz de negativo), `ZeroDivisionError` (norma 0) |
| `vectores_de_elemento.elemento` / `posting.elemento` | identidad entregada como `CoincidenciaVectorial.elemento` y pedida después al puerto | `IdentificadorInvalidoError` del puerto común |
| filas de `posting` | subconsulta de solapamiento con `JOIN` interno | una fila huérfana o incoherente **desaparece en silencio** |

Un fichero SQLite puede superar `quick_check` y contener exactamente esos
valores lógicamente corruptos. En ese caso escapan errores genéricos de
programación (`JSONDecodeError`, `TypeError`, `ValueError`, `KeyError`,
`ZeroDivisionError`, errores de dominio matemático) o un error de **otro
componente** (`IdentificadorInvalidoError` del puerto), en contradicción
directa con la declaración congelada de la ficha B v2 y del propio módulo:
«índice inexistente, corrupto o desfasado → fallo cerrado tipado, sin
degradación silenciosa».

### 1.3 La fuga de minimización

Si una identidad maliciosa del sidecar llega al puerto común, el mensaje de
`IdentificadorInvalidoError` reproduce hasta **64 caracteres del valor
crudo** (`port.py`, mensaje `identificador canonico invalido: {str(crudo)[:64]!r}`).
Para el puerto eso es correcto —su llamante legítimo construye identificadores
programáticamente—, pero cuando el valor procede de un **sidecar manipulado**
puede contener texto protegido, y B lo habría dejado salir en un mensaje de
error. Eso incumple la minimización prometida por B («identificadores y
clases, jamás contenido»).

### 1.4 La inconsistencia documental

`candidate.py` (blob vigente `10b109974eb82e4bf2047e41e7270d6b7e9bebe5`)
describe la composición como «`ADR002-B` = `ADR002-A` v2 + señal vectorial
tardía». La base vigente es **`ADR002-A` v3** (huella
`427905a06f6c12666a09c73b8720e229f17eeef3`), y la propia ficha B v2 ya cita a
la v3 como base. Se corrige la referencia documental; la lógica funcional y
la definición canónica de B no cambian.

## 2. Definición de corrupción lógica del sidecar

**Corrupción lógica** es todo estado del sidecar que supera las
comprobaciones físicas y estructurales de apertura (§1.1) pero viola el
formato persistido normativo de §3 en cualquier dato **consumido** por una
operación del lector. La corrupción lógica es indistinguible por `quick_check`
y solo puede detectarse validando los valores en el momento de consumirlos.

Queda fuera de esta definición —y de este paquete— la identidad **válida en
formato pero ausente del canon**: esa es la inconsistencia índice/canon que ya
falla cerrada como `IndiceInconsistenteError` (paquete de corrección 02) y no
cambia aquí.

## 3. Formato persistido normativo (lo que se valida)

### 3.1 Identidad canónica

Toda identidad leída de `vectores_de_elemento`, `posting` o entregada como
coincidencia debe cumplir **exactamente** el formato canónico vigente:

- clase real de `Clase` (el contrato común es la única fuente de los nombres
  de clase; usarlo NO modifica la capa común);
- separador único `:`;
- entero ASCII positivo, sin espacios, sin ceros iniciales, sin signo;
- sin contenido adicional — la comprobación es de **cadena completa**
  (`re.fullmatch` sin anclas), de modo que un salto de línea final u
  cualquier otro apéndice invalida, sin la ambigüedad del ancla `$`.

### 3.2 Vector persistido (término y elemento)

Un vector persistido válido es exactamente:

- una **lista** JSON;
- de **pares** (listas de longitud 2);
- dimensión: entero real (`int`, **no** `bool`), no negativo y **menor que el
  número de términos** declarado en `metadatos.terminos`;
- peso: entero real (`int`, **no** `bool`), **estrictamente positivo**;
- **sin dimensiones repetidas**;
- en **orden canónico** ascendente por dimensión;
- con cardinalidad ≤ `DIMENSIONES_MAXIMAS_POR_VECTOR` (256).

Se rechazan de forma tipada: JSON malformado; raíz que no sea lista; pares de
longitud ≠ 2; flotantes; cadenas numéricas; booleanos; `null`; dimensiones
negativas o fuera del vocabulario; pesos cero o negativos; dimensiones
repetidas; cardinalidad excesiva; orden no canónico.

**Decisión normativa sobre el peso cero:** el constructor calcula pesos como
`round(ppmi × 10⁶)` con `ppmi > 0`; en cánones enormes el redondeo podría
producir teóricamente un peso 0 persistido. Para que «estrictamente positivo»
sea un invariante real del formato y no una aspiración, `construir` descarta
desde este paquete los pares de peso 0 tras el redondeo —tanto en vectores de
término como de elemento— antes de persistir. Esto **alinea** el formato con
la declaración congelada de candidatura («≥ 2 dimensiones **positivas**
compartidas») y solo puede reducir trabajo: ninguna fila nueva, ningún par
nuevo, ningún cambio en los fixtures reales (donde el mínimo PPMI ronda
centenares de milésimas escaladas).

### 3.3 Norma

Para cada vector de elemento consumido:

- `norma_cuadrada` es entero real (`int`, no `bool`);
- **estrictamente positiva**;
- **igual exactamente** a la suma de los cuadrados de los pesos validados del
  vector;
- representable: ≤ 2⁶³ − 1 (el entero máximo que SQLite declara almacenar);
  la igualdad exacta con la suma recomputada hace el resto.

Una discrepancia cualquiera es corrupción lógica. Con estas garantías no hay
división por cero (norma > 0), ni raíz de negativo (norma > 0), ni coseno no
finito (numerador y denominador enteros positivos acotados).

### 3.4 Metadatos de conteo

`metadatos.terminos` y `metadatos.elementos` deben ser cadenas de dígitos
ASCII que representen enteros no negativos. Se validan **en la apertura**,
porque `terminos` es la cota superior del rango de dimensiones de §3.2.

### 3.5 Referencias lógicas (posting ↔ vectores)

En el alcance consumido por una consulta:

- la subconsulta de candidatos pasa de `JOIN` interno a **`LEFT JOIN`** desde
  los candidatos de `posting` hacia `vectores_de_elemento`, de modo que un
  candidato citado por `posting` **sin vector** aparece como fila con vector
  `NULL` y falla cerrado como referencia huérfana, en vez de desaparecer;
- la columna de solapamiento contada sobre `posting` se **selecciona** y se
  compara con el solapamiento recomputado desde el vector validado del
  elemento y el vector de consulta: una fila de `posting` duplicada, o que
  cite una dimensión que el vector del elemento no contiene, produce
  discrepancia y falla cerrada;
- las dimensiones de término consultadas se validan de tipo y rango antes de
  usarse.

**Límite explícito de la validación dirigida:** se valida lo que la consulta
**consume** —los ≤ 16 términos consultados, sus vectores de término, los
metadatos de conteo, y las ≤ 4096 filas candidatas devueltas con sus vectores,
normas e identidades—. Una fila de `posting` cuya dimensión no pertenece a la
consulta, o un vector de un elemento jamás candidato, no se leen y por tanto
no se validan: escanear el sidecar entero en cada consulta alteraría
materialmente el coste congelado de E3 sin proteger ningún dato adicional
realmente usado. La detección es completa **sobre los datos usados**, que son
los únicos que pueden influir en un resultado.

### 3.6 Similitud

Antes de crear una `CoincidenciaVectorial`:

- producto escalar entero, calculado sobre pares validados;
- normas validadas (§3.3) y norma de consulta estrictamente positiva —
  garantizada porque los pesos validados son estrictamente positivos y las
  sumas de positivos son positivas;
- coseno **finito** y dentro del intervalo matemáticamente permitido: con la
  norma igual exacta a la suma de cuadrados, Cauchy-Schwarz acota
  `producto ≤ √(n_c)·√(n_e)` en aritmética exacta; la evaluación en coma
  flotante introduce un error relativo del orden de 10⁻¹⁵, así que se admite
  una **tolerancia explícita de 10⁻⁹** solo para ese error de evaluación
  (`coseno ≤ 1 + 10⁻⁹`) y la puntuación fija se recorta a
  `min(round(coseno × 10⁶), 10⁶)` para que sea siempre representable en la
  escala;
- solapamiento coherente (§3.5).

Cualquier imposibilidad matemática restante es **corrupción tipada**, nunca
un error aritmético genérico.

## 4. Jerarquía de errores y política de minimización

### 4.1 Errores

- Toda corrupción lógica de §3 produce **`IndiceCorruptoError`** (subtipo ya
  existente y documentado de `IndiceNoUtilizableError`). No se crea un
  subtipo nuevo: la corrupción lógica es la misma categoría normativa que la
  física —«el sidecar existe pero no es íntegro o no es compatible»— y
  multiplicar tipos no añadiría información accionable; la tabla y el tipo de
  defecto van en el mensaje minimizado.
- `IndiceInconsistenteError` queda **reservado** a la identidad válida en
  formato pero ausente del canon (paquete 02); no cambia.
- `IdentificadorInvalidoError` del puerto **jamás** es salida externa de B.

### 4.2 Minimización de mensajes

Un mensaje de corrupción puede contener **únicamente**: la tabla afectada, el
tipo de defecto, y una posición ordinal o un conteo minimizado. **Nunca**: la
identidad corrupta, claves de sujeto, texto de celdas, fragmentos de JSON, ni
valores crudos. La regla operativa: en los `raise` de corrupción no se
interpola ninguna variable que provenga de una celda del sidecar.

### 4.3 Defensa en profundidad en la frontera con el puerto

`candidate.py` envuelve la llamada a `por_identificadores` capturando
**únicamente** `IdentificadorInvalidoError` y traduciéndolo a
`IndiceCorruptoError` con mensaje genérico minimizado y **causa preservada**
(`raise … from error`). No captura errores de programación
indiscriminadamente, no continúa con resultados parciales, no degrada a
`ADR002-A`, no fabrica `S7`. La validación del lector (§3.1) impide
normalmente llegar a esta defensa: es red de seguridad, no camino ordinario.

### 4.4 Cierre de conexiones

Toda corrupción detectada durante `consultar` **cierra la conexión** antes de
propagar el error: un lector que entregó corrupción no puede quedar
parcialmente válido. Las comprobaciones de apertura ya cerraban la conexión
en todos sus caminos de fallo y siguen haciéndolo. El error nunca se oculta y
nunca arrastra contenido. (El cierre explícito del lector durante la vida
**normal** —sin corrupción— sigue siendo la limitación ya registrada en la fe
de erratas 03; este paquete no la amplía ni la disimula.)

## 5. Momento de validación

| Momento | Qué se valida |
|---|---|
| Apertura (`__init__`) | lo ya vigente (§1.1) **más** `metadatos.terminos` y `metadatos.elementos` como enteros no negativos (§3.4) |
| Cada `consultar` | dimensiones de término (tipo y rango); vectores de término (§3.2); candidatos: identidad (§3.1), referencia no huérfana y solapamiento coherente (§3.5), vector (§3.2), norma (§3.3), similitud (§3.6) |
| Nunca | escaneo completo del sidecar por consulta (límite explícito de §3.5) |

## 6. Límites afectados — revisión uno a uno, sin conservación automática

| Límite | Decisión | Fundamento estático |
|---|---|---|
| E3 (20 ms, límite local) | **CONSERVADO** | mismas **3 sentencias** dirigidas al sidecar (el `LEFT JOIN` con columna de solapamiento sustituye al `JOIN` interno en la **misma** sentencia); la validación es trabajo de CPU **lineal en los datos ya deserializados** (≤ 16 filas de vocabulario, ≤ 16 vectores de término, ≤ 4096 filas candidatas × ≤ 256 pares), un factor constante pequeño sobre la deserialización JSON que el límite ya contenía como término dominante; ninguna sentencia añadida, ningún dato adicional leído |
| Apertura amortizada en E3 | **CONSERVADO** | añade dos conversiones de cadena a entero sobre metadatos ya leídos |
| Materialización por identidad (≤ 2 sentencias) | **CONSERVADO** | sin cambio: la validación ocurre antes, en memoria |
| Construcción (5·10⁹ ns) | **CONSERVADO** | el descarte de pares de peso 0 (§3.2) solo **elimina** trabajo (menos pares persistidos, mismas pasadas) |
| Reconstrucción | **CONSERVADO** | es borrado + construcción; ídem |
| Borrado (2·10⁸ ns) | **CONSERVADO** | sin cambio alguno |
| Almacenamiento (32 MiB techo) | **CONSERVADO** | igual o menor: ninguna fila ni par nuevo; el descarte de ceros solo resta bytes |
| Filas lógicas validadas por consulta | **NUEVA DECLARACIÓN** | ≤ 16 (vocabulario) + ≤ 16 (vectores de término) + ≤ 4096 (candidatas); es exactamente el conjunto consumido, no una pasada adicional |

Ninguna cifra procede de medición: no existe ninguna.

## 7. Consecuencia de custodia: ficha `ADR002-B` v3

La huella de la ficha B v2 cubre `vectores.py` y `candidate.py`, que cambian.
Por la regla de sustitución (TOL-210, regla 3):

1. `ficha_ADR002-B_v2.json` se conserva y se marca `SUSTITUIDA` (cambio de
   estado únicamente, con la huella que se recomputa de él);
2. se emite `ficha_ADR002-B_v3.json` — candidato `ADR002-B`, versión 3,
   sustituye a 2, estado `CONGELADA`, motivo exacto: **validación lógica
   incompleta de un SQLite estructuralmente válido**; declara la validación
   de identidades, la validación cerrada del JSON vectorial, la comprobación
   exacta de normas, las comprobaciones aritméticas, la traducción de toda
   corrupción a error tipado, la minimización de mensajes, la defensa en la
   frontera con el puerto, la composición sobre `ADR002-A` v3, el mismo árbol
   común vigente (`a83539e3…`), el nuevo árbol propio de B, los límites
   revisados de §6, ninguna medición, ningún resultado observado y las
   limitaciones restantes de §9;
3. **todas** las pruebas de B se repiten después de congelar la v3; ninguna
   ejecución previa se reutiliza;
4. ninguna ficha ni acta de `ADR002-A` se modifica.

## 8. Orden preinscrito de commits

| # | Contenido | Regla que respeta |
|---|---|---|
| 1 | este paquete (preinscripción) | contrato antes que código |
| 2 | validadores en `vectores.py` + descarte de ceros en `construir` + defensa de frontera y referencia «A v3» en `candidate.py` + pruebas **exclusivamente estáticas** + suspensión declarada de las suites funcionales de B | corrección estática sin ejecutar B |
| 3 | ficha B v3 congelada; B v2 → `SUSTITUIDA`; custodia e inventario | ficha antes que ejecución |
| 4 | pruebas posteriores a la ficha: JSON corrupto, norma corrupta, identidad corrupta, referencias lógicas, aritmética, defensa del candidato, regresión completa de B, verificación por árboles de que A y `common` no cambiaron | anterioridad estricta |

Si tras congelar la v3 hubiera que modificar una fuente incluida en su
huella, se emitiría B v4 congelada antes de volver a ejecutar; las pruebas
hechas bajo v3 no se reutilizarían.

## 9. Limitaciones que este paquete NO corrige (se conservan declaradas)

De la fe de erratas 03 y del paquete 12, siguen vigentes y no se presentan
como corregidas:

1. la ventana de 4 096 elementos examinados se aplica **antes** de las
   exclusiones;
2. un canon **ilegible** durante la lectura del propio canon puede escapar
   sin el error tipado específico del índice;
3. la ventana concurrente entre las lecturas de `construir` (TOCTOU);
4. el techo de almacenamiento del sidecar está declarado pero no
   autoimpuesto por el código;
5. las diferencias potenciales de `libm` entre entornos (√ y ln en la
   construcción y el coseno);
6. la creación de un fichero vacío por `sqlite3.connect` en utilidades mal
   invocadas;
7. la ausencia de cierre explícito del lector durante la vida normal;
8. `S7` sin camino de adjudicación en el motor común — un índice corrupto
   sigue fallando cerrado como error tipado, no como parada adjudicada.

La número 2 se roza aquí solo en lo inevitable: la validación nueva no la
corrige ni la empeora, y queda igual de declarada.

## 10. Lo que este paquete no autoriza

Ni benchmark, ni corpus oficial, ni casos oficiales, ni medición alguna de
rendimiento; ni aprobación de B (que quedará **técnicamente preparado,
PENDIENTE DE APROBACIÓN**); ni modificación de `common/`, `adr002_a/`, las
fichas o actas de A, o Sirius 0.1; ni `ADR002-C`/`ADR002-D`; ni `EJE-1`/`EJE-2`;
ni elección de ganador; ni fusión del PR #117.
