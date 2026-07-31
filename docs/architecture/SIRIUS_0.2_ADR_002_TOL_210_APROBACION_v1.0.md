# SIRIUS 0.2 — ADR-002 · Aprobación de TOL-210

**Versión:** 1.0  
**Estado:** **APROBADO · ADR002-TOL-210 SATISFECHA**  
**Fecha:** 31 de julio de 2026  
**Rama:** `evidence/adr001-spikes`  
**Autoridad:** Usuario / Proyecto Sirius  
**Commit auditado:** `ba77efdd578f5bbcaae7a12bbe6868709fdcdce0`  
**Commit del paquete 09:** `c8f9503608810e6f9563f04773b041a7e1bf19df`  
**Autorización explícita del usuario:** «Materializa la aprobación explícita de ADR002-TOL-210 desde el HEAD actual»

## 0. Objeto

Esta acta materializa la aprobación explícita de `ADR002-TOL-210` —**ficha de
candidato obligatoria**— tras el paquete de trabajo 09, que la convirtió de
una regla declarada en una regla **comprobable por máquina**.

Desde esta acta, `ADR002-TOL-210` queda **SATISFECHA** dentro del alcance
exacto definido aquí.

Los documentos y artefactos conservan sus nombres y etiquetas históricas
`PROPUESTO`. Esta acta prevalece sobre esas etiquetas sin reescribirlos,
preservando las identidades exactas auditadas.

## 1. Decisión aprobada

Se aprueba como **plantilla única y vinculante** de la ficha de candidato:

> `docs/architecture/SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.3_PROPUESTO.md`

Las v0.1 y v0.2 se conservan **sin modificar** y su intangibilidad es un
control bloqueante. La v0.3 las sustituye como norma vigente sin reescribirlas.

Se aprueba con ella el **contrato ejecutable** del paquete 09, que es lo que
hace auditable la regla:

> `experiments/adr002/cards/` — `card_protocol.py`, `schema_card_v0_1.py`,
> `verify_cards.py` y sus pruebas.

### 1.1 Las dos consecuencias que la fila declara, ahora exigibles

`ADR002-TOL-210` dice:

> Un candidato sin ficha confirmada **no es ejecutable**.
> Una ejecución que no referencie una ficha previa **no es utilizable como
> evidencia**.

Ambas quedan **hechas cumplir por máquina**. Hasta el paquete 09 eran
declaraciones que nadie comprobaba, que es exactamente el defecto que la
propia fila denuncia de la v0.3 del Registro.

### 1.2 Forma normativa

La ficha se materializa como **JSON**, validado por
`schema_card_v0_1.fallos_ficha`, y vive en:

```text
artifacts/adr002_cards/ficha_<ID>_v<N>.json
```

La plantilla v0.3 es su **lectura humana**; el JSON es lo normativo.

### 1.3 Anterioridad: se observa, no se declara

La congelación **no es una fecha**. Se exige, acumulativamente:

1. el fichero está **confirmado** en el repositorio con ese contenido exacto;
2. el commit en que **entró** —el más antiguo del historial en que esa ruta
   lleva ese blob, **observado por el verificador**— es **ancestro estricto**
   del commit que ejecuta.

**Estricto**: aparecer en el mismo commit que la ejecución no es haber
congelado antes.

La ficha **no declara el commit que la contiene**, y no puede hacerlo: el SHA
de un commit depende del contenido que lo incluye, de modo que el campo sería
autorreferencial e imposible de rellenar. La ficha declara su **commit de
referencia** —el del acto de gobierno bajo el que se congela—; cuándo entró lo
dice Git.

### 1.4 La huella

La huella es el **blob Git de la forma canónica de la ficha excluido el propio
campo de huella**. Se excluye por necesidad aritmética: una huella que se
incluyese a sí misma no tendría punto fijo.

La huella dice **qué** se congeló; el §1.3 dice **cuándo**. Ninguna sustituye
a la otra.

### 1.5 Ausencia de resultados

Una ficha contiene **límites y declaraciones**, jamás mediciones del propio
candidato. Se hace cumplir **cerrando** todos los conjuntos de campos: lo que
el esquema no prevé, no entra. Una lista de nombres prohibidos se esquivaría
renombrando.

### 1.6 Coherencia con las puertas ya satisfechas

La ficha **cita** los valores aprobados; no propone los suyos:

| Magnitud | Valor citado | Origen |
|---|---:|---|
| Presupuesto absoluto por candidato | `1.610.612.736 B` | acta de TOL-207 |
| `SM` | `17.405 ns` | acta de TOL-209 |
| `U50` | `2.685 ns` | acta de TOL-209 |
| Sesiones | `11`, exactamente | acta de TOL-209 |
| Protocolo aplicable | `PROTOCOLO_MEDICION_v0.2` | acta de TOL-209 |

Una ficha que declarase otros no estaría congelando una tolerancia: la estaría
**cambiando en silencio** para su propio candidato.

### 1.7 Universo de fichas

Las fichas son de las **alternativas mínimas** de ARQ-00 §23 —`ADR002-A`,
`ADR002-B`, `ADR002-C`, `ADR002-D`— más **`T0-control`**. La partición T1–T4
de ADR-002 v0.2 §3 **no es la misma**, y la Resolución de la partición de
candidatos v1.0 zanjó cuál rige.

**Solo `T0` puede fichar como control de falsación.** Marcar `ADR002-A` o
`ADR002-C` como control invalida la ficha: no declarar una señal tardía **no
es un déficit**, es la alternativa que se pone a prueba.

`T0-control` no declara alternativa mínima ni señal tardía: es la línea base,
incumple RF-14 y no compite.

## 2. Identidad vinculante de la familia aprobada

La identidad se fija mediante blobs Git en el commit auditado
`ba77efdd578f5bbcaae7a12bbe6868709fdcdce0`.

### 2.1 Documentación normativa

| Artefacto | Blob Git |
|---|---|
| `docs/architecture/SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.3_PROPUESTO.md` | `c2beba3e829163ea5fd052c9f1831a13b205873a` |
| `docs/architecture/SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_09_TOL210_FICHA_CANDIDATO_v0.1.md` | `a9e2b85ff9868c3a3fc7c5f787fdf75efaed9539` |

### 2.2 Contrato ejecutable y verificación

| Artefacto | Blob Git |
|---|---|
| `experiments/adr002/cards/card_protocol.py` | `e9b665fbdbb5c9baab3c4db245fe4f29f6cc6973` |
| `experiments/adr002/cards/schema_card_v0_1.py` | `5c437be4001d199e4f11e7fb1a6dc9044de62066` |
| `experiments/adr002/cards/verify_cards.py` | `9a17f2ac46462a6d305f496b4312869de4a2ecb2` |
| `experiments/adr002/cards/test_adr002_cards.py` | `eac35f7fac898978a567c66838d2203ec607148a` |
| `experiments/adr002/cards/__init__.py` | `f7345e760df0d15ec23f3317cbe8b57e74228b9e` |
| `experiments/adr002/cards/conftest.py` | `c1e48a4e3df34c86fccc57816cd2e5d908bfacdc` |

### 2.3 Dependencias aprobadas que la ficha cita

| Artefacto | Blob Git |
|---|---|
| `SIRIUS_0.2_ADR_002_TOL_207_APROBACION_v1.0.md` | `8044c3c9e52b9153d03a23c1491c7be09736569f` |
| `SIRIUS_0.2_ADR_002_TOL_209_APROBACION_v1.0.md` | `d2b02aaad9829469a1dde4bf82fe3bd26ec2032b` |
| `SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.2_PROPUESTO.md` | `cf65d67458b616d1f095a307c01ee1b6a590e0e2` |
| `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.5_PROPUESTO.md` | `a3dd91ffc74d2fb518998b89996e0d4c221f6394` |
| `artifacts/adr002_tolerances/perfil_tolerancias_v0.1.json` | `41003495620aaf9cd37404b45bf359410c4e7504` |
| `SIRIUS_0.2_ADR_002_CONGELACION_CORPUS_v0.4_APROBADA.md` | `414a2b3764f40461ead754b98945efcbe6345fae` |

### 2.4 Actos que fijan el universo de candidatos

| Artefacto | Blob Git |
|---|---|
| `SIRIUS_0.2_ADR_002_RESOLUCION_PARTICION_CANDIDATOS_v1.0_APROBADA.md` | `269e960ee00834a74c1171c1edda094e85042acf` |
| `SIRIUS_0.2_ADR_002_NOTA_SUPERACION_02_PARTICION_CANDIDATOS_v1.0_APROBADA.md` | `b93ab9fc59ff16af1e1bfa62a987d8b278b08c73` |

### 2.5 Plantillas anteriores, intangibles

**No se editan.** Sus blobs los citan el Registro, el paquete 02D y la
Resolución de la partición. Su intangibilidad es un **control bloqueante**:

| Artefacto | Blob Git |
|---|---|
| `SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.1_PROPUESTO.md` | `4e9fa861ed6ab22a6b19729ed44066c8d93d863e` |
| `SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.2_PROPUESTO.md` | `5bdc0133e6f7f578816969ead4e1ff7498a54a04` |

Cualquier modificación posterior de los contenidos de esta §2 requiere
revisión explícita y un acto sucesor.

## 3. Evidencia y resultado de auditoría

### 3.1 Catorce controles bloqueantes

Fallan **cerrado**. Se computan sobre las fichas presentes y **solo si hay
alguna**: con cero fichas el recorrido publica «sin fichas que controlar» en
vez de catorce verdes, porque publicarlos sin haber mirado ninguna ficha sería
el mismo defecto un nivel más arriba.

El control `ejecucion_sin_ficha_no_utilizable` no se deriva de que ninguna
ficha falle —eso sería compatible con un verificador que nunca denuncia nada—:
se **sondea**, comprobando que una referencia sin respaldo sale efectivamente
`NO_UTILIZABLE`.

### 3.2 El estado de las puertas se deriva

`verify_cards` no acepta que le declaren qué puertas están satisfechas: lo
**deriva de las actas que existen** en el repositorio.

### 3.3 Auditoría y corrección de un bloqueante

La autoauditoría del paquete 09 encontró y corrigió tres defectos antes de su
entrega: la huella sin punto fijo, el universo de candidatos erróneo (T1–T4 en
vez de las alternativas mínimas) y los controles que nadie computaba.

**Un cuarto defecto, bloqueante, se encontró al preparar esta acta** y se
corrigió en el commit `ba77efd`, antes de fijar ningún blob:

> `congelacion.commit` declaraba «el commit donde esta ficha está confirmada»,
> y el verificador comprobaba `blob_en_commit(commit, ruta)` contra el blob de
> la propia ficha. **Era insatisfacible por construcción**: el SHA de un
> commit depende del árbol que contiene la ficha, de modo que ninguna ficha
> real podía rellenar el campo.

Era la misma autorreferencia que ya se había corregido en la huella, presente
en un segundo lugar y no detectada entonces. Salió al construir la primera
ficha real. Fijar por blob un contrato imposible de satisfacer habría sido
aprobar un defecto, así que se corrigió primero.

### 3.4 Suites en el commit auditado

- paquete 09: `99 passed`;
- `experiments/`: `1 046 passed`;
- repositorio (`tests/`): `1 195 passed`;
- Ruff format y Ruff lint: conformes;
- mypy: sin errores;
- plantillas v0.1 y v0.2, y toda la evidencia anterior: **intactas byte a
  byte**.

## 4. Correcciones no bloqueantes registradas

1. **El contrato comprueba la forma, no la verdad.** Que un límite esté
   declarado, completo y sin contradecir lo aprobado no lo hace correcto. Lo
   que el contrato impide es declararlo **tarde**, **incompleto** o
   **contradictorio**.
2. La anterioridad se apoya en el grafo de Git: un historial reescrito la
   invalidaría —comportamiento querido—, pero la garantía es tan fuerte como
   la custodia del repositorio.
3. La coherencia entre coste por etapa y extremo a extremo se comprueba sobre
   los **límites duros**, no sobre los objetivos.
4. El contrato **no verifica que la rederivación de T0 exista**: solo exige
   que la ficha declare si existe y, si no, por qué.
5. `primer_commit_con_blob` recorre el historial de la ruta; en repositorios
   con miles de commits sobre la misma ficha su coste crece linealmente. Es
   irrelevante a esta escala y no se optimiza.

## 5. Limitaciones conocidas registradas

1. **Una ficha no acredita un candidato.** Acredita que sus límites se
   congelaron antes, completos y coherentes. Si el candidato los cumple es
   cosa del benchmark, que no está autorizado.
2. **`T0-control` no declara alternativa ni señal tardía.** Esas secciones
   quedan en `null` por ser la línea base y no competir.
3. **Ninguna ficha puede declarar hoy una rederivación de T0 real**, porque
   `ADR002-TOL-208` no está satisfecha en sus pasos 2 y 3.
4. **Un solo entorno.** Todo es `LAB-LINUX`.

## 6. Estado de las puertas tras esta acta

| Puerta | Estado |
|---|---|
| `SRC-ADR002-01` | **SATISFECHA** |
| `ADR002-TOL-207` | **SATISFECHA** |
| `ADR002-TOL-209` | **SATISFECHA** |
| `ADR002-TOL-210` | **SATISFECHA** — por esta acta |
| `ADR002-TOL-208` · paso 1 | **COMPLETADO** — corpus v0.4 congelado |
| `ADR002-TOL-208` · global | **NO SATISFECHA** — faltan los pasos 2 y 3 |

**La única puerta global de arranque pendiente es `ADR002-TOL-208`, en sus
pasos 2 y 3**: ejecutar T0 sobre el corpus congelado y rederivar la
comparación de línea base.

**El benchmark continúa bloqueado.**

## 7. Lo que esta acta no autoriza

- **No autoriza ejecutar T0.** Esa ejecución requiere autorización expresa e
  independiente.
- No ejecutar los pasos 2 y 3 de `ADR002-TOL-208`.
- No implementar ni ejecutar `ADR002-A`, `ADR002-B`, `ADR002-C` ni
  `ADR002-D`.
- No iniciar el **benchmark**.
- No aprueba ningún candidato ni ninguna ficha de alternativa mínima: aprueba
  la **regla** y su contrato, no su instanciación.
- No aprueba el resto del Registro v0.5.
- No modifica Sirius 0.1 (`src/`, `tests/`, `migrations/` ni configuración
  productiva).
- No abrir otro PR.
- **No fusionar el PR #117.**

## 8. Reglas de custodia

1. Toda ficha se congela **antes** de la primera ejecución de su candidato, y
   la anterioridad se comprueba contra el grafo de Git, no contra una fecha.
2. Una ejecución que no referencie una ficha previa por `candidato · versión ·
   huella` **no es utilizable como evidencia**.
3. **Una sola ficha `CONGELADA` por candidato.** Publicar una sucesora obliga
   a marcar `SUSTITUIDA` la anterior y a **repetir** las ejecuciones hechas
   bajo ella.
4. Las versiones de ficha crecen de una en una y nunca retroceden.
5. Cualquier cambio de los contenidos vinculados en §2 exige revisión y un
   **acto sucesor**.
6. Las plantillas v0.1 y v0.2 **se conservan intactas**. Ninguna se sustituye,
   se retira ni se reescribe.
7. Las etiquetas internas `PROPUESTO` permanecen como historia auditada y no
   disminuyen la autoridad de esta acta.

---

**Decisión final:** `ADR002-TOL-210` queda **APROBADA y SATISFECHA**. La única
puerta de arranque pendiente es `ADR002-TOL-208` en sus pasos 2 y 3, cuya
ejecución de T0 requiere **autorización expresa e independiente**. Los
candidatos, el benchmark y la fusión del PR #117 continúan no autorizados.
