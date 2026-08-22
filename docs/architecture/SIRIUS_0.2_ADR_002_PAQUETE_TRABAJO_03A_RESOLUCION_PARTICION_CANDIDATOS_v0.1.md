# SIRIUS 0.2 — ADR-002 · Paquete de trabajo 03A

## Resolución canónica de la partición de candidatos

**Versión:** 0.1  
**Estado:** AUTORIZADO PARA CORRECCIÓN DOCUMENTAL DIRIGIDA  
**Rama:** `evidence/adr001-spikes`  
**Autoridad:** aprobación explícita del usuario en el Proyecto Sirius  
**No autoriza:** corregir o congelar el corpus, aprobar TOL-207, ejecutar T0, implementar o ejecutar candidatos, satisfacer TOL-208/TOL-209/TOL-210 ni merge.

## 1. Decisión aprobada

La partición oficial y obligatoria del benchmark principal de ADR-002 es la fijada por **ARQ-00 v1.0 APROBADO §23** como conjunto mínimo de contraste:

- **ADR002-A — léxica/estructurada:** expansión escalonada mediante señales léxicas y estructuradas en E0–E5.
- **ADR002-B — semántica vectorial tardía:** base léxica/estructurada y señal semántica vectorial únicamente en etapas tardías, tras fallar la puerta de suficiencia.
- **ADR002-C — relacional tardía:** base léxica/estructurada y señal relacional explícita únicamente en etapas tardías.
- **ADR002-D — semántica y relacional separadas:** ambas señales en etapas tardías distintas, con orden predefinido y sin coordinación simultánea fuera de la etapa autorizada.

Estas cuatro alternativas son candidatos completos. Ninguna queda degradada de antemano a mero control ni excluida como recomendación posible. La evidencia decidirá cuál supera las puertas y aporta valor material.

**T0** es únicamente la línea base de Sirius 0.1 y control de falsación. No es una quinta alternativa de arquitectura.

## 2. Interpretación correcta de B04-RF-17

B04-RF-17 obliga a ejecutar la etapa de significado y relaciones con validación explícita de sujeto, polaridad, condición y tiempo.

No obliga por sí mismo a usar embeddings, vectores, grafos ni una tecnología concreta. B04-RF-31 y la neutralidad tecnológica de B04 impiden convertir una obligación de comportamiento en una realización técnica predeterminada.

Por tanto:

- la etapa E3 es obligatoria;
- una señal vectorial no es obligatoria para todos los candidatos;
- ADR002-A y ADR002-C siguen siendo hipótesis legítimas hasta que el benchmark las falsifique o sostenga;
- ningún documento posterior puede retirar una alternativa mínima de ARQ-00 sin una decisión canónica explícita.

## 3. Tratamiento de T1–T4

La partición T1–T4 de ADR-002 v0.2 queda **SUPERADA como universo principal de candidatos**, porque sustituyó sin autoridad el eje mínimo A/B/C/D.

No se borra ni se reescribe retrospectivamente. Se conserva como historial y como análisis de dos ejes técnicos secundarios:

1. sustrato léxico FTS5 frente a sustrato alternativo;
2. relaciones resueltas desde el canon frente a índice relacional derivado.

Esos ejes solo podrán abrirse después de la comparación primaria A/B/C/D y únicamente cuando la evidencia demuestre que pueden cambiar materialmente la decisión. No se ejecuta ahora el producto cartesiano A/B/C/D × sustratos × materialización relacional.

Regla de contención:

- primera ronda: T0 + ADR002-A/B/C/D sobre el mismo sustrato léxico FTS5 y la misma infraestructura común;
- sustrato alternativo o materialización relacional alternativa: máximo dos fichas adicionales, abiertas por una puerta o fallo atribuido a ese eje;
- las ablaciones técnicas miden la aportación marginal sin multiplicar candidatos.

## 4. Artefactos afectados

No modificar ni borrar versiones históricas o aprobadas. La corrección se materializa mediante resolución y nota de superación.

Quedan afectados:

1. `SIRIUS_0.2_ADR_002_RECUPERACION_RANKING_INDICES_v0.2_ABIERTO.md`
   - retirar T1–T4 como universo oficial;
   - restaurar ADR002-A/B/C/D;
   - corregir la interpretación de RF-17.

2. `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.4_PROPUESTO.md` y su acta de aprobación
   - el contenido de TOL-210 que exige arquitectura T1–T4 queda superado únicamente en la identificación del candidato;
   - TOL-210 pasa a exigir `ADR002-A`, `ADR002-B`, `ADR002-C`, `ADR002-D` o `T0-control`;
   - el resto de TOL-210 y del Registro permanece intacto.

3. `SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.1_PROPUESTO.md` y su aprobación
   - sustituir el selector T1–T4 por ADR002-A/B/C/D y T0-control;
   - añadir señal tardía habilitada, orden de etapas y restricciones propias de D;
   - conservar todas las reglas de congelación, límites y trazabilidad.

4. `SIRIUS_0.2_ADR_002_ESPECIFICACION_BENCHMARK_v0.2_PROPUESTO.md`
   - A/B/C/D como universo principal;
   - T1–T4 como ejes técnicos contingentes.

5. Matriz e informe de preparación del corpus v0.1
   - registrar que la cuestión dejó de ser observación abierta;
   - corregir la cita literal de ADR002-B para incluir “vectorial”;
   - no corregir todavía los demás defectos del corpus detectados por auditoría.

## 5. Entregables

Crear únicamente:

1. `docs/architecture/SIRIUS_0.2_ADR_002_RESOLUCION_PARTICION_CANDIDATOS_v1.0_APROBADA.md`
2. `docs/architecture/SIRIUS_0.2_ADR_002_NOTA_SUPERACION_02_PARTICION_CANDIDATOS_v1.0_APROBADA.md`
3. `docs/architecture/SIRIUS_0.2_ADR_002_RECUPERACION_RANKING_INDICES_v0.3_ABIERTO.md`
4. `docs/architecture/SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.2_PROPUESTO.md`
5. `docs/architecture/SIRIUS_0.2_ADR_002_ESPECIFICACION_BENCHMARK_v0.3_PROPUESTO.md`

No crear fichas concretas de A/B/C/D todavía. TOL-210 seguirá sin satisfacer.

## 6. Reglas de fidelidad

- Reproducir literalmente las cuatro alternativas de ARQ-00 §23 en la resolución, incluida la palabra **vectorial** en ADR002-B.
- No afirmar que T1–T4 eran una refinación legítima del mismo eje: la auditoría demostró sustitución parcial no autorizada.
- No declarar semántica vectorial obligatoria para todos.
- No convertir A o C en controles incapaces de ser recomendados.
- No alterar el contenido material de las tolerancias aprobadas fuera de la etiqueta de arquitectura exigida por TOL-210.
- No resolver ni mencionar como aprobados TOL-207, TOL-208 o TOL-209.
- No corregir silenciosamente versiones anteriores.

## 7. Validación

Comprobar:

- resolución coherente con ARQ-00 §23, B04-RF-17, B04-RF-31 y neutralidad tecnológica;
- A/B/C/D presentes como cuatro candidatos completos;
- T0 separado como control;
- T1–T4 conservados solo como ejes contingentes;
- restricción de ADR002-D preservada;
- TOL-210 corregida por nota de superación sin reescribir el Registro aprobado;
- plantilla v0.2 no permite T1–T4 como candidatos principales;
- ningún cambio en corpus, referencias, experimentos, artefactos, fuentes canónicas, código productivo o versiones anteriores;
- sin T0, sin candidatos, sin PR nuevo y sin merge.

## 8. Publicación

Commit único:

`docs(adr002): restore canonical candidate partition`

Push a `evidence/adr001-spikes`. No abrir otro PR ni fusionar el PR #117.
