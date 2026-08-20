# Defectos encontrados en el Work Engine — parte para actuar

- **Fecha:** 2026-08-20
- **Qué es esto:** el extracto accionable de
  `docs/audits/SIRIUS_LEARNING_SEAM_AUDIT_2026-08.md`. Esa auditoría iba de otra
  cosa (integrar un diseño de aprendizaje); estos seis defectos aparecieron por
  el camino y **no tienen nada que ver con el aprendizaje**. La auditoría es la
  fuente; este documento solo los saca a un sitio donde se puedan trabajar.
- **Base verificada:** `main` = `a25ee3b`; rama de la PR #207 (A5) = `9e3a79b`.
- **Todos reproducidos ejecutando**, no leyendo. Cada uno trae su comprobación.
- **Esto no autoriza ampliar alcance.** Es un parte de defectos. Cada arreglo va
  en su rama, con su prueba vista fallar antes de arreglar (ADR-001) y su ADR si
  produce una decisión.
- **Numeración**: `H-n` son los mismos identificadores que usa §14.5 del informe,
  para que ambos documentos hablen igual. Van **ordenados por gravedad**, no por
  número. No confundir con `D-n`, que en el informe son **decisiones** del
  propietario, no defectos.

| | Hallazgo | Bloque | Gravedad |
|---|---|---|---|
| **H-3** | El corte de presupuesto revienta fuera de `ACTIVE` | A5 | Alta |
| **H-4** | Dos ADR-042: la PR #207 en rojo | A5 | Bloqueante de esa PR |
| **H-2** | «No pude leer» → «éxito vacío»; falta `UNKNOWN` | A2 | Media (latente), crítica para la evidencia futura |
| **H-1** | El cuerpo de la incidencia esquiva el filtro de confianza | A3 | Media-baja |
| **H-5** | Los fallos del proveedor git no caben en `proveedores_fallidos` | A3 | Baja |
| **H-6** | `Run.worker` no cumple arquitectura §3.3 (divergencia, no defecto) | A1 | Baja, pero conviene antes de B1/C2 |

---

## H-3 — El corte de presupuesto no funciona cuando el Worker es asíncrono

- **Bloque:** A5 · **Rama:** `feature/a5-interaccion-intencion-v0` (PR #207, abierta)
- **Gravedad:** ALTA. Es la garantía principal del bloque, y falla en el caso normal.

### Qué pasa

`registrar_gasto` (`src/sirius_engine/governance.py`), al agotarse el
presupuesto, hace dos cosas **en este orden**:

1. mata el Run vivo (`store.fail_run(...)`),
2. escala (`store.escalate_work_item(work_id, now=now)`).

Pero `escalate()` exige estado `ACTIVE` (`domain/work_item.py`). Y un Worker
asíncrono deja el WorkItem en `WAITING` — `dispatch_work_item_async`,
arquitectura §3.2 —, que es exactamente el estado en el que se gasta dinero.

Resultado: el Run queda muerto, el WorkItem sigue en `WAITING` esperando un Run
que ya no existe, **no se emite escalada, no se notifica**, y el `Budget`
actualizado se pierde con la excepción (el llamador no recibe `ResultadoGasto`).

Lo mismo ocurre desde `PAUSED`, `NEEDS_DECISION`, `FAILED_SAFELY`, `DELIVERED` y
`CANCELLED`: cualquier estado que no sea `ACTIVE`.

### Comprobación (reproducible)

```python
# en un worktree de feature/a5-interaccion-intencion-v0, con `uv run python`
from datetime import datetime, timedelta, timezone
from sirius_engine.adapters.memory_store import InMemoryWorkEngineStore
from sirius_engine.domain.work_item import WorkItemClass
from sirius_engine.domain.budget import Budget
from sirius_engine.governance import registrar_gasto

now = datetime(2026, 8, 19, tzinfo=timezone.utc)
s = InMemoryWorkEngineStore()
s.create_work_item(work_id="WI-1", peticion_original="x", objetivo="x", contexto_origen=(),
    entregable="x", criterio_terminado="x", limites={"presupuesto": {"limite": 10.0}},
    prioridad=1, clase=WorkItemClass.INVESTIGACION, now=now)
s.activate_work_item("WI-1", now=now)
s.prepare_run(run_id="R-1", work_id="WI-1", paso="p1", worker="worker-externo",
    work_package={}, deadline=now + timedelta(hours=1), now=now)
s.dispatch_run("R-1", now=now)
s.confirm_run_running("R-1", now=now)
s.dispatch_work_item_async("WI-1", now=now)          # ACTIVE -> WAITING
registrar_gasto(s, work_id="WI-1", presupuesto=Budget(limite=10.0), coste=11.0,
                now=now, run_id="R-1")
```

Salida observada:

```
WorkItem mientras el Worker externo corre: waiting
EXCEPCION: IllegalTransitionError - cannot escalate WorkItem while in state WAITING
  Run tras la excepcion     : finished failed
  WorkItem tras la excepcion: waiting
  Escalada emitida          : NINGUNA
  Presupuesto actualizado   : PERDIDO
```

### Por qué sobrevivió

`tests/engine/test_governance.py` tiene cuatro pruebas
(`test_gasto_que_no_agota_no_corta_nada`,
`test_agotar_el_presupuesto_corta_el_run_y_escala_con_notificacion`,
`test_agotar_por_encima_del_limite_tambien_corta`,
`test_fallo_tecnico_corregible_nunca_escala`) y **las cuatro parten de `ACTIVE`**.
Ninguna pasa por `WAITING`. `grep -n "WAITING\|dispatch_work_item_async"` sobre
ese fichero no devuelve nada.

### Qué tiene que satisfacer el arreglo

No propongo la solución —es decisión de quien lleva A5—, pero sí lo que hay que
cumplir, porque son propiedades ya aprobadas:

1. **Agotar el presupuesto tiene que cortar y escalar desde cualquier estado no
   terminal**, no solo desde `ACTIVE`. La arquitectura §10 dice que agotar el
   presupuesto del WorkItem es causa 2 de `NEEDS_DECISION`, sin condicionarlo al
   estado.
2. **No dejar estado inconsistente.** Hoy mata el Run y luego revienta. Sea cual
   sea la solución, no puede quedar un WorkItem en `WAITING` sin Run vivo.
3. **El `Budget` actualizado nunca se pierde.** El docstring ya lo promete: «el
   nuevo valor, ya con el gasto aplicado, se devuelve siempre en
   `ResultadoGasto.presupuesto`, tanto si corta como si no». Hoy esa promesa se
   rompe por la excepción.
4. **Decidir explícitamente qué pasa en estado terminal.** Un coste que llega
   tarde, después de `DELIVERED`, no puede escalar un trabajo ya entregado; pero
   tampoco debería reventar. Registrarlo sin escalar es una opción; hay otras.
   Sea cual sea, es una decisión y va a un ADR.
5. **Prueba vista fallar antes de arreglar** (ADR-001): una prueba por cada
   estado no terminal, sembrada contra el código actual.

---

## H-4 — Dos ADR-042: la PR #207 está en rojo

- **Bloque:** A5 · **Rama:** `feature/a5-interaccion-intencion-v0`
- **Gravedad:** BLOQUEANTE de esa PR (explica su `mergeable_state: unstable`).

La rama añade `ADR-042-gobierno-previo-al-primer-worker-externo-…md` mientras
`main` ya tiene `ADR-042-un-paso-de-preparacion-sin-plazo-propio-…md`.

```
$ uv run pytest tests/automation/test_registro_de_decisiones.py -q
FAILED test_no_new_number_is_ever_reused
  {42: ['ADR-042-gobierno-previo-al-primer-worker-externo-…md',
        'ADR-042-un-paso-de-preparacion-sin-plazo-propio-…md']}
1 failed, 3 passed
```

Es la familia exacta que ADR-032 describió: dos ramas leen el mismo listado y
eligen el mismo número. La prueba está haciendo su trabajo.

**Arreglo:** renumerar el ADR de A5 al **siguiente número válido en `main` en el
momento de corregirlo**, calculado con `uv run python scripts/siguiente_adr.py
--solo-numero` **contra `main`**. Hay que actualizar también las referencias
cruzadas al «ADR-042» que apunten al de A5 (el cuerpo de la PR #207 y el propio
ADR lo citan).

**No consultes ninguna rama exploratoria para elegir el número.** En particular,
la rama `claude/sirius-learning-audit-ixtr0g` (auditoría de aprendizaje) no está
aprobada y **no reserva numeración**: A5 es trabajo del Work Engine ya
autorizado y tiene prioridad. Si esa rama llega a integrarse, será ella la que
recalcule su propio número.

---

## H-2 — «No pude leer el resultado» se convierte en «éxito con resultado vacío»

- **Bloque:** A2 · **Rama:** `main`
- **Gravedad:** MEDIA hoy (latente), ALTA cuando llegue el observador real de C1.

`src/sirius_engine/recovery.py:93-95`:

```python
store.succeed_run(live.run_id, resultado=observation.resultado or {}, now=now)
```

Si el mundo reportó `SUCCEEDED` pero no se pudo leer el resultado, el Run se
cierra como **éxito con resultado vacío**. Y el puerto no ofrece forma de decir
«no pude observar»: `RemoteRunStatus` (`src/sirius_engine/ports/world.py:23-33`)
enumera `PENDING`, `SUCCEEDED`, `FAILED`, `LOST`, `CANCELLED` — **no hay
`UNKNOWN`**.

Es la familia que **ADR-036 ya cerró para el espejo** («una lectura caída no es
una ausencia»), reaparecida en el barrido de recuperación, que es el único camino
por el que el resultado real de un Worker llega al diario.

Hoy es latente porque la única implementación de `RunWorldObserver` es un doble
de pruebas (el propio módulo lo dice: «en A2, su única implementación es un doble
de pruebas»). Por eso es barato ahora y caro después.

**Qué tiene que satisfacer el arreglo:** un desenlace observado sin resultado
legible no puede cerrarse como `SUCCEEDED`; y el puerto tiene que poder expresar
«no pude observar» distinguiéndolo de `PENDING`.

---

## H-1 — El cuerpo de la incidencia esquiva el filtro de confianza

- **Bloque:** A3 · **Rama:** `main`
- **Gravedad:** MEDIA-BAJA en la práctica, pero la función afirma algo falso.

`src/sirius_engine/mirror_projection.py:188-197`, función
`_texto_cronologico_de_confianza`: filtra los comentarios con
`es_autor_de_confianza` y después concatena el **cuerpo sin filtrar**:

```python
de_confianza = [c.cuerpo for c in comentarios if es_autor_de_confianza(c)]
return "\n".join((*de_confianza, cuerpo))
```

Y no se puede arreglar sin tocar el puerto: `LecturaCuerpo`
(`src/sirius_engine/ports/github_mirror.py:61-65`) tiene `estado`, `cuerpo` y
`error`, y **ningún campo de autor**.

Ese texto alimenta `sirius_convergence.parse_round_records` y la racha de fallos
de CI, o sea: gobierna la numeración de rondas.

**Alcance real, comprobado:** nada de la automatización escribe el cuerpo de una
incidencia — `grep` sobre `scripts/automation/` y `.github/workflows/` solo
devuelve `issue edit --add-label/--remove-label` y `issue comment`. El cuerpo lo
escribe el propietario, o ChatGPT al redactar el work item (contrato §0). Así que
el vector es acotado. Lo que no es acotado es que el nombre de la función promete
una propiedad que la función no tiene.

**Arreglo:** o el puerto transporta el autor del cuerpo y la función lo filtra, o
la función deja de llamarse «de confianza» y el llamador sabe lo que recibe.

---

## H-5 — Un tercio de `contexto.recuperar` no puede reportar su fallo

- **Bloque:** A3 · **Rama:** `main` · **Gravedad:** BAJA

`src/sirius_engine/context_recall.py:262`:

```python
proveedores_fallidos=fallidas_arbol + fallidas_incidencias,
```

El tercer proveedor (historial de git) no cabe ahí por construcción:
`buscar_en_historial_git` devuelve solo referencias, y el fallo de lectura vive
antes, en `leer_historial_git`, que lanza `EspejoIlegibleError` hacia quien
construya las entradas. Quien reciba un `ContextoRecuperado` no puede distinguir
«git no tenía nada» de «git no se pudo leer».

El patrón de ADR-036 está cerrado en dos de tres proveedores.

---

## H-6 (GAP-1) — `Run.worker` no cumple la arquitectura §3.3

- **Bloque:** A1 (arrastrado por A2 y A4) · **Rama:** `main`
- **Gravedad:** BAJA hoy. No urge, pero conviene cerrarlo antes de B1/C2.

La arquitectura §3.3 define el campo como «adapter + perfil + (si aplica)
**modelo/runtime concretos usados**». El código tiene
`worker: str` (`src/sirius_engine/domain/run.py:71`): una cadena libre, sin
estructura ni registro. En las pruebas es literalmente `"claude-code"`.

Tampoco lo llevan el `AgentProfile` (`domain/profile.py:36-48`) ni el
`WorkerRequest` (`worker_request.py:45-54`), que sí lleva `perfil_ref` y
`perfil_version`.

Consecuencia: el motor **no puede** comparar dos Runs por modelo, ni explicar por
qué se sustituyó un Worker en términos de con qué se ejecutó, ni sostener ninguna
afirmación sobre qué modelo hizo qué.

**Momento natural de arreglarlo:** cuando exista el primer Worker real (B1 o C2),
que es cuando el dato nace. Antes no hay nada que registrar.

---

## Lo que NO es un defecto

Para no perder tiempo con ello:

- **La maquinaria de A4 no la ejecuta ningún camino de producción.**
  `project_worker_request` (`src/sirius_engine/worker_request.py:57`) encadena el
  cálculo del envelope, la validación de egress y la resolución de capacidades
  (`:65-67`), pero **nadie llama a esa proyección** fuera de las pruebas. Es
  **correcto**: el plan dice que A4 «entrega la proyección, el campo y las
  pruebas» y sitúa el cableado en C2/C3. Lo único que hay que cuidar es no
  afirmar «el egress es imposible de saltar» del sistema en marcha: hoy lo es del
  camino de código, no de lo que corre.


- **El checksum del diario no lleva clave.** Protege contra corrupción del medio,
  que es su amenaza declarada. Contra manipulación no protege, pero ADR-012 ya
  decidió que un proceso local está dentro de la frontera de confianza.
- **`src/sirius` (Sirius 0.1).** Revisado a fondo el dominio de memoria,
  decisiones y precedencia de V4. No encontré nada.
