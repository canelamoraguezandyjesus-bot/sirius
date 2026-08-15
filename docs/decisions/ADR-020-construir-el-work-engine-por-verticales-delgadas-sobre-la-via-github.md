# ADR-020 — Construir el Work Engine por verticales delgadas, reutilizando la vía GitHub y aplazando cada decisión a su punto exacto de consumo

- Estado: PROPUESTO
- Fecha: 2026-08-15
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario. La fusión
  aprueba el PLAN (`docs/implementation/SIRIUS_WORK_ENGINE_PLAN_IMPLEMENTACION.md`) como
  secuencia de trabajo; la autorización de implementación efectiva es E0 (mini-PR a
  `docs/evolution/STATUS.md`, patrón de la PR #174), porque la excepción vigente cubre
  solo la fase de diseño. Numeración: ADR-019 es el último en `main`; 017/018 siguen
  reservados por la rama de la PR #171 (abierta).

## Contexto y problema

El diseño del Work Engine está aprobado (#172, #173 fusionada, ADR-019; excepción de
diseño registrada por #174). Falta ordenar su construcción. Los riesgos conocidos, todos
con historia en este repositorio: construir media plataforma antes de obtener valor
(WORK_PROCESS_AUDIT: la meta-reparación fue la mayor familia de PRs); crear vías paralelas
a la automatización existente (prohibido por #172 §4.7); y depender de decisiones aún no
tomadas (C1/C2/C5 detenidas; I4/I5 pendientes; coste de GPT Researcher NO VERIFICADO).

## Criterio de parada (escrito ANTES de decidir)

Publicado en la nota de arranque (comentario en #172, 2026-08-15, antes del primer
commit): cada bloque con los 7 campos exigidos por el encargo; ningún bloque puede
depender de C1/C2/C5 antes de su enmienda ni de I4/I5 antes de su punto de bloqueo
declarado; máximo 2 rondas de autorevisión (misma familia de defectos dos veces → parar y
buscar la raíz); si la secuencia exigiera violar una frontera aprobada del diseño, esa
rama se detiene y se consulta; una única PR documental con el menor número de ficheros.

## Opciones consideradas

1. **Construir el motor completo y conectarlo al final**: descartada — repite el patrón
   media-plataforma-sin-valor y deja los supuestos sin contrastar hasta el final.
2. **Empezar por el despacho (la parte más visible)**: descartada — depende de C1/C2
   (enmiendas del contrato) desde el primer día y convierte las decisiones del
   propietario en bloqueo inicial.
3. **Evolucionar los workflows existentes hacia el motor**: descartada — el defecto de
   durabilidad es estructural (el observador dentro de lo observado) y el diseño aprobado
   ya lo resolvió con un motor externo; además ADR-002 limita tocar workflows.
4. **Verticales delgadas con valor por fase, espejo antes que escritura, y decisiones
   aplazadas a su punto exacto de consumo**: elegida.

## Decisión

Adoptar el plan de `docs/implementation/SIRIUS_WORK_ENGINE_PLAN_IMPLEMENTACION.md`, cuyas
decisiones de plan son:

1. **Secuencia E0 → A (núcleo puro → spike I3 → almacén durable → espejo de solo lectura
   + contexto v0 → perfiles/WorkerRequest/Resolver/egress) → B (spike I2 → investigación
   con GPT Researcher) → E1 (contrato v1.7: C1+C2+C5) → C (spike I1 → supervisión activa
   → despacho end-to-end → documental → auditor) → D (canonicidad por clase → servicio
   desatendido → Telegram opcional)**, con hitos de valor observable al fin de cada fase.
2. **La investigación (Fase B) va antes que el motor activo (Fase C)** a propósito: da
   valor nuevo sin depender de ninguna enmienda del contrato.
3. **El código del motor vive en `src/sirius_engine/`**: fuera de `src/sirius/` (frontera
   aprobada), pero bajo `src/` para que `quality.yml` lo cubra sin modificar ningún
   workflow; con prueba de frontera que prohíbe importaciones entre `sirius` y
   `sirius_engine` en ambos sentidos.
4. **Una única enmienda del contrato (E1, v1.7)** resuelve C1, C2 y C5 juntas, después
   del hito M2 y antes de cualquier bloque de la Fase C; su texto operativo sale de la
   arquitectura §14.
5. **Los spikes se insertan solo delante de la decisión que dependen de ellos**
   (I3→almacén, I2→investigador, I1→cotas de LOST); I4 bloquea únicamente el servicio
   desatendido (D2); I5 es un dato que no bloquea nada.
6. **Migración de canonicidad sin doble autoridad**: autoridad como función total por
   clase de trabajo con conmutador fechado y reversible; espejo explícitamente
   no-autoritativo antes; proyección obligatoria verificada después (plan §4).
7. **Disposición recomendada para la PR #171: extraer piezas y cerrar sin fusionar** —
   su Investigador (repo privado + web) es incompatible con la política de egress
   aprobada; sus piezas compatibles (registro de acciones, runbooks neutrales, mejoras
   del arnés del Auditor, banco de evaluación) se extraen en PRs pequeñas en los bloques
   A4 y C4. El cierre es un acto del propietario; no bloquea ningún bloque.

## Comprobación que la sostiene

- Base verificada antes de planificar: `main` = `54bb690` con #173/#174 fusionadas; los
  tres documentos de diseño en `main` byte a byte idénticos a lo auditado (diff vacío
  contra `d951163`); la excepción de `docs/evolution/STATUS.md` cubre solo diseño —
  de ahí E0.
- Estado de la PR #171 reverificado por API en esta misma sesión (abierta, sin reviews,
  `quality` verde, prohibición de fusión vigente) antes de recomendar su disposición.
- La cobertura de `src/sirius_engine/` por `quality.yml` se apoya en los comandos reales
  del workflow (`ruff format --check .`, `ruff check .`, `mypy src tests`, `pytest`,
  verificados en `quality.yml:49-59`) y en `testpaths = ["tests"]`
  (`pyproject.toml:76`): `src/` y `tests/` quedan cubiertos sin editar ningún workflow.
- Cada dependencia declarada en el plan se contrastó contra las contradicciones y
  cotas del diseño (arquitectura §14 y §15): ningún bloque consume C1/C2/C5/I1–I5 antes
  de su resolución.

## Consecuencias

- El primer bloque de código (A1) puede empezar en cuanto E0 esté fusionada; no requiere
  ninguna otra decisión, dato ni spike.
- Las decisiones del propietario quedan concentradas en actos contados: aprobar este plan
  (fusión de su PR), E0, E1, la posible decisión de gasto si el spike I2 la demuestra,
  I4 antes de D2, cada conmutación de canonicidad (D1), y el cierre de #171 cuando quiera
  ejecutar la disposición recomendada.
- La vertical funcional completa de #172 §6 queda cubierta al hito M3 con CUATRO perfiles
  (ejecutor de repo, revisor, investigador, auditor) más pasos deterministas, sin crear
  un agente por punto.
- Si la evidencia de los primeros bloques contradice la secuencia, el plan se corrige con
  una revisión de este ADR, no con parches silenciosos.

## Alternativas descartadas y por qué

Las opciones 1–3 de arriba. Además: ejecutar los spikes durante la planificación
(prohibido por el encargo; además I2 puede levantar una decisión de gasto que es del
propietario); fusionar o cerrar la PR #171 desde este plan (la prohibición y el acto son
del propietario); introducir la base de datos definitiva del motor ahora (la decide el
resultado de I3/I4 detrás del puerto de persistencia); y empezar por Telegram (interfaz
sustituible: la vertical se demuestra con la interfaz v0 de sesión/CLI y Telegram queda
como decisión propia al llegar a D3).
