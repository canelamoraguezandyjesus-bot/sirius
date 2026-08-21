# Dónde estamos

Foto del **21 de agosto de 2026, 03:24 UTC**. Nada de este documento cambia el
repositorio: todo lo que hay aquí son lecturas.

    $ date -u
    Fri Aug 21 03:24:24 UTC 2026

Cada afirmación lleva debajo el comando que la sostiene y su salida recortada.
Si algo no lo pude comprobar, está al final, en su propia sección, sin maquillar.

**Aviso antes de empezar.** Has dicho que paras. El ciclo automático no ha
parado: la incidencia #211 seguía moviéndose sola mientras se escribía esto.

    issue_read(get_labels, 211) → [{"name":"sirius:repairing"}]
    (a las 02:45 estaba en `sirius:implementing`; a las 03:17, en `sirius:repairing`)

Si lo que quieres es congelar y mirar, hoy no está congelado.

---

## 1. Dónde estamos

### Lo que está terminado y funcionando

**La Fase A del motor está completa.** Ocho bloques de diecinueve están dentro
de `main`, todos entre el 15 y el 21 de agosto. Seis días.

| Bloque | Qué es, en una línea | Fusionado |
|---|---|---|
| E0 | El permiso escrito para construir el motor | 15-ago |
| A1 | Las reglas del juego: qué es un trabajo y qué saltos están prohibidos | 17-ago |
| S1 | Experimento desechable: cómo guardar en disco sin perder ni duplicar | 17-ago |
| A2 | El motor ya no olvida al reiniciarse | 18-ago |
| A3 | El motor ya puede MIRAR GitHub (sin tocar nada) | 18-ago |
| A4 | Qué puede y qué no puede hacer cada rol, y la barrera de salida de datos | 19-ago |
| E1a | Quién manda sobre cada tipo de trabajo (contrato v1.7) | 19-ago |
| A5 | Distinguir charla de orden, presupuesto con corte, escalado al propietario | 21-ago |

    $ git log --date=format-local:'%Y-%m-%d %H:%M' --pretty='%ad %s' <sha>
    2026-08-15 21:46  E0: autorizar la implementacion del Work Engine (#176)
    2026-08-17 01:42  A1: núcleo puro determinista del Sirius Work Engine (#178)
    2026-08-17 13:26  S1 — Spike I3: patrón de escritura seguro del almacén (#185)
    2026-08-18 14:55  A2 — Almacén durable + barrido de recuperación (#189)
    2026-08-18 23:31  A3 — Espejo de solo lectura + contexto.recuperar v0 (#194)
    2026-08-19 13:38  A4: perfiles + WorkerRequest + Resolver v0 + egress (#203)
    2026-08-19 14:55  Contrato v1.7: la autoridad de cada clase se fija antes (#205)
    2026-08-21 01:03  A5: interacción e intención v0 (#207)
    2026-08-21 02:05  El corte por presupuesto no salía de WAITING (#210)

**Main está en verde ahora mismo.**

    $ git log -1 --pretty='%H %ad %s' --date=iso origin/main
    e8123499076817317dde7c59adb00dda62971fa8 2026-08-21 04:05:33 +0200
    El corte por presupuesto no salía de WAITING, que es donde se gasta (#210)

    actions_list(quality.yml, branch=main)
    721 success 2026-08-21T02:05:36Z e8123499   ← la cabeza de main

### Los números reales

- **2.852 pruebas**, repartidas en 205 ficheros.
- **El motor**: 43 ficheros de Python, 6.179 líneas. Sus pruebas suman 7.073
  líneas: hay más prueba que motor.
- **El Sirius de siempre** (la aplicación de escritorio): 22.425 líneas. El
  motor nuevo es todavía una cuarta parte de eso.
- **44 documentos de decisión (ADR)**.

```
$ ./.venv/bin/python -m pytest --collect-only -q | tail -1
2852 tests collected in 5.62s

$ find src/sirius_engine -name '*.py' | xargs wc -l | tail -1
  6179 total
$ find tests/engine -name '*.py' | xargs wc -l | tail -1
  7073 total
$ find src -name '*.py' -not -path '*sirius_engine*' | xargs wc -l | tail -1
 22425 total
$ ls docs/decisions/ADR-*.md | wc -l
44
```

### Tres cosas que conviene que sepas sin buscarlas

**1. El primer hito (M1) está alcanzado por las pruebas, pero tú no puedes
usarlo.** M1 prometía que puedas hablar con Sirius y preguntarle por cualquier
trabajo. Las 449 pruebas del motor pasan. Pero **no existe ningún comando que
puedas teclear**: la "interfaz" es una clase de Python que solo usan las
pruebas. No hay entrada de programa, no hay arranque, no hay nada que ejecutar.

    $ git show origin/main:pyproject.toml | grep -A3 'project.scripts'
    [project.scripts]
    sirius = "sirius.main:main"
    sirius-voz = "sirius.voice_doctor:main"
    sirius-obs = "sirius.capture_setup:main"
    (ninguna entrada para el motor)

    $ git grep -rn '__main__\|argparse' origin/main -- src/sirius_engine
    (sin resultados)

Es un hueco pequeño de tapar. Pero mientras no se tape, M1 es un hito que
verifican las máquinas y que tú no has vivido.

**2. El motor nunca ha ejecutado un encargo real. Ni uno.** El cuaderno donde
apuntaría lo que hace está vacío, y no existe siquiera la pieza que arranca a
un trabajador.

    $ find /home/user/sirius -name '*.jsonl' -not -path '*/.git/*'
    (vacío: el diario del motor está sin estrenar)

    $ git ls-tree --name-only origin/main src/sirius_engine/ports/
    __init__.py  github_mirror.py  notification.py  store.py  world.py
    (no hay worker.py: no existe la puerta para arrancar un trabajador)

Esto no es un fallo. Es dónde estamos: el chasis está construido y el motor
todavía no ha arrancado nunca.

**3. Anoche main estuvo unas cuatro horas en rojo y no se puede saber por qué.**

    actions_list  713 failure 2026-08-20T22:57:40Z fbc5282b   (PR #209)
    ...           719 success 2026-08-21T01:03:05Z
    get_job_logs(job_id=96609665274) → Error: HTTP 404

Duró 2 segundos y GitHub ya no da los registros. **No pude leerlo.** No digo
que fuera inofensivo: digo que no se sabe.

---

## 2. Qué falta, y en qué orden

Quedan once bloques. Uno está en marcha. La regla corta, primero:

> **Todo lo que queda se puede construir sin gastar un céntimo, salvo dos
> cosas: una parte de S2 (que puede exigir una clave de pago, y para saberlo
> hay que hacer S2) y D3 (Telegram, que exige abrir un bot).**
>
> Lo que bloquea a casi todo lo demás **no es el dinero: es tu firma en un
> documento** (el contrato v1.8, bloque E1b).

Los minutos de GitHub son gratis porque el repositorio es público, y la
revisión de Codex va incluida en la cuenta que ya tienes.

    API de GitHub → "full_name": "canelamoraguezandyjesus-bot/sirius", "private": false
    Contrato v1.7 §0: «Codex participa además como segundo revisor ... mediante su
    integración nativa con GitHub incluida en ChatGPT Business (sin API de OpenAI).»

### La lista, en orden del plan

| Bloque | Qué es | ¿Se puede hoy? | ¿Dinero? |
|---|---|---|---|
| **S2** | Probar si el investigador externo funciona y qué cuesta | **SÍ, hoy** | Solo si el camino gratis falla |
| **B1** | Que Sirius investigue de verdad desde una orden | Código sí; terminarlo exige S2 | Hereda el de S2 |
| **E1b** | Contrato v1.8: permitir al motor activar y vigilar | **SÍ, hoy. Es un documento** | No |
| **S3** | Medir cuándo GitHub dice que algo terminó | **EN MARCHA AHORA** | No |
| **C1** | Que el motor desatasque solo lo que se cuelga | No: falta S3 y el v1.8 | No |
| **C2** | Una orden tuya y no tocas GitHub hasta "fusiona" | No: falta C1 | No |
| **C3** | El mismo ciclo para documentos | No: falta C2 | No |
| **C4** | La auditoría dentro del motor | No: falta C2 | No |
| **D1** | Pasar el mando de GitHub al motor, clase por clase | No: falta C3 + 14 días en verde | No |
| **D2** | Que el motor corra solo, siempre | No: falta que decidas DÓNDE vive | Quizá |
| **D3** | Hablar con Sirius por Telegram | No, y está fuera del alcance aprobado | Bot gratis, cuenta nueva |

    $ git show origin/main:docs/.../AUTOMATION_OPERATING_CONTRACT.md | sed -n '1,3p'
    # SIRIUS - Contrato operativo de automatización
    - **Versión:** 1.7            ← la 1.8 (E1b) no existe

    Plan, línea 404, literal:
    «Dependencia real: A3 + S3 + **E1b (C2)**. Sin la v1.8 este bloque NO empieza.»

### El salto de fase que nadie escribió

El plan puso la **Fase B** (S2 + B1, "que Sirius investigue") **antes** que la
Fase C, a propósito, porque da valor nuevo sin depender de GitHub. El ciclo
automático ha arrancado **S3, que es Fase C**, y la Fase B sigue intacta: cero
ficheros, cero incidencias.

    $ git ls-tree -r --name-only origin/main | grep -i 'spike_i2'
    (sin resultados)
    $ git grep -il 'gpt_researcher' origin/main -- src
    (sin resultados)
    18 incidencias abiertas: ninguna de S2 ni de B1.

    Plan, líneas 63-65: «B1 demuestra la promesa diferencial de #172 §6 ... Se
    coloca ANTES que la Fase C a propósito»

S3 no es tiempo perdido (mide para C1 y no cuesta nada). La pregunta es qué va
**después**, y hoy la inercia va por la Fase C sin que nadie lo haya decidido.

### Sobre el dinero, con precisión

Hay **un solo punto** en todo lo que queda donde puede aparecer un gasto: dentro
de S2, al probar si el investigador funciona con un modelo que corre en tu
propio ordenador (gratis) o solo con una clave de pago.

    Plan, líneas 320-327, literal:
    «Probar primero el camino sin gasto (modelo local vía Ollama) ...
     si solo funciona con clave de pago, eso es un dato que sube al propietario.»
    «Decisión humana previa: SOLO SI el spike demuestra que exige gasto.
     Si el camino local basta: ninguna.»

O sea: **S2 se arranca hoy sin pedirte permiso y sin pagar nada.** Solo si el
camino gratis no sirve te sube la pregunta. Y el coste real de esa herramienta
está hoy **sin verificar** — literalmente eso es lo que S2 existe para averiguar.

---

## 3. Lo que se ha quedado atrás

### Lo más grave: cuatro defectos encontrados siguen vivos, y no están apuntados en ningún sitio

Una auditoría del 20 de agosto encontró seis defectos. Dos se arreglaron. **Los
otros cuatro siguen dentro de `main` hoy**, comprobados uno a uno:

| # | Qué pasa | Dónde |
|---|---|---|
| D-3 | Si no se puede leer el resultado de un trabajo, se guarda como **éxito vacío**. Indistinguible de un éxito de verdad | `recovery.py:94` |
| D-4 | El "filtro de autores de confianza" filtra los comentarios pero **no el cuerpo** de la incidencia | `mirror_projection.py:196` |
| D-5 | Dos de las tres fuentes de contexto saben decir "no pude leer"; **la tercera no** | `context_recall.py:263` |
| D-6 | El campo que dice **con qué se ejecutó** un trabajo es texto libre, no lo que la arquitectura exige | `run.py:71` |

```
$ git show origin/main:src/sirius_engine/recovery.py | grep -n succeed_run
94:  store.succeed_run(live.run_id, resultado=observation.resultado or {}, now=now)

$ git show origin/main:src/sirius_engine/mirror_projection.py | sed -n '196,197p'
de_confianza = [c.cuerpo for c in comentarios if es_autor_de_confianza(c)]
return "\n".join((*de_confianza, cuerpo))          ← el cuerpo entra sin filtrar

$ git show origin/main:src/sirius_engine/context_recall.py | grep -n proveedores_fallidos
263:  proveedores_fallidos=fallidas_arbol + fallidas_incidencias,   ← falta git

$ git show origin/main:src/sirius_engine/domain/run.py | grep -n 'worker:'
71:    worker: str
```

**Y ahora lo que de verdad importa.** El único documento que enumera esos
cuatro defectos **no está en main**, no tiene ninguna solicitud de fusión
abierta, y **ninguna de las 18 incidencias los menciona**.

    $ git cat-file -e origin/main:docs/audits/DEFECTOS_ENCONTRADOS_2026-08-20.md
    fatal: path ... does not exist in 'origin/main'
    $ git branch -a --contains 45e5894
      remotes/origin/claude/sirius-learning-audit-ixtr0g     ← solo ahí
    PRs desde esa rama (state: all): []
    Búsqueda en incidencias: total_count: 0

Traducido: **si tú no te acuerdas de que existen, nadie más lo sabe.** Eso es
exactamente tu queja, en su forma más pura: encontrar el defecto no sirvió de
nada, porque el hallazgo no quedó enganchado a nada que lo persiga. Y la suite
entera pasa en verde con los cuatro dentro (2846 passed).

### Papeles rotos

**El documento que arregló el fallo de ayer cita como prueba un fichero que no
existe en main.** ADR-045 se apoya en ese parte de defectos. Quien mañana quiera
comprobar por qué se decidió eso, encuentra una ruta rota.

    ADR examinados: 44 | citas de ruta reales: 76 | ADR con citas rotas: 3
    ADR-045-...  NO EXISTE: docs/audits/DEFECTOS_ENCONTRADOS_2026-08-20.md
    ADR-027 y ADR-028 → citan un fichero borrado a propósito (ahí lo roto es el texto)

**Hay dos ADR con el mismo número, el 016, y faltan el 017 y el 018.** No se han
perdido: viven en la solicitud de fusión #171, que está congelada por decisión
tuya.

    $ ls docs/decisions/ADR-*.md | sed -E 's/.*ADR-([0-9]+).*/\1/' | sort | uniq -c | awk '$1>1'
          2 016
    $ ls docs/decisions/ADR-01[78]*
    ls: No such file or directory

### Incidencias antiguas paradas: qué espera a ti y qué no

Hay 18 abiertas. Ocho son tableros permanentes (#8 a #15) y no son trabajo
parado. De las demás:

**ESPERAN A ALGO TUYO** (hardware, tus manos, o una decisión):

| # | Qué falta exactamente |
|---|---|
| #126 Voz | El código entero está en main. Falta probar el micrófono en Windows. Solo puedes hacerlo tú. Lleva desde el 7 de agosto con la etiqueta de "parada en fallo" puesta |
| #127 Captura | Código en main. Faltan dos cámaras físicas, OBS real y una grabación con tres cambios de escena |
| #134 Interfaz | Implementada. Falta que mires una grabación a 1080p y digas si te gusta. Diez minutos |
| #154 Auditoría | El trabajo terminó el 15 de agosto. Espera que decidas si se fusiona la #171 |

    Cuerpo de #126: «No puede declararse APTO todavía. Ninguna prueba automática
    usa micrófono, altavoces, red ni clave real... solo puede confirmarlo la
    prueba manual del día 5, que sigue pendiente.»
    #126 labels: ["sirius:failed-safely"], sin tocar desde 2026-08-07
    #127 labels: ["sirius:planned"],       sin tocar desde 2026-08-06

**NO DEPENDEN DE TI** (se pueden cerrar o mover sin que hagas nada):

- **#164** ya está arreglada en main (la prueba intermitente de copias se hizo
  determinista, con su ADR-038). Sigue abierta y parece un fallo vivo. No lo es.
- **#167** (estreno del Auditor) entregó su informe. De sus dos hallazgos, uno ya
  está corregido en main; el otro es que un documento promete un permiso que el
  Auditor no tiene.
- **#25** describe una forma de trabajar de julio que el contrato v1.7 ya no usa.
  Tenerla abierta como vigente contradice el contrato real.
- **#137** (prueba intermitente de la conversación) está parada **por decisión
  tuya**, del 10 de agosto, y a propósito: cerrarla borraría el único sitio donde
  está explicado por qué falla. En 12 pasadas completas del 19 de agosto no falló
  ninguna vez.

```
tests/integration/test_sqlite_backup_restore.py:242 (ya en main)
  sustituto = "A" if ciphertext[0] != "A" else "B"     ← #164, arreglado
#137, comentario del 10-08: «Decisión del propietario: opción B — Se deja
  documentado y no se arregla»
```

### Ramas y deuda de código

De más de 150 ramas, **solo tres tienen trabajo real que main no tenga**: la de
la auditoría de defectos (sin solicitud de fusión), la del Investigador (#171,
esperando tu decisión desde el 15 de agosto) y una enorme de evidencia antigua
(#117, del 25 de julio, 220 commits). Todo lo demás que parecía trabajo perdido
resultó estar ya integrado con otro nombre; se comprobó una por una.

**Deuda escondida en el código: no hay.** Cero marcadores de "arreglar esto
luego". Este frente está limpio y merece decirse igual de claro que lo malo.

    En src/ y tests/ de main:  TODO 5  FIXME 0  XXX 0  HACK 0
    (los 5 "TODO" son la palabra española «todo» dentro de frases)

---

## 4. El aprendizaje

### Qué es

Que Sirius aprenda **de su propio historial de trabajo**, no de internet. Cuando
un encargo termina, eso queda escrito en el cuaderno del motor. La idea es que,
**cuando tú lo pidas**, alguien lea ese cuaderno y saque **candidatos** a
lección: qué salió mal, qué procedimiento funcionó.

Con tres cerrojos escritos: lo que sale son candidatos y nunca entra en vigor
sin que tú lo apruebes; quien detecta la lección no puede activarla; y si una
lección cambiaría quién decide, cuánto se gasta o qué permisos hay, **eso no es
un candidato, es una pregunta para ti**.

    Auditoría §7: «HISTORIA: no se aprende, se registra» | «MEMORIA: sí, como
    candidato; jamás activo sin aprobación» | «GOBIERNO/DECISIONES: Nunca. Ni
    como candidato»

### Qué se decidió

**No construirlo todavía**, y por un motivo que no es pereza. La sesión sometió
su propio diseño a rondas de crítica. Dos rondas seguidas devolvieron defectos
de la misma familia, así que se activó tu propia regla: parar y buscar la raíz.

La raíz, literal: *«El brief se escribió contra los documentos de Sirius, no
contra su código»*. Y la razón fuerte para no construirlo, también literal:
**«no hay experiencia real de la que aprender»**. El cuaderno está vacío
(comprobado arriba: cero ficheros de diario). Un sistema que aprende sin nada
de lo que aprender es, en sus palabras, *«un generador de ruido con coste»*.

**No está muerto ni aplazado a ojo.** Está detrás de una puerta con siete
condiciones comprobables. Las volví a comprobar hoy contra main:

| # | Condición | Hoy |
|---|---|---|
| 1 | ¿Existe la pieza que arranca un trabajador? | **NO** |
| 2 | ¿Existe un trabajador real? | **NO** |
| 3 | ¿Hay cuadernos escritos en disco? | **NO** (cero) |
| 4 | ¿Hay variedad en lo registrado? | **NO** |
| 5 | ¿Se sabe con qué modelo se hizo cada cosa? | **NO** |
| 6 | ¿El observador puede decir "no pude mirar"? | **NO** |
| 7 | ¿El corte de presupuesto funciona fuera del estado feliz? | **SÍ, desde ayer** |

```
$ git ls-tree --name-only origin/main src/sirius_engine/ports/
__init__.py  github_mirror.py  notification.py  store.py  world.py   (no hay worker.py)
$ find /home/user/sirius -name '*.jsonl' -not -path '*/.git/*'
(vacío)
$ git show origin/main:src/sirius_engine/domain/run.py | grep -icE 'modelo|runtime|model'
0
$ git show origin/main:src/sirius_engine/ports/world.py | grep -c UNKNOWN
0
   (los estados posibles son: pending, succeeded, failed, lost, cancelled)
```

**Un aviso que importa**: la condición 5 —saber con qué modelo se hizo cada
cosa— **no la programa ningún bloque del plan**. Si nadie la engancha a B1 o a
C2, llegará el final del plan, se cumplirán las demás y la puerta seguirá
cerrada sin que nadie sepa por qué. Es una decisión pequeña y barata de tomar
ahora.

### Dónde encaja, y el cabo suelto

**El "modo aprendizaje" no está en el plan. Ni mencionado.**

    $ git show origin/main:docs/.../SIRIUS_WORK_ENGINE_PLAN_IMPLEMENTACION.md | grep -iE "aprend|learning"
    (vacío: ninguna coincidencia en todo el plan)

Y hay una razón formal que te protege: el permiso vigente autoriza el motor
*«estrictamente según ADR-020 y su plan aprobado»*. El aprendizaje no está ahí,
así que **hoy no está amparado ni en su forma mínima**. Para que entrara haría
falta una decisión tuya que amplíe ese permiso, igual que hizo falta para
empezar el motor. Eso es lo que quiere decir el título de ese documento:
*entra por la puerta de autoridad, no por el plan*.

**Cabo suelto confirmado:** el documento de esa rama se numeró 043, y en main ya
hay un ADR-043 (el de A5). Si se integrase tal cual, la solicitud se pondría en
rojo, igual que pasó con los dos 042. La propia rama ya lo avisó por escrito y
dice que renumerará. Es un arreglo de un minuto, pero hay que hacerlo antes de
tocar esa rama.

### Tus dos peticiones, con la verdad delante

**"Que esté pendiente de todas las tareas y me avise": está a medias.** Existe la
tubería (A5 trajo un puerto de notificación y una salida por terminal, pensados
para que Telegram lo implemente después sin tocar el motor). Pero **solo avisa
de escaladas** —cuando se atasca o necesita que decidas—, no cuando algo
termina bien. Y no guarda nada: si no estás mirando, el aviso se pierde. Que te
llegue al móvil es D3, que está explícitamente fuera del alcance aprobado.

    ports/notification.py: «class NotificationPort(Protocol): def notificar(self, escalada)»
    adapters/cli_notification.py: «no es un histórico durable ni sobrevive a la sesión»
    domain/escalation.py: «Las siete causas de arquitectura §10, y ninguna más.»

**Tu preocupación por la memoria repartida es justa, y ya tiene nombre.** Hoy hay
cinco sitios que guardan estado: el cuaderno del motor (construido y vacío), su
versión de pruebas, el espejo de GitHub (solo mira), **GitHub mismo** (que hoy
es quien manda de verdad) y la memoria del producto Sirius (una base de datos
con 12 tablas, esa sí viva).

Hay una prueba que impide que los dos mundos se importen entre sí, y eso
protege el código. **Pero no impide compartir el concepto.** Si el motor se
construye su propia memoria antes de que decidas si la del producto debe
servirle, acabas con dos memorias, dos ciclos de vida y dos autoridades. La
auditoría lo dice sin escaparse:

    §11 A4: «Veredicto: la objeción sobrevive entera. No la puedo cerrar con
    evidencia. ... Construir la MEMORY del motor antes de decidir si la memoria
    del producto debe servir al motor es exactamente el error de ADR-005
    cometido a mayor escala.»

    $ git grep -l -i "dos memorias|segunda memoria" origin/main -- docs/
    (vacío: NINGÚN ADR de main decide esta pregunta)

Como precaución, el diseño ya dejó bloqueado el conocimiento activo del motor
hasta que respondas. **No cuesta código: cuesta que contestes.**

---

## 5. Por qué los fallos los encuentras tú

Tienes razón, y el motivo tiene nombre exacto.

### Quién encontró cada fallo real de estos dos días

| Fallo | Quién lo encontró | ¿Costó algo tuyo? |
|---|---|---|
| Dos ADR con el mismo número (042) | **Una guarda automática** | No. La solicitud se puso en rojo sola |
| Etiqueta de activación mal puesta en #211 | **Una guarda automática**, en 14 segundos | Poner la etiqueta que faltaba |
| **El corte de presupuesto no salía de WAITING** | **Una sesión auditando, DESPUÉS de fusionar** | Sí. Pasó por todo el ciclo en verde |
| El volcado de conversaciones al registro público | **Una sesión auditando** | Sí. No existía ninguna guarda |
| Cuelgue de 20 minutos, dos veces | La guarda **detectó la parada**, no la levantó | Sí. Diagnóstico y arreglo manuales |
| Un hallazgo falso del revisor | Lo refutó el corrector, gastando dos rondas | Acabó parado y hubo que intervenir |

```
Timeline de la incidencia #206 (el fallo del presupuesto):
  2026-08-21T00:52:01Z  REVIEW_APPROVED — dual aprobada (Claude + Codex)
  2026-08-21T01:02:47Z  el propietario: «Fusiona»
  2026-08-21T01:03:30Z  SIRIUS_COMPLETED — el defecto entró en main
Rondas de revisión: cinco. El defecto estaba dentro en las cinco.
```

### El mecanismo, dicho claro

Hay **once guardas automáticas** y diez no dependen de ningún modelo. Son buenas.
Pero todas cazan **la misma clase de error: la violación de una regla que
alguien ya escribió después de tropezar** — un número repetido, una etiqueta que
falta, una sección que falta, un import prohibido.

**Ninguna caza lo que nadie previó.** La única guarda pensada para eso es la
revisión doble, y es justo la que depende del modelo: en la #207 uno de los dos
revisores aprobó tres de las cuatro rondas que sí tenían defectos, y al final
los dos aprobaron el trabajo con el fallo dentro.

Lo que **sí** ha encontrado defectos nuevos estos dos días —tres de los seis
casos— es **una sesión haciendo una auditoría dedicada**. Y una auditoría solo
arranca cuando tú la pides.

> **No eres el que encuentra los fallos. Eres el disparador del único mecanismo
> que los encuentra.**

### El agujero, con nombre y sitio

El fallo del presupuesto era de esta clase: *una función de política da por
supuesto en qué estado está el trabajo, y sus pruebas solo lo arrancan desde el
estado feliz*. El trabajo estaba en **WAITING** —que es justo el estado en el
que hay un proceso fuera gastando dinero— y ninguna prueba pasaba por ahí.

    El mismo grep, antes del arreglo (citado en ADR-045):
    $ grep -c "WAITING\|dispatch_work_item_async\|waiting" tests/engine/test_governance.py
    0
    Hoy, después: 3

Un revisor lee **lo que está escrito**. Esto era **una ausencia**. Por eso no lo
vio nadie.

**Y aquí está la buena noticia disfrazada:** tu repositorio YA tiene la solución
escrita, una capa más abajo. Las reglas del juego (`test_work_item_transitions.py`)
sí tienen una **tabla exhaustiva**: cada operación contra cada estado, 96 casillas,
y si alguien añade un estado nuevo la prueba se rompe hasta que lo rellene. Lo
que no tiene esa tabla es la capa que **llama** a las reglas. Ahí vivía el fallo.

    $ grep -n 'parametrize' tests/engine/test_work_item_transitions.py
    181:@pytest.mark.parametrize("state", list(WorkItemState), ids=lambda s: s.value)

Y hay **cuatro sitios más con la misma forma**, hoy, medidos: una función hermana
en el mismo fichero del fallo, y tres casos de estado que ninguna prueba visita.

    $ coverage run --branch --source=src/sirius_engine -m pytest tests/engine -q
    449 passed
    governance.py   93%  → 77, 128->130
    work_item.py    99%  → 254
    run.py          98%  → 192
    recovery.py     98%  → 117

### Lo que NO funcionaría (para no venderte humo)

**Exigir más "cobertura de pruebas" no habría cazado el fallo.** Lo demostré: se
midió el árbol exacto anterior al arreglo y la cobertura salió **93 %, la misma
cifra que hoy después de arreglarlo**. Y la línea del defecto no aparecía como
descubierta: estaba ejecutada al 100 % — desde el estado bueno.

    $ git archive 6369fa5 | tar -x -C <scratchpad>   (el árbol CON el fallo dentro)
    $ coverage report --show-missing
    src/sirius_engine/governance.py   93%   77, 119->121
    $ grep -n 'cancel_all_live_runs_and_escalate_work_item' .../governance.py
    82: ...   ← la línea del defecto. NO figura como descubierta. Cubierta y rota.

La cobertura cuenta **líneas ejecutadas**, no **estados visitados**.

### Las cuatro guardas que cerrarían esto

Las cuatro son pruebas normales y Python corriente. **Ninguna necesita que el
modelo sea caro ni listo: son tablas, lectura de ficheros y comprobar si una
ruta existe. No razonan.**

**1. Una tabla de estados para la capa que llama a las reglas.** Copiar arriba
el patrón que ya funciona abajo: cada función de política × cada estado, y qué
debe pasar en cada casilla. Añadir un estado nuevo rompe la prueba hasta que
alguien la rellene. *Caza exactamente el fallo de ayer y las cuatro casillas
vacías de hoy.* Coste estimado: un fichero de pruebas, unas 150 líneas.

**2. Que ninguna operación se quede fuera de esa tabla.** Hoy dos operaciones
(`change_scope` y `reprioritize`) tienen guarda de estado y **no están en la
tabla**, y nadie se dio cuenta. Una prueba de treinta líneas lee el código y
falla si alguna se queda fuera. *Impide que el agujero se vuelva a abrir.*

    $ grep -n 'change_scope\|reprioritize' tests/engine/test_work_item_transitions.py
    NO APARECEN

**3. Una lista de defectos abiertos, en main, con incidencia obligatoria.** Un
fichero con una fila por defecto vivo y su número de incidencia. Una prueba que
falla si una fila no tiene incidencia o cita un fichero que ya no existe. Y un
aviso si una fila lleva días sin moverse, usando el reconciliador que ya corre
cada seis horas. *Caza exactamente lo que pasó con los cuatro defectos vivos:
encontrados y evaporados.* No encuentra defectos nuevos; garantiza que uno
encontrado no se pierda.

**4. Que toda ruta citada en un documento de decisión exista.** Ya está medido:
44 documentos, 76 citas, **3 rotas**, una de ellas la de ayer. *Caza la
afirmación cuya prueba no se puede abrir* — que es literalmente lo que tu propia
regla prohíbe. Unas 40 líneas; el prototipo ya está escrito y corre.

**Lo que ninguna de las cuatro arregla, y hay que decirlo:** ninguna encuentra un
defecto de una clase completamente nueva fuera de las máquinas de estado. Eso
sigue dependiendo de que alguien mire con mala idea. Lo que sí hacen es
**reducir el terreno** que ese alguien tiene que cubrir: si lo ya conocido lo
cazan pruebas automáticas, el revisor caro se gasta solo en lo genuinamente
nuevo, en vez de volver a mirar lo mismo cinco rondas seguidas.

---

## 6. Lo siguiente

### El orden que propongo

1. **Congelar de verdad.** El ciclo sigue vivo (#211 pasó de "implementando" a
   "reparando" mientras se escribía esto, y la solicitud #212 ya está abierta).
   Si quieres mirar antes de seguir, hay que pararlo a propósito.
2. **Enganchar los cuatro defectos vivos a algo que los persiga.** Hoy solo
   existen en una rama sin solicitud de fusión. Es lo más barato y lo que más
   directamente ataca tu queja.
3. **Construir las guardas 1, 2 y 4.** Son deterministas, baratas, y quitan de
   tu espalda la clase de fallo que ya te ha mordido.
4. **Taparle el hueco a M1**: un comando que puedas teclear para hablar con el
   motor. Son pocas líneas y convierte un hito que verificaron las máquinas en
   un hito que puedes usar tú.
5. **Después, y no antes, seguir construyendo bloques.**

### Las tres decisiones que hacen falta

**DECISIÓN 1 — ¿Fase B o Fase C? (cuándo: antes de arrancar el próximo bloque)**
La Fase B es "que Sirius investigue de verdad". La Fase C es "que Sirius se
desatasque solo". El plan puso B antes a propósito. La inercia va por C. Nadie
ha escrito la decisión de invertirlo. *Coste de decidir: cero. Coste de no
decidir: la promesa grande se aplaza sin que nadie lo haya elegido.*
→ Si eliges B: **S2 se puede arrancar hoy, sin pagar nada y sin pedir permiso.**
→ Junto con esto, apunta si "saber con qué modelo se hizo cada cosa" va en B1 o
en C2. Hoy no va en ninguno, y es lo que dejaría la puerta del aprendizaje
cerrada para siempre.

**DECISIÓN 2 — ¿Firmas el contrato v1.8? (cuándo: cuando quieras, no corre prisa
hasta que S3 termine)** Es un documento, no cuesta nada, y su dependencia está
cumplida desde hace días. Pero **sin él no empieza C1, y sin C1 no hay C2, ni
C3, ni C4, ni D1.** Es el tapón más grande de todo el plan y es papel.

**DECISIÓN 3 — ¿La memoria del producto sirve también al motor, o el motor tiene
la suya? (cuándo: antes de que nadie construya memoria activa en el motor)** Es
tu intuición sobre "dos memorias", y está confirmada como la única objeción que
sobrevivió entera. No hay ningún documento que la decida. No cuesta código.

**Fuera de las tres, y no urgente:** dónde va a vivir Sirius en definitiva.
Bloquea exactamente un bloque (D2) y nada anterior se para por ello. Si la
contestas pronto, D2 se reduce a la mitad.

---

## Lo que no pude comprobar

Esto es "no lo pude leer", no "no hay nada". Se dice en vez de callarlo.

1. **Por qué falló la pasada de calidad de anoche** (commit fbc5282, 20-ago
   22:57). `get_job_logs(job_id=96609665274) → HTTP 404`. Sé que falló y que
   duró 2 segundos. Nada más. No afirmo que fuera inofensivo.
2. **Cómo va a terminar el trabajo de S3 (#211).** Sigue corriendo mientras se
   escribe esto. Lo que digo es su estado a las 03:24, no su desenlace.
3. **No se ejecutó la batería completa de pruebas aquí.** Las 2.852 se contaron
   recogiéndolas, no corriéndolas. Lo que sí está comprobado es que la pasada de
   GitHub sobre la cabeza de main terminó en verde.
4. **Si el investigador externo necesita además un buscador con cuenta propia**,
   aparte del modelo. El entorno denegó la salida a internet para consultarlo, y
   el repositorio tampoco lo responde: el propio plan dice que el coste está
   "hoy NO VERIFICADO". Si lo exige, "sin abrir ninguna cuenta" podría fallar
   por ahí. Es justo lo que S2 debe destapar.
5. **Si tu ordenador tiene potencia para el camino gratis** (modelo local). El
   repositorio no guarda ningún dato de la máquina real.
6. **Si el interruptor de la segunda revisión (Codex) está encendido hoy.** Es un
   valor de entorno en GitHub, no un fichero. No bloquea nada, pero hace falta
   para dar por cerrado el hito final.
7. **Los dos documentos de aprendizaje que aportaste no están en el repositorio.**
   Todo lo que aquí se dice de lo que proponían viene de cómo lo describe la
   auditoría, no de haberlos leído.
8. **No se leyeron los cuerpos de las incidencias #8 a #15.** Por el título
   parecen tableros permanentes; eso es una lectura del título, no del contenido.
9. **No se comprobó si la solicitud #117 (la enorme, de julio) se puede fusionar
   en la práctica.** Diverge desde el 7 de agosto y va 71 commits por detrás.
   Medirlo habría exigido escribir en el repositorio.
10. **No se midió si el ciclo funcionaría con un modelo pequeño y barato.** Que
    las cuatro guardas propuestas no dependan del modelo es un argumento sobre su
    mecanismo, no una medición. Lo contrario sí está medido: la revisión doble,
    que sí depende del modelo, aprobó el fallo.
11. **De las cuatro guardas propuestas solo se prototipó la cuarta.** Los costes
    de las otras tres son estimaciones por comparación con código que ya existe.
12. **El repositorio local no está en main.** La rama activa es
    `claude/corte-presupuesto-desde-waiting`. Todas las comprobaciones de "lo que
    hay hoy" se hicieron contra `origin/main` explícitamente.

    $ git branch --show-current
    claude/corte-presupuesto-desde-waiting
