# SIRIUS 0.2 — ADR-002 · Corpus del benchmark

**Versión:** 0.3
**Estado:** PROPUESTO · NO CONGELADO
**Rama:** `evidence/adr001-spikes`
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_03C_ENDURECIMIENTO_CORPUS_v0.1.md`
**No autoriza:** congelar el corpus, aprobar `ADR002-TOL-207`, ejecutar T0, implementar o ejecutar `ADR002-A/B/C/D`, satisfacer `ADR002-TOL-208/209/210`, abrir otro PR ni merge.

Las versiones v0.1 y v0.2 del corpus se conservan íntegras y siguen validando. Ninguna se ha modificado para hacerla pasar.

---

## 1. Dos corpus independientes

| | Conformidad | Rendimiento |
|---|---|---|
| Fichero | `conformance_corpus_v0_3.json` | `performance_corpus_v0_2.json` |
| Versión | 0.3 | 0.2 |
| Qué adjudica | puertas, exactitud, contaminación, negación, ámbito, tiempo, conflicto, ausencia y explicación | latencia, tamaño, construcción, reconstrucción y estabilidad |
| Elementos | 94 anclajes canónicos | 5.550 elementos sintéticos |
| Proyectos | 7 | **2 reales** |
| Referencias funcionales | sí | **no** |

Comparten versión de contrato (`0.3`), semilla (`20260726`) y vocabulario de estados. **No comparten contenido**: el corpus de rendimiento no reproduce los anclajes byte a byte y su léxico es disjunto del léxico protegido.

Prohibido fijar cifras de rendimiento sobre el corpus de conformidad y prohibido adjudicar conformidad sobre el corpus de rendimiento.

---

## 2. Corpus de conformidad v0.3

Conserva los **94 elementos** del v0.2: 79 recuerdos y 15 decisiones, más 7 proyectos, 5 entidades, 6 mensajes, 5 documentos y 9 relaciones. Los conteos publicados se **cuentan sobre los datos**, no se declaran.

### 2.1 Lo único que cambia

- El cierre de `B04-CA-47` deja de estar escrito a mano y se **deriva del corpus** (§3).
- Se publica la **identidad** de cada colección y de cada elemento: huella SHA-256 por colección y por `id`, para items, mensajes, documentos, relaciones, entidades y proyectos. Alterar un mensaje, un documento o una relación cambia su huella y el validador lo detecta.
- Se publican las **colisiones por raíz entre anclajes**: 29 raíces compartidas por elementos de proyectos distintos. No son un defecto —el canon exige que `presupuesto` aparezca en más de un ámbito— pero deben estar declaradas. El validador las recalcula y exige igualdad exacta: una colisión nueva y no declarada cambiaría en silencio el significado de un caso.

### 2.2 Neutralidad de los datos

La única tecnología nombrada en todo el corpus es `PostgreSQL`, en `DEC-010` y en `ENT-POSTGRESQL`, ambos trazados a `B04-CA-42`, cuyo texto canónico la nombra literalmente. Ninguna otra tecnología y ningún candidato `ADR002-A/B/C/D` aparece en ningún campo.

---

## 3. Cierre exhaustivo de `B04-CA-47`

El artefacto declara el filtro base y el filtro temporal de cada rama, y el conjunto se **calcula**:

```
filtro base: kind=DECISION · project_id=PRJ-BETA · confirmacion=CONFIRMADA
             validez=VIGENTE · disponibilidad=DISPONIBLE · sensibilidad=ORDINARIA
             no_usar_como_memoria=false
universo en ámbito: DEC-005 DEC-009 DEC-011 DEC-013 DEC-014 DEC-015
```

| Rama | Predicado temporal | Elegibles | Prohibidos |
|---|---|---|---|
| `R1` | `occurred_at ∈ [2026-01-01, 2026-02-01)` | `DEC-011 DEC-015` | `DEC-005 DEC-009 DEC-013 DEC-014` |
| `R2` | `valid_from ≤ 2026-01-20 < valid_to` o `valid_to` abierto | `DEC-005 DEC-009 DEC-014` | `DEC-011 DEC-013 DEC-015` |
| `R3` | `recorded_at ≤ 2026-02-15` | `DEC-005 DEC-014 DEC-015` | `DEC-009 DEC-011 DEC-013` |

`DEC-012` queda fuera de las tres ramas por `validez = SUSTITUIDA`, no por selección manual. Los prohibidos son exactamente el complemento del universo.

El validador reimplementa el predicado y compara. Si alguien recorta `R2` a `{DEC-014}` —el conjunto que el v0.2 declaraba— la comprobación falla.

---

## 4. Corpus de rendimiento v0.2 · sintético de estrés neutral

**No representa producción.** Es un corpus sintético de estrés cuyo propósito es medir magnitudes, y sus distribuciones se publican para que puedan discutirse.

### 4.1 Escala exacta, contada sobre los datos

| | Valor |
|---|---|
| Mensajes | **5.000** |
| Recuerdos (`MEMORIA`) | **500** |
| Decisiones (`DECISION`) | **50** |
| Proyectos reales | **2** (`PRJ-ARRECIFE`, `PRJ-CUMBRE`) |
| Documentos | 120 |
| Relaciones | 180 |
| Entidades | 24 |

No hay un proyecto artificial único de volumen: los 5.550 elementos se reparten entre los dos proyectos reales.

### 4.2 Generación

- **Semilla fija** `20260726`. Sin reloj, sin red, sin dato real.
- **Nueve familias temáticas** (astronomía, marina, mineral, panadería, música, textil, meteorología, botánica, alfarería) con vocabularios intercalados, de modo que ningún tema domine los rangos.
- **Doce estructuras gramaticales**: declarativa, declarativa adjetivada, negativa, interrogativa, condicional, temporal subordinada, enumerativa, comparativa, causal, concesiva, pasiva refleja e impersonal. Cada texto combina de una a cuatro cláusulas.
- **Vocabulario Zipf-Mandelbrot**: `peso(rango) = 1/(rango+5)` sobre 236 palabras de contenido.
- **Ningún número de secuencia en el texto**: ningún texto del corpus contiene un dígito. La variedad procede de la combinación gramática × vocabulario, no de un contador.

### 4.3 Distribución observada

Calculada por el validador **sobre los datos**, nunca comparando una declaración con otra.

**Longitud de texto** (6.194 textos)

| media | mediana | p95 | desviación | mínimo | máximo | longitudes distintas |
|---|---|---|---|---|---|---|
| 86,66 | 82 | 169 | 43,55 | 24 | 220 | **186** |

**Vocabulario**

| tokens informativos | tamaño | frecuencia máxima | frecuencia relativa máxima | pendiente Zipf (log-log) |
|---|---|---|---|---|
| 55.219 | **236** | 1.408 (`junto`) | **2,55 %** | **−0,796** |

Diez más frecuentes: `junto` 1.408 · `telar` 1.083 · `nebulosa` 1.009 · `arrecife` 914 · `glaciar` 882 · `bruma` 870 · `granizo` 855 · `basalto` 832 · `cielo` 820 · `taller` 806.

**Textos**: 6.194 de 6.194 distintos (**100 %**). No hay plantilla repetida.

**Fechas**: 457 fechas distintas en 15 meses, del `2025-03-01` al `2026-05-31` (intervalo declarado).

**Reparto por proyecto**: `PRJ-ARRECIFE` 53,51 % · `PRJ-CUMBRE` 46,49 %. Ninguno supera el 60 %.

**Ejes de estado**

| Eje | Reparto observado |
|---|---|
| confirmación | CONFIRMADA 61,6 % · CANDIDATA 19,3 % · RECHAZADA 12,0 % · SUPRIMIDA 7,1 % |
| validez | VIGENTE 66,0 % · SUSTITUIDA 15,6 % · INVALIDADA 10,2 % · SIN_SOPORTE 8,2 % |
| disponibilidad | DISPONIBLE 73,5 % · ARCHIVADA 12,4 % · ELIMINADA 5,8 % · PURGADA 5,3 % · NO_GUARDADA 3,1 % |
| sensibilidad | ORDINARIA 82,0 % · RESTRINGIDA 18,0 % |
| polaridad | AFIRMATIVA 79,6 % · NEGATIVA 20,4 % |
| condición presente | sí 18,4 % · no 81,6 % |
| temporalidad cerrada (`valid_to`) | sí 28,7 % · no 71,3 % |

**Proporciones**: items con entidades 36,6 % · con procedencia 40,9 % · con criticidad 22,0 % · entidades con alias 33,3 %.

**Relaciones**: 180 relaciones, 6 tipos (`APOYA`, `REFUTA`, `CONFLICTO_CON`, `CORRIGE`, `SUSTITUYE_A`, `DERIVA_DE`), densidad 0,327 por item.

**Estructuras gramaticales**: entre 1.028 y 1.127 usos cada una de las doce.

### 4.4 Invariantes que el validador exige

≥20 longitudes distintas y desviación ≥15 · vocabulario ≥150 · frecuencia relativa máxima ≤6 % · pendiente Zipf en `[−1,45, −0,55]` · ≥60 fechas distintas y ≥6 meses · ninguna cuota de proyecto >60 % · ≥2 valores por eje con el segundo ≥2 % · ≥4 tipos de relación y densidad ≥0,10 · ≥20 % de items con entidades · ≥5 % de entidades con alias · ≥20 % con procedencia · ≥10 % con criticidad · ≥5 familias temáticas y ≥6 estructuras · ≥98 % de textos distintos.

Un corpus uniforme —todos los textos iguales, o distinguidos solo por un contador— falla al menos cuatro de estas comprobaciones a la vez.

---

## 5. Contaminación

El léxico protegido se construye **automáticamente** desde el corpus de conformidad y los casos: textos de items, condiciones, razones de criticidad, mensajes, títulos y textos de documentos, notas de relación, nombres y alias de proyectos y entidades, consultas instanciadas, explicaciones esperadas, textos canónicos de los casos y textos de cada rama.

Hoy contiene 720 tokens informativos, 408 raíces, 24 nombres y alias y 3.866 n-gramas.

Se normaliza Unicode (NFKD), se quitan acentos, se pasa a minúsculas y se eliminan signos. La detección usa cinco mecanismos:

| Mecanismo | Qué detecta | Ejemplo |
|---|---|---|
| `TOKEN_EXACTO` | coincidencia literal normalizada | `presupuesto` |
| `SINGULAR_PLURAL_O_SUFIJO` | flexión por sufijo | **`turnos` ← `turno`** |
| `RAIZ_COMUN` | prefijo normalizado de 6 caracteres | **`registrado` ← `regist`** |
| `ENTIDAD_O_ALIAS` | nombre o alias multipalabra | `Proyecto Atlas Alfa` |
| `NGRAMA` | bigramas y trigramas con al menos un token informativo | `presupuesto maximo` |

Los dos pares mínimos que el paquete 03C exige —`turno/turnos` y `registro/registrado`— se detectan por mecanismos distintos y hay una prueba para cada uno.

**Resultado sobre el corpus de rendimiento: 0 textos contaminados de 6.194**, y ningún nombre ni alias de entidad o proyecto comparte léxico.

---

## 6. Reglas de protocolo del arnés

`pdp_harness_rules_v0_1.json` recoge `PDP-CA-02`, `-03`, `-06`, `-16`, `-17` y `-18` con texto canónico, fuente PDP, regla que las importa, regla de ejecución, evidencia requerida, consecuencia y estado de aplicabilidad (`APLICABLE_TRAS_CONGELACION` en las seis: gobiernan una ejecución que todavía no puede empezar).

El fichero declara los campos que una regla **no puede** llevar y el validador lo comprueba: sin consulta, sin modo, sin cardinalidad, sin etapa, sin parada, sin elegibles ni prohibidos, sin ficha del PDP §7 y sin previsión frente a T0.

---

## 7. Determinismo y no mutación

- Doble regeneración en directorio temporal, byte a byte idéntica entre sí y con los artefactos comprometidos.
- El validador **no escribe en el árbol de trabajo**: toma una instantánea de tamaño, fecha de modificación y bytes de todos los `.json` del paquete antes de validar y comprueba que ninguno cambió. El único fichero que produce es su propio informe, en `artifacts/`.

---

## 8. Puertas

`ADR002-TOL-207` **no se aprueba ni se modifica**: su presupuesto ligado al corpus solo puede calcularse midiendo sobre este corpus de rendimiento, y T0 no se ha ejecutado. `ADR002-TOL-208`, `ADR002-TOL-209` y `ADR002-TOL-210` siguen **NO SATISFECHAS**.
