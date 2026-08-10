# ADR-004 — Una red de seguridad periódica, porque un run muerto no puede avisar

- Estado: PROPUESTO
- Fecha: 2026-08-10
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario

## Contexto y problema

La incidencia #138 registró una raíz, no un defecto: **un proceso que muere no
puede informar de su propia muerte**. La PR #136 intentó siete correcciones
seguidas para que el corrector siempre dejara veredicto, y las siete fallaron
por lo mismo —cada una vivía dentro del run que puede morir—:

| Corrección | Dónde vivía | Cómo se la saltó el fallo |
|---|---|---|
| Paso de diagnóstico medido | dentro del job | podía tumbar el job que observaba |
| «Veredicto como última acción» | dentro del corrector | `--max-turns` lo corta antes |
| Veredicto provisional al empezar | dentro del corrector | el tope del job lo corta antes |
| Topes de paso al corrector | dentro del job | la puerta quedaba sin acotar |
| Todos los pasos acotados | dentro del job | el corte externo no produce desenlace |
| Plazo interno de la puerta | dentro del paso | un `gh` colgado no se interrumpe |
| Encaminar todo por `_sirius_gh` | dentro del proceso | el checkout puede morir antes |

La octava tendría el mismo destino. **La lista es infinita porque el observador
está dentro de lo observado.**

Cuando un run muere, la incidencia queda con su etiqueta de estado puesta, y
`issues: labeled` **no vuelve a dispararse con una etiqueta ya aplicada**. El
flujo por eventos, por construcción, no puede notarlo.

La pieza que lo notaría ya existía y estaba probada —`sirius_reconcile.sh` tras
`reconcile-sirius-states.yml`— pero solo arrancaba con `workflow_dispatch`, y su
propia cabecera explicaba por qué: *el contrato prohíbe la vigilancia horaria
como motor del flujo*. Verificado: de trece workflows, **ninguno** tenía
`schedule:`. Es decir, la única pieza capaz de detectar un run muerto dependía de
que una persona detectara primero que había un run muerto.

## Criterio de parada (escrito ANTES de decidir)

- Si para detectar hiciera falta que el reconciliador **repare algo nuevo**, no
  se hace: eso es otra decisión.
- Si el coste de programarlo no se puede acotar con un número concreto, se
  pregunta en vez de estimar por encima.
- El umbral no se escribe a mano y ya está: se ata por prueba a los
  `timeout-minutes` reales (ADR-003).

## Opciones consideradas

1. **Programar el reconciliador** con una excepción acotada al contrato.
2. **Dejarlo abierto y documentado**, que era el estado vigente: defensas
   internas *best-effort* y desatasco manual.
3. **Un observador externo fuera de GitHub** (otro servicio que vigile).

## Decisión

**Opción 1**, con la frontera escrita en el contrato v1.6 §9.1.

La prohibición del contrato decía «vigilancia horaria como **motor** del flujo».
Esa palabra es la que hace el trabajo: lo prohibido es que el ciclo lo dirija una
tarea que sondea. Una red de seguridad que **no** inicia trabajo, **no** avanza
un ciclo sano, **no** fusiona, y ante la duda informa en vez de tocar, no es el
motor de nada. Ampliar la prohibición a «ninguna tarea programada jamás» era leer
en ella más de lo que dice, y el precio de esa lectura era quedarse sin la única
detección posible.

La opción 3 se descarta: introduce un servicio nuevo, y por tanto coste y
superficie, para hacer lo que GitHub ya puede hacer gratis.

**Cadencia: seis horas.** No es comodidad, es el coste: el job dura menos de un
minuto y GitHub factura por minuto empezado, así que 4 ejecuciones al día son
~120 min/mes de los 2000 gratuitos del repositorio privado; cada hora serían
~720. La latencia de detección de un repositorio de una sola persona no vale esa
diferencia.

**Qué se detecta.** No la muerte del run —eso solo lo sabe el run— sino que un
estado que solo la máquina puede mover lleva más de `STUCK_MINUTES` sin avanzar.
Es lo único observable desde fuera, y es suficiente.

**Qué se hace al detectarlo.** Se publica **un** comentario en la incidencia,
deduplicado por aplicación de etiqueta. No se repara. Un resumen de job que nadie
abre no es una detección; un comentario en la incidencia sí llega a una persona.

## Comprobación que la sostiene

- La fecha del estado la da GitHub (`/issues/{n}/events`, último evento
  `labeled` con esa etiqueta). Deducirla de `updated_at` de la incidencia sería
  reconstruir desde fuera un hecho ajeno —cualquier comentario la mueve— que es
  el mismo error que abrió todo esto. **RECON-STUCK-001** siembra ruido a
  propósito (eventos que no son `labeled`, otras etiquetas, dos aplicaciones de
  la misma) y falla si se fecha por la primera.
- **RECON-STUCK-002**: un estado de 10 minutos no se denuncia.
- **RECON-STUCK-003**: si el historial no se puede leer, **no se afirma nada**.
  Interpretar una lectura fallida como «lleva mucho» publicaría una acusación
  falsa en la incidencia.
- **RECON-STUCK-004**: dos pasadas, un solo comentario.
- **RECON-STUCK-005**: `blocked-decision`, `failed-safely` y `ready-for-merge`
  esperan a una persona por diseño; llevar semanas ahí es lo correcto.
- **RECON-STUCK-006**: el umbral se compara con los `timeout-minutes` **reales**
  de todos los workflows. Subir el revisor de 85 a 200 minutos rompe la prueba.
- **RECON-STUCK-007**: el `schedule:` existe, el disparo manual sigue, y el
  workflow conserva `contents: read` —no puede empujar nada—.
- El `gh` simulado aplica el `--jq` **real** con `jq`: si lo ignorara, el filtro
  —que es donde puede estar el defecto— no quedaría medido. Verificado por
  mutación: con el simulado devolviendo la línea ya filtrada, RECON-STUCK-001
  deja de fallar ante un filtro roto.
- Diez mutaciones en las dos direcciones, todas con el resultado predicho antes
  de ejecutarlas.

## Consecuencias

- El **caso B** del reconciliador (`ci-pending` con Quality en verde) pasa a
  repararse **sin supervisión**, y esa reparación despierta al revisor. No es
  trabajo nuevo —es lo que el flujo por eventos habría hecho de no perderse la
  transición— pero antes solo ocurría a petición y ahora puede ocurrir de
  madrugada.
- **Lo que esto NO hace**, y conviene que no se lea de más:
  - no repara los estados atascados: avisa a una persona;
  - no detecta un run muerto, sino un estado que no avanza;
  - no cubre el hueco entre el atasco y la siguiente pasada: hasta seis horas;
  - no cubre una incidencia CERRADA que quedara mal, porque solo recorre las
    abiertas;
  - no notifica fuera de GitHub.
- Reversible por completo: quitar el `schedule:` devuelve el comportamiento
  anterior sin tocar nada más.
- Si en el futuro se quisiera que **repare** los estados atascados (tier 2), eso
  es otra decisión y otro ADR: exige distinguir «el run murió» de «el run sigue
  vivo», que desde fuera no es decidible sin consultar Actions.

## Alternativas descartadas y por qué

- **Cadencia horaria**: seis veces el coste para una latencia que aquí no vale
  esa diferencia. Un número, cambiable si la evidencia lo pide.
- **Avisar solo en el resumen del job**: es lo que ya había, y es la razón de que
  el problema llevara desde el 7 de agosto sin que nadie lo viera.
- **Que el reconciliador reintente la etiqueta por su cuenta** (quitar y volver a
  poner para redisparar el evento): reintentaría también sobre runs vivos, porque
  desde fuera no puede saber si lo están. Sustituiría un fallo silencioso por
  ejecuciones duplicadas.
