# ADR-205 — La fusión no espera al propietario cuando los dos revisores aprueban

- Estado: APROBADO
- Fecha: 2026-09-20
- Aprobación: el propietario, el 20-09-2026: «quiero que a partir de ahora
  puedas fusionar todo simple y cuando ambos revisores den el visto bueno».
- Nota de arranque: la de ADR-204, que cubre esta tanda entera.

## Contexto y problema

El contrato operativo §8 dice que el merge permanece bajo control humano y que
la autorización es un comentario del propietario con la palabra exacta
`fusiona` sobre la incidencia en `sirius:ready-for-merge`. §9 lo repite como
prohibición: *«fusionar una PR sin el comentario explícito de autorización
descrito en §8 (ese comentario, no la mera llegada a `sirius:ready-for-merge`,
es la autorización)»*.

Esa regla tenía una razón buena cuando se escribió: la revisión era de un solo
revisor y el propietario era la única segunda opinión. Desde ADR-121 y la
revisión dual, ya no lo es. Y el coste medido de mantenerla es el que el paso 4
de la auditoría contó:

- La incidencia #650 llegó a `ready-for-merge` el 19-09 a las 18:17 UTC y se
  fusionó a las 23:58. **Cinco horas y cuarenta minutos** de espera con todo en
  verde y ningún hallazgo abierto, y ocho despertares horarios de la vigilancia
  diciendo «sin cambios».
- La incidencia #148 cerró su ciclo el 11-08 a las 05:12 y esperó al propietario
  hasta las 19:50 para que retirara una etiqueta, y hasta las 21:34 para
  fusionar.
- La espera no añade ninguna comprobación: el propietario ha dicho, y la
  auditoría lo registró, que no puede verificar por sí mismo lo técnico. Su
  `fusiona` no es una revisión; es un trámite que solo puede hacer él.

## Criterio de parada (escrito ANTES de decidir)

Si la etiqueta `sirius:ready-for-merge` pudiera ponerse con un solo revisor
aprobando —o sin ninguno—, la etiqueta no valdría como autorización y esta
decisión no se tomaría: haría falta primero un dato nuevo que dijera «los dos
aprobaron». Se comprueba en el código antes de decidir.

## Decisión

**La aprobación de los dos revisores es la autorización de merge.** El
comentario `fusiona` del propietario deja de ser necesario y se conserva como
mando manual: sigue funcionando igual, y es la vía para reintentar después de
resolver un bloqueo.

Lo que **no** cambia, y es la mitad importante: las comprobaciones. Por las dos
vías, antes de fusionar se verifica por REST, en el momento de actuar:

- que la incidencia sigue en `sirius:ready-for-merge`;
- que hay **una única** PR asociada, abierta, no borrador y no fusionada ya;
- que no tiene conflictos con la base;
- que no está por detrás de la base (su verde se calculó contra otra base);
- que el head es exactamente el aprobado, sin commits posteriores sin revisar;
- que Quality está verde sobre ese head exacto.

Si algo falla, no se fusiona: se publica el motivo en la incidencia y se para,
igual que antes.

## Comprobación que la sostiene

**El criterio de parada, comprobado en el código antes de decidir:**
`sirius:ready-for-merge` la pone un único sitio,
`scripts/automation/sirius_apply_verdict.sh`, en la rama `REVIEW_APPROVED`
(línea 690), y ese veredicto en modo dual es el **agregado** de Claude y Codex:
basta que uno pida cambios para que la incidencia vaya a `repairing`, y si uno
no contesta dentro del plazo absoluto va a `failed-safely`. Las dos ramas están
en el mismo script y las dos se observaron de verdad en la sesión del ciclo del
11-08: Codex encontró un defecto real que Claude había aprobado, y en otra
ronda Codex no contestó y el sistema se negó a aprobar solo. **La etiqueta ya
significa «los dos aprobaron»**, así que el criterio no se dispara.

**La implementación**, con sus mutaciones:

- `scripts/automation/sirius_merge_on_command.sh` gana un modo de autorización
  que llega por entorno (`SIRIUS_MERGE_AUTORIZACION`), con dos valores:
  `comentario` —el de siempre, y el que se usa si nadie declara nada— y
  `revision-dual`. **Cualquier otro valor detiene el merge** en vez de dejarlo
  pasar: una errata en un YAML no puede convertirse en «fusiona sin comprobar».
- `.github/workflows/merge-sirius-work.yml` gana el disparador
  `issues: [labeled]`, acotado a la etiqueta `sirius:ready-for-merge`.
- `tests/automation/test_sirius_merge.py` pasa de 22 a 27 pruebas. Las cinco
  nuevas se verificaron por mutación, cada una sobre el árbol confirmado:

| Mutación | Resultado |
|---|---|
| el modo desconocido deja pasar en vez de detener | falla 1 prueba |
| el modo por omisión pasa a `revision-dual` | fallan 3 pruebas |
| en modo dual se salta la reverificación de la etiqueta | falla 1 prueba |

Las 27 pasan sobre el árbol restaurado.

## Consecuencias

- El contrato pasa a **v1.11**: §8 y §9 quedan enmendadas por §14.
- Una PR del ciclo que llegue a `ready-for-merge` se fusiona sola, en minutos
  en vez de en horas, y `complete-sirius-after-merge.yml` la cierra como
  siempre.
- El propietario deja de ser un paso del camino crítico para el trabajo
  técnico. Sigue siéndolo para lo que ADR-204 le reserva: dinero, salud y
  cambio de producto.
- **El riesgo que se acepta a propósito:** un defecto que los dos revisores
  aprueben entra en `main` sin que nadie más lo mire. Ya podía ocurrir —el
  `fusiona` del propietario no lo habría detectado, porque él mismo dice que no
  puede verificarlo—, pero antes había una espera que a veces servía de
  casualidad. Lo que queda en su lugar es lo que de verdad lo caza: la revisión
  dual, la suite completa, los guardianes del árbol y la regla de las dos
  rondas.
- **Cómo se revierte, si sale mal:** quitando el disparador `issues: [labeled]`
  del workflow. El modo por omisión ya es el de siempre, así que el
  comportamiento anterior vuelve sin tocar el script.

## Alternativas descartadas y por qué

- **Que la sesión interactiva publique `fusiona` en nombre del propietario.** No
  requiere ningún cambio de código y es exactamente lo que ADR-204 prohíbe: una
  decisión de la máquina firmada como si fuera suya. El registro diría que
  autorizó algo que no vio.
- **Fusionar solo las PR pequeñas o solo las de documentación.** Añade un
  criterio nuevo que alguien tendría que mantener, y el tamaño no predice el
  daño: el defecto que Codex cazó el 11-08 cabía en una línea.

## La lección

- familia: `tramite-que-solo-puede-hacer-una-persona-y-no-anade-comprobacion`
- sin esto se repetiría: el ciclo volvería a quedarse horas en verde esperando
  una palabra que no verifica nada, y la vigilancia gastaría despertares vacíos
  mientras tanto.
- lo hace cumplir: `tests/automation/test_sirius_merge.py`
