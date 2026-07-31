# SIRIUS 0.2 — ADR-002 · Paquete de trabajo 10 · `ADR002-TOL-208` pasos 2 y 3 · rederivación de T0

**Versión:** 0.1
**Estado:** **PROPUESTO · PREPARADO, NO EJECUTADO** — no aprueba ninguna puerta y no autoriza ninguna medición
**Fecha:** 31 de julio de 2026
**Rama:** `evidence/adr001-spikes`
**Commit de partida:** `9507f96` — acta de aprobación de `ADR002-TOL-210`
**Puerta que trabaja:** `ADR002-TOL-208`, pasos 2 y 3
**Protocolo aplicable:** `SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.2_PROPUESTO.md`
**No autoriza:** **ejecutar T0**, ninguna medición, implementar o ejecutar candidatos, el benchmark, ni fusionar el PR #117.

---

## 1. Qué queda de las cinco puertas

`ADR002-TOL-208` fija una regla de arranque en tres pasos, **en ese orden**:

| Paso | Estado |
|---|---|
| 1. congelar el corpus definitivo del benchmark | **COMPLETADO** — corpus v0.4 congelado por su acta |
| 2. **ejecutar T0** sobre ese mismo corpus | pendiente |
| 3. **rederivar** la comparación de línea base | pendiente |

Con `SRC-ADR002-01`, `TOL-207`, `TOL-209` y `TOL-210` satisfechas, **los pasos 2 y 3 son lo único que queda** de las cinco puertas de arranque.

Este paquete los deja **preinscritos y ejecutables**, sin ejecutarlos.

## 2. Por qué hay que rederivar y no reutilizar

La línea base histórica se midió sobre el corpus 5.000/500 con **cinco** sesiones. Las cifras vigentes de `TOL-107` exigen **once**, y la regla 5 declara `NO_COMPARABLE` cualquier rango obtenido con otro número: `(máx − mín)` es un rango y la esperanza de un rango crece con el tamaño de la muestra.

De ahí que el perfil aprobado por `TOL-209` **no pueda pronunciarse** sobre FTS5 ni sobre `rank()`. Rederivar no es repetir por gusto: **es la única vía para que la línea base vuelva a ser comparable**, y es exactamente lo que el paso 3 ordena.

**La línea base histórica no se remide ni se sustituye.** Permanece congelada con su head y sus ficheros. Lo que se producirá es una medición **nueva** sobre el corpus definitivo, publicada aparte. El esquema lo hace cumplir: `linea_base_historica.sustituida` debe ser `False`.

## 3. La guarda de autorización

Ejecutar T0 requiere **autorización expresa e independiente**, y ninguna acta la ha dado. El recorrido lo comprueba **contra el repositorio**:

```text
$ uv run python -m experiments.adr002.rederivation.run_rederivation --check
la rederivacion de T0 NO puede ejecutarse. Falta:
  - ejecutar_t0_no_esta_autorizado: falta SIRIUS_0.2_ADR_002_TOL_208_AUTORIZACION_T0_v1.0.md.
    Ejecutar T0 exige autorizacion expresa e independiente, y ninguna acta la ha dado
  - t0_no_tiene_ficha_congelada: T0-control no tiene ficha CONGELADA; una ejecucion sin
    ficha previa no es utilizable como evidencia (TOL-210)

Ejecutar T0 exige autorizacion expresa e independiente.
```

**La autorización no es una bandera de línea de órdenes.** El parser solo admite `--plan` y `--check`; no existe `--execute` ni equivalente. La autorización es un **documento del repositorio** que existe o no existe, y una prueba comprueba que el parser no ofrece ninguna otra puerta.

Las precondiciones **no cortocircuitan**: quien prepare la ejecución ve de una vez todo lo que le falta, en vez de descubrirlo de uno en uno.

## 4. El plan preinscrito

| Concepto | Valor |
|---|---|
| Candidato | `T0-control` · head de Alembic `61be4bb269bf` |
| Corpus | v0.4 congelado, citado **por blob** |
| Escenarios | `cero_resultados` · `un_resultado_exacto` · `muchos_candidatos` |
| Capas | `solo_indice_fts5` · `recuperacion_completa_rank` |
| Magnitudes | **6** (escenario × capa) |
| Sesiones | **exactamente 11** |
| Repeticiones por magnitud | **100** (§3.2 del protocolo; mínimo 30) |
| Percentiles | nearest-rank, nunca interpolados |
| Salida prevista | `artifacts/adr002_tolerances/rederivacion_t0_v0.1.json` |

**Los escenarios y las capas se conservan idénticos a los de la línea base histórica.** Rederivar debe medir *lo mismo* con otro tamaño de muestra; medir otra cosa con el mismo nombre no sería una rederivación.

**Lo que cambia es el tamaño de muestra, no el criterio.** Los veredictos se delegan enteramente en el perfil aprobado de `TOL-209`: la rederivación **no inventa criterio propio**. Una prueba lo comprueba llamando a las dos vías y exigiendo el mismo resultado.

## 5. El esquema, congelado antes de que exista la medición

`schema_rederivation_v0_1` se congela **ahora**, que es lo que impide ajustarlo después de ver los resultados. Exige:

- las **seis magnitudes**, en orden, sin faltar ni sobrar ninguna;
- **once** valores por percentil y magnitud, enteros de nanosegundos;
- mínimos y máximos **recomputados** desde los valores por sesión;
- el veredicto **recomputado** con el perfil aprobado, no aceptado como viene;
- que ninguna magnitud siga siendo `NO_COMPARABLE` —si lo fuera, la rederivación no habría cumplido su propósito—;
- el corpus citado **por blob** y la línea base histórica **no sustituida**;
- todos los conjuntos de campos **cerrados**.

Es **total por contrato**: nunca lanza.

## 6. Once controles bloqueantes

Fallan **cerrado**: un control ausente o distinto de `True` es fallido.

`autorizacion_expresa_presente` · `actas_de_puerta_presentes` · `corpus_congelado_intacto` · `linea_base_historica_intacta` · `ficha_de_t0_congelada_y_anterior` · `once_sesiones_completas` · `repeticiones_suficientes` · `percentiles_por_rango_mas_cercano` · `escenarios_y_capas_identicos_a_la_linea_base` · `veredictos_delegados_al_perfil_aprobado` · `sin_sustituir_la_linea_base_historica`

## 7. Lo que este paquete NO hace

1. **No ejecuta T0** ni ninguna medición. Una prueba comprueba que ningún módulo del paquete menciona `perf_counter`, `sqlite3`, `time.time` ni `multiprocessing`.
2. **No escribe nada.** El artefacto previsto no existe, y una prueba lo comprueba.
3. **No satisface `ADR002-TOL-208`.** La satisfará su acta, tras la ejecución autorizada.
4. **No sustituye la línea base histórica.**
5. **No implementa candidatos**, no inicia el benchmark, no fusiona el PR #117.

## 8. El bloqueo real: la ficha de `T0-control`

El recorrido reporta **dos** bloqueos, no uno. El segundo es sustantivo y merece registrarse:

> `T0-control` **no tiene ficha congelada**, y `ADR002-TOL-210` exige que toda ejecución referencie una ficha previa para ser utilizable como evidencia.

**Esa ficha no puede derivarse hoy de las decisiones existentes.** Se comprobó campo a campo contra el contrato aprobado:

| Campo exigido | Estado para `T0-control` |
|---|---|
| `arquitectura.etapas_implementadas` (E0–E5) | **inaplicable**: la Resolución de la partición §3 declara que T0 **no implementa E0–E5** |
| `coste_por_etapa` (seis etapas con límites enteros) | **no existe** ninguna decisión que los congele para T0 |
| `extremo_a_extremo` (objetivo P95 y límite duro P99) | **no existe**: el Registro declara que T0 «no es un presupuesto heredable» y que **no se descarta por superar el tiempo de T0** |
| `almacenamiento.consumo_declarado_b` | **sería una medición de T0**, que este paquete no autoriza |
| `ciclo_de_indice` (cuatro límites) | **no existe** decisión que los congele para T0 |

Rellenarlos exigiría **medir T0** —prohibido— o **inventarlos** —lo que la regla 1 del §9 del Registro prohíbe expresamente: «ningún valor se fija después de observar el resultado», y con más razón sin observar nada—.

**Por eso este paquete no emite la ficha de `T0-control`.** Fabricarla con números sin respaldo habría sido exactamente el fraude que todo el aparato de congelación existe para impedir.

### 8.1 La decisión de gobierno que esto abre

El contrato de `TOL-210` exige al **control** lo mismo que a un **candidato**, y el control no puede darlo. Hay dos salidas y **ninguna es mía**:

- **(a)** el contrato **exime al control** de los campos que solo tienen sentido para un candidato, exigiéndole en su lugar declarar **por qué** no aplican —coherente con la regla 3 del propio contrato, «si un valor no puede declararse, se declara por qué»—;
- **(b)** la ficha de `T0-control` se congela **después** de la rederivación, con los valores que esta produzca, lo que invierte el orden que TOL-210 exige y habría que justificar.

Cualquiera de las dos es una **modificación del contrato aprobado** y exige un **acto sucesor**, conforme a la regla de custodia §8.5 del acta de `ADR002-TOL-210`.

---

## 9. Estado de las puertas al cerrar este paquete

| Puerta | Estado |
|---|---|
| `SRC-ADR002-01` | **SATISFECHA** |
| `ADR002-TOL-207` | **SATISFECHA** |
| `ADR002-TOL-209` | **SATISFECHA** |
| `ADR002-TOL-210` | **SATISFECHA** |
| `ADR002-TOL-208` · paso 1 | **COMPLETADO** |
| `ADR002-TOL-208` · pasos 2 y 3 | **NO SATISFECHOS** — preparados y bloqueados por autorización |

**El benchmark continúa bloqueado.**

---

**Siguiente movimiento único:** que el usuario resuelva la decisión del §8.1 sobre la ficha de `T0-control` y, si procede, **autorice expresamente la ejecución de T0** mediante el acta `SIRIUS_0.2_ADR_002_TOL_208_AUTORIZACION_T0_v1.0.md`. Con esas dos cosas —y solo con ellas— el recorrido de este paquete deja de estar bloqueado.
