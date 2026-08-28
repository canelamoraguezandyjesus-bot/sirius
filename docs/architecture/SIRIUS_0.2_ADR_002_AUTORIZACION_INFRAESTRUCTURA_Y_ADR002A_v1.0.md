# SIRIUS 0.2 — ADR-002 · Autorización y preinscripción · infraestructura común y `ADR002-A`

**Versión:** 1.0
**Estado:** **APROBADO** — autorización de implementación, preinscrita antes de escribir código
**Fecha:** 31 de julio de 2026
**Rama:** `evidence/adr001-spikes`
**Autoridad:** Usuario / Proyecto Sirius
**HEAD de partida verificado:** `c1385b180045c3efc3d8345be6128cceaad1e987`
**Autorización literal del usuario:** «**venga siguiente**»
**Paquete que autoriza:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_11_INFRAESTRUCTURA_COMUN_Y_ADR002A_v0.1.md`
**No autoriza:** ejecutar el benchmark, medir rendimiento del candidato, usar el corpus congelado v0.4 para evaluarlo, implementar `ADR002-B/C/D`, abrir `EJE-1` o `EJE-2`, elegir ganador, modificar Sirius 0.1 ni fusionar el PR #117.

---

## 1. Alcance exacto de la autorización

Con las cinco puertas de arranque satisfechas, el usuario autoriza —y **solo**
esto—:

1. **diseñar y congelar la infraestructura común** de la primera ronda,
   reutilizable por `ADR002-A/B/C/D`;
2. **implementar el prototipo completo de `ADR002-A`**;
3. **emitir y congelar su ficha** conforme a `TOL-210` y su acto sucesor 01;
4. **ejecutar pruebas técnicas posteriores a la ficha**, con fixtures propios.

**Nada más.** El benchmark, la medición de rendimiento, el uso del corpus
oficial para evaluar al candidato, los demás candidatos, los ejes `EJE-1` y
`EJE-2`, la elección de ganador y la fusión del PR quedan fuera.

## 2. Límites de la infraestructura común, congelados antes de implementar

### 2.1 Lo que la capa común **debe** contener

Puerto de acceso equivalente a `KnowledgeSearchRepository` · modelo de
petición y contexto autorizado (`B04-RF-01`) · expansión estrictamente
escalonada `E0–E5` sin saltos (`B04-RF-14`) · condiciones de insuficiencia
explícitas entre etapas (`B04-RF-16`) · puertas `G1–G12` no compensables en su
orden canónico (`B04-RF-09`) · paradas `S1–S7` con `S1` deshabilitada en
`EXHAUSTIVA` · validación de ámbito, sujeto, polaridad, condición y tiempo
(`RF-17`, `RF-19`, `G11`) · explicación por resultado (`RF-28`) · traza del
plan reproducible (`RF-29`) · borrado completo y regeneración desde el canon ·
instrumentación por etapa · semilla y comportamiento deterministas · **cero
red y cero datos reales**.

### 2.2 Lo que la capa común **no puede** contener

**Prohibido, y comprobado por prueba:**

- embeddings o cualquier representación vectorial densa;
- señal semántica vectorial de cualquier forma;
- índice relacional derivado;
- coordinación simultánea de espacios tardíos (`B04-D15`);
- **reglas especiales que solo beneficien a `ADR002-A`** —ni a `B`, `C` o `D`—.

### 2.3 La separación entre código común y código de candidato

| | Decide | No puede |
|---|---|---|
| **Común** | cuándo se ejecuta cada etapa, qué puertas se aplican, cuándo se para, qué se registra | aportar señales de recuperación propias, ni conocer qué candidato la usa |
| **Candidato** | con qué señales responde a cada etapa | controlar el bucle, saltar etapas, adelantar espacios ni alterar puertas |

**El candidato no controla el orden**: lo controla el motor común. Esa es la
razón estructural por la que ningún candidato puede saltarse `E0–E5`.

### 2.4 Neutralidad: cuatro comprobaciones fail-closed

1. la capa común **no nombra** a ningún candidato ni ramifica por identidad;
2. la capa común **no contiene** vocabulario ni dependencias de señal
   vectorial ni de índice relacional derivado;
3. **un solo camino de código** para todos los candidatos;
4. **un candidato de prueba mínimo, ajeno a `ADR002-A`, recorre el motor
   entero** — si el motor solo sirviera a A, esto fallaría.

### 2.5 Esquema de trazas minimizadas

La traza registra **identificadores, clases y decisiones**; **nunca** contenido
protegido (`B04-Q18`, no revelación). Contiene: petición efectiva, modo,
puertas aplicadas con su veredicto, etapas ejecutadas con su causa de
transición, expansiones, agrupaciones, razones por resultado, parada adjudicada
y estado de suficiencia. Una traza que revelara contenido protegido convertiría
la auditoría en canal lateral, y por eso el esquema la minimiza por
construcción.

### 2.6 Forma de registrar `E0–E5`, `G1–G12` y `S1–S7`

- **Etapas**: una entrada por etapa ejecutada, con su causa de entrada, el
  recuento de candidatos aportados y si resultó suficiente.
- **Puertas**: una entrada por puerta evaluada, con el veredicto y el motivo
  del descarte. Fallan **cerrado**: lo que no pasa una puerta no llega al
  ranking.
- **Paradas**: exactamente **una** parada adjudicada por ejecución, con su
  identificador `S1–S7` y su fundamento.

## 3. `ADR002-A`: obligaciones congeladas

Debe implementar `E0–E5` íntegramente; ejecutar `E3` con mecanismos
**léxico-estructurados concretos** —buscando paráfrasis, dependencias,
apoyo/refutación y relaciones **sin señal vectorial adicional**—; aplicar
validación explícita de sujeto, polaridad, condición y tiempo; respetar la
expansión sin saltos; registrar la causa de cada transición; aplicar
suficiencia y parada; aislar ámbitos; soportar borrado y reconstrucción de
todo derivado; producir explicaciones y trazas auditables; y **declarar
expresamente que no tiene señal tardía adicional**
(`senal_tardia.habilitada = ninguna_adicional`).

**`ADR002-A` no es `T0` ni una variante degradada** (Resolución de la
partición §3): es un candidato completo que puede resultar recomendable, y si
falla, fallará por una puerta **medida**, nunca por definición documental.

## 4. Custodia de la ejecución

1. **El prototipo no se ejecuta antes de su ficha.** En el commit del
   prototipo solo se permiten comprobaciones estáticas: formato, tipos e
   inspección estructural. Ninguna prueba instancia el candidato.
2. **La ficha se congela en un commit distinto y posterior** al prototipo, sin
   haberlo ejecutado, con la huella canónica recomputada y **sin resultados
   observados**.
3. **Toda ejecución funcional del candidato exige que el commit de entrada de
   su ficha vigente sea ancestro estricto** del commit que ejecuta.
4. **Las pruebas usan fixtures propios y pequeños**, ajenos al corpus oficial
   del benchmark. No recogen ni publican métricas de rendimiento, no ejecutan
   casos oficiales y no producen resultados utilizables como benchmark.
5. **Si una prueba obliga a modificar una fuente incluida en la huella del
   candidato**: se conserva la ficha v1, se corrige el prototipo en un commit
   nuevo, se emite **ficha v2 con motivo de sustitución** y se congela antes de
   volver a ejecutar pruebas sobre el candidato.
6. **Ningún valor de la ficha se fija después de observar un resultado.** Si
   algún campo material no pudiera fijarse honestamente sin ejecutar el
   candidato, la emisión se detiene y se eleva **esa** decisión concreta.

## 5. Fundamento de los límites que la ficha congelará

Ningún límite se inventa. Cada uno procede de una decisión aprobada, de una
medición ya aprobada o de análisis estático del prototipo:

| Límite de la ficha | Fundamento previo |
|---|---|
| Presupuesto de almacenamiento | acta de `TOL-207`: `1 610 612 736 B` |
| Consumo declarado y proyección | `ADR002-A` **no añade** índice, embedding ni estructura persistente alguna —comprobable por análisis estático—, de modo que su almacenamiento es el del canon más el FTS5 medido, ya caracterizado |
| Ciclo de índice (`tamaño`, `construcción`, `reconstrucción`, `borrado`) | mediciones del paquete 02B sobre el **mismo** FTS5, repetidas **30 veces** sobre copias limpias |
| Estabilidad (`SM`, `U50`, sesiones, regímenes) | perfil aprobado por el acta de `TOL-209` |
| Protocolo, sesiones y repeticiones | protocolo v0.2 aprobado: **11** sesiones exactas, **100** repeticiones |
| Corpus y rederivación | corpus congelado v0.4 y rederivación aprobada por el acta de `TOL-208` |
| Coste por etapa y extremo a extremo | límites **auto-impuestos** por el candidato bajo su responsabilidad, coherentes entre sí, **sin derivar de `TOL-102B`** y **sin invocar el barrido de T0** |

## 6. Lo que esta acta no autoriza

- **No autoriza ejecutar el benchmark** ni medir rendimiento del candidato.
- **No autoriza usar el corpus congelado v0.4 para evaluar `ADR002-A`.**
- No autoriza implementar `ADR002-B`, `ADR002-C` ni `ADR002-D`.
- No abre `EJE-1` ni `EJE-2`.
- No elige ganador ni adelanta ninguna recomendación de ADR-002.
- No modifica Sirius 0.1 (`src/`, `tests/`, `migrations/` ni configuración
  productiva).
- **No fusiona el PR #117.**

---

**Decisión final:** queda autorizada la implementación de la **infraestructura
común neutral** y del candidato **`ADR002-A`**, con los límites del §2
congelados **antes** de escribir código, la custodia del §4 y los fundamentos
del §5. `ADR002-A` quedará **implementado, auditable y preparado** para una
autorización posterior de ejecución del benchmark, que esta acta **no**
otorga. El PR #117 permanece abierto y sin fusionar.
