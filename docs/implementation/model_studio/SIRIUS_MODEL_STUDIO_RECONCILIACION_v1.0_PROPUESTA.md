# SIRIUS · MODEL STUDIO

## RECONCILIACIÓN DE ALCANCE, ESTADOS Y ETAPAS

**Documento:** SIRIUS-MODEL-STUDIO-REC-001
**Versión:** 1.1
**Estado:** **APROBADA POR EL USUARIO el 7 de agosto de 2026**, salvo R-11
**Fecha:** 7 de agosto de 2026
**Base:** `main` en `a017b6f`
**Origen:** hallazgos MS-A01 a MS-A11 de `docs/audits/SIRIUS_AUDITORIA_MODEL_STUDIO_2026-08.md`
**Piezas que reconcilia:** #126 (`SIRIUS-EXP-VOICE-002`), #127 (`SIRIUS-MODEL-STUDIO-003`), PR #128 (`SIRIUS-MODEL-STUDIO-UI-001 v1.0`)

> **Qué es y qué no es este documento**
> Reconcilia tres piezas escritas por separado que se contradecían. El usuario aprobó R-01 a R-10 el 7 de agosto de 2026; R-11 sigue pendiente de su decisión. No modifica documentos canónicos y no sustituye a `SIRIUS-MODEL-STUDIO-UI-001`, cuya dirección de diseño se conserva salvo en la presencia visual, que el propio usuario redefinió ese mismo día (véase el cuadro).
>
> La versión 1.0 registraba propuestas. Esta 1.1 registra además qué se ha construido de verdad y qué no, para que nadie tenga que deducirlo del código.

## 1. Cuadro de decisiones

| # | Decisión | Estado | Hallazgo |
|---|---|---|---|
| R-01 | Nombre único de la vertical: **Model Studio** | APROBADO · **implementado** | MS-A08 |
| R-02 | La captura de voz se inicia y se detiene por acción discreta | APROBADO · **implementado** | MS-A05 |
| R-03 | Model Studio vive como página conmutable dentro de la ventana actual | APROBADO · **implementado** | MS-A01 |
| R-04 | Máquina de estados unificada de interacción y de captura | APROBADO · **implementado** | MS-A06 |
| R-05 | Abrir incidencia propia para la interfaz (`SIRIUS-MODEL-STUDIO-UI-002`) | APROBADO · incidencia abierta | MS-A03 |
| R-06 | QtMultimedia se importa de forma perezosa; `libpulse0` se añade a Quality | APROBADO · **implementado y vigilado por prueba** | MS-A02 |
| R-07 | `BudgetTracker` se amplía para registrar coste de audio, sin migración | APROBADO · **implementado** | MS-A04 |
| R-08 | La voz de síntesis se verifica antes de fijarse en documento | APROBADO · **verificado: `cedar` NO existe en el endpoint autorizado** | MS-A09 |
| R-09 | Ejecución en tres etapas: E1 concha grabable, E2 voz, E3 captura | APROBADO · E1 y E2 entregadas, E3 sin empezar | MS-A01 |
| R-10 | Fusionar #128 antes de abrir cualquier implementación | APROBADO · **pendiente de que el usuario lo fusione** | MS-A07 |
| R-11 | Envolvente de gasto de Model Studio | **PENDIENTE DE DECISIÓN DEL USUARIO** | MS-A10 |

> **Decisiones visuales tomadas por el usuario el 7 de agosto de 2026, sobre prototipo renderizado**
>
> - Sirius abre en la interfaz técnica, con un botón arriba para pasar a Model Studio.
> - El cuerpo de la conversación es algo mayor que el normal de escritorio, pensado para leerse al ver el vídeo en un móvil.
> - La columna izquierda muestra proyecto y contexto pegados bajo la presencia, con el hueco de notas rápidas reservado.
> - **La presencia no es un rostro.** Es una entidad digital abstracta y geométrica: ojos robóticos que parpadean y cambian de tamaño de forma sutil e irregular, boca de barras verticales tipo ecualizador, y cuatro marcas de esquina que la encuadran como interfaz. Sin sincronización labial y sin análisis de audio: la agitación es continua y nace de un pulso constante.

## 2. R-01 · Nombre único

**Problema.** #126 dice *"Modo Estudio"*; #127 y #128 dicen *"Model Studio"*.

**Propuesta.** **Model Studio** como nombre de la vertical y del paraguas operativo, por ser el que ya usan la incidencia paraguas (#127) y la especificación de interfaz (#128), y el que da nombre al Work ID `SIRIUS-MODEL-STUDIO-*`.

Se conserva la subdivisión que ya establece #127:

- **Model Studio · Módulo Interfaz** — la superficie audiovisual (nuevo, R-05).
- **Model Studio · Módulo Voz** — #126.
- **Model Studio · Módulo Captura** — #127.

Alcanza a: texto visible en la interfaz, nombres de módulos y clases, rutas bajo `docs/implementation/model_studio/`, títulos de incidencia y etiquetas. `SIRIUS-EXP-VOICE-002` conserva su Work ID para no romper trazabilidad; solo cambia el nombre visible del bloque.

## 3. R-02 · Modelo de captura de voz — DECIDIDO

**Decisión del usuario, 7 de agosto de 2026:** la captura se inicia con una acción discreta sobre el control de micrófono y se detiene con otra acción discreta. **No** se exige mantener el botón pulsado.

**Motivo registrado.** El objetivo declarado de la vertical es grabar el montaje de HEAD-R1; mantener el ratón pulsado durante toda la intervención es incompatible con tener las manos en el Arduino y la protoboard.

**Salvaguardas que se conservan íntegras.** La decisión afecta a cómo se inicia y termina la captura, no a los límites ni a la privacidad:

- el micrófono solo puede estar activo tras una acción explícita y visible del usuario;
- se mantiene el tope de 60 s y 10 MiB por intervención de #126; alcanzado el límite, la captura se cierra sola y pasa a `TRANSCRIBIENDO`;
- el estado `ESCUCHANDO` debe ser inequívoco en pantalla mientras el micrófono esté abierto;
- se mantiene la revisión previa: cancelar en `REVISANDO` no crea mensaje ni persiste nada;
- no se habilita escucha permanente, palabra de activación ni detección automática de fin de turno; todo eso sigue fuera de alcance.

**Correcciones que obliga en #126:**

| Ubicación | Texto actual | Texto propuesto |
|---|---|---|
| Alcance permitido | *"Captura pulsar-para-hablar, con máximo de 60 s y 10 MiB por intervención."* | *"Captura iniciada y detenida por acción explícita del usuario, con máximo de 60 s y 10 MiB por intervención; alcanzado cualquiera de los dos límites la captura se cierra automáticamente."* |
| Prueba SV-002 | *"pulsar y soltar captura solo el intervalo visible"* | *"la captura cubre exactamente el intervalo entre la acción de inicio y la de parada, y el estado `ESCUCHANDO` es visible durante todo él"* |
| Prueba nueva SV-002b | — | *"alcanzado el tope de 60 s o 10 MiB, la captura se cierra sola, informa del motivo y no descarta el audio ya capturado"* |

**Corrección que obliga en #128.** §5.1 pasa a describir el ciclo completo, no solo el inicio: iniciar captura visible → `ESCUCHANDO` → detener → `TRANSCRIBIENDO` → `REVISANDO` → enviar, cancelar o repetir.

## 4. R-03 · Dónde vive la superficie

**Problema (MS-A01).** #126 promete modificaciones localizadas en `main_window.py`; #128 describe una superficie de ventana completa. `main_window.py` tiene 1615 líneas y organiza la aplicación en pestañas. Un widget de Model Studio embebido en la pestaña de conversación quedaría bajo una barra de pestañas, que es justo la interfaz técnica que #128 quiere evitar.

**Propuesta.** Model Studio es una **página conmutable de primer nivel dentro de la misma ventana y el mismo proceso**:

1. El widget central de `MainWindow` pasa a ser un `QStackedWidget` con dos páginas.
2. Página 0: la interfaz actual completa, sin ningún cambio de comportamiento — las pestañas Conversación, Conocimiento y Ajustes siguen exactamente como están.
3. Página 1: la superficie de Model Studio, construida en un módulo propio (`src/sirius/presentation/model_studio/`), con el fondo negro y la distribución 25/75 de #128 ocupando toda la ventana.
4. Conmutar oculta por completo la barra de pestañas, de modo que el modo limpio de #128 §9.1 se obtiene sin trucos.
5. La vuelta a la interfaz técnica es una sola acción, siempre disponible.

**Por qué esta opción.**

- Cumple literalmente *"no será una segunda aplicación independiente"* (#128 §2) y *"no crear una segunda aplicación"* (#126): mismo proceso, misma base de datos, mismos casos de uso, misma raíz de composición.
- Cumple *"no sustituirá la interfaz técnica actual"* (#128 §2): la página 0 queda intacta.
- El cambio real en `main_window.py` sí es localizado: envolver el widget central existente y añadir la acción de conmutación. No obliga a reescribir sus 1615 líneas ni a tocar la lógica de conversación, copias de seguridad o exportación.
- El código nuevo nace aislado en su propio paquete, con frontera de importación verificable por las pruebas de arquitectura ya existentes (`tests/unit/test_presentation_boundaries.py`).

**Alternativas descartadas.** Una pestaña más deja la barra visible durante la grabación y contradice el modo limpio. Una ventana de primer nivel separada complica el estado compartido y roza la lectura de *"segunda aplicación"*.

**Corrección que obliga en #126.** Sustituir `src/sirius/presentation/studio_mode_widget.py` por el paquete `src/sirius/presentation/model_studio/`, y declarar la conmutación de página como el cambio previsto en `main_window.py`.

## 5. R-04 · Máquina de estados unificada

Los estados son un contrato entre la lógica y la interfaz. Esta tabla sustituye a las listas parciales de #126, #127 y #128 §8, que hoy no coinciden.

### 5.1 Estados de interacción

| Estado | Significado | En #126 | En #128 | Comportamiento visual |
|---|---|---|---|---|
| `DESACTIVADO` | Model Studio apagado; no hay micrófono ni conexión de captura | sí | añadir | Superficie no activa; sin indicadores |
| `PREPARADO` | Listo para recibir texto o voz | sí | sí | Partículas en reposo; controles disponibles |
| `ESCUCHANDO` | Micrófono abierto tras acción explícita | sí | sí | Pulso suave en los ojos; indicador de captura inequívoco |
| `TRANSCRIBIENDO` | Convirtiendo audio a texto | sí | sí | Entrada bloqueada temporalmente; estado claro |
| `REVISANDO` | Transcripción editable antes de enviar | sí | sí | Texto editable; enviar, cancelar y repetir disponibles |
| `PENSANDO` | El modelo genera texto | sí | sí | Redistribución suave del campo de puntos |
| `EJECUTANDO` | Ejecutando un comando tipado, no generando texto | **añadir** | sí | Estado propio, distinguible de `PENSANDO` |
| `SINTETIZANDO` | Generando el audio de la respuesta | sí | **añadir** | Espera explícita antes de `HABLANDO` |
| `HABLANDO` | Reproduciendo la respuesta | sí | sí | Boca de puntos animada de forma mínima |
| `ERROR` | Fallo recuperable | sí | sí | Mensaje claro; degradación visual no destructiva |

Dos precisiones que resuelven la contradicción de MS-A06:

- **`EJECUTANDO` se conserva** y se define con precisión: es el estado de una orden tipada en curso —por ejemplo `START_RECORDING` o `SWITCH_SCENE` de #127— frente a `PENSANDO`, que es generación de texto. #128 lo introdujo sin definirlo; #126 no lo tenía porque no contempla comandos de captura.
- **`SINTETIZANDO` es obligatorio en la interfaz.** Es la espera entre el fin del texto y el comienzo del audio; sin representarla, el usuario cree que Sirius se ha colgado y repite la orden.

### 5.2 Estados de captura

Independientes de los de interacción y mostrados por separado, conforme a #128 §8 y al criterio de aceptación 10.

| Estado | Significado | En #127 | En #128 | Comportamiento visual |
|---|---|---|---|---|
| `DESACTIVADO` | Módulo Captura apagado | sí | añadir | Sin indicador de captura |
| `PREPARADO` | Backend confirmado y disponible | sí | añadir | Controles de grabación habilitados |
| `INICIANDO` | Orden de inicio enviada, sin confirmación | sí | **añadir** | Espera explícita; **no** se muestra `GRABANDO` |
| `GRABANDO` | El backend confirma grabación activa | sí | sí | Indicador rojo persistente, tiempo y escena si están disponibles |
| `PAUSADO` | Grabación pausada | sí | sí | Estado diferenciado; no se confunde con detenido |
| `CAMBIANDO` | Cambio de escena en curso | sí | añadir | Transición visible; escena anterior aún vigente |
| `DETENIENDO` | Orden de parada enviada, sin confirmación | sí | añadir | Espera explícita; no se afirma cierre |
| `ERROR` | Fallo del módulo de captura | sí | añadir | Degradación sin bloquear chat ni voz |
| `INCIERTO` | Estado real desconocido | sí | sí | No se afirma éxito; se solicita reconciliación al backend |

`INICIANDO` y `DETENIENDO` son las dos que más importan: son exactamente los intervalos en los que el modelo podría afirmar que ya se está grabando sin que el backend lo haya confirmado, y #127 lo prohíbe expresamente (*"las confirmaciones proceden del estado del backend, no de la frase del modelo"*).

## 6. R-05 · Incidencia que falta

**Propuesta.** Abrir **`SIRIUS-MODEL-STUDIO-UI-002` — Model Studio · Módulo Interfaz**, con `main` como rama base y el cuerpo completo que exige el validador (work id, bloque, objetivo, base y dependencias, alcance permitido, fuera de alcance, requisitos y pruebas, validaciones, rama base, condiciones de parada, salvaguardas).

Contenido propuesto, resumido:

- **Objetivo.** Construir la superficie de `SIRIUS-MODEL-STUDIO-UI-001` como página conmutable (R-03), con la conversación existente conectada y los estados representados de forma simulada, de modo que el usuario pueda grabar sesiones de trabajo antes de que existan voz y cámaras.
- **Alcance permitido.** Distribución 25/75, barra superior, barra inferior de iconos, zona auxiliar izquierda plegable, presencia de partículas animada, chat con etiquetas `TÚ` y `SIRIUS` sin avatares, caja única de entrada expandible, modo limpio, conmutación desde y hacia la interfaz técnica, y la máquina de estados de §5.1 con transiciones simuladas.
- **Fuera de alcance.** Captura de audio real, transcripción, síntesis, reproducción, backend de captura, cámaras, escenas y cualquier dependencia nueva.
- **Pruebas.** Los criterios 1 a 10 y 12 de `SIRIUS-MODEL-STUDIO-UI-001` §11, verificables sin audio ni hardware. El criterio 11 (parada de emergencia accesible durante grabación) pertenece a E3; el criterio 8 se verifica en E1 solo en su parte de texto.
- **Condición de cierre.** La ya redactada en `SIRIUS-MODEL-STUDIO-UI-001` §13: el usuario confirma proporciones, tipografía, presencia visual y ubicación de controles sobre una grabación real a 1080p.

**Salvaguarda específica que se propone añadir.** El botón de micrófono existe desde E1, visible y deshabilitado, con tooltip que declara que la voz aún no está disponible. Evita rediseñar la barra al llegar E2 y respeta el criterio 12 (*"corregir un componente no rediseña ni sustituye el resto de la interfaz aprobada"*).

## 7. R-06 · QtMultimedia y Quality

**Problema (MS-A02).** `from PySide6.QtMultimedia import ...` falla en Linux con `ImportError: libpulse.so.0`. `quality.yml` corre en `ubuntu-latest` e instala solo `libegl1 libgl1 libxkbcommon0`. Un import a nivel de módulo rompe la recolección de `pytest` aunque todas las pruebas usen adaptadores simulados.

**Propuesta, tres medidas conjuntas:**

1. **Import perezoso obligatorio.** Ningún módulo de `sirius.adapters.audio` importa `PySide6.QtMultimedia` a nivel de módulo. El import ocurre dentro del método que realmente abre el dispositivo. Los adaptadores simulados no tocan QtMultimedia en ningún momento.
2. **`libpulse0` en Quality.** Añadir el paquete al paso *"Install Qt system libraries for PySide6 (offscreen)"* de `quality.yml`, para que un import real sea posible en CI si alguna prueba futura lo necesita.
3. **Prueba de regresión.** Una prueba que verifique, por análisis de imports igual que hace `test_presentation_boundaries.py`, que ningún módulo de audio importa QtMultimedia a nivel de módulo. Convierte la salvaguarda en algo que el CI vigila, no en una convención que se olvida.

La medida 1 es la que protege; la 2 elimina la causa raíz; la 3 impide la regresión. Ninguna introduce dependencia nueva: QtMultimedia ya viene en PySide6 y `libpulse0` es una biblioteca del sistema del runner, no del proyecto.

**Corrección que obliga en #126.** Añadir las tres medidas al alcance permitido, antes del bloque del día 1.

## 8. R-07 · Registro de gasto de audio

**Problema (MS-A04).** `BudgetTracker.record_usage(input_tokens, output_tokens)` y `BudgetPolicy` solo entienden tokens de texto. #126 exige reutilizar el ledger sin nueva tabla y que SV-011 bloquee antes de llamar.

**Propuesta.** Reutilizar la persistencia y ampliar el tracker:

- `LLMUsageRepository` **no se toca**: almacena `year_month -> usd` y es agnóstico del origen. Sin tabla nueva y sin migración, como exige #126.
- `BudgetPolicy` incorpora las tarifas de audio necesarias (transcripción y síntesis) como campos propios con valor por defecto explícito.
- `BudgetTracker` incorpora un método de registro de coste de audio que acumula en el mismo mes UTC y respeta el mismo cerrojo.
- `has_remaining_budget()` **no cambia**: al acumular sobre el mismo total, el bloqueo previo al envío pasa a cubrir también el audio sin tocar la comprobación.

**Corrección que obliga en #126.** El alcance dice hoy *"reutilizar el ledger mensual de gasto actual, sin nueva tabla ni migración"*. Se propone precisar: *"reutilizar la persistencia de gasto actual sin nueva tabla ni migración, ampliando `BudgetPolicy` y `BudgetTracker` para contabilizar el coste de transcripción y síntesis en el mismo total mensual"*.

Sin esta ampliación, SV-011 pasaría en verde sin proteger nada: el gasto de audio nunca se registraría y el tope no se alcanzaría jamás por esa vía.

## 9. R-08 · Verificación de la voz

**Problema (MS-A09).** #126 fija `gpt-4o-mini-tts` con voz provisional `cedar`, y su día 2 compara `cedar`, `onyx` y `echo`. `onyx` y `echo` pertenecen al conjunto del endpoint de síntesis por lotes; `cedar` se introdujo asociada a la API Realtime, que #126 declara fuera de alcance.

**Propuesta.** Antes de fijar voz en documento, comprobar contra el proveedor qué voces admite realmente el endpoint autorizado, y sustituir en #126 *"voz provisional `cedar`"* por *"voz provisional pendiente de verificación entre las admitidas por el endpoint de síntesis"*. La elección final se decide en el día 2 con la evidencia delante, que es lo que #126 ya prevé.

Comprobación de coste prácticamente nulo que evita descubrir en mitad de la puerta del día 2 que una de las tres candidatas no es invocable.

## 10. R-09 · Ejecución en tres etapas

| Etapa | Contenido | Entregable | Depende de |
|---|---|---|---|
| **E1 · Concha grabable** | Superficie de #128 con conversación existente y estados simulados | El usuario puede grabar sesiones de trabajo con una interfaz propia | R-01, R-03, R-04, R-05, R-10 |
| **E2 · Voz mínima** | #126 corregido: hablar, transcribir, revisar, enviar, oír, detener, repetir, silenciar | Sirius habla y escucha dentro de la concha | E1, R-02, R-06, R-07, R-08 |
| **E3 · Captura y cámaras** | #127 completo, precedido de su investigación técnica | Grabación, escenas y cambio de cámara por voz e interfaz | E2, investigación técnica de #127 |

**E1 no amplía alcance.** Es el orden 1-2-4 que `SIRIUS-MODEL-STUDIO-UI-001` §13 ya recomienda, con su condición de cierre ya redactada. Lo único nuevo es reconocerlo como entregable con incidencia propia (R-05) en lugar de como preámbulo de #126.

**Efecto sobre la puerta de Sirius 0.2.** #127 declara que Model Studio debe quedar utilizable antes de reanudar la implementación productiva de 0.2, y su puerta G-MS-01 a G-MS-06 exige módulo de voz apto, dos ángulos físicos y una grabación real de HEAD-R1. Esa puerta **no se modifica**. La partición solo permite que E1 desbloquee la grabación mientras E2 y E3 avanzan, en lugar de esperar al paquete completo.

**Lo que la partición no hace.** No reduce ninguna prueba, no rebaja ninguna salvaguarda y no adelanta ninguna puerta. Reparte las mismas exigencias entre tres entregas verificables.

## 11. R-10 · Fusionar #128 primero

**Problema (MS-A07).** #126 y #127 ordenan partir de `main`, pero la especificación de interfaz aprobada solo existe en la rama de la PR #128. Un implementador que cumpla la instrucción no puede leer el documento que debe cumplir.

**Propuesta.** Fusionar #128 antes de abrir E1. Es documentación pura, `mergeable_state` está limpio y no toca código. Mientras siga abierta, cualquier trabajo sobre Model Studio parte de una base que no contiene su propia especificación.

El merge sigue exigiendo la autorización explícita prevista por el contrato operativo; esta propuesta no lo automatiza ni lo presupone.

## 12. R-11 · Envolvente de gasto — pendiente de decisión

DR-018 fija 20 USD/mes con aviso a 15. Ese envolvente se dimensionó para conversación escrita; una sesión de grabación añade transcripción y síntesis por turno.

Tres opciones, **ninguna propuesta como preferente** porque afecta a una decisión canónica que solo el usuario puede tomar:

1. Mantener 20 USD/mes y aceptar que Model Studio consume del mismo bolsillo.
2. Mantener el total y asignar a Model Studio un sublímite propio dentro de él.
3. Revisar DR-018 al alza, lo que exige decisión canónica expresa.

Lo que sí conviene decidir antes de E2, con independencia de la opción: agotar el presupuesto a mitad de una grabación es un fallo visible, y el aviso proactivo ya existente (B7c) debería cubrir también el gasto de audio.

## 13. Qué queda sin tocar

- La dirección de diseño visual de `SIRIUS-MODEL-STUDIO-UI-001`: partículas, ojos, boca, paleta, chat sin avatares, caja única, iconos con tooltip. No se propone ningún cambio estético.
- Los documentos canónicos: Producto, Arquitectura Técnica, ATD, identidad, memoria y decisiones.
- La arquitectura `presentation -> application -> ports <- adapters`.
- Todas las exclusiones de alcance de #126 y #127: Realtime, escucha permanente, clonación de voz, visión artificial, edición automática, control general del ordenador, control de HEAD-R1.
- La prohibición de merge automático en las tres piezas.
- La puerta G-MS-01 a G-MS-06 previa a Sirius 0.2.

## 14. Estado de ejecución al 7 de agosto de 2026

Lo que existe de verdad en la rama `claude/model-estudio-review-qpbknq`, verificado con la suite completa (1605 pruebas en verde), Ruff y mypy.

### E1 · Concha grabable — ENTREGADA

- Superficie conmutable con la interfaz técnica intacta en la página 0.
- Presencia geométrica animada, determinista, que se detiene cuando no está a la vista.
- Conversación existente conectada, con streaming, historial y persistencia compartidos.
- Caja única expandible, barra de iconos dibujados en código, modo limpio.

### E2 · Voz — ENTREGADA EN CÓDIGO, SIN PRUEBA REAL

- Los cuatro puertos, el orquestador, los adaptadores de Qt y de OpenAI, y los simulados.
- Ciclo completo: pulsar, hablar, pulsar, revisar, corregir, enviar, oír.
- Detener, silenciar y repetir.
- Presupuesto de audio contabilizado en el mismo total mensual.

> **Lo que todavía NO está demostrado**
> Ninguna prueba automática usa micrófono, altavoces, red ni clave real: todas van con dobles. Que la voz se oiga bien, que el micrófono capte en Windows y que la latencia sea aceptable **solo puede confirmarlo la prueba manual del usuario**. Hasta entonces, E2 no puede declararse APTA.

### E3 · Captura y cámaras — SIN EMPEZAR

Ni una línea de código. La investigación técnica previa que el propio #127 exige está registrada en `SIRIUS_MODEL_STUDIO_CAPTURA_INVESTIGACION.md`, y no sustituye a la prueba real.

## 15. Lo que sigue pendiente

1. **R-11**, el envolvente de gasto: única decisión de este documento que sigue sin tomarse.
2. **Fusionar #128**, para que la especificación de interfaz exista en `main`.
3. **Prueba manual de la voz en Windows 11** con clave real: elegir voz entre las que sí existen, comprobar latencia y confirmar que no queda audio en disco ni en registros.
4. **Decidir el backend de captura** a partir de la investigación, y verificarlo antes de escribir código.
