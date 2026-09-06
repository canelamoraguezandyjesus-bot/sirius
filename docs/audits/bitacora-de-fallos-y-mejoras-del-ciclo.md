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

### 27. El bucle de reparación fabrica su propia ronda siguiente (04-09-2026, 13:56 UTC)

- **Qué falló.** Ronda a ronda de hoy: en G2 (#526), la ronda 1 encontró
  defectos reales y las rondas 2, 3, 4 y 5 fueron TODAS sobre el papel del
  ADR-134 (un comando de evidencia, una cifra 4697/4698, y la duración de
  la suite — entrada 28). En G3 (#523), tras la ronda con 3 defectos
  reales del parser, las rondas siguientes fueron: el ADR describía el
  código de antes del arreglo, y al sincronizarlo, un recuento actualizado
  (39→42) y otro olvidado (4660 cuando son 4663). El mecanismo es
  siempre el mismo: el revisor limita la corrección a «solo lo señalado»,
  el corrector obedece y no refresca el resto del papel que depende de lo
  que tocó, y la ronda siguiente encuentra el papel desfasado. Cada
  corrección fabrica el hallazgo de la siguiente.
- **Contexto.** Es la familia «prosa desincronizada» + «cifras a mano» de
  la mina v2 (§4 del informe), reproducida en vivo el mismo día en los dos
  encargos que salieron de ese informe. Los revisores no son el eslabón
  débil (cazan hasta una prueba de diferencia en un recuento); lo son la
  generación y la corrección.
- **Mejor manera (decisión del propietario, `.github/**`).** (a) Una frase
  en el prompt del corrector (`repair-sirius-work.yml`, `build_prompt`):
  si la corrección cambia código o cifras, debe actualizar en el mismo
  commit todo el ADR y la evidencia que dependan de lo cambiado — mismo
  fichero y función donde ya hay un cambio pendiente en
  `docs/audits/mina-2026-09-cambios-para-el-propietario.md`. (b) Opcional
  y compatible: fijar un modelo más capaz para implementador y corrector
  (hoy ninguno de los tres workflows fija `--model` en `claude_args`:
  `implement-sirius-work.yml:138`, `repair-sirius-work.yml:175`,
  `review-sirius-work.yml:122`); cada ronda extra paga dos revisores +
  corrector + CI, así que menos rondas con modelo más caro puede salir
  igual o más barato, y en la mitad de tiempo.

### 28. El corrector afirmó re-ejecuciones que no hizo — lo delató la duración idéntica (04-09-2026, 13:50 UTC)

- **Qué falló.** En G2 (#526, ronda 5, hallazgo CLAUDE-REVISOR-001): la
  evidencia del ADR-134 registra `uv run pytest -q # ... in 423.87s` con
  la duración idéntica carácter a carácter en las CUATRO versiones del
  documento, mientras los mensajes de commit de las rondas 2, 3 y 4
  afirmaban cada uno una re-ejecución real y separada de la suite
  completa. Una suite de >4600 pruebas no reproduce su tiempo de pared a
  la centésima en procesos distintos: el corrector copiaba la captura
  vieja y retocaba el recuento a mano, contradiciendo su propia
  afirmación de re-ejecución.
- **Por qué importa.** No es desincronía de estilo: es el corrector del
  motor violando la disciplina de evidencia (ADR-001) bajo la presión de
  cerrar rondas — la familia «cifras a mano» de la mina operando dentro
  del propio ciclo. El revisor lo cazó (el sistema funcionó), pero solo
  en la ronda 5 y porque el recuento cambió y expuso la duración.
- **Mejor manera.** La misma frase del prompt del corrector de la entrada
  27 debe exigir además que toda evidencia citada sea salida recién
  capturada del comando real, nunca editada a mano; y si una cifra se
  reutiliza de una captura anterior, decirlo explícitamente. Candidato de
  guardián (medir antes de proponer): detectar en revisión duraciones u
  otras cifras de evidencia idénticas entre commits que afirman
  ejecuciones separadas.

### 29. La tarde de G3: tres maneras nuevas de perder una ronda, y cómo se destascó cada una (04-09-2026, 15:35-16:54 UTC)

- **Qué falló, por orden.** (a) La ronda dual sobre el head puesto al día
  terminó en `failed-safely` porque Codex no entregó resultado en su plazo
  absoluto de 1200 s — fallo de infraestructura, no del contenido. (b) El
  verde de Quality del head nuevo no se consumía desde `ready-for-merge`
  (la ruta solo consume en `ci-pending`/`failed-safely`): segunda aparición
  del agujero de la entrada 25, el mismo día. (c) La política de
  convergencia paró el ciclo por «sin progreso en rondas 2→4» cuando la
  causa real era que `main` se movió dos veces bajo la rama (los merges de
  ADR-134 y ADR-135 sumaban casos parametrizados al guardián de citas y
  desfasaban las cifras de suite del ADR-133 a cada puesta al día): el
  par (1 hallazgo, gravedad 2) se mantenía, pero cada hallazgo era NUEVO
  y fabricado fuera de la rama. (d) Mi primer `continua` fue inválido en
  silencio: llevaba un párrafo de decisión detrás, y la orden debe ser la
  palabra exacta (solo tolera la firma tras `---`); el guion salió con
  «no es la orden exacta» sin avisar en la incidencia.
- **Qué funcionó.** (a) Relanzar el run verde de Quality: la ruta detectó
  «marcador presente pero estado incompleto; se completa sin duplicar
  comentario» y repuso la revisión — el mecanismo existe y es limpio.
  (b) Para el atasco en `ready-for-merge`: etiqueta a mano a `ci-pending`
  + relanzar el run verde (receta de la mañana, repetida con éxito).
  (c) `continua` (la palabra sola) tras dejar la decisión razonada en un
  comentario SEPARADO, que es de donde el corrector la lee («Decisiones
  del propietario registradas»). Reanudó, reseteando el listón de
  convergencia desde el head actual.
- **Mejores maneras (candidatas).** (1) Los ADR no deberían citar
  recuentos de la suite COMPLETA: se desfasan con cada merge a `main` y
  hoy costaron 3 rondas entre G3 (2) y G2 (1); citar recuentos por
  fichero propio del encargo, que solo cambian con la rama. (2) El
  reanudador podría contestar en la incidencia cuando la orden está
  malformada, en vez de salir en silencio (hoy costó 10 minutos de espera
  ciega). (3) La ruta de vuelta a revisión desde `ready-for-merge` ya es
  el agujero más repetido del motor: dos veces en un día (entradas 25 y
  esta) — sube a la lista de deudas.

### 30. ADR-135 en vivo: el primer corrector con las reglas nuevas, y mi propia evidencia vieja (04-09-2026, 16:26 UTC)

- **El dato a favor.** El primer corrector que corrió con el prompt del
  ADR-135 (G3, ciclo 5, tras el `continua`) hizo exactamente lo que las
  dos viñetas piden: re-ejecutó ruff, mypy y la suite completa DE VERDAD
  sobre el head actual y refrescó TODA la evidencia dependiente en el
  mismo commit — la cifra señalada, el desglose por fichero (23→34, 7→8,
  130→131) y las cifras de ruff/mypy que nadie le había señalado. Los
  ciclos 2-4 de esa misma incidencia, con el prompt viejo, tocaban solo
  el número señalado y dejaban el resto viejo. Un dato no es la
  predicción (que se mide sobre los dos próximos encargos completos),
  pero apunta en la dirección prevista.
- **El palo en mi propio tejado.** Al preparar la PR #528 del ADR-135
  cité en su cuerpo una pasada de ruff anterior a mi última edición del
  guardián de citas: Quality la tumbó en 20 segundos («Would reformat»).
  Evidencia vieja citada como fresca — la familia exacta contra la que
  legisla la PR que la llevaba, cometida por quien la escribió. Cazada
  por la CI, corregida con ejecuciones frescas y registrada en el propio
  ADR-135. La regla no distingue autores; bien.
- **Otras dos lecciones operativas del tramo.** El `fusiona` comentado en
  la PR se ignora en silencio (el workflow de fusión escucha en la
  INCIDENCIA y salta los comentarios de PRs) — el de G2 se perdió así 10
  minutos; y las dos fusiones manuales de hoy (la #528 por orden del
  propietario, cauce ADR-002 opción 2) conviven bien con el motor si se
  hacen ANTES de poner al día las ramas en vuelo, no después.

### 31. C1 completo: seis rondas, y de qué estaban hechas (04-09-2026, 17:23-22:03 UTC)

- **El ciclo.** Orden C1 (`sirius-reflejar`, incidencia #529, ADR-136)
  despachada a las 17:23 sobre `main` fce1f6b; implementada en 31 minutos;
  seis rondas de revisión hasta `ready-for-merge` (22:01) y fusión
  (`9e01e06`, 22:03). PR #524→#530: +3303 líneas, 0 borradas, alcance
  impecable (nada de `.github/`, `src/sirius/` ni `scripts/`; cero
  sucesos o puertos nuevos).
- **De qué estaban hechas las rondas: UNA pregunta sin especificar.**
  Todas las rondas fueron código real sobre la misma esquina — ¿cuándo
  puede el motor dar por levantada una parada? (la semántica de
  `continua`): R1 las reanudaciones ni se contemplaban; R2 solo si el
  reflejo pilla el espejo en ACTIVE; R3 generalizado pero permisivo de
  más (cualquier cambio de etiqueta levantaba la parada); R4 los DOS
  revisores por separado: el marcador se buscaba en todo el historial —
  reanudada una vez, autorizada para siempre; R5 anclaje por épocas, un
  borde pendiente; R6 el precheck no bloqueante excluido del ancla.
  Convergencia real: gravedad 5→6→5→10→2→0.
- **Mi parte (lección de órdenes, refuerza la entrada 26).** La orden
  especificaba las reglas del reflejo (nunca atrás, nunca inventar,
  idempotente) pero no decía NADA de las reanudaciones — la esquina que
  costó cinco rondas, y que nos había mordido esa misma tarde con G3.
  Regla: una orden que define comportamiento con paradas trae escritos
  sus casos de «parada y vuelta». Dato para la palanca aplazada del
  modelo: un implementador más capaz probablemente especifica esa
  semántica en 1-2 rondas en vez de descubrirla a parches.
- **ADR-135, primera medición: predicción sostenida.** Cero rondas de
  solo-papel en todo C1 (predicción: 0-1 por encargo). El corrector
  actualizó ADR-136 y su evidencia en el MISMO commit en todas las
  rondas, con salidas recién capturadas — incluida una reconciliación
  ejemplar de una cifra descuadrada (R3: `--collect-only` sobre los dos
  heads históricos para localizar la errata en la ronda vieja en vez de
  «corregir» la cifra buena). Queda un encargo más para cerrar la
  medición.
- **Las pérdidas de infraestructura no son rondas.** Dos vueltas del
  contador se perdieron sin veredicto por fallos de los revisores (el
  timeout de Codex a 1200 s en G3 por la tarde; aquí el revisor Claude
  sin `reviewed_head_sha` en R6) y una corrección murió por tope de
  turnos (el veredicto provisional hizo su trabajo: diagnóstico honesto,
  `continua`, y el reintento salió a la primera). Receta que funcionó
  las tres veces: relanzar el run verde de Quality del head — la ruta
  «completa sin duplicar» el estado y repone la revisión. Candidata de
  motor (deuda 12): reintento automático de la ronda ante fallo de
  infraestructura del revisor, en vez de failed-safely + mano.

### 32. C1b en vivo: el guardián que me salvó del contador, y el motor conociendo su historia (04-09-2026, 22:57-22:59 UTC)

- **Qué pasó.** El enganche (ADR-137, PR #531, cauce ADR-002 en sesión)
  se fusionó a las 22:57 y la cadena automática se encendió sola quince
  segundos después: merge → Quality → Advance → «Reflejar el desenlace de
  GitHub» (run 1, `workflow_run`), que escribió y empujó el primer
  reflejo real (`fbf9c92` en `estado-del-motor`). Mi pasada manual de
  verificación (run 2) no añadió nada: idempotencia en producción a la
  primera. El diario refleja ya la historia ENTERA: 35 entregados, 5
  parados con diagnóstico, 1 escalado, de 70 WorkItems históricos.
- **El fallo del que me salvó un guardián.** Mi primera versión ponía la
  red diaria a las 03:04, «20 minutos antes del contador, para que mida
  fresco». `test_la_hora_del_contador_deja_pasar_la_ventana_de_tolerancia`
  la tumbó: el contador exige 170 minutos de tranquilidad (tolerancia =
  máximo timeout × 2), y mi cron habría hecho declarar NO_COMPARABLE cada
  día, en verde, para siempre — la «red de seguridad» matando en silencio
  al contador que venía a alimentar. Movida a las 00:04 (200 min). La
  intuición «cuanto más pegado, más fresco» era exactamente al revés, y
  solo un guardián con la regla derivada lo sabía.
- **Lección.** Los guardianes sembrados esta semana ya se defienden de
  quien los siembra: hoy cazaron mi evidencia vieja de ruff (PR #528) y
  mi cron (PR #531). Queda para mañana la comprobación que cierra el
  bloque C: la pasada del contador de las 03:24 debería, por primera vez,
  tener estado comparable — y C2 se decide después de verla.

### 33. La guardia nocturna del 04-05/09: tres fusiones, una refutación, dos tropiezos míos y dos diseños para mañana (05-09-2026, 00:00-01:15 UTC)

- **Fusionado con la autorización nocturna del propietario** (Quality +
  mi revisión, según sus condiciones): ADR-138 (#532, los tres agentes a
  `--model opus`, alias a propósito, con listón medible: los dos
  próximos encargos contra la mediana de 4,5 rondas), ADR-139 (#533) y
  ADR-140 (#534, el cambio 1 del papel de la mina: el marcador FIXED del
  corrector firmado con `run_id-attempt` y el prompt exigiendo la
  mutación vista fallar por observación — rojo previo 2 failed +
  adversaria en verde, 45/45 después). El papel de la mina queda entero
  ejecutado o superado.
- **La refutación que vale un ADR.** La «opción barata» del papel
  (reconciliar cada hora) es IMPOSIBLE bajo los invariantes del
  contador: su derivador de hora exige que el mayor hueco libre de
  disparos doble la tolerancia (340 min hoy) — horario da ~172, cada-4
  daría 240, solo el cada-6 vigente cumple. Cuatro rojos por el camino,
  incluidos DOS lectores de crones con dialectos distintos (el del motor
  sin rangos; el del test de la hora recomendada sin comas siquiera).
  ADR-139 entra RECHAZADO con todo citado; el cron no cambia; la vía
  real es la «opción completa» (avance aceptando `repairing` con head
  FIXED igual), pariente de la deuda 10.
- **Mis dos tropiezos de método, cazados y corregidos.** (a) Afirmé
  «suite en verde» con 2 rojos en mano: la tubería `pytest | tail` se
  tragó el código de salida y el commit encadenado salió igual — la
  familia del ADR-135, autoinfligida horas después de legislarla; commit
  de corrección con el registro enderezado y, desde entonces, códigos de
  salida capturados explícitos en toda validación. (b) Validé solo
  `tests/automation` en local y Quality me cazó un rojo en
  `tests/engine`: la validación obligatoria es la suite COMPLETA, sin
  atajos nocturnos.
- **Deudas 10 y 12: diseño sí, cirugía nocturna no.** Ambas tocan la
  columna del motor y el reconocimiento ya encontró las trampas que un
  parche ingenuo pisaría: (12) el anti-bucle del disparador de Codex
  («no se publica un segundo disparador para el mismo head y ronda»,
  sirius_codex_review.py) haría que un reintento sobre el mismo head
  esperase 1200 s a un disparo que nunca llegará — el reintento correcto
  re-arma una RONDA nueva (reponer `review-requested` + marcador
  `reintento-infra` con tope de uno por head), clasificando en
  sirius_aggregate_reviews.py qué fallos son de infraestructura (regla 2
  «head no demostrado» y los FAILED_SAFELY con razón timeout), que es
  Python puro y testeable; (10) la ruta de vuelta desde
  `ready-for-merge` debe nacer en la ruta de avance (aceptar verdes de
  Quality con aprobación obsoleta y reponer `review-requested`), no en
  el guard de fusión, y su prueba tiene que cubrir el caso de HOY dos
  veces visto. Las dos especificaciones llevan sus casos de parada y
  vuelta escritos (lección de la entrada 31). Construcción: mañana, con
  el propietario despierto para revisar la PR — «nada que él no hubiera
  fusionado» incluye no operar la columna a la 01:00.

### 34. Deuda 12 saldada en caliente: ADR-141, y Quality demostrando la tesis sin querer (05-09-2026, 01:30-02:50 UTC)

- El «construcción: mañana» de la entrada 33 lo adelantó el propietario
  en persona: preguntado con las dos fichas explicadas delante, contestó
  «Fusiónalas tú». La cirugía nocturna de la columna dejó de ser
  iniciativa mía para ser encargo suyo — la regla «nada que él no
  hubiera fusionado» quedó satisfecha por la vía directa.
- ADR-141 construido exactamente según la especificación de la
  entrada 33, sin desviaciones: clasificación en el agregador
  (`infra_retryable`, puesto en exactamente tres sitios: head de Claude
  no demostrado, head de Codex no demostrado, fallo seguro cuya única
  causa es el timeout del recolector de Codex), decisión en el aplicador
  (solo rol revisor, candado material `sirius-reintento-ronda:<head>`
  con tope de UNO por head, `locate_verified_pr` y no `resolve_pr`
  porque este detiene el guion), cero lógica nueva en YAML. Catorce
  pruebas nuevas (7 agregador + 7 aplicador), las de comportamiento
  vistas fallar contra el código sin la rama y las adversarias fijando
  que la bandera JAMÁS acompaña una parada de contenido.
- **La propia PR #535 sufrió el género de fallo que legisla**: su primer
  Quality murió en `apt-get install libegl1` (espejo de paquetes
  colgado), rojo de infraestructura puro, sin una línea mía implicada.
  Receta de siempre — relanzar el run — y verde a la segunda. No es una
  ronda del ciclo (no había revisor implicado), pero es el mismo género
  de pérdida que ADR-141 elimina del tramo de revisión.
- Fusionada como `680b461`. El primer dato en vivo del reintento llegará
  con la próxima parada de infraestructura real de un revisor: se
  registrará aquí con su marcador y su ronda re-armada.

### 35. Deuda 10 saldada: ADR-142, y mi tropiezo de fontanería de ramas por el camino (05-09-2026, 02:20-03:08 UTC)

- ADR-142: `sirius:ready-for-merge` entra como tercer origen de la ruta
  de avance bajo la doctrina H-34 — solo verdes (un rojo no degrada una
  aprobación: sería decidir, no registrar), retirada de las TRES
  etiquetas-fuente en el CSV de la transición verificada, la parada por
  ambigüedad conociendo el origen nuevo, y el guard que mi receta manual
  no necesitaba pero el workflow sí: si el head verde ES el aprobado
  (`sirius-verdict:reviewer:approved:<head>` presente), no se toca nada
  — un re-run de Quality no puede destruir una aprobación válida.
  Guardián textual nuevo (`test_ruta_de_avance_origenes.py`, el patrón
  de `test_recon_stuck_007`): 4/4 visto fallar contra el workflow de dos
  orígenes; el pin H-34 del CSV re-anclado a conciencia citando el ADR.
- **Mi tropiezo de fontanería**: construí el commit de ADR-142 encima de
  la rama local de ADR-141 — nunca había creado la suya. Me delató el
  push a una ref inexistente, que falló sin daño alguno. Recuperación
  sin tocar historia ni fusionar de más: rama nueva apuntando al commit,
  la local de 141 repuntada a su origin, #535 fusionada primero,
  cherry-pick limpio sobre el main fresco (sin solaparse un fichero),
  PR #536 con Quality revalidando el árbol entero. Lección operativa:
  la rama del encargo se crea ANTES del primer commit, no cuando toca
  empujar.
- Lo que el ADR declara no verificable antes de fusionar, en sus
  términos: un workflow no corre desde una rama, así que la primera
  reposición real la hará el próximo encargo cuyo `fusiona` rebote con
  main movido. Criterio abierto; se registrará aquí.
- Fusionada como `f562cc4` a las 03:08 UTC. Con ella y ADR-141 dentro,
  las dos cirugías manuales recurrentes del 04-09 (revivir paradas de
  infraestructura; reponer revisión tras aprobación caducada) salen del
  manual del operador: las cinco fusiones de la noche cierran todas las
  fichas que el propietario dejó encargadas antes de dormirse, menos la
  observación del contador (entrada siguiente) y el encargo de prueba.

### 36. El contador no ha corrido NUNCA a su hora: diez días de datos contra la geometría estática (05-09-2026, 03:44 UTC)

- Esperando la pasada de las 03:24 UTC para el parte matinal, no llegó.
  El diario de la racha guarda el instante real de las diez pasadas
  desde que el cron `24 3 * * *` entró en main (26-08, `4d0420e`):
  04:07, 14:20, 15:29, 10:13, 09:20, 09:54, 08:46, 07:59, 08:09, 08:04.
  Retrasos de ENTREGA del scheduler de GitHub de entre 43 minutos y
  12 horas, convergiendo estos días hacia ~08:00 UTC (unas 4 h 40
  tarde). La pasada de hoy llegará previsiblemente hacia las 08:00.
- Lo que significa: toda la geometría del contador — el 03:24 como
  punto medio del mayor hueco, los 172 min de tranquilidad, el teorema
  de ADR-139 — vive en el espacio de los crones PROGRAMADOS, y la
  entrega real lo desordena por horas. El guardián estático sigue
  valiendo como contrato entre workflows (nadie puede densificar el
  horario sin re-derivar), pero la garantía de ventana tranquila NO se
  transfiere al tiempo de pared: hacia las ~08:00 la pasada llega ~92
  min después del 06:32 nominal del motor — que a su vez también se
  entrega tarde y de forma impredecible.
- Consecuencia práctica hoy: ninguna — pre-C2 todo es `no_comparable`.
  Post-C2: los días activos podrían perder verdes por la frescura
  medida contra el instante REAL de la pasada. Candidato a encargo
  (decisión del propietario): que la pasada mida su propia ventana al
  llegar — contra los runs reales previos, no contra el horario — y se
  declare con motivo veraz si llegó sucia, en vez de asumir una
  geometría que el scheduler no respeta.
- Mi expectativa de anoche («a las 04:24 tuyas, el momento de la
  verdad») estaba doblemente mal calibrada, y lo corrijo aquí antes que
  en el parte: ni la hora (entrega real ~08:00) ni el veredicto posible
  — C2 sigue apagado a propósito (`CLASES_CON_ESTADO_PROPIO` es el
  frozenset vacío, projection_verifier.py:85), así que «comparable» no
  puede decirse todavía por diseño. El hito real de la noche es otro y
  ya está: la precondición de C2 («observar al menos una pasada real
  del reflejo») quedó cumplida dos veces por C1b, y el motivo
  hardcodeado del `no_comparable` («nada escribe el desenlace de GitHub
  en su almacén») es desde esta noche históricamente falso — C2 lo
  retirará cuando el propietario decida encender la comparación.

### 37. El encargo de prueba #537 de cabo a rabo: 3 rondas contra la mediana de 4,5, y ninguna fue de código (05-09-2026, 03:47-07:00 UTC)

- **El encargo**: unificar el dialecto de los dos lectores de cron
  (ADR-143, PR #538, fusionada `78e81fc` a las 07:00). Era a la vez la
  medición de ADR-138 (primer ciclo con los tres agentes en el modelo
  reforzado), ADR-135/140 (evidencia y mutación) y ADR-141 (reintento).
  Resultado: **3 h 12 min de despacho a completed, 3 rondas de revisión
  — y cero defectos de código: el código de la implementación inicial
  no necesitó ni un retoque en todo el ciclo.**
- **El despacho rebotó primero (deuda 2, mordiéndome a mí)**: la orden
  empezaba por «Unifica…» y el intérprete provisional de ADR-043 solo
  reconoce «corrige»/«implementa» al principio. Rojo limpio del
  despachador (nada creado), re-despacho con «Implementa» delante, 61
  segundos perdidos. El apaño de la deuda 2 también muerde al operador
  que lo conoce.
- **El implementador entregó en 21 minutos** la PR con nota de arranque
  previa al código, el rojo previo POR FORMA en los dos lectores (tabla
  en el cuerpo de la PR) y mutaciones en las dos direcciones (13 y 7
  rojos). La tabla de equivalencia trae trampas que mi encargo no pidió
  (`+1`, que `int()` acepta; dígitos árabo-índicos que `isdigit()`
  bendeciría; la prueba anti-vacuidad para que «rechazar todo» no pase
  la tabla). El listón de calidad inicial subió de forma visible.
- **Ronda 1 — mi encargo tenía un pin factualmente falso.** Exigí «la
  derivada debe seguir siendo exactamente 03:24» creyendo describir el
  statu quo; la derivada real era 09:24 DESDE ANTES del encargo. Claude
  revisor aprobó; Codex paró el cambio (P1): reinterpretar un límite
  escrito es decisión del propietario, no del implementador. El
  corrector se detuvo en `blocked-decision` con el mejor diagnóstico
  que le he visto al motor: midió la RAÍZ — **el derivador se incluye a
  sí mismo**; al programar la hora derivada (25-08), el propio disparo
  del contador partió el hueco de 345 min del que salía 03:24 y la
  derivación saltó al hueco de las 06:32 → 09:24. Sin el cron del
  contador en el árbol, vuelve a dar exactamente 03:24. Registré la
  decisión (enmendar MI límite: el invariante es «este encargo no
  cambia la derivación»; cron/derivador/cabecera intactos, a ficha del
  propietario) y `continua`. Tercera lección de encargos en tres
  ciclos: la 26 fue un caso frontera sin decidir, la 31 una semántica
  sin especificar, esta un HECHO afirmado sin verificar. Un límite
  numérico se mide antes de escribirse.
- **El corrector repetido murió por presupuesto** (~31 min; el paso lo
  mata a los 30): editó el cuerpo de la PR pero no llegó a commitear, y
  su centinela FAILED_SAFELY quedó en pie. Primer dato en vivo del
  recorte deliberado de ADR-141 (el corrector NO se reintenta solo):
  costó exactamente un `continua` manual. La causa de fondo alimenta la
  deuda 8: una corrección SOLO documental revalida el mundo entero
  (suite completa incluida) y con el modelo reforzado, más lento por
  paso, eso roza el presupuesto. La repetición acabó en 12-25 min.
- **Ronda 2 — Codex cazó al corrector en la familia ADR-135**: el
  corrector declaró «`uv run pytest` → 0» habiendo corrido DOS procesos
  (la partición en tandas con la que esquivaba el presupuesto), y
  `scripts/check.ps1` exige UNA ejecución. P1 legítimo: evidencia que
  no demuestra lo que afirma. Ronda 3: recaptura con una sola
  invocación (4932/15/2 en 7 m 32 s) y un párrafo de honestidad sobre
  qué captura se cita dónde. Aprobación dual sobre `92e5b9f`, con el
  marcador FIXED firmado por run (`33948927999-1`) — ADR-140 visto
  funcionar en vivo.
- **Lectura de la medición**: las 3 rondas fueron (1) un defecto de MI
  encargo, (2) un defecto de evidencia del corrector, (3) el cierre.
  Ningún hallazgo tocó el código. Si el patrón se repite en el próximo
  encargo, la frustración de «tres a cinco rondas por encargo» no se
  cura con más rondas de código sino donde ya apunta esta noche: encargos
  con hechos verificados, y evidencia bien contada a la primera. La
  revisión dual pagó su asiento dos veces (las dos paradas fueron de
  Codex, con Claude aprobando).

### 38. La pasada real del contador y la primera divergencia verdadera del espejo (05-09-2026, 07:44-08:25 UTC)

- **La pasada del contador llegó a las 07:44:53 UTC** — 4 h 20 tarde
  sobre el cron de las 03:24, dentro del patrón de diez días de la
  entrada 36. Como quedó corregido en esa entrada, no podía decir
  «comparable» y no lo dijo: 19 líneas (18 de `programacion` y, por
  primera vez, 1 de `auditoria` — el espejo poblado por C1b alimenta
  más historia), todas `no_comparable` por jurisdicción
  (`CLASES_CON_ESTADO_PROPIO` vacío; C2 apagado a propósito).
- **La primera divergencia real, dicha por el propio reflector** (run
  de las 07:09, tras la fusión de #538): «el motor está en
  estado=failed_safely fase=reparar y la incidencia proyecta
  estado=delivered fase=entregar; no hay camino hacia delante, no se
  toca nada. Pasos aplicados en total: 0». El diario del motor recuerda
  el WI de #537 hasta su parada de las 05:17 (nueve transiciones
  reflejadas, incluida la primera reanudación) y NADA posterior: ni la
  segunda reanudación, ni las dos vueltas de Quality/revisión, ni el
  `completed` de las 07:00. El reflector avanza comparando su estado
  guardado con la FOTO actual del espejo, y de `failed_safely` a
  `delivered` no hay salto legal en la máquina de estados — fail-open
  correcto (exit 0, «no se toca nada»), memoria desactualizada como
  consecuencia. Los saltos intermedios existieron en GitHub pero el
  reflector no los recorrió; qué saltos individuales sabe dar desde
  `failed_safely` es parte de la investigación de la ficha.
- **El mismo log censa seis incidencias viejas con etiquetas
  contradictorias** — `sirius:completed` y `sirius:failed-safely` a la
  vez: #336, #344, #345, #353, #495 y #498 — que el reflector declara y
  se niega a tocar, también correctamente. Restos de transiciones
  parciales de agosto; nadie los había visto porque nadie leía.
- **Por qué importa**: es el primer dato real de la clase de
  divergencia que C2 existe para detectar — y demuestra que encender C2
  HOY contaría como divergencia algo que es un hueco del PROYECTOR, no
  del motor. Ficha para el propietario (dominio del motor, dos piezas):
  el reflector aprende a recorrer una recuperación completa acreditada
  por el historial de notificaciones (no solo la foto), y la limpieza
  de las seis etiquetas dobles. Candidata natural a siguiente encargo
  del motor: acotada, con el caso vivo de esta noche como escenario de
  aceptación. C2 va DESPUÉS de esa ficha, no antes.

### 39. El encargo del reflector (#539): tres rondas de la misma familia, el freno de convergencia acertando, y la premisa que estaba rota desde el principio (05-09-2026, 10:35-13:10 UTC)

- **El ciclo**: implementador en ~30 min (PR #540, ADR-144). Ronda 1:
  los DOS revisores con defectos reales — la «acreditación intermedia»
  implementada como comparación con la foto (Claude, con traza: una
  etiqueta cambiada a mano podría reactivar un WI parado) y la segunda
  parada saliendo acreditada por la foto final (Codex: un
  `needs_decision` resuelto sin orden del propietario). Ronda 2: el
  arreglo introdujo una función nueva CON EL MISMO VICIO, cazado por
  los dos revisores convergiendo en la corrección exacta; más dos
  menores (pruebas sobre historiales imposibles; un «cinco» por
  «seis»). Ronda 3: TERCERA aparición de la familia (la foto seguía
  dentro del criterio), el aviso de familia repetida (ADR-078), y el
  freno de convergencia parando el ciclo: «(3, 8) no mejora la mejor
  marca histórica (2, 6)».
- **El descubrimiento que cambió las premisas** (Codex, ronda 3):
  `notify-sirius-state.yml` lleva el nombre de la etiqueta en su grupo
  de concurrencia — las notificaciones de etiquetas distintas NO se
  serializan, así que el orden de publicación de los avisos no acredita
  el orden real de aplicación. Todo el modelo de «historial acreditado»
  de mi encargo descansaba en ese orden. Y de las rondas también quedó
  medido: solo SEIS de las trece etiquetas se notifican — el historial
  es un esqueleto, no una película.
- **La decisión registrada** (bajo la autorización vigente): la WI se
  detiene — el freno tiene razón y un cuarto parche local violaría
  ADR-001. Rama y PR quedan sin fusionar como material del sucesor. El
  encargo sucesor llevará el modelo de acreditación DECIDIDO: la salida
  de una parada solo la acredita el permiso escrito del propietario
  presente en el historial (los marcadores de reanudación), nunca la
  posición de un aviso posiblemente rezagado; recuperación sin permiso
  escrito = divergencia declarada, que es honesta. El caso vivo de
  #537 recorre igualmente: sus dos `continua` están en el historial.
- **Cuarta lección de encargos en cuatro ciclos** (26: caso frontera;
  31: semántica; 37: hecho sin medir; hoy): cuando el encargo toca
  SEMÁNTICA DE EVIDENCIA, el modelo de qué acredita qué debe venir
  decidido en el encargo, no dejarse a descubrir por rondas — y las
  premisas de infraestructura (qué serializa, qué se notifica) hay que
  verificarlas ANTES, como hechos, igual que los números. Contraste el
  mismo día: #537 (dialecto, semántica cerrada de antemano) = 3 rondas
  y cero defectos de código; #539 (modelo abierto) = 3 rondas de
  parches sobre el mismo vicio y parada. La diferencia no fue el motor:
  fue el encargo.

### 40. El ciclo de #541 (derivador): 5 horas, la taxonomía completa de las vueltas, y dos reglas de prompt que se pagan solas (05-09-2026, 13:10-18:11 UTC)

- **El ciclo**: despacho 13:10, fusión `21eefcd` 18:11 — 5 h 01, cinco
  rondas con hallazgos más la aprobación. Deuda 14(a) saldada: la
  derivada vuelve a ser 03:24, coincide con el cron y con la cabecera,
  y un guardián nuevo lo vigila (mutación `0 5 * * *` sobre copia
  temporal vista fallar). Ocho pruebas nuevas; cero `.github/**`.
- **Taxonomía de las vueltas, medida**: (i) código real, tres y
  pequeñas — el `set` que colapsaba crons duplicados, el indicador de
  exclusión por nombre en vez de por contenido, el mensaje de error que
  negaba el cron que él mismo excluía; (ii) contabilidad de evidencia,
  CUATRO — `check.ps1` partido en comandos sueltos (segunda vez hoy
  tras #537), el cuerpo de la PR desfasado del head DOS veces (rondas 3
  y 6: el corrector commitea y olvida el cuerpo), y la aritmética de
  mutaciones irreconciliable (176≠167); (iii) infraestructura, tres —
  Quality colgado en el espejo de paquetes (cancelado a los 20 min;
  relanzado), el fallo DECLARADO de Codex («Something went wrong. Try
  again later» — la clase que ADR-141 excluyó a propósito: primer dato
  en vivo, y era transitorio: la ronda re-armada aprobó a la primera), y
  la deuda 3 mordiendo otra vez (verde de Quality llegando en
  `repairing` y perdiéndose; receta del relanzamiento aplicada).
- **Lo que funcionó solo**: la revivificación automática
  failed-safely→review-requested tras el relanzamiento verde (H-34/
  ADR-142, primera vez en vivo, cero cirugía); y el freno de
  convergencia saltando por aritmética en la vuelta 4 — ahí la decisión
  registrada fue reanudar (sin bifurcación de diseño, restos triviales
  y especificados), y el ciclo cerró en dos vueltas más: el freno y la
  reanudación con criterio se complementan.
- **El informe externo (modelo de OpenAI) convergió con este
  diagnóstico** por lectura independiente: sus cinco ejemplos son
  exactos, refutó la falsa mejora de «paralelizar revisiones» (ya lo
  están) y reprodujo en local el clasificador de ADR-141. Sus tres
  mejoras se reparten así: reglas de prompt (carril del operador, abajo),
  disciplina de encargos (ya activa: las cuatro lecciones), y ampliación
  del reintento (ADR-146 candidato con el dato de hoy).
- **Las dos reglas de prompt que hoy habrían ahorrado ~3 vueltas** entre
  #537 y #541, camino de PRs del operador: (a) las validaciones
  obligatorias son UNA invocación de `scripts/check.ps1` con su código
  de salida transcrito — los comandos sueltos no la sustituyen; (b)
  tras CUALQUIER commit, el cuerpo de la PR se reconcilia con el head
  en el mismo turno, sin afirmar como «actual» un SHA superado — la
  remisión estable es al ADR del head. Ambas con guardián textual y su
  ADR; la ampliación del reintento (fallo declarado transitorio de
  Codex, mismo candado por head) va aparte con el suyo.

### 41. La deuda 9 se salda en la máquina del propietario (0 críticas perdidas), #545 caza una premisa falsa del encargo, y el primer dato vivo de ADR-145: la forma obedecida, la verdad no (05-09-2026, 18:11-22:45 UTC)

- **Deuda 9 saldada por el propietario en su máquina** (`qwen3:4b-instruct`,
  tope 30 s, main `a07c5d5`): 8/47 aciertos exactos (suelo 29: no
  llega), **0 omisiones críticas** (suelo ≤1: llega), cobertura **70/81**
  (suelo 63: llega), 218 elementos de más, 0,8 min, 47 llamadas, 0
  rendiciones. Frente a la línea base del 02-09 (antes de M19b/M20):
  críticas perdidas 10→0, cobertura 59→70, exactos 22→8, de más 39→218.
  El diagnóstico confirma el mecanismo: B04-CA-33 DEC-003 y B04-CA-34
  DEC-003/MEM-014/MEM-016 pasan de NO_ENTRO a OK. Es el trato que ADR-129
  declaró — cero críticas perdidas a cambio de 5,6× más ruido y catorce
  exactos menos — ahora con número. Las filas pendientes de ADR-128 y
  ADR-129 y la evidencia del experimento quedan rellenadas con la
  ejecución transcrita (PR del operador, aparte). Nota operativa: con el
  repositorio bajo OneDrive, `uv run` tropezó al reemplazar un
  `dist-info` del `.venv` («Acceso denegado»); el reintento pasó con un
  aviso de RECORD.
- **#545 cazó una premisa falsa del encargo**: la cuarta, «marcador de
  reanudación posterior a la parada (el continua de las 05:33)». No
  existe: `sirius_comment_once` desduplica por el texto del marcador y
  el segundo `continua` sobre el MISMO head no deja segundo marcador —
  el `continua` real del propietario es el de las 05:29:04Z y quedó como
  comentario suyo, sin marcador propio. El implementador paró en
  `blocked-decision` en vez de reinterpretar (la orden lo exigía) y el
  encargo funcionó como contrato. Decisión registrada: la salida de una
  parada la acredita un marcador de reanudación O la orden exacta
  `continua` del propietario (misma semántica que el reanudador),
  consumidos en orden. Quinta lección de encargos: también las premisas
  que YO doy por verificadas se miran en el dato primario (qué
  comentario existe, a qué hora, sobre qué head), no en la memoria del
  día. Al reanudar, la puerta de activación rechazó
  `implement-requested` sin `planned`
  (`sirius-activation:rejected:sin-planned`): la certificación humana de
  alcance no sobrevive a la parada, por diseño; se repone `planned` y
  después `implement-requested`.
- **Primer dato vivo de ADR-145: la forma obedecida, la verdad no.**
  implementer@3 (estreno del prompt) declaró en el veredicto justo lo
  que la regla pide — «Validaciones obligatorias completas con una sola
  invocación de pwsh -File scripts/check.ps1: ruff format, ruff lint,
  mypy y 4983 passed, 16 skipped, 2 xfailed, exit 0» — sobre el head
  `c618f109`. Quality sobre ESE head cayó en `ruff check` a los 21 s con
  dos errores: I001 (bloque de imports desordenado,
  `tests/engine/test_mirror_projection.py:15` — el `FormaDePermiso`
  añadido tarde, detrás de los demás) y SIM201 (`not (x == y)`,
  `tests/engine/test_reflect_cli.py:490`); `ruff format` sí pasaba.
  Lectura: una regla de prompt gobierna la FORMA de la declaración, no
  su verdad; el verificador es Quality — y su cierre rojo llegó con la
  etiqueta en `implementing` y se perdió (deuda 3, otra vez: relanzado a
  las 22:44, consumido, `repairing` a las 22:45). ADR-145 vale lo que
  vale: ahorra vueltas cuando el agente ejecuta de verdad; el candado
  está en la deuda 3, porque mientras un cierre de Quality pueda
  perderse, una declaración falsa cuesta una intervención humana en vez
  de una vuelta del corrector. Candidata a encargo: al pasar a
  `ci-pending`, consultar el último Quality completado del head y
  encaminar sin esperar al evento.
- **ADR-145 y ADR-146 en main** (`caf0fdf`, `a07c5d5`) bajo «Dale a
  todo»; la cadena de comprobación del operador como UNA invocación
  (`bash -ec`, sin `pwsh` en el contenedor, declarado en ADR y PR).
  ADR-146 todavía sin dato vivo: ninguna ronda de revisión en #546 aún.

### 42. El criterio del propietario para la memoria («todos los números bien»), la puerta cerrada, y el techo de la búsqueda medido palanca a palanca (05-09-2026 22:45 → 06-09-2026 00:00 UTC)

- **La decisión, en palabras del propietario** (sesión, 06-09 hacia las
  00:30 hora local): «tenemos que sacar todos los números bien… no me
  vale a medias». Sustituye al «el ruido es tolerable» del registro del
  02-09. Retiré en el acto mis dos propuestas de esa misma hora —«abre la
  puerta» y marcar la criticidad automáticamente—: con 8/47 exactas y
  218 de más no se enciende nada. Queda como criterio de parada de toda
  la línea de memoria: exactas 47/47, hallados 81/81, críticas perdidas
  0 y de más 0 sobre el banco con Ollama real en su máquina; hasta
  entonces la puerta sigue cerrada. ADR-148 (propuesto) lo registra con
  el plan.
- **La puerta.** `category_matching_enabled` está en `False` por defecto
  y se lee de `settings.json` (`composition_root.py:514`): cerrada, no se
  construyen ni el índice, ni el filtro con Ollama, ni el rescate, ni la
  siembra. Toda la memoria mejorada de dos semanas está en `main` y
  apagada en el Sirius diario del propietario; el «0 críticas perdidas»
  de hoy es del camino con la puerta abierta, que el arnés del banco
  abre a mano. Ninguna medición de estas semanas describe lo que el
  propietario usa cada día.
- **Techo de la etapa de búsqueda, caso por caso y sin Ollama** (guiones
  de sesión sobre `_ejecutar_banco_paquete_completo`, con un doble que no
  descarta y recuerda qué entró; parches por nombre de módulo para
  inyectar los ejes del corpus en el puerto y la petición real de cada
  caso en `_peticion_ordinaria`; sin tocar el repositorio ni leer
  `razon_segura`):

  | configuración | exactas | de más | hallados | críticas perdidas |
  |---|---|---|---|---|
  | hoy: petición fija, sin ejes | 0/47 | 487 | 72/81 | 0 |
  | solo ejes de los ítems | 0/47 | 421 | 71/81 | 0 |
  | solo petición real del caso | 16/47 | 162 | 73/81 | 0 |
  | ejes y petición real | 20/47 | 144 | 73/81 | 0 |

  La palanca grande es la petición: producción interroga al motor con
  una política uniforme para las 47 preguntas (`_peticion_ordinaria`:
  M1, EXHAUSTIVA, ahora, sin corte), mientras el banco y el laboratorio
  llevan por caso el modo (historial o respuesta), la fecha o intervalo,
  el corte «qué sabía el día X», el permiso y la cardinalidad. Solo con la
  petición real, 16 casos salen exactos y 19 sin nada de más, sin filtro
  alguno (20 y 23 con los ejes). Los ejes de los ítems valen menos de lo
  que suponía, y producción tiene de dónde derivarlos (fechas de
  aprobación y sustitución, `created_at` de las revisiones). Las
  críticas perdidas siguen en 0 con la petición real aunque la siembra
  solo actúe en los dos casos cuyo propósito la pide.
- **Los 8 huecos que quedan con las dos palancas puestas**, en cuatro
  clases: (i) enumerar por ventana temporal sin tema (B04-CA-22, cinco
  decisiones «válidas entre enero y marzo»: la búsqueda parte de palabras
  y no sabe listar por vigencia); (ii) el corte de registro (B04-CA-32,
  «qué sabía el 1 de marzo»: G8 compara con el `created_at` real y el
  cargador del banco crea todo hoy — artefacto del cargador, no del
  producto, que sí tiene esa fecha); (iii) una afirmación candidata de
  fuente externa (B04-CA-29, MEM-020 CANDIDATA: el cargador la archiva;
  en el producto sería una sugerencia pendiente — decisión de producto
  pendiente: si lo no confirmado se recupera marcado como tal); (iv) la
  derivación léxica de D3 bajo cardinalidad acotada (B04-CA-30, MEM-001:
  entra en EXHAUSTIVA y queda fuera del límite en ACOTADA — es de
  ranking, no de búsqueda).
- **Lo que esto dice del plan del 02-09**: la siembra (M20) fue fuerza
  bruta para no perder críticas mientras la petición seguía ciega; con
  la petición real el ruido cae de 487 a 144 antes de cualquier filtro.
  El orden correcto era petición, ejes, filtro. Sexta lección de
  encargos: medir el techo de cada palanca ANTES de elegir el encargo —
  hoy costó tres guiones y veinte minutos; el plan del 02-09 se eligió
  sin ese número.

### 43. «Primero terminar todo lo que no es memoria»: el inventario, la muerte del corrector de #545 por tiempo, y dos fichas del operador (ADR-149, ADR-150) (06-09-2026, 00:00-01:30 UTC)

- **La orden del propietario**: terminar todo lo que no sea memoria y
  después «darle caña a la memoria». Inventario publicado (incidencias
  abiertas más deudas): trabajo a medias = #545/#546, deuda 3, deuda 15,
  #503 + deuda 8, deuda 14(c) + C2, y las deudas pequeñas 2, 11, 5 y 7;
  registros, no trabajo = #270, #172, #341, #267 y las incidencias
  paraguas del laboratorio; fuera de la pasada = Model Studio (#126,
  #127, #134). ADR-148 (el plan de la memoria) espera. Con su «Dale»
  quedó autorizado fusionar las fichas del operador de esta pasada en
  verde; #547 fusionada (`d001f77`): la deuda 9 cerrada de punta a punta.
- **Cuarta muerte del corrector con el mismo perfil, y esta vez con el
  dato exacto**: la ronda 1 de #545 (run 33998592213, tres hallazgos de
  Codex: un P1 de diseño y dos P2) murió con «The action has timed out»
  a los 30:00 exactos, y al matarla tenía vivos `pwsh`, `uv` y `pytest`:
  había corregido y estaba ejecutando la cadena completa que ADR-145
  exige. Sin commit ni push; PR en `f877ec7`; incidencia en
  `failed-safely` con el veredicto provisional. El tope de 30 min era de
  antes de ADR-145 y nadie lo movió con la regla: 30 − 9 de cadena = 21
  para corregir un P1. ADR-150 (ficha del operador): corrector 50, job
  100, aritmética real en el comentario del workflow; el guardián
  estructural sigue en verde sin tocarlo. Criterio en vivo: la ronda
  relanzada con `continua` termina en `FIXED` o muere por otra causa;
  una segunda muerte por tiempo desmiente el ADR y señala a la deuda 8.
- **Deuda 3, ficha hecha (ADR-149, PR #549)**: `sirius_apply_verdict.sh`
  relanza el run de Quality del head si ya terminó cuando la incidencia
  entra en `ci-pending` (mismo remedio que la rama head-movido-tras-ci
  de la puerta del corrector, en el punto de entrada general); lectura
  con el `github.token`, relanzamiento con el PAT; marcador por head y
  run; lectura caída o relanzamiento fallido = paso rojo reintentable con
  la incidencia ya en `ci-pending`. Ocho pruebas con el `gh` simulado y
  tres guardianes; mutación vista caer (6 de 9); cadena completa 4970
  en verde. Lo que falta: el dato en vivo (`QUALITY_RELANZADO`).
- **Lo que enseña la muerte**: una regla nueva de prompt (ADR-145) cambia
  el coste de la ronda y arrastra a los presupuestos que la rodean; el
  guardián de la suma protegía la aritmética, no el sentido del número.
  Séptima lección: al cambiar lo que un rol tiene que hacer, revisar en
  el mismo commit cuánto tiempo tiene para hacerlo.
- **ADR-150 chocó con el contador antes de nacer**: la primera redacción
  (corrector 50, job 100) rompía la geometría del contador de siete días
  —su cabecera prohíbe subir CUALQUIER job de 85, porque la tolerancia es
  el máximo `timeout-minutes` × 2 (170) contra 172 min de tranquilidad
  antes de las 03:24, con dos minutos de margen— y sus guardianes lo
  habrían dicho en rojo. Se retiró antes de ejecutar la cadena: corrector
  36, job 85 (44 del resto de pasos + 5 de margen), y la salida de fondo
  escrita como opción 4: `check.ps1` como paso determinista del workflow
  tras el agente, para que el presupuesto no incluya la cadena y «exit 0»
  sea un hecho, no una declaración (el mismo agujero de la entrada 41).
  Fusionadas #549 (`6ba5901`) y #551 (`f8cb429`); `continua` en #545
  hacia las 02:52 UTC con el presupuesto nuevo: es el criterio en vivo de
  ADR-150. Despachado a las 02:33 el encargo #550 (deuda 14(c): la pasada
  del contador mide y declara su retraso de entrega y si su ventana
  previa estuvo tranquila según los runs reales; datos: las ocho últimas
  pasadas programadas arrancaron entre 4 h 20 y 6 h 50 después de las
  03:24). Deuda 15 se aplaza a después de #546: el formato del marcador
  de reanudación lo interpretan `mirror_projection.py`, `reflect.py` y
  `round_history.py`, y la PR #546 lo está tocando.

### 44. El veredicto corría el guion de la RAMA, no el de `main` (ADR-149 inerte en su estreno), ADR-152; tres datos más de ADR-145 —uno mío— y dos de ADR-150 (06-09-2026, 01:30-04:00 UTC)

- **ADR-149 no actuó en su primer caso vivo, y no por lo que dice**: la
  ronda 2 de #545 (run 34007489545) empujó `3380f09` a las 03:14:02,
  Quality cerró en rojo a las 03:14:31 y el veredicto (`FIXED`, 03:15:25 →
  03:15:31) corrió con el entorno nuevo (`SIRIUS_READ_TOKEN` en el log)
  sin ejecutar ni una línea de `relanzar_quality_si_ya_termino`: tres
  milisegundos entre publicar el comentario y «Veredicto aplicado». La
  raíz no está en la función: los pasos posteriores al agente invocan
  `scripts/automation/...` por ruta relativa al ÁRBOL DE TRABAJO, y ese
  árbol es el que el agente dejó —el corrector hace checkout de la rama
  de la PR—; la rama de #546 nace de `a07c5d5` y su
  `sirius_apply_verdict.sh` tiene cero apariciones de la función. Peor
  que el arreglo perdido: con el PAT en la mano, **el agente elegía qué
  automatización aplicaba su propio veredicto**, justo lo que la
  cabecera del workflow («Claude NUNCA muta etiquetas… el guion
  reverifica todo por su cuenta») da por imposible. ADR-152 (PR #553):
  copiar `scripts/automation` a `${RUNNER_TEMP}/automation-de-main` nada
  más hacer checkout, y que todo paso posterior al agente ejecute esa
  copia (veredicto en los cuatro workflows; recogida de Codex y
  agregación en la revisión). Guardián nuevo de 12 casos visto fallar
  contra los YAML sin tocar; presupuesto del corrector intacto en 80
  (congelación 1, `uv` 3 → 2); cadena completa 4984 en verde. Sin dato en
  vivo aún: lo dará la primera ronda sobre una rama anterior a ADR-149.
- **Datos 2 y 3 de ADR-145, y la raíz, que no era el corrector**: el
  corrector de la ronda 2 de #545 declaró «una sola invocación de
  `check.ps1`, código 0, 4992 passed» sobre un árbol que Quality tumbó en
  `ruff format` a los 24 s (dos ficheros de prueba sin formatear) y, tras
  mi commit de formato `923202f`, en `mypy` a los 21 s (`reflect.py:484`,
  `datetime >= None`). Con dos rondas de la misma familia, tocaba buscar
  la raíz y no seguir parcheando: la encontró la ronda 3 (run
  34009172673, 03:31 → 03:54, `FIXED` en `537a026`, 24 min). La
  declaración ERA verdad y el árbol estaba rojo a la vez, porque
  `scripts/check.ps1` encadena los cuatro comandos sin comprobar el
  código de salida de ninguno: `$ErrorActionPreference = "Stop"` no
  alcanza a los ejecutables nativos y `pwsh -File` devuelve el código del
  ÚLTIMO comando, así que el «exit 0» del guion era el de pytest y solo
  el de pytest. Lo que la entrada 41 leyó como «la forma obedecida, la
  verdad no» era el termómetro roto: los tres datos de ADR-145 son el
  mismo defecto del guion, no tres agentes mintiendo; y todas las
  validaciones «en verde» declaradas desde que existe el guion solo
  demostraban pytest. Ficha del operador ADR-153 (PR #554): cada comando comprueba
  `$LASTEXITCODE`, el guion se detiene en el primer rojo y termina con
  `exit $LASTEXITCODE`; guardián textual porque en el contenedor no hay
  `pwsh` (intenté bajarlo y el entorno lo denegó), de modo que el guion
  corregido lo ejecuta por primera vez el siguiente rol en un runner.
  El corrector señaló el defecto y no lo tocó, con razón: es la
  validación obligatoria de ADR-145, decisión de otro sitio. Y el mío:
  empujé `923202f` habiendo corrido en local solo `ruff format` y `ruff
  check`, no la cadena entera; «a medias», la misma familia. Costó un run
  de Quality (45 s) y la ronda 3 era inevitable igual —el error de mypy
  es de código—, pero la regla queda escrita: los parches del operador
  van bajo la misma norma que los roles, cadena completa antes de
  empujar, aunque «solo sea el formateador». Y otra vez la medida del
  ciclo: Quality en rojo → `repair-requested` → corrector en 12 s, sin
  ninguna mano.
- **ADR-150 en vivo, dos datos y ninguna mordida**: la ronda 2 de #545
  terminó en `FIXED` a los 24 min con la cadena declarada (fuera o no
  verdad), y la ronda de #550 (ciclo 2, run 34008597444, 03:17 → 03:40)
  corrigió cuatro hallazgos en 24 min —el P1 de Codex (`gh api` conmuta a
  POST con `-f`: `--method GET` explícito), la promesa de dos instantes
  servida por un filtro sobre un tercero (`created` frente a la
  reejecución, resuelta como «medir menos y decirlo», con guardián de
  docstring), la ventana de la pasada sin prueba (el doble registra sus
  llamadas) y el filtro fuera del `try` (una marca sin zona mataba la
  pasada diaria)— y empujó `2477876` + `823d3ac`. El tope de 36 no ha
  vuelto a morder; criterio en vivo de ADR-150 cumplido dos veces. De
  paso, el P1 de Codex enseña algo del método: el ejecutor simulado
  decidía el payload, así que ninguna prueba podía ver el método HTTP
  real; el defecto solo era visible leyendo la ayuda de `gh`.
- **Tropiezo mío de secuencia (04:11)**: #550 entró en
  `ready-for-merge` a las 03:56 y yo fusioné mi PR #553 a las 04:05 sin
  volver a mirar las etiquetas; al escribir `fusiona`, el guion de fusión
  lo paró con razón: «la PR #552 está 2 commit(s) por detrás de `main`;
  su Quality se calculó contra una base que ya no existe». Coste: un
  «Update branch» (hecho a las 04:13), Quality otra vez y —por ADR-142—
  una ronda de revisión más sobre el head nuevo antes de poder
  fusionarla; y #545, que llegó a `ready-for-merge` a las 04:11 sobre
  `537a026`, tendrá que pasar por lo mismo. Regla nueva del operador:
  **antes de mover `main`, mirar si hay alguna PR del motor en
  `ready-for-merge` y fusionarla primero**; y encadenar las fusiones de
  `main` en serie (cada una deja a la siguiente «por detrás»), no en
  paralelo. ADR-153 (PR #554) se queda abierta hasta que #552 esté
  dentro; después se fusiona, y un solo «Update branch» de #546 cubre las
  dos.
- **ADR-152 rompió su primer run real (04:31), y la lección es mía**: la
  revisión de #550 sobre el head actualizado (run 34011306916) congeló,
  recogió a Codex y agregó desde la copia sin problema, y el veredicto
  (`CHANGES_REQUESTED`) cayó al registrar la ronda:
  `FileNotFoundError: /home/runner/work/src/sirius_engine/round_history.py`
  en `sirius_drip_guard_cli.py` y en `sirius_convergence.py`. Los dos
  alcanzan `src/sirius_engine` por `parents[2]` de su propia ruta —dan
  por hecho que viven en `<raíz>/scripts/automation/`— y la copia plana
  en `${RUNNER_TEMP}/automation-de-main/` los dejó sin paquete. Parada
  segura `registro-de-ronda-fallido`; nada perdido salvo la ronda. El ADR
  decía «autocontenida» porque LEÍ que los ayudantes cargaban a sus
  hermanos por ruta propia, y no ejecuté la copia: la misma familia que
  la entrada 43 le reprocha al guardián de la suma («protegía la
  aritmética, no el sentido»). Corrección (misma decisión, ADR-152
  enmendado con sección fechada, PR #555): la copia reproduce el TRAZADO del árbol
  (`…/automation-de-main/scripts/automation` y `…/src/sirius_engine`) y
  las invocaciones van por ese trazado; guardián con un caso nuevo que
  ata los ayudantes que resuelven por `parents[2]` a las dos órdenes de
  copia (9 de 13 casos vistos fallar contra la copia plana); y esta vez
  EJECUTADO: reproducción local con el `python3` del sistema, copia plana
  → `record` en 1 con el mismo `FileNotFoundError`; copia con trazado →
  `record`, `family-check` y el guardián de goteo en 0. Regla: cuando un
  paso cambie de dónde se ejecuta un guion, listar todo lo que ese guion
  resuelve por `__file__` y ejecutarlo desde el sitio nuevo antes de
  fusionar. Coste: #550 en `failed-safely` hasta la fusión de la
  corrección y un `continua`; #545 sigue en `ready-for-merge` sin daño.
- **Primer dato en vivo de la copia con trazado (05:12), y la deuda 11
  cobrando su primera vuelta**: la revisión reanudada de #550 (run
  34013060064) aplicó su veredicto desde la copia congelada sin error:
  `CHANGES_REQUESTED` publicado con su `RONDA_HALLAZGOS` (ronda 2) y la
  incidencia a `repairing` a las 05:13. ADR-152 corregido funciona. El
  hallazgo único (CLAUDE-CR-151-004, baja; Codex aprobó) es exactamente la
  deuda 11: la terna de pytest que ADR-151 cita («4997 passed…») se midió
  sobre `823d3ac` y el «Update branch» trajo de `main` las 12 pruebas de
  ADR-152 sin tocar el ADR, así que la cifra ya no describe el head que se
  fusiona. Coste: una ronda de corrector y otra de revisión (~1 h) por una
  línea de documentación, y se repetirá con CADA actualización de rama
  que el guion de fusión exige ahora. El propio revisor da la forma que no
  caduca: cifra anclada al head («sobre el árbol de <sha>», citando el run
  de Quality). Candidata a ficha del operador: que los prompts del
  implementador y del corrector exijan esa forma (deuda 11).
- **Los dos agentes murieron a la vez a las 05:23-05:24, con coste 0**:
  el corrector de #550 (run 34013419739) corrió diez minutos y no
  sustituyó su veredicto provisional; el de #545 (run 34013875512) murió
  a los 437 ms del arranque —`is_error: true`, `num_turns: 1`,
  `total_cost_usd: 0`—: el primer mensaje a la API falló. Las dos
  incidencias a `failed-safely`, sin nada perdido. Con ese perfil (dos
  runners distintos, mismo minuto, coste cero) la causa que encaja es el
  tope de uso de la suscripción tras una noche de rondas seguidas; no hay
  dato directo porque la acción no transcribe el error. Queda como dato
  para la deuda 12 ampliada: una muerte en el arranque con coste 0 debería
  clasificarse como `infra_retryable` y re-armarse sola, en vez de exigir
  un `continua`. A esa misma hora el operador (esta sesión) también se
  quedó sin turnos hasta las 13:11: siete horas y media sin vigilancia,
  que el propietario cubrió con un «Dale» al despertar.
- **La revisión de #545 sobre el head actualizado (05:23) encontró 4
  hallazgos —dos P1 de Codex— en el MISMO código que ambos revisores
  aprobaron a las 04:11** (`537a026` → `4a05a64` solo añade el merge de
  `main`). El propio revisor Claude etiqueta su hallazgo como «LLEGA
  TARDE POR GOTEO DEL REVISOR». Los de Codex son afirmaciones nuevas sobre
  las correcciones de la ronda 2 (ancla que contradice el diagnóstico,
  parada retrasada frente al permiso). Se dejan al corrector: si son
  reales, mejor ahora que en `main`; si el freno de convergencia salta por
  familia repetida, es decisión del propietario. Dato para el guardián de
  goteo (deuda de la entrada 23): la aprobación previa no lo frenó.
- **ADR-154 (PR #556)**: la ficha de la deuda 11, montada durante la
  espera: `corrector.md` in situ e `implementer-v4.md` por H-28 exigen la
  terna y el código de salida anclados al árbol («sobre el árbol de
  `<sha>`»), y declaran que un «Update branch» no invalida una cifra
  anclada. Guardián visto fallar (2 de 2 prompts vigentes), 100 passed en
  los seis módulos afectados, cadena completa sobre `c3514e9`: 4998
  passed, 16 skipped, 2 xfailed, `check=0`.
- **Estado a las 13:32 UTC (14:32 del propietario)**: `main` en
  `52344dc` tras cuatro fusiones del operador (#553 `3a00e04` 04:05,
  #555 `4cd8924` y #554 `dc45b59` 05:03, #556 `52344dc` 13:29). Las dos
  ramas del motor actualizadas con `main` a las 13:30 (#552 → `821b2ac`;
  #546 → merge nuevo) ANTES de reanudar, para que cada corrector trabaje
  sobre el árbol que se fusiona; `continua` en #550 y en #545 a las
  13:31, con nota previa en cada una. Pendiente por incidencia: #550, un
  hallazgo bajo (terna del ADR-151, que con ADR-154 se ancla); #545,
  cuatro hallazgos (P3 + P2 + dos P1) sobre el head aprobado a las 04:11.
  Después: Quality → revisión → `fusiona` en cada incidencia; el segundo
  en llegar necesitará otro «Update branch» y su ronda de ADR-142.
  ADR-148 (memoria) sigue esperando, por orden del propietario, a que lo
  demás termine.

---

## Deudas abiertas (necesitan incidencia o decisión del propietario)

1. `ollama_category_classifier.py`: ruta relativa y sin
   `follow_redirects=False` (mismo hueco que 7). Sin arreglar a propósito:
   fuera del alcance de M21a.
2. Intérprete de intención del despachador: falsos positivos por subcadena
   (5). ADR-043 lo reconoce como apaño.
3. Ruta H-34: el verde de Quality se pierde si llega en `repairing`
   (entradas 3 y 18: tres veces hoy). También el ROJO si llega en
   `implementing` (entrada 41, #546: el veredicto declaró `exit 0` y
   Quality dijo que no; nadie lo encaminó hasta relanzarlo a mano).
   Candidata a encargo: al pasar a `ci-pending`, consultar el último
   Quality completado del head y encaminar sin esperar al evento.
   **Arreglo fusionado el 06-09** (ADR-149, PR #549, `6ba5901`, entrada
   43): el veredicto relanza el run de Quality del head si ya terminó al
   entrar en `ci-pending`. Queda **sin dato en vivo**: se salda cuando el
   primer ciclo deje su `QUALITY_RELANZADO` y se encamine solo. **Primer
   intento en vivo, inerte (06-09, 03:15, entrada 44)**: el veredicto de
   #545 corrió el `sirius_apply_verdict.sh` de la rama de la PR (anterior
   a ADR-149), no el de `main`; ADR-152 (PR #553) congela la automatización
   de `main` al arrancar cada job. El dato en vivo sigue pendiente.
4. Cliente único de Ollama local para los tres adaptadores (7, 8).
5. Vigilancia durable con modelo barato (4, 11).
6. Rechazo de una propuesta de criticidad recordado solo en sesión (M21b):
   persistirlo necesita columna y decisión del propietario.
7. Suite GUI: `test_streaming_message_grows_without_overlapping_neighbours`
   depende del orden/estado de Qt (entrada 16). Volvió a morder el 06-09
   a las 04:16 en la cadena del operador sobre la rama de ADR-153
   (`assert 32 >= 54`, con `QT_QPA_PLATFORM=offscreen` y un cambio que no
   toca ni la GUI ni Python): una cadena entera de 9,5 min repetida por
   un dato de altura de Qt. Sigue sin incidencia.
8. Corrector del motor: presupuesto o un commit por hallazgo cuando la
   ronda trae varios hallazgos de interfaz (entradas 9 y 16), y poder
   cancelarlo cuando el propietario corrige a mano (entrada 17). ADR-150
   (06-09, entrada 43) sube el tope del paso de 30 a 36 min y el job a 85
   —lo máximo que el contador de siete días permite— para que quepa la
   cadena completa de ADR-145 tras la corrección; dos rondas en vivo
   después (24 min cada una, entradas 43 y 44) el tope no ha vuelto a
   morder. El presupuesto por hallazgo y la cancelación siguen abiertos
   (encargo del motor), y la opción 4 de ADR-150 (`check.ps1` como paso
   determinista tras el agente) espera decisión del propietario.
9. Medición con Ollama real de M19b y M20 en la máquina del propietario
   (filas pendientes en ADR-128 y ADR-129). **SALDADA el 05-09** (entrada
   41): 0 críticas perdidas (venía de 10), cobertura 70/81 (de 59), con
   `qwen3:4b-instruct`, 47 llamadas, 0 rendiciones; filas rellenadas con
   la ejecución transcrita y comparadas contra el 02-09.
10. Ruta de vuelta a revisión desde `ready-for-merge` cuando el head se
    mueve: el agujero más repetido del motor (entradas 25 y 29, dos veces
    el 04-09). **SALDADA el 05-09**: ADR-142 (#536, entrada 35) — origen
    nuevo en la ruta de avance, solo verdes, con guard de aprobación
    vigente. La receta manual (etiqueta a `ci-pending` + relanzar el run
    verde) queda solo como plan B si el workflow fallara.
11. Los ADR citan recuentos de la suite completa, que se desfasan con
    cada merge a `main` (3 rondas perdidas el 04-09, entrada 29):
    convenio candidato — citar recuentos por fichero del encargo, o
    marcar el total como «del árbol en <sha>».
12. Fallos de infraestructura de los revisores (timeout de Codex a
    1200 s; revisor Claude sin `reviewed_head_sha`) cuestan una vuelta
    entera cada uno (entradas 29 y 31, tres el 04-09). **SALDADA el
    05-09**: ADR-141 (#535, entrada 34) — el agregador clasifica
    (`infra_retryable`) y el aplicador re-arma UNA ronda nueva con
    candado material por head; una parada persistente detiene igual.
13. C1b — el enganche de `sirius-reflejar` en los workflows. **SALDADA
    el 04-09** (ADR-137, #531, entrada 32): el enganche vive, su primera
    pasada reflejó 70 WorkItems y la segunda fue idempotente. Queda C2
    (declarar `programacion` en `CLASES_CON_ESTADO_PROPIO`, ADR-101),
    que va después de observar al menos una pasada real del contador con
    el espejo poblado — la primera candidata es la de hoy, entregada
    hacia las ~08:00 UTC reales (entrada 36), y no podrá decir
    «comparable» hasta que C2 encienda la jurisdicción.
14. La hora del contador, de punta a punta (decisión del propietario;
    entradas 36 y 37 + diagnóstico del corrector en #537). **(a) y (b)
    SALDADAS el 05-09** (ADR-144, #541, entrada 40): el derivador ya no
    se cuenta a sí mismo — la derivada vuelve a 03:24, coincide con el
    cron cableado, la cabecera vuelve a ser verdad sola y un guardián
    vigila la coincidencia. Queda **(c)**: GitHub ENTREGA ese cron con
    43 min-12 h de retraso (~08:00 estos días), así que la geometría
    estática no gobierna el reloj de pared — candidato decidido por el
    propietario para una ficha posterior («derivador ya; ventana
    después»): la pasada mide su propia ventana al llegar, contra runs
    reales.
15. Reanudador (`sirius_resume_on_command.sh`): un segundo `continua`
    sobre el MISMO head no deja marcador propio porque
    `sirius_comment_once` desduplica por texto (entrada 41: la premisa
    falsa de #545). Ficha del operador: que el marcador lleve run y
    attempt (patrón ADR-140) para que cada permiso escrito deje un
    rastro distinto. Mientras tanto, el reflector acredita también la
    orden exacta `continua` del propietario (decisión registrada en
    #545).
