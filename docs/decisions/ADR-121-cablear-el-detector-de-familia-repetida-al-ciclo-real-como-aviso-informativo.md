# ADR-121 — Cablear el detector de familia repetida al ciclo real como aviso informativo

- Estado: APROBADO
- Fecha: 2026-08-31
- Aprobación: fusión de la PR por el propietario
- Contexto: incidencia #495, propuesta 1 del informe de la mina
  (`docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-08.md` §7, aprobado por
  el propietario al fusionar la PR #494)
- Relacionadas: ADR-078 (construyó y midió el detector, sin llamante a
  propósito porque cablearlo tocaba `.github/**`, prohibido por ADR-002),
  ADR-002 (la automatización no edita `.github/**`), incidencia #267 (una
  comprobación gana autoridad cuando demuestra en el árbol real que caza más
  defectos reales que falsos positivos), incidencia #251 (diagnosticar la
  causa raíz, fuera de este bloque), ADR-118 (precedente de "detente y deja
  la parte de `.github/**` a la sesión interactiva")

## Contexto y problema

`src/sirius_engine/round_family_detector.py` (ADR-078) existe, está medido (4
aciertos, 0 falsos positivos sobre 14 incidencias candidatas del propio
repositorio) y tiene su propio CLI (`sirius-familia-repetida`) desde el
23-08-2026. Pero nadie lo invoca: ADR-078 dejó la construcción y la medición
completas y paró ahí a propósito, porque conectar el detector al ciclo de
revisión-corrección real -para que su veredicto llegue a publicarse en la
incidencia- exige tocar el punto donde ese ciclo publica sus eventos, y ese
punto vive en `.github/workflows/**`, que ADR-002 prohíbe editar a la
automatización.

El informe de la mina (§7, propuesta 1) señala esta pieza construida y sin
llamante como la primera oportunidad de aprendizaje operativo: una
comprobación que ya demostró su criterio sobre datos reales, pagando coste de
mantenimiento (su propia suite corre en cada `pytest`) sin producir ningún
valor porque nunca se ejecuta sobre una incidencia viva.

## Criterio de parada (escrito ANTES de decidir)

Publicado en la incidencia #495 antes de tocar ningún archivo:

- (a) Si la única forma de cablear el detector pasa por editar un fichero de
  `.github/**`, parar con `BLOCKED_BY_DECISION`, indicando exactamente qué
  fichero y qué líneas harían falta, y qué alternativa existe fuera de
  `.github/**`.
- (b) El detector no puede cambiar ninguna transición de estado ni bloquear
  nada en esta primera versión: solo informa. Si la única forma de wiring
  encontrada obligara a bloquear o desviar una decisión, se para y se
  registra como una decisión de producto pendiente, no se implementa.
- (c) Si la interfaz de `round_family_detector.py` resulta incompatible con
  el punto de wiring elegido sin poder resolverse por fuera (p. ej. sin poder
  cargarlo sin modificarlo), se documenta el cambio exacto y el motivo; no se
  cambia el criterio del detector en sí (los 4 aciertos y 0 falsos de
  ADR-078 no se tocan).
- (d) Tiene que existir una prueba que se vea FALLAR antes del cambio,
  demostrando que hoy el detector no se invoca desde ningún punto del ciclo.

Ninguno de los cuatro se disparó: el wiring completo vive en
`scripts/automation/` y `src/sirius_engine/`, sin tocar `.github/**`; el
detector solo añade una sección informativa al comentario que
`sirius_apply_verdict.sh` ya publica en `CHANGES_REQUESTED`, sin tocar la
transición ni las etiquetas; la interfaz del detector sí resultó
incompatible con el intérprete que lo invoca (ver "Consecuencias") y se
resolvió sin modificar `round_family_detector.py`; y
`test_reviewer_changes_requested_publishes_family_repeated_notice` se
comprobó en rojo contra el árbol previo al cambio (ver "Comprobación que la
sostiene").

## Opciones consideradas

1. **Wiring en `.github/workflows/review-sirius-work.yml`**, invocando
   `sirius-familia-repetida` como paso del workflow tras la revisión.
   Descartada de raíz por el criterio de parada (a): es exactamente la
   prohibición de ADR-002, y ADR-078 ya la dejó fuera a propósito.
2. **Wiring en `scripts/automation/sirius_convergence.py`**, añadiendo un
   subcomando `family-check` que reutiliza la infraestructura de carga de
   módulos por ruta que el script ya tiene para `round_history.py`.
3. **Wiring en `scripts/automation/sirius_apply_verdict.sh`**, invocando
   directamente `sirius-familia-repetida` (el CLI ya instalado del paquete)
   sobre el historial ya leído.
4. **Combinación de 2 y 3**: `sirius_convergence.py` expone la comprobación
   (subcomando nuevo, sin tocar su interfaz pública existente) y
   `sirius_apply_verdict.sh` -que ya construye el registro de la ronda
   actual en el mismo punto del flujo de `CHANGES_REQUESTED`- la invoca y
   decide qué publicar. Es la opción elegida.

La opción 3 sola (invocar `sirius-familia-repetida` directamente) se probó y
se descartó al leer el entorno real: `review-sirius-work.yml` -el workflow
que emite `CHANGES_REQUESTED` y por tanto el único punto donde esta
comprobación tiene sentido- **no ejecuta `uv sync`** ni instala el proyecto
(es una pasada de solo lectura, con permiso `contents: read`; su única
preparación es `actions/checkout`). `sirius_apply_verdict.sh` se ejecuta ahí
con el `python3` desnudo del sistema, exactamente la misma restricción que ya
documenta la cabecera de `sirius_convergence.py` para `round_history.py`
(incidencia #275). El CLI instalado (`sirius-familia-repetida`, un
entry-point del paquete) no existe en ese intérprete: solo existe tras `uv
sync`, que ese workflow nunca corre. Invocarlo habría fallado en producción
con `command not found` la primera vez que se disparara, un fallo que ningún
test de este repositorio -que sí corren con el proyecto instalado- podría
haber detectado sin, precisamente, reproducir esa restricción de entorno
(ver `test_cli_family_check_runs_under_the_bare_system_python_without_the_project_installed`).

## Decisión

Se añade un subcomando `family-check` a `scripts/automation/sirius_convergence.py`,
construido con el mismo mecanismo que ya usa ese script para
`round_history.py`: carga el módulo por ruta de archivo en vez de por
`import sirius_engine...`, para funcionar bajo el `python3` del sistema sin
el proyecto instalado.

`sirius_apply_verdict.sh`, en la rama `CHANGES_REQUESTED` -el único punto del
ciclo donde ya se lee el historial de rondas y ya se construye el registro
de la ronda actual, para `sirius_convergence.py record`-, reutiliza ese mismo
historial (una sola lectura de la API, sin llamadas adicionales): le añade el
registro de la ronda que está a punto de publicar y llama a
`sirius_convergence.py family-check` sobre el resultado. Si el detector señala
familia repetida, añade una sección `## AVISO_FAMILIA_REPETIDA` al mismo
comentario que ya iba a publicar -no crea un comentario aparte-, con el
detalle exacto de qué archivo y qué rondas. Un fallo en la comprobación
(python3 ausente, historial corrupto) se ignora en silencio: nunca se
convierte en `stop_safely`, porque este aviso informa y no decide (requisito
(b) de la incidencia #495 y de la incidencia #267: gana autoridad cuando
demuestre en producción que acierta más que falla, y hasta entonces no puede
bloquear nada).

## Comprobación que la sostiene

`test_reviewer_changes_requested_publishes_family_repeated_notice`
(`tests/automation/test_sirius_apply_verdict.py`) se ejecutó contra el árbol
sin el cambio (`git stash` de `sirius_apply_verdict.sh` y
`sirius_convergence.py`) y falló exactamente como se esperaba:

```
assert "AVISO_FAMILIA_REPETIDA" in comments
AssertionError: assert 'AVISO_FAMILIA_REPETIDA' in 'QUALITY_SUCCESS\n...'
```

confirmando que, antes de este bloque, tres rondas consecutivas sobre el
mismo archivo no producían ningún aviso. Con el cambio aplicado, la misma
prueba pasa, junto con
`test_reviewer_changes_requested_without_three_consecutive_rounds_has_no_family_notice`
(el caso normal de dos rondas no dispara nada, igual que mide ADR-078) y las
pruebas nuevas de `tests/automation/test_sirius_convergence.py`:
`test_cli_family_check_writes_the_evidence_when_three_consecutive_rounds_share_a_file`,
`test_cli_family_check_two_rounds_is_the_normal_case_not_a_family`,
`test_cli_family_check_unreadable_history_reports_false_and_never_fails` y
`test_cli_family_check_runs_under_the_bare_system_python_without_the_project_installed`
-esta última reproduce exactamente la restricción de entorno de
`review-sirius-work.yml`: un `python3` distinto del de este proyecto
(`/usr/bin/python3`), con el `PATH` como único entorno heredado, sin
`PYTHONPATH` ni `.venv`-.

Toda la suite existente de ambos scripts sigue en verde sin modificarse:

```
uv run pytest tests/automation/test_sirius_apply_verdict.py tests/automation/test_sirius_convergence.py -q
93 passed
```

## Consecuencias

- `round_family_detector.py` no se modifica: sigue siendo un módulo de
  paquete normal (`from sirius_engine.round_history import
  _normalize_location`), pensado para instalarse. Su interfaz SÍ resultó
  incompatible con la carga por ruta que `sirius_convergence.py` necesita
  (a diferencia de `round_history.py`, que no depende de nada del paquete):
  el import de paquete falla bajo un intérprete sin `sirius_engine`
  instalado. Se resuelve enteramente en el lado del cargador
  (`sirius_convergence.py`), registrando en `sys.modules` un paquete
  `sirius_engine` mínimo con `round_history` ya resuelto antes de ejecutar
  el archivo, en vez de tocar la fuente del detector. Es exactamente lo que
  el requisito (c) de la nota de arranque preveía: se deja escrito qué se
  cambió (nada en el detector; sí un cargador nuevo en su llamador) y por
  qué.
- El detector sigue sin autoridad: no bloquea ni cambia ninguna transición.
  Su próxima etapa -si los datos de producción lo sostienen (incidencia
  #267)- es una decisión de producto separada, no parte de este bloque.
- El aviso puede no aparecer nunca si ninguna incidencia real vuelve a tocar
  el mismo archivo en 3 rondas consecutivas; eso es exactamente lo que se
  quiere medir, no un fallo de este bloque.
- Sigue habiendo, formalmente, una ruta de wiring en `.github/**`
  (disparar el CLI instalado desde un paso de workflow con el proyecto ya
  sincronizado) que este bloque no toma, por el criterio de parada (a) y
  porque no hacía falta: el punto elegido, fuera de `.github/**`, ya tenía
  acceso al historial completo y al mismo comentario de salida.

## Alternativas descartadas y por qué

- **Invocar `sirius-familia-repetida` (el CLI instalado) directamente desde
  `sirius_apply_verdict.sh`**: descartada porque `review-sirius-work.yml` no
  ejecuta `uv sync`; el entry-point no existe en el `python3` que ejecuta ese
  script en producción. Ver "Opciones consideradas".
- **Publicar el aviso como un comentario separado**: descartada por
  simplicidad y por evitar una segunda escritura no idempotente en la misma
  invocación; el comentario de `CHANGES_REQUESTED` ya es el evento natural
  donde vive toda la información de la ronda, y el marcador que lo gobierna
  ya resuelve la idempotencia.
- **Dar autoridad al detector desde ya (bloquear o escalar automáticamente
  ante familia repetida)**: fuera de alcance por el requisito (b) de la
  incidencia #495 y por el criterio de la incidencia #267: la autoridad se
  gana midiendo en producción, no se concede por adelantado.
- **Modificar `round_family_detector.py` para que cargue `round_history` de
  forma tolerante a no estar instalado**: descartada por el objetivo mismo
  de la incidencia #495 ("no cambies el detector en sí salvo que su interfaz
  lo impida"); el problema se resuelve enteramente del lado del cargador,
  sin tocar el módulo medido por ADR-078.
</content>
