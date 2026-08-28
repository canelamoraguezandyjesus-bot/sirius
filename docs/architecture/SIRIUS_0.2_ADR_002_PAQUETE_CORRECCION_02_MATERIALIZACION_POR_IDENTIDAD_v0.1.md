# SIRIUS 0.2 — ADR-002 · Paquete de corrección 02: materialización por identidad canónica

**Versión:** 0.1
**Estado:** PROPUESTO · PREINSCRITO — fija el diagnóstico y el contrato **antes** de modificar código
**Fecha:** 1 de agosto de 2026
**Rama:** `evidence/adr001-spikes`
**Commit de partida:** `35ed9cf3bbf03c82dc2ce4fa79397af1ba9a1064`
**Origen:** limitación 1 de la fe de erratas 03 (`SIRIUS_0.2_ADR_002_FE_DE_ERRATAS_03_ADR002B_ARITMETICA_Y_LIMITACIONES_v1.0.md`), hallada por la revisión adversarial previa al push de `ADR002-B`
**Fichas afectadas:** `ficha_ADR002-A_v2.json` (huella `4ed820fab545dd9154ce078349c214f870baecd1`) · `ficha_ADR002-B_v1.json` (huella `c1ca17a7f5345b4cec2a0ea63dac6c8b1bb6e5fd`)
**No autoriza:** aprobar automáticamente `ADR002-A` o `ADR002-B` como PREPARADOS PARA BENCHMARK; ejecutar el benchmark; usar el corpus oficial; medir rendimiento; implementar `ADR002-C` o `ADR002-D`; modificar Sirius 0.1 productivo; abrir `EJE-1` o `EJE-2`; elegir ganador; fusionar el PR #117.

---

## 1. Diagnóstico exacto del defecto

El índice vectorial de `ADR002-B` identifica cada coincidencia por el
**identificador canónico exacto** del elemento (`MEMORIA:<id>` /
`DECISION:<id>`). Sin embargo, `CandidatoB._vectoriales` materializa hoy así:

1. extrae las **claves de sujeto** de las coincidencias;
2. `ordenar_estable` descarta implícitamente las claves vacías al acotar;
3. llama a `por_clave_exacta(claves)`;
4. reconstruye un mapa por identificador con lo devuelto;
5. **omite en silencio** (`if item is None: continue`) cualquier
   identificador que no aparezca en ese mapa.

Eso pierde, sin traza y sin error:

- elementos con **clave de sujeto vacía** (el puerto filtra cadenas vacías en
  `_acotar`: esa clave jamás se consulta);
- elementos con **claves duplicadas** cuando el conjunto devuelto no contiene
  el id exacto pedido;
- elementos situados **después del límite de 512 filas** de una misma clave
  (`LIMIT 512` en las consultas por clave);
- en general, **cualquier coincidencia que el índice identificó y el rodeo
  por clave no materializa**.

### 1.1 Por qué la clave de sujeto no puede sustituir a la identidad

La clave de sujeto es una **relación estructural**: agrupa, empareja y filtra.
No es única (claves duplicadas), no es total (elementos sin clave) y su
recorrido está acotado por diseño (512 filas). El identificador canónico es
**la identidad**: único, total y estable. Materializar por clave lo que se
identificó por id es responder a una pregunta distinta de la que se hizo: el
índice afirmó «el elemento 513», y el rodeo respondió «los primeros 512 que
comparten su clave». La materialización por clave **no es equivalente** a la
materialización por identidad, y la diferencia es exactamente lo que se pierde
sin traza.

## 2. Decisión arquitectónica

**La corrección pertenece al puerto común.** El puerto ya materializa por id
internamente (`_items`, `_por_ids_mixtos`, SQL dirigido por `id IN (...)`):
lo que falta es la operación **pública, neutral y auditable**. Queda prohibido
resolverlo dentro de `ADR002-B` mediante: acceso directo propio a SQLite,
llamadas a métodos privados del puerto, `isinstance` contra `PuertoSqlite`,
un segundo puerto acoplado al proveedor, recuperación por clave como sustituto
del identificador, o degradación silenciosa. La operación nueva queda
disponible para `ADR002-A/B/C/D` sin favorecer a ninguno: no conoce
similitudes, ni vectores, ni sidecars, y no cambia el comportamiento de
ningún método existente.

## 3. El contrato nuevo, congelado antes de implementarlo

### 3.1 Operación

```
PuertoDeRecuperacion.por_identificadores(
    identificadores: Sequence[str],
) -> MaterializacionPorIdentidad
```

Nombre coherente con la familia existente (`por_clave_exacta`,
`por_termino_lexico`, `por_prefijo_de_sujeto`).

### 3.2 Resultado cerrado y neutral

El contrato de retorno actual (`tuple[ItemCanonico, ...]`) no permite
distinguir de forma segura lo pedido de lo encontrado y de lo ausente, de
modo que se introduce un dataclass inmutable en la capa común:

```
MaterializacionPorIdentidad(
    pedidos: int,                      # entradas recibidas, duplicados incluidos
    solicitados: tuple[str, ...],      # normalizados, unicos, orden canonico
    items: tuple[ItemCanonico, ...],   # los que existen, orden canonico estable
    ausentes: tuple[str, ...],         # solicitados que el canon no contiene
)
```

con `encontrados = len(items)` y `completa = not ausentes` derivables. Ningún
candidato tiene que reconstruir esa distinción a mano.

### 3.3 Formato cerrado de identificadores

Se aceptan **únicamente** identificadores canónicos construidos desde los
valores reales de `Clase` —sin cadenas paralelas divergentes—:

```
^(MEMORIA|DECISION):<entero sin ceros a la izquierda, >= 1>$
```

### 3.4 Validación: errores tipados (`IdentificadorInvalidoError`)

Rechazan, con error tipado y sin ejecutar SQL alguno: formato desconocido;
clase desconocida; separadores adicionales; id no numérico; id cero; id
negativo (y ceros a la izquierda, que serían codificaciones duplicadas de la
misma identidad); **argumento vacío**; y **más identificadores únicos que la
cota autorizada** (`ARGUMENTOS_MAXIMOS = 16`), que **no se trunca**: se
rechaza. Un identificador sintácticamente válido pero inexistente **no es un
error de formato**: aparece en `ausentes`.

### 3.5 Determinismo y cotas

- deduplicación determinista de la entrada; ordenación canónica por
  (clase, número);
- cota explícita **anterior a SQL**; exceder la cota falla tipado, jamás
  trunca;
- la división por clase ocurre **después** de validar la entrada entera;
- el trabajo máximo depende de la cantidad de identificadores solicitados,
  nunca del tamaño del canon (búsqueda por clave primaria).

### 3.6 SQL permitido

Exclusivamente consultas equivalentes a `WHERE id IN (...)`, separadas por
clase, con orden estable y cota explícita, registradas en
`RegistroDeConsultas` con operación propia (`por_identidad:<clase>`). Nada de
clave de sujeto, proyecto, FTS, prefijos, relaciones semánticas, barridos ni
contenido suministrado por el sidecar. Se devuelven exclusivamente los
elementos exactos pedidos que existan en el canon.

### 3.7 Instrumentación y minimización

Entre el registro del puerto y el resultado quedan registrados, como mínimo:
operación y clase, SQL dirigido, cota y filas devueltas (en
`RegistroDeConsultas`); y entradas recibidas, únicos válidos solicitados,
encontrados y ausentes (en `MaterializacionPorIdentidad`). Nunca contenido
protegido: identificadores y conteos.

## 4. Corrección de `ADR002-B`

La ruta vectorial materializa **directamente los identificadores exactos**
devueltos por el sidecar —a lo sumo `TOP_K = 8`, dentro de la cota de 16—
mediante la operación pública nueva. La materialización basada en clave de
sujeto **desaparece de la ruta vectorial**. La clave de sujeto puede seguir
formando parte de la representación vectorial, de las señales estructurales y
de la explicación; lo que ya no puede es determinar qué fila canónica se
recupera.

**Comportamiento obligatorio ante inconsistencia:** si el sidecar devuelve un
identificador válido que el canon no contiene, `ADR002-B` no lo descarta, no
devuelve recuperación parcial, no continúa como si no hubiera coincidencia y
no degrada a `ADR002-A`: lanza **`IndiceInconsistenteError`** (subtipo de
`IndiceNoUtilizableError`), registrando solo identificadores y clases, nunca
contenido. No se adjudica `S7`, porque el motor común sigue sin ofrecer esa
ruta (limitación registrada, no disimulada). Quedan así distinguidos los tres
casos: (1) coincidencia válida descartada después por una puerta —visible en
la traza—; (2) coincidencia cuyo id ya no puede materializarse —fallo cerrado
tipado—; (3) consulta vectorial sin coincidencias —cero candidatas, sin
error—.

## 5. Consecuencia de custodia

Modificar `experiments/adr002/candidates/common/` cambia fuentes incluidas en
la huella de la ficha `ADR002-A` v2; modificar `adr002_b/` cambia fuentes de
la ficha `ADR002-B` v1. Por la regla 3 de custodia del acta de TOL-210:

| Ficha | Destino |
|---|---|
| `ADR002-A` v2 | se conserva como historial y pasa a `SUSTITUIDA` |
| `ADR002-A` v3 | se emite y congela **antes** de repetir cualquier ejecución de A |
| `ADR002-B` v1 | se conserva como historial y pasa a `SUSTITUIDA` |
| `ADR002-B` v2 | se emite y congela **antes** de repetir cualquier ejecución de B |

- **Todas** las pruebas funcionales de A y de B se repiten bajo sus fichas
  sucesoras; ninguna ejecución previa se reutiliza como evidencia.
- El **acta histórica** que declaró a `ADR002-A` v2 PREPARADO PARA BENCHMARK
  **permanece intacta**, y esa aprobación **no se traslada automáticamente**
  a la implementación vigente: al terminar, `ADR002-A` queda **técnicamente
  preparado pero PENDIENTE DE REAPROBACIÓN**, y `ADR002-B` queda
  **técnicamente preparado pero PENDIENTE DE APROBACIÓN**. Este paquete no
  crea actos de preparación ni de aprobación.
- Para `ADR002-A` v3: su comportamiento funcional **no cambia** —su código
  propio no se toca y A no llama a la operación nueva—; sus límites se
  conservan **tras revisión**, y la regresión funcional completa lo
  demuestra ejecutando, no reutilizando resultados históricos.
- Para `ADR002-B` v2: los límites se revisan uno a uno contra el camino
  nuevo (menos sentencias y más baratas: la materialización pasa de ≤18
  sentencias por clave a ≤2 por identidad); ninguna cifra se conserva
  automáticamente y ninguna procede de medición.

## 6. Orden de ejecución preinscrito

| Commit | Contenido | Restricción |
|---|---|---|
| 1 | este paquete | nada de código ejecutable |
| 2 | contrato y operación comunes + corrección de B + instrumentación + errores tipados + pruebas **estáticas y de formato/cotas/errores** + suspensión declarada de las suites funcionales de A y B | sin ejecutar funcionalmente A ni B |
| 3 | fichas `ADR002-A_v3` y `ADR002-B_v2` congeladas; v2/v1 → `SUSTITUIDA` | sin ejecutar funcionalmente A ni B |
| 4 | pruebas posteriores: puerto por identidad, clave vacía, claves duplicadas, >512 con la misma clave, id inconsistente, regresión completa de A y de B | solo cuando ambas fichas sucesoras sean **ancestro estricto** |

Las limitaciones de la fe de erratas 03 que este paquete **no** corrige
(ventana de examinados, canon ilegible sin tipar, ventana concurrente en
construcción, techo de almacenamiento no autoimpuesto, `libm`, ficheros
creados por `connect`, cierre del lector, `S7` sin adjudicación) **siguen
vigentes y no se presentarán como corregidas**.

---

**Siguiente movimiento único:** implementar el contrato del §3 y la
corrección del §4, sin ejecutar funcionalmente ningún candidato, y
confirmarlo como commit 2.
