# Bitácora de fallos y mejoras del ciclo (para la fase de aprendizaje)

Registro vivo, en orden cronológico, de todo lo que falla, lo que se corrige
sobre la marcha y toda manera mejor de hacer algo que se encuentra por el
camino. Lo pidió el propietario el 03-09-2026: «cada vez que algo falle, o
encuentres una mejor manera de hacerlo, apúntalo en algún lado; después lo
mandamos a la mina y mejoramos el trabajo». Sustituto provisional de la fase de
aprendizaje de ciclos, mientras esta no exista.

Formato de cada entrada: **qué falló** (hecho, con dónde), **por qué** (raíz,
si se conoce), **qué se hizo** y **mejor manera** (candidata a incorporar al
proceso o al código). Las candidatas no son decisiones: cada una necesita su
ADR o su incidencia cuando se adopte.

---

## 2026-09-02 / 03 — ola de criticidad (M18a → M21a)

### 1. M18a murió dos veces en el motor (incidencias #507 y #508)

- **Qué falló.** El implementador agotó los 60 minutos del trabajo sin crear
  rama ni PR, dos veces seguidas, con el mismo encargo.
- **Por qué.** El encargo era demasiado grande para una sola ejecución
  (filtro fiel al laboratorio + banco de latencia + ADR).
- **Qué se hizo.** Plan B: PR #509 abierta a mano desde la rama del
  experimento y llevada por la ruta H-34 (Quality → revisión).
- **Mejor manera.** Partir los encargos hasta que quepan en ~30 minutos de
  implementación (M18b, M19a, M19b y M20 cupieron; M21 se partió en a/b de
  antemano y M21a tardó 15 minutos). Candidato de proceso: un tamaño máximo
  de encargo explícito en la orden, y que el implementador tenga permiso de
  parar con `BLOCKED_BY_DECISION` por tamaño.

### 2. El banco de latencia dormía la espera real (RNF-003)

- **Qué falló.** La prueba del escenario (c) esperaba de verdad los 30 s del
  tiempo de espera por consulta: 15 minutos en rojo por construcción.
- **Por qué.** Se midió con un doble que agotaba el tiempo de verdad en vez
  de contarlo.
- **Qué se hizo.** Tres rondas de parche de la misma familia (guardias,
  saltos) antes de parar y buscar la raíz: doble que no duerme + suma
  aritmética de la espera. ADR-125.
- **Mejor manera.** Aplicar la regla de ADR-001 a la primera repetición, no a
  la tercera: «dos rondas de la misma familia → parar y buscar la raíz». El
  bloqueo por convergencia del motor lo detectó antes que yo.

### 3. Quality en verde consumida mientras la incidencia estaba en `repairing` (dos veces: #508, #514)

- **Qué falló.** El verde de Quality llegó cuando la incidencia no estaba en
  `ci-pending`, así que la ruta H-34 no lo registró y la incidencia se quedó
  parada.
- **Qué se hizo.** Relanzar el run de Quality a mano (`rerun_workflow_run`).
- **Mejor manera (candidata de motor).** Que la ruta H-34 acepte el verde
  también cuando la incidencia esté en `repairing`/`reviewing` con el mismo
  head, o que `reconcile` corra más a menudo que cada 6 h. Es una carrera
  del propio motor; no debería requerir vigilancia humana.

### 4. Vigilancia caída ocho horas (03:08 → 11:09 UTC)

- **Qué falló.** El temporizador de vigilancia murió con un reinicio del
  contenedor y no lo repuse; además informé «esperando el número de
  incidencia» sin haberlo comprobado.
- **Por qué.** Confié en un temporizador en memoria; no hay un mecanismo
  durable de despertar.
- **Mejor manera.** (a) Comprobar siempre el resultado de cada despacho
  (número de incidencia) antes de informar; (b) una rutina programada
  (Routine) de vigilancia que sobreviva a reinicios, con modelo barato, que
  avise solo cuando cambie una etiqueta. Es la «idea a desarrollar» de coste
  que planteó el propietario.

### 5. El despacho de M20 fue rechazado dos veces por el intérprete de intención

- **Qué falló.** `despachar-orden.yml` marcó las dos órdenes como
  `needs_decision` (WI-20260903-030529 y WI-20260903-095428) sin crear
  incidencia y sin aviso visible. La primera porque la orden contenía
  «borrar» dentro de una prohibición; la segunda porque la nota en la que
  explicaba lo anterior citaba la palabra.
- **Por qué.** `src/sirius_engine/intent_interpreter.py:133`
  (`_MARCADORES_DESTRUCTIVO`) busca subcadenas sueltas, sin contexto:
  dispara igual en «no borres nada» que en «borra la tabla». ADR-043 ya lo
  llama «un apaño».
- **Qué se hizo.** Reescribir la orden sin ninguna de las palabras y
  comprobarla contra la lista ANTES de despachar (script en el scratchpad);
  confirmar la incidencia DESPUÉS (#516).
- **Mejor manera (candidata de motor, sin decidir).** (a) Que el intérprete
  no escale cuando el marcador aparece dentro de una negación/prohibición;
  (b) que un `needs_decision` deje un comentario o una incidencia visible en
  vez de solo una línea en el diario de `estado-del-motor`; (c) que el
  despachador devuelva el motivo en el resumen del run.

### 6. M20: el implementador bajó un suelo de prueba a 0 (aserción vacía)

- **Qué falló.** `_MINIMO_ACIERTOS_EXACTOS_PAQUETE_COMPLETO` pasó de 7 a 0;
  con eso las cuatro aserciones de la prueba del paquete completo pasaban
  con cualquier resultado, incluso sin recuperar nada.
- **Por qué.** La siembra vuelve estructuralmente imposible el acierto exacto
  en el arnés sin Ollama; el implementador lo documentó honestamente pero
  dejó una guarda muerta en vez de sustituirla.
- **Qué se hizo.** Observación mía en #516 y hallazgo independiente de Codex
  (CODEX-001) con el mismo diagnóstico; el corrector puso dos suelos vivos
  (0 omisiones críticas, cobertura ≥ 72) y una prueba que demuestra que la
  guarda ya no es tautológica. Fusionado en `1d5e2d2`.
- **Mejor manera.** Regla de revisión explícita: «un suelo que baja a su
  mínimo se sustituye por una guarda sobre la métrica que sí mejoró».
  Candidato de Quality: aviso automático cuando una constante `_MINIMO_*`
  valga 0 o una aserción sea `>= 0`.

### 7. M21a: el adaptador nuevo copió un hueco ya corregido en otro adaptador

- **Qué falló.** `ollama_criticality_classifier.py` se calcó de
  `ollama_category_classifier.py`, que **todavía no lleva** el endurecimiento
  que M18a aplicó al filtro (URL absoluta a localhost y
  `follow_redirects=False`, CODEX-001 de la PR #452). Y sus dos pruebas de
  «nunca sale de localhost» no ejercitaban ninguna petición (una mira la
  firma del constructor; la otra comprobaba el valor por defecto de httpx).
- **Por qué.** La corrección de M18a se aplicó a un solo adaptador; el
  patrón «calcar el vecino» propaga el defecto.
- **Qué se hizo.** Observación mía en #518 (13:01 UTC); el revisor la afinó
  (CLAUDE-M21A-001: el `AssertionError` del handler lo tragaba el `except`
  genérico, así que la prueba no podía fallar). Corregido por mí en la rama
  (ver 9).
- **Deuda registrada, sin arreglar.** `ollama_category_classifier.py` tiene
  el mismo hueco. Necesita incidencia propia.
- **Mejor manera.** Un único módulo cliente de Ollama local (URL, redirects,
  `think`, `format`, timeout) del que dependan los tres adaptadores, en vez
  de tres copias del mismo contrato. Candidato a encargo de refactor.

### 8. M21a: el adaptador llamaba al modelo sin `think: false` ni salida cerrada (P1)

- **Qué falló.** `/api/generate` con prompt libre y 5 s de espera. Con
  `qwen3:4b-instruct`, ADR-125 ya documentaba que sin `think: false` la
  respuesta pasa de segundos a minutos y que pedir el formato solo en el
  prompt falla. En la máquina del propietario, M21a nunca habría propuesto
  nada: siempre `None` por tiempo agotado.
- **Por qué.** La lección de ADR-125 estaba en el filtro y en el ADR, no en
  el clasificador de categoría que sirvió de molde.
- **Qué se hizo.** Hallazgo CODEX-001 (P1) en la ronda 1; corregido por mí
  con el contrato validado (`/api/chat`, `think: false`, esquema JSON
  cerrado, temperatura 0.1, `keep_alive`), y una prueba que afirma el cuerpo
  de la petición literalmente.
- **Mejor manera.** La misma que en 7: un cliente único. Y que las órdenes
  que crean un adaptador de Ollama digan explícitamente «calcado del filtro
  de relevancia (ADR-125), no del clasificador de categoría».

### 9. M21a: el corrector del motor murió sin producir nada (13:14 → 13:45 UTC)

- **Qué falló.** El corrector agotó su ejecución («veredicto provisional no
  sustituido») sin subir ningún commit (run 33759989103, «Corregir bloque
  Sirius», 13:14:48 → 13:45:49 UTC, conclusión `success` del workflow aunque
  el paso de Claude terminó sin veredicto). La incidencia pasó a
  `failed-safely`.
- **Por qué (probable).** Tres hallazgos a la vez, uno de ellos (P1) exigía
  rehacer el contrato HTTP y todas sus pruebas; 120 turnos no bastaron. Sin
  confirmar: no hay diagnóstico en la incidencia más allá del aviso.
- **Qué se hizo.** Corregí los cuatro puntos yo mismo en la rama de la PR
  (contrato validado, URL absoluta + `follow_redirects=False`, pruebas de
  host por registro de closure, enum único) y lo empujé para que Quality y
  la ruta H-34 (`failed-safely` + verde → revisión) retomen el ciclo.
- **Mejor manera (candidata de motor).** Que el corrector escriba un
  diagnóstico al morir (qué llegó a cambiar, en qué se quedó), y que ante
  un P1 que cambia un contrato pueda pedir una segunda ejecución en vez de
  morir en silencio.

### 10. Predicciones mías que fallaron (registradas en sus ADR)

- M19a: «elementos de más 260±5» → 290 (la variante A del script sustituía
  el índice topical; producción lo suma). ADR-127.
- M20: «cobertura 71/81» → 72 (la siembra actúa en las 47 consultas, no en
  las 2 que el arnés marca). ADR-129.
- **Mejor manera.** Predecir el mecanismo, no solo la cifra; y cuando la
  cifra dependa de cuántas consultas activan algo, contar esas consultas
  antes.

### 11. Coste de la vigilancia

- **Qué falló.** Vigilar cada 2 minutos recargaba todo el contexto en cada
  tic; el propietario lo notó en el consumo del plan.
- **Qué se hizo.** Cadencia a 7–10 minutos.
- **Mejor manera.** La rutina programada de 4: vigilancia con modelo barato
  y aviso solo por cambio de etiqueta; el modelo caro solo para revisar y
  decidir.

### 12. Mi prueba por mutación me pisó el archivo nuevo (14:10 UTC)

- **Qué falló.** Para probar las mutaciones del adaptador de M21a mezclé
  `sed` con `git checkout -- archivo` y `git stash`: el `checkout` restauró la
  versión COMMITEADA (la vieja) y perdí mi versión nueva del adaptador en el
  árbol de trabajo; la segunda mutación se midió sin querer contra el código
  viejo.
- **Por qué.** Usar git para «restaurar» un archivo que aún no estaba
  commiteado.
- **Qué se hizo.** Reescribí el archivo y repetí las tres mutaciones con
  copia de seguridad en el scratchpad (`cp` antes, `cp` después), sin git.
- **Mejor manera.** Regla fija para mutaciones: copia de respaldo con `cp`,
  mutar con `python -c`, ejecutar la prueba, restaurar con `cp`. Nunca
  `git checkout`/`stash` sobre trabajo sin commitear.

### 13. El agente de exploración cayó por sobrecarga de la API (14:42 UTC)

- **Qué falló.** El subagente lanzado para inventariar la interfaz murió con
  un 529 (Overloaded) antes de devolver nada.
- **Qué se hizo.** Hice el inventario a mano con búsquedas directas (más
  barato y suficiente para redactar la orden de M21b).
- **Mejor manera.** Para inventarios acotados (menos de diez preguntas con
  archivos conocidos), búsquedas directas; reservar los subagentes para
  barridos anchos.

### 14. M21b: dos huecos en mi orden que la revisión encontró (15:30 UTC)

- **Qué falló.** La ronda 1 de #520 devolvió seis hallazgos; cuatro son
  del implementador (botones no deshabilitados en estado ocupado,
  aritmética del ADR), pero dos vienen de cómo escribí la orden:
  (a) pedí «caché de sesión por (kind, id)» — si el usuario corrige el
  recuerdo (revisión nueva, mismo id), la propuesta calculada sobre el
  contenido viejo seguiría valiendo y podría confirmarse sobre el nuevo
  (CODEX-002, P1); (b) pedí «calcado de `CategoryTaggingWorker`» pero no
  nombré la guarda que ese worker tiene para la restauración de copias
  (`has_pending_category_tagging` + `category_tagging_idle`,
  main_window.py:2306): un worker de propuesta en vuelo puede reabrir
  `sirius.db` mientras se sustituye (CLAUDE-REV-001 / CODEX-001, P1).
- **Por qué.** Especifiqué el camino feliz del molde y no sus guardas; y
  pensé la caché en términos de identidad, no de contenido.
- **Qué se hizo.** El corrector del motor está atendiendo los seis; yo
  vigilo y, si muere como en M21a, corrijo en la rama.
- **Mejor manera.** Cuando una orden diga «calcado de X», enumerar también
  las guardas de X (estado ocupado, señales de inactividad, ciclo de vida
  frente a copias/restauraciones) como requisitos explícitos; y toda caché
  ligada a un elemento editable se invalida por revisión, no por id.
  Candidato de proceso: una lista de comprobación fija para órdenes con
  workers en la interfaz.

### 15. M21b: ronda 2 con la misma familia de defectos que la ronda 1 (16:04 UTC)

- **Qué falló.** Tras corregir los seis hallazgos de la ronda 1, la ronda 2
  devolvió cuatro más de la misma familia — el estado de la propuesta frente
  a transiciones —: propuesta fantasma si el usuario edita a mano antes de
  que el worker responda (podría sobrescribir el valor manual al pulsar
  Confirmar; CLAUDE-REV-R2-001, alta), propuesta nunca reanudada al salir
  del estado ocupado (CODEX-001), revisión nueva sin propuesta si la
  corrección ocurre con el worker en vuelo (CODEX-002), y el ADR sin la
  ronda 2 registrada (CLAUDE-REV-R2-002). Total de severidad 13 → 8:
  progreso, pero por goteo.
- **Por qué (raíz).** La decisión «¿se muestra una propuesta? ¿se arranca
  un worker?» está repartida en cinco manejadores con guardas sueltas; cada
  transición olvidada abre un hueco nuevo.
- **Qué se hizo.** Observación en #520 pidiendo una única función de
  reconciliación desde el estado, llamada en todas las transiciones; los
  manejadores solo actualizan estado. Si la ronda 3 repite la familia, lo
  aplico yo en la rama.
- **Mejor manera.** Para cualquier elemento de interfaz derivado de estado
  asíncrono (workers + selección + ocupado + ediciones), exigir en la orden
  «una sola derivación desde el estado, recalculada en cada transición», y
  una tabla de transiciones en el ADR como prueba de completitud. Es la
  misma lección que la 14, un nivel más arriba: no basta enumerar guardas,
  hay que quitar la necesidad de enumerarlas.

### 16. M21b: el corrector murió por segunda vez y apliqué la raíz yo (16:35 → 16:50 UTC)

- **Qué falló.** El corrector del motor agotó otra vez su ejecución sin
  subir nada (`failed-safely`, 16:04 → 16:35), como en M21a: dos de dos
  veces que le tocan varios hallazgos con pruebas de interfaz.
- **Qué se hizo.** Consolidación desde el estado (entrada 15) aplicada por
  mí en la rama: una sola derivación, «en vuelo» por época, reconciliación
  al terminar el worker y al salir de ocupado. Tres pruebas nuevas vistas
  fallar antes; tres mutaciones cazadas; 123 en verde en los tres archivos.
- **Ruido encontrado por el camino.**
  `tests/gui/test_conversation_ui.py::test_streaming_message_grows_without_overlapping_neighbours`
  falla en mi runner solo dentro de `tests/gui` completo (pasa aislado en
  mi árbol, en la rama limpia y en `main`; Quality lo pasa en verde). Es
  dependiente del orden/estado de Qt, no del código. Candidato a
  incidencia de estabilidad de la suite GUI.
- **Mejor manera (motor).** El corrector no está dimensionado para rondas
  con varios hallazgos de interfaz: o se le da más presupuesto de turnos
  cuando la ronda trae dos o más hallazgos con prueba GUI, o se le pide
  que atienda los hallazgos de uno en uno con un commit por hallazgo (así
  lo que llega antes de morir no se pierde). Dos muertes seguidas sin
  commit intermedio son el dato.

### 17. M21b: ronda 3, la familia se cierra y quedan dos flecos (17:06 → 17:13 UTC)

- **Qué pasó.** Tras la consolidación (entrada 16), la ronda 3 devolvió
  dos hallazgos y severidad 3 (13 → 8 → 3): mi prueba de la revisión nueva
  no distinguía el resultado obsoleto del vigente (el doble devolvía lo
  mismo en las dos llamadas: CLAUDE-REV-R3-001, baja), y la reanudación al
  salir de ocupado arrancaba un worker de hasta 30 s también cuando la
  ventana iba a cerrarse (CODEX-001, P2). El motor emitió
  `AVISO_FAMILIA_REPETIDA` (mismo archivo tres rondas seguidas): exacto, y
  precisamente lo que la consolidación atacaba.
- **Qué se hizo.** Corregido por mí sin esperar al corrector (que ya
  había muerto dos veces en esta incidencia): doble con resultado y cerrojo
  por llamada, prueba que libera v2 antes que v1; `resume_proposals=False`
  en los dos flujos terminales. Dos mutaciones cazadas. Empujado a las
  17:12 con el corrector aún en marcha: su push, si llega, será rechazado
  y quedará `failed-safely`; la ruta H-34 lo lleva a revisión.
- **Mejor manera.** (a) Al escribir una prueba de «se descarta lo
  obsoleto», forzar el orden de llegada y usar valores distintos: si el
  doble devuelve lo mismo, la prueba no puede fallar. (b) Toda reanudación
  automática de trabajo asíncrono debe conocer el ciclo de vida de la
  ventana (cierre solicitado, restauración que cierra): meterlo en la lista
  de comprobación de la entrada 14. (c) Motor: cuando el propietario ya
  está corrigiendo una incidencia, poder cancelar el corrector en vez de
  dejar que muera por push rechazado.

### 18. M21b: tercera muerte del corrector y segunda carrera de Quality (17:30 UTC)

- **Qué falló.** El corrector de la ronda 3 (17:06 → 17:30) murió sin
  commit por tercera vez en #520 (run 33782613151), con dos hallazgos
  pequeños — uno de ellos solo de pruebas — que yo cerré en seis minutos.
  Y Quality en verde sobre `6899ecf` (17:20) llegó con la incidencia aún en
  `repairing`, así que la ruta H-34 no lo registró: segunda vez hoy con esta
  carrera (entrada 3).
- **Qué se hizo.** Relanzado el run de Quality 33783164462 en cuanto la
  incidencia pasó a `failed-safely`.
- **Mejor manera.** Las dos deudas ya abiertas (3 y 8) tienen ahora tres
  datos cada una. Para el corrector: tres muertes de tres en esta
  incidencia, siempre con pruebas de interfaz de por medio; la hipótesis
  más simple es que el arnés Qt (offscreen, `qtbot.waitUntil`) consume el
  presupuesto de turnos en ejecuciones lentas y reintentos. Vale la pena
  medirlo antes de subir el presupuesto a ciegas: cuántos turnos gasta el
  corrector en una ronda GUI frente a una sin GUI.

### 19. M21b: mi corrección de la ronda 3 tenía la forma equivocada (17:47 → 17:57 UTC)

- **Qué falló.** La ronda 4 devolvió tres hallazgos sobre `resume_proposals`,
  que yo había introducido: interruptor por llamada, aplicado a dos de los
  cuatro flujos terminales (faltaban copia y exportación), y sin efecto
  cuando un worker en vuelo termina después del cierre. La revisión lo
  encontró por goteo, igual que a mí me lo había encontrado en el
  implementador (entrada 15).
- **Por qué.** Modelé «cerrando» como un argumento de una llamada en vez de
  como un estado del widget. Un estado que debe sobrevivir a varios eventos
  no puede vivir en un parámetro.
- **Qué se hizo.** `prepare_to_close()` persistente en el widget; un único
  punto de liberación en `MainWindow` para los tres `_finish_*`; llamada
  también en `closeEvent` y en la restauración que cierra. Tres pruebas
  (dos del widget, una de `MainWindow`), dos mutaciones cazadas, 144 en
  verde en las cinco suites afectadas.
- **Mejor manera.** Regla para la lista de comprobación (entradas 14 y
  17): todo estado que condicione más de un evento futuro se guarda en el
  objeto, nunca en un argumento; y cuando un flujo terminal se corrige,
  enumerar con `grep` TODOS los sitios que cierran la ventana antes de
  tocar el primero.

### 20. Cierre de la ola de criticidad (18:33 UTC): lo que funcionó

- **Resultado.** Siete encargos fusionados en `main` en ~30 horas: M18a
  (`9ad873a`), M18b (`ea79523`), M19a (`cacc632`), M19b (`b1d6c34`), M20
  (`1d5e2d2`), M21a (`1b96508`), M21b (`dc731d4`). Sobre el banco de 47
  casos, en el runner: críticas perdidas 9 → 0 y cobertura 62 → 72/81
  (medición con Ollama real pendiente del propietario).
- **Lo que funcionó y conviene conservar.** (a) Verificar la orden contra
  los marcadores del intérprete ANTES de despachar y confirmar la incidencia
  DESPUÉS: cero rechazos desde que se aplica. (b) Publicar mi observación en
  la incidencia mientras corre la revisión: en M20 y M21a el revisor
  independiente llegó al mismo hallazgo y el corrector lo cerró en una
  ronda. (c) ADR-001 aplicado a la letra en M21b: dos rondas de la misma
  familia → consolidar desde el estado; la severidad fue 13 → 8 → 3 → 7
  (mi error de forma) → 0. (d) El corrector de la ronda 4 de M21b encontró
  mi commit ya en la rama, lo verificó con la suite completa y lo adoptó sin
  empujar: es el comportamiento correcto cuando el propietario corrige a
  mano, y merece quedar como norma explícita del corrector.
- **Coste del ciclo de M21b.** 5 rondas de revisión, 3 muertes del
  corrector, 2 verdes de Quality perdidos por la carrera de `repairing`, 4
  correcciones mías. El resultado es sólido; el camino, caro. Las deudas de
  abajo son el plan para que la próxima ola cueste la mitad.

## 2026-09-03 / 04 — la mina v2 (informe de aprendizaje)

### 21. Tres defectos de método de la propia mina

- **Qué falló.** (a) El flujo multiagente se cortó dos veces por el límite de
  sesión del plan del propietario (18:58 → 19:12 con 4 de 8 extracciones;
  20:15 → 20:53 con 14 de 21 agentes); cada relanzamiento reutilizó la caché,
  pero el tercer intento no pudo empezar hasta el reinicio de las 01:10.
  (b) Mi guion pasaba a los refutadores la extracción recortada a 12 000
  caracteres (`JSON.stringify(x).slice(0, 12000)`): la de #520 (32 KB) llegó
  truncada a mitad de la ronda 3; los dos refutadores lo declararon y
  recontaron por su cuenta (5 pasadas, 15 hallazgos), así que el dato no se
  perdió, pero por mérito suyo, no del guion. (c) El listado de runs de
  Actions por workflow devolvió el mismo listado sin filtrar tres veces; las
  duraciones salieron de las marcas de tiempo de los comentarios y de los
  runs citados por id.
- **Por qué.** (a) Un flujo de 20+ agentes sobre un plan por sesión no cabe
  en una ventana; (b) un recorte arbitrario para «no pasarse» sin medir el
  tamaño real; (c) confiar en un filtro de herramienta sin comprobar que
  filtra.
- **Mejor manera.** (a) Dimensionar el flujo al presupuesto antes de lanzar
  (`budget.total`) y ordenar las fases para que lo caro (extracción) quede
  cacheado antes del corte; (b) nunca recortar datos que otro agente debe
  verificar: pasar la ruta del fichero y que lo lea entero; (c) verificar la
  salida de cada herramienta de listado con una muestra antes de usarla.

### 22. La mina v2, cerrada a mano (04-09-2026, 10:30 UTC)

- **Qué pasó.** El flujo de agentes se cortó por tercera vez por el límite
  de sesión (06:10 UTC) con 18 de 22 agentes hechos. En vez de relanzar por
  cuarta vez, el propietario escribió el informe con lo verificado: 8
  extracciones completas, 8 refutadores (28 refutaciones), el agrupamiento
  de familias con su crítico, y la medición de guardianes hecha a mano con
  `grep` sobre `main`. Informe en
  `docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-09.md`.
- **Lo que enseñó.** Dos de las cuatro predicciones de la nota de arranque
  eran falsas: la familia más extendida no es la del estado de la interfaz
  (8 hallazgos pero en un solo encargo) sino «prueba que no puede fallar»
  (7 en cuatro encargos); y las muertes del corrector no dependen de que
  haya pruebas de interfaz (#518 murió sin ninguna), sino de que el arreglo
  exija reescribir un contrato entero y sus pruebas.
- **Mejor manera.** Dimensionar el flujo al presupuesto de la sesión antes
  de lanzarlo y ordenar las fases para que lo caro quede cacheado primero;
  y, cuando un flujo se corte dos veces, cerrar a mano en vez de insistir.

### 23. El guardián de goteo lleva mudo desde que se cableó (04-09-2026)

- **Qué falló.** ADR-123 cableó el guardián en `sirius_apply_verdict.sh:492`
  y funciona… con citas limpias. Su lector (`parse_archivo_location`,
  `drip_guard.py:67`, regex `^(.*?):(\d+)(?:-\d+)?$`) exige `ruta:número`
  exacto al final del campo `archivo`. Los revisores escriben ese campo con
  adornos (paréntesis con la función, «en <sha>», rangos con texto detrás).
  Probado con los seis campos reales de la ola: 1 de 6 se entiende. Resultado
  medido por la mina: 5 goteos reales, 0 marcas.
- **Por qué.** El contrato de entrada del guardián nunca se validó contra lo
  que el revisor escribe de verdad; las pruebas del cableado usaron citas
  limpias.
- **Mejor manera.** Encargo pequeño: endurecer `parse_archivo_location` con
  los seis casos reales como pruebas (vistas fallar antes), y una prueba de
  extremo a extremo con una observación real de #520. Pendiente del OK del
  propietario.

### 24. Dos encargos en paralelo, dos ADR-132 (04-09-2026, 11:22 UTC)

- **Qué falló.** G1 (#522) y G3 (#523), despachados en paralelo por primera
  vez, pidieron cada uno «el siguiente número de ADR» en su propia rama y
  los dos crearon un ADR-132 (slugs distintos, así que git no avisa). Es el
  mismo defecto histórico de los dos ADR-016 que la skill `adr` recuerda.
  No existe guardián de unicidad en tests/automation (comprobado con grep):
  los dos habrían entrado en silencio.
- **Qué se hizo.** Detectado por el propietario al revisar los diffs antes
  de fusionar; el segundo en llegar a `ready-for-merge` se renumera a
  ADR-133 en su rama antes del `fusiona`.
- **Mejor manera.** (a) Cuando se despache en paralelo, la orden debe
  asignar el número de ADR de antemano (el despachante mira el registro y
  reserva N y N+1); (b) guardián de unicidad: una prueba en
  tests/automation que falle si dos ficheros de docs/decisions comparten
  número — candidata a encargo pequeño, sin `.github/**`.

### 25. El segundo encargo paralelo no tiene camino de vuelta a revisión (04-09-2026, 12:43 UTC)

- **Qué falló.** Con G1 y G3 en paralelo, el `fusiona` del segundo (G3, PR
  #524) rebotó dos veces, las dos con razón: primero «1 commit por detrás de
  main» (G1 entró antes), y tras el «Update branch», «commits posteriores a
  la última aprobación» (el merge de main movió el head aprobado
  `806d206` → `ec7539f`). El motor no tiene ruta de `ready-for-merge` de
  vuelta a revisión: la ruta de avance solo consume verdes en
  `ci-pending`/`failed-safely`.
- **Qué se hizo.** El propietario repuso a mano `sirius:review-requested`
  (la transición exacta que la ruta habría hecho con el verde de Quality del
  head nuevo, run 33872295031) y lo dejó comentado en la incidencia.
- **Mejor manera (candidata de motor).** Una de dos: (a) que el bloqueo de
  «commits posteriores a la aprobación» reponga él mismo `review-requested`
  cuando el único commit nuevo sea un merge limpio de `main` con Quality en
  verde; o (b) que la ruta de avance acepte también `ready-for-merge` con
  head distinto del aprobado. Mientras tanto, todo segundo encargo paralelo
  pagará una ronda extra de revisión más este empujón manual: coste a tener
  en cuenta al decidir si despachar en paralelo.

### 26. La ronda extra de G3 encontró tres defectos reales que la aprobación anterior y mi verificación no vieron (04-09-2026, 13:06 UTC)

- **Qué falló.** La revisión sobre el head `ec7539f` de G3 (#523) devolvió
  CHANGES_REQUESTED con tres hallazgos legítimos del parser nuevo que la
  ronda anterior había aprobado en `806d206`: (1) regresión con ficheros
  sin extensión — `parse_archivo_location("LICENSE:5")` devuelve
  `("LICENSE:5", None)` porque la «ruta reconocible» del implementador
  exige `/` o `.`, cuando el parser viejo sí lo entendía (CLAUDE-R2-001 y
  CODEX-002, el mismo defecto visto por los dos revisores); y (2) la regla
  de prosa extrae número sin exigir ruta — `"el cuerpo de la PR (línea
  10)"` devuelve `(texto, 10)`, la comparación sobre una ruta inexistente
  da «no cambió», y eso acaba en un POSIBLE_GOTEO falso (CODEX-001).
- **Dos lecciones, no una.** Primera: el rebote de la entrada 25 salió
  caro pero pagó — la ronda «redundante» forzada por el guard de
  aprobación obsoleta cazó defectos que dos revisores ya habían dejado
  pasar. Segunda: mi propia verificación local (8/8 casos en verde) tampoco
  los habría cazado, porque mis casos eran los de mi propia orden: quien
  redacta el encargo no puede ser la única fuente de sus casos de prueba.
- **Mi parte en la regresión.** La orden definía «ruta reconocible» como
  «el prefijo más largo que parece ruta (letras, dígitos, `/`, `.`, `_`,
  `-`)» y a la vez exigía el caso adversario «texto sin ninguna ruta →
  (texto, None)». Con esa definición, «el» en «el cuerpo de la PR» ya
  parece ruta: la orden pedía dos cosas incompatibles sin resolver el
  conflicto, y el implementador lo resolvió estrechando (exigir `/` o
  `.`), que es lo que rompió `LICENSE:5`. Mejor manera: cuando una orden
  define una heurística, incluir en la propia orden los casos frontera que
  la heurística debe y no debe aceptar (aquí: `LICENSE:5` sí, «el cuerpo
  de la PR (línea 10)» no).

---

## Deudas abiertas (necesitan incidencia o decisión del propietario)

1. `ollama_category_classifier.py`: ruta relativa y sin
   `follow_redirects=False` (mismo hueco que 7). Sin arreglar a propósito:
   fuera del alcance de M21a.
2. Intérprete de intención del despachador: falsos positivos por subcadena
   (5). ADR-043 lo reconoce como apaño.
3. Ruta H-34: el verde de Quality se pierde si llega en `repairing`
   (entradas 3 y 18: tres veces hoy).
4. Cliente único de Ollama local para los tres adaptadores (7, 8).
5. Vigilancia durable con modelo barato (4, 11).
6. Rechazo de una propuesta de criticidad recordado solo en sesión (M21b):
   persistirlo necesita columna y decisión del propietario.
7. Suite GUI: `test_streaming_message_grows_without_overlapping_neighbours`
   depende del orden/estado de Qt (entrada 16).
8. Corrector del motor: presupuesto o un commit por hallazgo cuando la
   ronda trae varios hallazgos de interfaz (entradas 9 y 16), y poder
   cancelarlo cuando el propietario corrige a mano (entrada 17).
9. Medición con Ollama real de M19b y M20 en la máquina del propietario
   (filas pendientes en ADR-128 y ADR-129): `uv run python
   scripts/medir_banco_con_ollama_real.py --diagnostico`.
