# ADR-207 — Archivar los dos mapas caducados de julio, retirar el workflow de Word y poner en D4 el estado que ya tenía

- Estado: APROBADO
- Fecha: 2026-09-20
- Aprobación: el propietario, el 20-09-2026, decisión por decisión. La 3 y la 6
  con sus palabras; la 1 delegada en la sesión («haz lo que tú creas»), que es
  lo que ADR-204 acaba de fijar.
- Nota de arranque: la de ADR-204, que cubre esta tanda entera.

## Contexto y problema

Tres de las diez decisiones que la auditoría de la forma de trabajar puso
delante del propietario. Las tres son de la misma familia —`pieza-sin-lector`:
algo escrito que ya no describe nada y que nadie mantiene— y por eso van en un
solo ADR en vez de tres.

## Criterio de parada (escrito ANTES de decidir)

Si alguna de las tres piezas resultara tener un lector vivo —una prueba, un
workflow o un ADR que dependa de ella—, no se archiva sin resolver antes ese
lector. Se comprueba buscando quién la cita antes de tocar nada.

## Decisión

### 1. Los dos mapas de julio quedan derogados en su sitio

`docs/operations/CLAUDE_SIRIUS_KNOWLEDGE_BASE.md` y
`docs/operations/CLAUDE_PROJECT_ONBOARDING.md` son fotos del 20-07-2026. El
primero dice que el contrato operativo va por la v1.1 cuando va por la v1.11, y
el trabajo de los dos lo hace hoy `MEMORIA.md`, que se genera del árbol y no
puede quedarse atrás.

Cada uno gana arriba un aviso de que está derogado, qué lo sustituye y por qué
se conserva. **No se mueven y no se borran**, que es lo que ADR-195 dice que
significa archivar un documento: *«dejarlo donde está y marcar en él qué lo
deroga»*.

Y una consecuencia que no es cosmética: la base de conocimiento **sale** de
`DOCUMENTS_STATING_CURRENT_POLICY` en `tests/automation/test_sirius_convergence.py`.
Un documento archivado no debe mantenerse al día; exigirle la política vigente
obligaría a actualizar para siempre una foto de julio, que es justo lo
contrario de archivar.

### 2. El workflow que fabrica los Word queda retirado

Decisión del propietario: *«eso de que cree Word no me convence, yo quiero
documentos fáciles de editar, ni uno fijo»*.

`.github/workflows/materialize-approved-docx.yml` convertía dos documentos a
`.docx` en cada push y los volvía a confirmar. Los originales en Markdown ya
están en el repositorio y son los editables. **Se queda sin disparador
automático**: solo `workflow_dispatch`, para que una persona pueda lanzarlo a
mano el día que necesite un `.docx` suelto. El fichero no se borra.

**Lo que esta decisión NO toca:** los ocho documentos `.docx` de
`docs/canonical/`, que siguen siendo la fuente canónica aprobada. Pasarlos a
Markdown es una decisión mucho mayor —tocaría la aceptación de Sirius 0.1 y lo
que `STATUS.md` declara aprobado— y es **cambio de producto**, así que por
ADR-204 la decide él, no esta sesión. Queda nombrada, no tomada.

### 3. La línea de D4 dice lo que ya estaba decidido

`docs/implementation/bloques_del_motor.yml` decía de D4, «partir un objetivo
grande en bloques», que el descomponedor automático quedaba *«APLAZADO, no
descartado»*, citando ADR-089. **ADR-198, del 14-09-2026, lo descartó** con la
razón escrita: decidir un reparto exige un modelo y el motor no ejecuta
ninguno, que es la premisa de ADR-082.

La línea pasa a decir eso, y el bloque pasa de `pendiente` a
`fuera_de_alcance`: el trabajo se hace —lo hace la sesión interactiva— pero no
lo hace el motor. El propietario lo dijo en una frase: *«que ponga lo que es. Si
está hecho, ponga hecho, es pura lógica; y si se decidió que no se hacía, pues
que no se hace y ya está»*.

## Comprobación que la sostiene

**El criterio de parada, comprobado pieza por pieza antes de tocar nada:**

| Pieza | Quién la citaba | Qué se hizo con ese lector |
|---|---|---|
| Base de conocimiento | `tests/automation/test_sirius_convergence.py` (la política de ciclos) y ADR-012 (la frontera de confianza, §14) | Sale de la lista de documentos que declaran la política vigente, con la razón escrita en el propio fichero de pruebas. La cita de ADR-012 sigue resolviendo: el documento no se mueve |
| Documento de incorporación | nadie, salvo auditorías y `MEMORIA.md` | Nada que resolver |
| Workflow del DOCX | ningún fichero lo invoca; solo lo mencionan auditorías y ADR-082 | Nada que resolver: las menciones son históricas |
| Línea de D4 | `src/sirius_engine/memoria.py` lee el registro entero | `MEMORIA.md` regenerada en el mismo commit, como exige ADR-171 |

**Después del cambio:** `tests/automation/test_sirius_convergence.py` y
`tests/automation/test_registro_de_bloques.py` pasan (90 pruebas); el YAML del
workflow sigue siendo válido y su único disparador es `workflow_dispatch`; el
comprobador documental no encuentra defectos en los dos documentos derogados.

## Consecuencias

- Quien abra la base de conocimiento ve en la primera línea que no debe
  creérsela, en vez de descubrirlo tres párrafos después al leer una versión
  del contrato que no existe.
- Un push a `main` deja de regenerar dos ficheros `.docx` y de confirmarlos.
- El registro de bloques del motor deja de tener una línea que contradice a un
  ADR de hace seis días.
- **Lo que no mejora:** los dos documentos derogados siguen ocupando sitio en
  `docs/operations/` y `MEMORIA.md` los sigue listando. Es el coste declarado
  de ADR-195, y se paga a propósito.

## Alternativas descartadas y por qué

- **Regenerar los dos mapas en vez de archivarlos.** Es lo que ya hace
  `MEMORIA.md`, y mantener dos generadores del mismo mapa es la forma de que
  vuelvan a divergir. La deriva documental que la sesión del ciclo arregló el
  10-08 nació exactamente así.
- **Borrar el workflow.** Más limpio de leer y contrario a ADR-195. Dejarlo sin
  disparador cuesta un fichero muerto y conserva el porqué.

## La lección

- familia: `pieza-sin-lector`
- sin esto se repetiría: seguirían conviviendo documentos que nadie mantiene y
  que una sesión nueva se cree, y una línea de registro contradiciendo al ADR
  que la decidió.
- lo hace cumplir: `tests/automation/test_registro_de_bloques.py`
