# SIRIUS 0.2 — ADR-002 · Aprobación de `ADR002-D` v2 como PREPARADO PARA BENCHMARK

**Versión:** 1.0
**Estado:** **APROBADO · `ADR002-D` v2 PREPARADO PARA BENCHMARK**
**Fecha:** 7 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**
**HEAD aprobado:** `9677e4d9392f60f777d310fc1c98f1585d25ce18`

**Autoridad:** paso **9** del plan aprobado por
`..._RESOLUCION_PREBENCHMARK_..._v1.0_APROBADA.md` §4 — «implementar, congelar
y probar `ADR002-D`».

**Acto de aprobación:** el usuario, directamente en el chat de trabajo:

> «Sí, apruebo explícitamente ADR002-D v2, huella
> `7cc6ccc9afab331322cc45da17215def2566beae`, sobre el HEAD
> `9677e4d9392f60f777d310fc1c98f1585d25ce18`.»

Con esta acta, **las cuatro alternativas mínimas de `ARQ-00 §23` y el control
de falsación quedan preparados**. La ronda primaria tiene sus cinco
participantes.

---

## 1. Lo aprobado

| Ficha | Estado | Huella canónica | Sustituye a |
|---|---|---|---|
| `ficha_ADR002-D_v2.json` | **CONGELADA · PREPARADO PARA BENCHMARK** | `7cc6ccc9afab331322cc45da17215def2566beae` | v1 |

---

## 2. Lo que `ADR002-D` es, y por qué su orden es el que es

`ADR002-D` = base léxico-estructurada de `ADR002-A` **más las dos señales
tardías, en dos etapas distintas**:

| Puesto | Etapa | Señal | De dónde viene |
|---|---|---|---|
| 1.º | **`E3`** | `relacional_explicita` | la fuente de `ADR002-C` vigente (v2) |
| 2.º | **`E4`** | `semantica_vectorial` | el lector de `ADR002-B` vigente (v7) |

**El orden no se eligió: se derivó del canon**, y se congeló por
`SIRIUS_0.2_ADR_002_ORDEN_CONGELADO_DE_LAS_ETAPAS_TARDIAS_DE_ADR002_D_v1.0.md`
en un commit **anterior** al de la implementación y al de la ficha. Tres reglas
aprobadas apuntan en el mismo sentido:

1. `B04 §15.1` nombra las **relaciones** ya en `E1`, la etapa de máxima
   autoridad, y describe `E4` como **fallback controlado**;
2. el desempate del motor común es `ETAPAS_DE_EXPANSION.index(etapa)`, de modo
   que `E3` es **más autoritativa** que `E4`;
3. `B04 §15` y `RF-14` obligan a empezar por el espacio más autorizado y a
   ampliar sólo por insuficiencia.

Una arista nombrada es evidencia declarada; una similitud distribucional es una
conjetura de forma. Ponerlas al revés colocaría la conjetura por encima de la
evidencia.

**Partir `E3` en dos subpasos quedó descartado** porque `B04 CA-43` llama a eso
**coordinación intra-etapa**, que es exactamente lo que esta alternativa existe
para evitar (Resolución de la partición §7).

---

## 3. Las tres restricciones acumulativas, satisfechas de forma estructural

| # | Restricción | Cómo se cumple, y cómo se comprueba |
|---|---|---|
| 1 | Señales en **etapas distintas** | un único despachador lee una tabla **inmutable** derivada del orden congelado; una etapa tiene a lo sumo una señal. `test_una_etapa_no_puede_alojar_dos_senales_tardias`, `test_la_tabla_de_despacho_no_se_puede_modificar` |
| 2 | Orden **predefinido antes de ejecutar** | el acta que lo congela es ancestro **estricto** de la implementación y de la ficha, comprobado contra el grafo de Git. `test_el_orden_se_congelo_antes_que_la_implementacion`, `..._antes_que_la_ficha` |
| 3 | **Nunca** coordinación simultánea | guardia de reentrada, y el orden se valida **antes** de que la señal actúe: una señal prohibida no llega a abrir su fuente. `test_dos_senales_activas_a_la_vez_fallan_cerrado`, `test_la_senal_prohibida_no_llega_a_actuar_antes_de_abortar` |

Cada ejecución acumula su propio orden observado, que debe ser **subsecuencia**
del congelado. Subsecuencia y no igualdad porque una señal puede faltar por dos
razones legítimas —la política escalonada paró antes, o una ablación la
apagó— y ninguna reordena nada.

---

## 4. El doble discriminante, y las tres ablaciones

Sobre el mismo fixture y la misma petición:

| Candidato | Objetivo sólo relacional | Objetivo sólo vectorial |
|---|---|---|
| `ADR002-A` | no | no |
| `ADR002-B` | no | sí, en `E3` |
| `ADR002-C` | sí, en `E3` | no |
| **`ADR002-D`** | **sí, en `E3`** | **sí, en `E4`** |

Esa última fila es `ADR002-D` y ninguna otra cosa. Y las ablaciones lo cierran
por el otro lado: **sin relacional `D` entrega lo mismo que `B`; sin vectorial,
lo mismo que `C`; sin ninguna, lo mismo que `A`** — y apagar una señal **no
mueve** la otra de etapa.

---

## 5. Por qué hubo dos versiones y no una

La `v1` se presentó a aprobación y **la revisión independiente encontró dos
defectos reales del coordinador**, los dos **reproducidos antes de corregirlos**:

| # | Defecto | Consecuencia |
|---|---|---|
| **1** | El orden observado se acumulaba durante toda la vida del objeto | reutilizar la misma instancia **abortaba la segunda recuperación**. El protocolo exige **100 repeticiones por magnitud**: habría roto el benchmark entero |
| **2** | La tabla de despacho era un `dict`, y `Final` sólo prohíbe reasignar el nombre | escribir la señal vectorial en `E3` bastaba para que el despachador la ejecutase allí, y la comprobación de orden llegaba con el sidecar ya abierto y consultado |

La corrección hace tres cosas: el orden observado pasa a tener **alcance de
ronda**; la tabla pasa a ser **inmutable**; y el orden se comprueba **antes** de
ejecutar la señal. Para una restricción que existe para que una señal no actúe
fuera de su etapa, abortar tarde es no cumplirla.

**La `v2` declara exactamente la misma semántica que la `v1`**: mismas dos
señales, mismas dos etapas, mismo orden congelado, mismas cotas y mismos
límites. La `v1` queda `SUSTITUIDA` —huella `0ca203f07ebc550a4e37f956f92aa1723f927572`—
conservada y no reescrita; nunca llegó a aprobarse.

---

## 6. Identidad vinculante, resuelta desde Git en el HEAD aprobado

| Artefacto | Hash |
|---|---|
| `artifacts/adr002_cards/ficha_ADR002-D_v2.json` | blob `b9078aad22489e28e07b54a95e49a3575d6c54f7` |
| `artifacts/adr002_cards/ficha_ADR002-D_v1.json` | blob `41bc882ff0db57d2f9a11ebe9ce4930b4d1711f7` |
| `experiments/adr002/candidates/adr002_d/candidate.py` | blob `04ac68eff9d491f0d7d694d1451c8f92788ad54f` |
| `experiments/adr002/candidates/fixtures_d.py` | blob `0e6ebbb2358226219d8ac5f4d5d6896a097b1ace` |
| `experiments/adr002/candidates/adr002_d` | árbol `066c18b607cc58c3ed2d0cc278decfd65bd2219a` |
| `experiments/adr002/candidates/adr002_a` | árbol `ceb4247c9fee913ae86d5203f199b19341f1c833` — **sin cambios** |
| `experiments/adr002/candidates/adr002_b` | árbol `43eaa374d6eef827599472588a54494be9704565` — **sin cambios** |
| `experiments/adr002/candidates/adr002_c` | árbol `6767fb9f3bc276fe0361174c300634dc0cef4860` — **sin cambios** |
| `experiments/adr002/candidates/common` | árbol `30984c1f054fc47b12f708fad23ddf617a46645c` — **sin cambios** |
| `migrations` | árbol `98ef8ac794f6996c14f82c08ccb4f2cfa83ab9e1` — **idéntico al del commit del prototipo de `T0`** |

**`A`, `B`, `C` y la capa común siguen byte a byte donde sus fichas los sitúan.**
`ADR002-D` no los tocó: los usa.

---

## 7. Evidencia de verificación

| Comprobación | Resultado |
|---|---|
| Suite experimental completa | **1 742 pruebas en verde** |
| Suite propia de `D` | **72** funcionales + **22** de coherencia ficha↔código |
| `verify_cards --check` | 17 fichas conformes · una `CONGELADA` por candidato · **14/14** controles bloqueantes |
| Recomputación de todas las huellas | coinciden con las declaradas |
| Ruff format, Ruff lint, mypy | conformes |
| **Quality** sobre `9677e4d` | **success** |
| **Revisión independiente (Codex)** | 2.ª ronda sobre `9677e4d939`: **sin hallazgos** |

### 7.1 Sobre la revisión independiente

La 1.ª ronda encontró los dos defectos del §5 y **los dos eran reales**. Se
reprodujeron, se corrigieron, se fijaron con pruebas de regresión y se relanzó
la revisión, que vino limpia. Se deja constancia porque una revisión que no
encuentra nada sólo vale si antes encontró algo.

---

## 8. Limitaciones conocidas aceptadas como NO bloqueantes

1. **`adr002_d` reescribe los cuerpos de las dos señales** en vez de importar
   métodos privados de `adr002_b` y `adr002_c`, porque esos árboles están
   congelados y tocarlos exigiría fichas sucesoras que la reaprobación conjunta
   prohíbe. La garantía de que la reescritura no las alteró es una **igualdad
   ítem a ítem comprobada**, no una promesa; pero si `B` o `C` se corrigieran,
   `D` no les seguiría solo.
2. **`E4` aporta en `D` elementos canónicos** y no sólo evidencia atribuida,
   porque la señal vectorial materializa por identidad exacta. Una recuperación
   que llegue a `E4` puede dejar de ser `SOLO_HISTORICO`.
3. **La misma señal vectorial rankea después en `D` que en `B`**, por la escala
   de autoridad del motor. Es el coste real de la separación, comprobado.
4. **`D` abre dos conexiones y sólo las cierra con `cerrar()` explícito**, igual
   que `C`.
5. Las limitaciones abiertas de la capa común, de `A`, de `B` y de `C`, que `D`
   hereda por composición, siguen siendo las de sus propias actas.

Estas limitaciones **no se declaran resueltas**, **no se aprueban como
decisiones productivas**, **deben permanecer visibles durante la ronda
primaria** y **pueden convertir al candidato en fallo o en NO EVALUABLE** si
afectan a la ejecución.

---

## 9. Estado de gobierno tras esta acta

| Elemento | Estado |
|---|---|
| `T0-control v1` | **CONGELADA**, intacta — identidad canónica y superficie ejecutada byte a byte (fe de erratas 07) |
| `ADR002-A v5` | **PREPARADO PARA BENCHMARK** |
| `ADR002-B v7` | **PREPARADO PARA BENCHMARK** |
| `ADR002-C v2` | **PREPARADO PARA BENCHMARK** |
| **`ADR002-D v2`** | **PREPARADO PARA BENCHMARK** — por esta acta |
| `ADR002-D v1` | **SUSTITUIDA**, conservada |
| Ronda primaria | `T0 + A + B + C + D`: **los cinco participantes, preparados** |
| Benchmark | **BLOQUEADO, NO AUTORIZADO y NO EJECUTADO** |
| Ganador | **NO ELEGIDO** |
| Sirius 0.1 | **NO MODIFICADO por ADR-002** |
| PR #117 | **ABIERTO y SIN FUSIONAR**; `main` no se toca |

---

## 10. Lo que esta acta no autoriza

- **No** autoriza ejecutar el benchmark, usar el corpus oficial ni medir
  rendimiento de ningún candidato.
- **No** autoriza ejecutar `ADR002-D` aisladamente.
- **No** elige ganador ni declara arquitectura final o productiva; en
  particular, **no aprueba** embeddings, proveedor, almacenamiento ni grafo de
  relaciones para producción.
- **No** modifica Sirius 0.1, `T0-control`, la capa común, `ADR002-A`,
  `ADR002-B` ni `ADR002-C`.
- **No** fusiona el PR #117.

**La autorización de la ronda primaria es un acto de gobierno distinto,
posterior y conjunto para los cinco participantes. Hoy no existe.**
