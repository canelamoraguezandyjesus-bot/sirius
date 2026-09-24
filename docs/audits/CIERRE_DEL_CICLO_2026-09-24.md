# Cierre del ciclo: qué hay de verdad a 24 de septiembre de 2026

- Fecha: 2026-09-24
- Quién lo lee: el propietario, antes de decidir qué hace con Sirius; y la
  sesión que reabra el repositorio después de la pausa. Se llega desde
  `MEMORIA.md` y desde ADR-216.
- Caduca con: la primera decisión suya sobre el rumbo. Hasta entonces, vale.

Este documento existe porque el propietario dijo el 24-09-2026 que en cuatro
meses no ve nada que la aplicación haga, y que lo que se le ha contado —
fusiones, revisiones, correcciones — no es lo que él mide. Tiene razón en el
criterio: **una fusión no es una capacidad**. Así que aquí no hay fusiones.
Hay lo que existe, lo que funciona demostrado, lo que no, y con qué número.

## 1. Lo que la aplicación hace hoy, y está demostrado

Sirius 0.1 es una aplicación de escritorio real, empaquetada para Windows y
**aceptada por él mismo el 17-08-2026** ejecutándola en su máquina (B13 y B14,
PR #122). No es una maqueta. Al abrirla hay cuatro pestañas:

| Pestaña | Qué puede hacer el usuario |
|---|---|
| Conversación | hablar con el modelo, con la respuesta llegando por partes, historial que persiste al cerrar y abrir |
| Memoria y decisiones | ver lo guardado, confirmar o rechazar lo que Sirius propone recordar, corregirlo, archivarlo, marcar criticidad y categoría |
| Configuración | clave de API validada contra el proveedor, ubicación de los datos, copia de seguridad y restauración |
| Proyectos históricos | lista los proyectos ya terminados y sus revisiones. Es una vista de solo lectura: la continuidad del proyecto activo vive en otro componente, dentro de la pestaña Conversación |

Y una página aparte, **Model Studio**, donde hay más de lo que parece:

- **La voz llega a la aplicación real**, sale por el reproductor del sistema,
  empieza a hablar antes de terminar de generarse y **se calla en seco al
  cancelar** (ADR-009).
- **La captura está probada contra OBS Studio 32.2.1 en Windows 11**: conexión
  y autenticación por su servidor local, lista de escenas, cambio de plano y
  vuelta, y una **grabación real de tres segundos con su archivo en disco**;
  después, las mismas órdenes dichas desde Model Studio —«graba», «cambia a
  cara», «para»— con confirmación hablada
  (`docs/implementation/model_studio/SIRIUS_MODEL_STUDIO_CAPTURA_INVESTIGACION.md`).
- **Lo que sigue sin verificarse**, y así está escrito: varias cámaras a la vez,
  el móvil como segunda cámara, sesiones largas, y la reconexión si OBS se
  cierra a mitad de una grabación.

Lo que sostiene eso: **7 438 pruebas automáticas en verde**, medidas hoy (24-09) sobre
el árbol de `3a491cc8`, en 12 min 33 s, más las dos validaciones manuales en su Windows del
10-08 y el 17-08. Arranca sin hablar con nadie cuando no hay proveedor: eso se
midió (B14), no se supone.

## 2. Lo que NO hace, con su número

Sirius 0.2 —la parte que debía hacerlo **recordar lo que importa**, que es el
problema que él nombró al principio— no está. Y no es una opinión:

| Qué se quería | Suelo exigido | Medido |
|---|---|---|
| aciertos exactos sobre el banco de 47 casos | 29/47 | **7/47** (ADR-202, 14-09-2026) |
| latencia P95, tres escenarios | ≤ 300 ms | **682 / 671 / 669 ms** |

El límite de 300 ms está suspendido mientras se mide (ADR-125), así que la
segunda fila no es un rojo: es un dato. La primera sí es la distancia real.
**Esa es la brecha entre lo que los documentos prometen y lo que la aplicación
hace.** Estaba medida y escrita desde el 14-09; no se le puso delante con esta
claridad.

## 3. Dónde se fue el trabajo

Cuando la auditoría de septiembre contó los ADR que había —196 entonces, **210**
con este cierre dentro—, el reparto salió así: **44 tratan de la aplicación y 152 del motor, del
método o de la automatización** (ficha PROC-006, estimación declarada como tal).
Es decir: la mayor parte del esfuerzo de estos meses fue en la máquina que
construye, no en lo que él abre. La auditoría lo dejó escrito el 19-09; este
documento lo repite porque es la respuesta honesta a su pregunta.

## 4. Qué queda parado y cómo se reenciende

- **El motor**, tal como está **ahora mismo** en la rama `estado-del-motor`:
  91 trabajos, **59 entregados, 27 cancelados, 4 esperando decisión y 1
  activo**. Los cuatro que esperan **siguen esperando**: esta sesión comprobó
  sobre una copia que se cierran limpiamente, pero no puede escribir en esa
  rama. Cuando él ejecute el lote de ADR-216, el recuento pasará a **59 / 31 /
  0 / 1**. Ese último 1 **se queda ahí a propósito**, y abajo está por qué.
- **Cinco workflows con horario** siguen despertando solos. Cuatro solo miran
  (`motor-sirius`, `reconcile-sirius-states`, `reflejar-desenlace`,
  `contador-siete-dias`): con el diario sin trabajo vivo, el turno mira, no
  encuentra nada y sale; no rompen nada, pero consumen minutos de Actions. **El
  quinto, `mina-mensual`, es distinto: ese CREA trabajo.** Su reloj es el día 1
  de cada mes a las 09:24 UTC y para un disparo por horario ejecuta de verdad
  (`mina-mensual.yml:117` y `:136`), así que **el 1 de octubre despacharía un
  encargo nuevo** y el motor dejaría de estar vacío. Si el cierre tiene que
  aguantar, ese es el que tiene fecha. Se apagan desde la pestaña **Actions**
  de GitHub, cada uno con «···» → «Disable workflow», y se vuelven a encender
  igual. **No se han tocado los ficheros a propósito**: su horario está
  derivado y vigilado por guardas cruzadas
  (`tests/automation/test_contador_de_siete_dias.py`), y desactivarlos desde la
  interfaz no toca ese diseño ni exige cambiar ninguna prueba.
- **El repositorio entero es la copia de seguridad**: todo lo decidido está en
  `docs/decisions/`, el método en `.claude/skills/`, el estado del motor en la
  rama `estado-del-motor`. Un `git clone` se lo lleva todo.

## 5. Lo que este cierre NO pudo hacer

- **Los cuatro trabajos que esperaban decisión siguen esperando en la rama
  `estado-del-motor`.** Se comprobó que `sirius-decidir … --terminar` los cierra
  limpiamente —se ejecutó sobre una copia y los cuatro quedaron `cancelled`,
  terminal—, pero esta sesión **no puede escribir en esa rama**: es estado
  compartido que solo escribe el workflow (idea aparcada I-009). Los cuatro
  comandos que lo cierran desde su ordenador están en ADR-216, para el lote.
- **`WI-20260828-122242` sigue `active` desde el 28-08, y ningún comando lo
  cierra.** No por un fallo: **el diseño lo aparta a propósito.** Su incidencia
  es la **#392**, cerrada el 28-08 con **dos etiquetas que se contradicen**
  (`sirius:failed-safely` y `sirius:completed`). El reflector sí lo alcanza
  —su clase `investigacion` está en la tabla que consulta (ADR-099, ADR-173)—,
  y al llegar aplica su primera regla: ante etiquetas contradictorias no toca
  nada y devuelve la divergencia (`src/sirius_engine/reflect.py:275-283`).
  ADR-173 lo dejó escrito por adelantado: «se queda `active` a propósito: es el
  único de los 21 que un humano tiene que mirar», y ADR-181 protege esa regla
  como criterio de parada. La salida, entonces, no es un comando: es **mirar la
  #392 y decidir cuál de las dos etiquetas es la verdadera**, dejar solo esa
  por el procedimiento que corresponda, y dejar que el reflector pase. Esta
  sesión no retira etiquetas y el lote de ADR-216 no lo intenta.
  Esta afirmación se equivocó **dos veces** antes de quedar así —primero «no
  hay salida ninguna», después «el reflector lo cierra»—, y las dos las cazó la
  revisión de Codex sobre esta misma PR.
  Lo que sigue abierto como defecto (H-216, incidencia #662) no es el trabajo:
  es que esa contradicción lleva **veintisiete días sin que nadie la haya
  mirado**. El diseño dice «esto lo mira un humano» y no hay nada que ponga a
  ese humano delante. Se encontró auditando, no por un aviso.

## 6. El motor: en qué estado queda, y qué le falta

Es lo que el propietario conserva, así que esta sección es la que importa al
volver. Sale de `docs/implementation/bloques_del_motor.yml`, del diario y del
registro de defectos, no de un resumen.

**Veinte bloques: 17 cerrados, 2 fuera de alcance y 1 pendiente.**

- **Fuera de alcance**: D3 (hablar por Telegram; su centro de mando es la sesión
  interactiva) y D4 (partir un objetivo grande en encargos), este último
  **descartado con razón escrita** en ADR-198, no aplazado: repartir exige un
  modelo y el motor no ejecuta ninguno, que es la premisa de ADR-082.
- **Pendiente, uno solo: D1, «pasar el mando de GitHub al motor, clase por
  clase».** Y lo que le falta **no es código**. Sus tres piezas existen y desde
  el 27-08-2026 las tres tienen llamante, incluida `authority_reversion.py`, la
  salida de emergencia del §11.4 que devuelve el mando si el motor se porta mal.
  Lo que falta es lo que el contrato exige para cerrarlo: **siete días
  consecutivos en verde por clase** (§11.2). Los siete días no han empezado
  porque un día sin trabajo circulando no cuenta como día verde. **D1 se cierra
  usándolo, no programándolo.**

**Lo que el motor ya ha hecho, medido en su diario**: 91 encargos, **59
entregados** con su commit de fusión, 31 cancelados y 1 atascado. No es una
maqueta: ha llevado trabajo real de punta a punta.

**Lo que está roto o sin terminar, con su nombre:**

| Qué | Dónde |
|---|---|
| Una contradicción de etiquetas que el diseño deriva a un humano lleva 27 días sin que nadie la mire | H-216, incidencia #662 |
| La vigilancia de la vigilancia es humana: la red de seguridad estuvo **35 días ciega** sin que nadie lo notara | ADR-193, ficha PROC-003 |
| El ciclo no distingue criticidad: 7 rondas de revisión, todas P2, sobre un aviso que por contrato no puede romper nada | incidencia #503 |
| El método no está mecanizado: la regla de las dos rondas, la mutación declarada y la detección de listas a mano las aplica una persona leyendo | incidencia #267 |
| Nadie cuenta las rondas de la revisión externa | idea I-008 |
| Una decisión del propietario no tiene vía segura hasta el diario de `estado-del-motor` | idea I-009 |
| Un agente que revise el repositorio por módulos cuando nadie está delante | idea I-005 |

**Lo que NO le falta**, y conviene no reconstruirlo por olvido: despachador con
su puerta de sensibilidad, supervisor, reflector de desenlaces, tablero por
incidencia, revisión dual con Claude y Codex, la cola de revisión de ADR-191, el
contador de siete días con su hora derivada, y la reversión de autoridad.

## 7. Si mañana se retoma solo el robot

Lo que vale para eso y ya está construido: el motor de trabajo con su diario,
el ciclo de revisión, la disciplina de evidencia y las diecinueve skills de
`.claude/skills/`. Lo que no: la aplicación de escritorio y la memoria de 0.2,
que son otro producto. Separarlos es una decisión suya, no de esta sesión.
