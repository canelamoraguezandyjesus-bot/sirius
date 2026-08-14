# SIRIUS — Auditoría de Model Studio (7 de agosto de 2026)

**SHA auditado de `main`:** `a017b6f`
**Piezas auditadas:** incidencia #126 (`SIRIUS-EXP-VOICE-002`), incidencia #127 (`SIRIUS-MODEL-STUDIO-003`), PR #128 (`SIRIUS-MODEL-STUDIO-UI-001 v1.0`, rama `docs/model-studio-ui-001`, sin fusionar).
**Motivo:** el usuario necesita una superficie mínima grabable antes de reanudar la implementación productiva de Sirius 0.2, y las tres piezas se escribieron por separado sin una pasada de coherencia entre ellas.

> **Alcance de esta auditoría**
> Audita coherencia documental, estado real de implementación y viabilidad técnica verificable desde el repositorio. No aprueba alcance, no autoriza implementación y no modifica ninguna decisión canónica. Las correcciones propuestas se registran en `docs/implementation/model_studio/SIRIUS_MODEL_STUDIO_RECONCILIACION_v1.0_PROPUESTA.md` y requieren aprobación explícita del usuario.

## 1. Estado real verificado

| Pieza | Tipo | Etiqueta / estado | Código en `main` |
|---|---|---|---|
| #126 · Módulo Voz | Incidencia abierta | `sirius:failed-safely` | **Ninguno** |
| #127 · Módulo Captura | Incidencia abierta | `sirius:planned` | **Ninguno** |
| #128 · Interfaz v1 | PR abierta, 1 archivo, 272 líneas | `mergeable_state: clean` | **Ninguno** (el documento vive solo en su rama) |

Verificación ejecutada sobre `main`: ningún archivo del árbol contiene `studio`, `audio`, `voice`, `speech`, `capture` ni `obs` en su ruta. **La vertical Model Studio no tiene una sola línea implementada.** Las tres piezas son documentación y planificación.

Consecuencia positiva: no existe deuda técnica previa que arrastrar ni código a medias que reconciliar. El punto de partida está limpio.

## 2. Por qué #126 quedó en `failed-safely`

Reconstrucción a partir de los cuatro comentarios de la automatización (5 de agosto de 2026, 17:49Z–17:55Z):

1. **17:49Z** — Activación rechazada (`sin-planned`): faltaba `sirius:planned`.
2. **17:52Z** — Activación rechazada (`cuerpo-incompleto`): el validador detectó ausencia de *work id, base y dependencias, requisitos y pruebas, validaciones, rama base, condiciones de parada, salvaguardas*.
3. **17:55:04Z** — Activación rechazada (`estado-incompatible`): la incidencia ya estaba en `sirius:implementing`.
4. **17:55:21Z** — Parada segura: *"El rol `implementer` no escribió ningún veredicto"*.

**Ninguno de los cuatro fallos fue técnico.** Los tres primeros son la misma clase de defecto de arranque ya documentada en `SIRIUS_AUDITORIA_ACTIVACION_2026-07.md` (hallazgo A1: las incidencias creadas por API no nacen con las precondiciones que la activación exige) y el cuarto es su consecuencia. El cuerpo actual de #126 sí contiene todas las secciones que el validador reclamó, de modo que fue editado después del rechazo 2, pero la reactivación se hizo sin resolver antes el estado `sirius:implementing` heredado del intento anterior.

**Lectura:** el intento de #126 no demostró que la voz sea inviable. Demostró que se consumió sin llegar a escribir código. Cualquier reactivación debe partir de estado limpio (`failed-safely` e `implementing` retirados conscientemente) o el ciclo se repetirá igual.

## 3. Hallazgos

### MS-A01 · P1 · La superficie que describe #128 no cabe en el alcance que declara #126

#126 acota su intervención en la interfaz a *"integración en la conversación existente"*, *"no crear una segunda aplicación"* y *"modificaciones localizadas en `composition_root.py`, `main_window.py`"*, con un único widget nuevo (`studio_mode_widget.py`).

#128 describe una superficie completa: fondo negro a pantalla completa, columna izquierda al 25–30 %, zona derecha al 70–75 %, barra superior propia con identidad y estados, barra inferior de iconos, zona auxiliar plegable y modo limpio a pantalla completa.

`src/sirius/presentation/main_window.py` tiene **1615 líneas** y organiza la aplicación en pestañas (Conversación, Conocimiento, Ajustes) construidas por `_build_conversation_tab`, `_build_knowledge_tab` y `_build_settings_tab`. Insertar la superficie de #128 como un widget dentro de la pestaña de conversación produciría una presencia de partículas embebida bajo una barra de pestañas — es decir, exactamente la interfaz técnica que #128 existe para evitar.

**Los dos documentos no pueden cumplirse simultáneamente tal como están escritos.** O #128 renuncia a ser una superficie propia, o #126 amplía su alcance de interfaz. Es el hallazgo de mayor impacto: condiciona dónde vive el código y cuánto cuesta.

### MS-A02 · P1 · QtMultimedia rompe la validación Quality en Linux

#126 fija QtMultimedia como adaptador de captura y reproducción (`qt_capture.py`, `qt_playback.py`) y lo trata como dependencia ya disponible, sin decisión nueva.

Verificación ejecutada en este entorno Linux con el `uv.lock` del repositorio (PySide6 6.11.1):

```
from PySide6.QtMultimedia import QAudioSource, QMediaDevices, ...
ImportError: libpulse.so.0: cannot open shared object file: No such file or directory
```

`.github/workflows/quality.yml` ejecuta en `ubuntu-latest` e instala únicamente `libegl1 libgl1 libxkbcommon0`. **No instala `libpulse0`.**

Si `qt_capture.py` o `qt_playback.py` importan `PySide6.QtMultimedia` a nivel de módulo, `pytest` falla en la fase de recolección —antes de ejecutar una sola prueba y aunque todas usen adaptadores simulados—, Quality queda roja y la cadena de automatización se atasca en el mismo punto que en el intento anterior.

Mitigación conocida y barata (import perezoso dentro de las funciones del adaptador, o import protegido, más `libpulse0` en el workflow), pero **debe decidirse antes de abrir la vertical**, no descubrirse durante el día 1 del plan.

### MS-A03 · P1 · No existe incidencia que autorice construir la interfaz

#126 cubre voz. #127 cubre captura. La interfaz —la pieza que realmente desbloquea la grabación— tiene documento aprobado (`SIRIUS-MODEL-STUDIO-UI-001`) pero **ninguna incidencia con ese Work ID**, ni alcance ejecutable, ni pruebas de aceptación registradas como tales, ni puerta.

Bajo el contrato operativo del repositorio, un documento aprobado no autoriza implementación por sí solo (el propio #128 lo dice en su cierre). El resultado es un diseño aprobado que nadie está autorizado a construir.

### MS-A04 · P2 · El registro de gasto no puede contabilizar audio

`src/sirius/adapters/llm/budget.py` expone:

```python
def record_usage(self, input_tokens: int, output_tokens: int) -> None
```

y `BudgetPolicy` solo define `input_cost_usd_per_million_tokens` y `output_cost_usd_per_million_tokens`. El contrato es exclusivamente de tokens de texto.

#126 exige *"reutilizar el ledger mensual de gasto actual, sin nueva tabla ni migración"* y la prueba **SV-011** exige que *"presupuesto agotado bloquea antes de llamar"*.

La tabla sí es reutilizable: `LLMUsageRepository` almacena `year_month -> usd` y es agnóstica del origen del coste. Lo que **no** es reutilizable sin ampliarlo es `BudgetTracker`: no hay forma de registrar el coste de una transcripción ni de una síntesis. Si el audio nunca se apunta, `has_remaining_budget()` seguirá devolviendo verdadero mientras el gasto real crece, y SV-011 pasaría en verde sin proteger nada.

La ampliación necesaria (un método de registro de coste de audio y su tarifa en `BudgetPolicy`) es pequeña y no exige migración, pero **no está escrita en ninguna de las tres piezas**.

### MS-A05 · P2 · Modelo de captura de voz contradictorio

- #126, alcance permitido: *"Captura pulsar-para-hablar"*. Prueba **SV-002**: *"pulsar y soltar captura solo el intervalo visible"*.
- #128, §5.1, paso 1: *"El usuario inicia una captura visible mediante el control de micrófono"*, seguido de *"corregir, cancelar, volver a grabar o enviar"*.

El primero describe mantener el botón físicamente pulsado durante toda la intervención; el segundo describe iniciar y detener por acción discreta. Son modelos de interacción distintos, con pruebas distintas y ergonomía distinta.

Relevancia operativa: el objetivo declarado de la vertical es grabar el montaje de HEAD-R1. Mantener un botón pulsado exige una mano permanentemente en el ratón, precisamente durante una actividad manual.

**Resuelto por decisión del usuario el 7 de agosto de 2026:** clic para empezar y clic para parar. Obliga a corregir el alcance de #126 y su prueba SV-002.

### MS-A06 · P2 · La máquina de estados no coincide entre los tres documentos

**Estados de interacción:**

| Estado | #126 | #128 |
|---|---|---|
| `DESACTIVADO` | sí | **ausente** |
| `PREPARADO` | sí | sí |
| `ESCUCHANDO` | sí | sí |
| `TRANSCRIBIENDO` | sí | sí |
| `REVISANDO` | sí | sí |
| `PENSANDO` | sí | sí |
| `EJECUTANDO` | **ausente** | sí |
| `SINTETIZANDO` | sí | **ausente** |
| `HABLANDO` | sí | sí |
| `ERROR` | sí | sí |

**Estados de captura:** #127 define nueve (`DESACTIVADO`, `PREPARADO`, `INICIANDO`, `GRABANDO`, `PAUSADO`, `CAMBIANDO`, `DETENIENDO`, `ERROR`, incierto recuperable). La tabla de #128 §8 solo recoge tres (`GRABANDO`, `PAUSADO`, `ESTADO INCIERTO`), sin declarar que la omisión sea deliberada.

Una interfaz que no puede representar un estado que la lógica produce es un defecto de producto, no de estilo: `SINTETIZANDO` e `INICIANDO` son precisamente los estados de espera que el usuario necesita ver para no repetir una orden.

### MS-A07 · P2 · La especificación aprobada no está en `main`

#126 y #127 ordenan *"partir del `main` vigente y actualizado"*. El documento `SIRIUS-MODEL-STUDIO-UI-001` existe únicamente en la rama `docs/model-studio-ui-001` de la PR #128, sin fusionar.

Un implementador que cumpla la instrucción de partir de `main` **no puede leer la especificación de interfaz que debe cumplir**. Mientras #128 siga abierta, la dirección de diseño aprobada es invisible desde la rama base.

### MS-A08 · P3 · Dos nombres para la misma vertical

#126 la llama *"Modo Estudio"*; #127 y #128 la llaman *"Model Studio"*. #127 declara además que Model Studio es el paraguas y que #126 es su Módulo Voz, pero #126 no usa ese nombre en ningún punto de su cuerpo. La denominación afecta a etiquetas, rutas de archivos, nombres de clases, texto visible en la interfaz y trazabilidad documental.

### MS-A09 · P3 · La voz `cedar` no está verificada para el endpoint elegido

#126 fija síntesis con `gpt-4o-mini-tts` y voz provisional `cedar`, y su día 2 propone comparar `cedar`, `onyx` y `echo`.

`onyx` y `echo` pertenecen al conjunto de voces del endpoint clásico de síntesis. `cedar` se introdujo asociada a la API Realtime, que #126 declara explícitamente fuera de alcance. **No se ha podido verificar en esta auditoría** (requiere clave real, prohibida en pruebas automáticas) si `cedar` está disponible en el endpoint de síntesis por lotes.

Riesgo: la voz fijada como provisional en el documento podría no ser invocable desde el único endpoint autorizado, invalidando la puerta del día 2. Comprobación de coste nulo antes de implementar.

### MS-A10 · P3 · El presupuesto mensual no se ha revisado para uso audiovisual

DR-018 fija 20 USD/mes con aviso a 15 (`BudgetPolicy` los codifica). Ese envolvente se dimensionó para conversación escrita. Una sesión de grabación añade una transcripción y una síntesis por turno sobre el coste de texto ya existente.

No es un defecto: es una magnitud sin revisar. Conviene decidir antes si el envolvente se mantiene, si Model Studio consume del mismo bolsillo o si se le asigna un sublímite propio, porque agotar el mes a mitad de una grabación es un fallo visible.

### MS-A11 · P3 · SHA base desactualizado en las tres piezas

Las tres piezas citan como base verificada `aedb071166b79b967a5aac55dea9c3780c8bc5a4`. `main` avanzó después a `a017b6f` (PR #129). La desviación es de un solo commit y no afecta a las superficies implicadas, pero invalida la literalidad de la instrucción *"base SHA verificado"* si se reactivan sin actualizar.

## 4. Riesgo de repetición del atasco

El intento de #126 no se perdió por dificultad técnica sino por precondiciones de activación. Ese riesgo sigue vivo y se agrava:

- #126 conserva `sirius:failed-safely`; el propio contrato exige retirarla conscientemente antes de reactivar.
- El cuerpo de #126 quedará desalineado en cuanto se corrijan MS-A05, MS-A06 y MS-A08, y el validador de cuerpo es estricto con las secciones obligatorias.
- MS-A02 garantiza Quality roja en el primer push si nadie decide antes el tratamiento de QtMultimedia; con Quality roja no hay revisión, y sin revisión el ciclo vuelve a pararse.

Reactivar cualquiera de las dos incidencias sin cerrar antes MS-A01, MS-A02 y MS-A03 tiene alta probabilidad de reproducir el mismo resultado.

## 5. Desajuste entre la necesidad declarada y el paquete exigido

La necesidad expresada por el usuario es una superficie mínima grabable, disponible pronto, mientras avanza el montaje físico de HEAD-R1 con Arduino y protoboard.

Lo que exigen las piezas actuales antes de considerar nada entregado:

- #126: cinco días de trabajo concentrado, 14 pruebas SV, evidencia real en Windows 11, capturas de cinco estados, tabla de tres turnos cronometrados, revisión de logs y vídeo de aceptación.
- #127: 18 pruebas MS, investigación técnica previa no realizada, dos ángulos físicos más captura de pantalla, tres sesiones consecutivas y vídeo de aceptación MS-018; además se declara **bloqueante para la implementación productiva de Sirius 0.2**.

Ambos paquetes son razonables como definición de vertical completa y son inadecuados como camino más corto a la primera grabación. Nada en las tres piezas identifica un subconjunto entregable antes.

## 6. Recomendación

Partir la vertical en tres etapas con entregable propio, de modo que la primera desbloquee la grabación sin depender de audio ni de hardware:

- **E1 · Concha grabable.** Estructura de #128 en funcionamiento con la conversación existente y estados simulados. Sin voz real, sin cámaras. Es el subconjunto que permite grabar.
- **E2 · Voz mínima.** #126 corregido (MS-A02, MS-A04, MS-A05, MS-A06, MS-A08, MS-A09) sobre la concha ya construida.
- **E3 · Captura y cámaras.** #127, precedido de la investigación técnica que él mismo exige y que sigue sin hacerse.

E1 no es alcance nuevo: es exactamente el orden 1-2-4 que el propio #128 §13 recomienda, y su condición de cierre ya está redactada allí (*"cuando el mockup pueda reproducirse como una pantalla estática, se vea correctamente en 1080p y el usuario confirme proporciones, tipografía, presencia visual y ubicación de controles"*).

El desglose ejecutable, la máquina de estados unificada y las correcciones concretas a cada pieza se registran en `SIRIUS_MODEL_STUDIO_RECONCILIACION_v1.0_PROPUESTA.md`.

## 7. Qué no se ha verificado

- Comportamiento real de QtMultimedia en Windows 11 (solo se verificó el fallo de importación en Linux).
- Disponibilidad de la voz `cedar` en el endpoint de síntesis por lotes (exige clave real).
- Coste real por turno de transcripción y síntesis.
- Cualquier extremo de #127: backend de captura, protocolo de cámaras, rendimiento o empaquetado. El propio #127 los declara NO VERIFICADOS y esta auditoría no los ha investigado.
- Rendimiento de una animación de partículas en la máquina del usuario.
