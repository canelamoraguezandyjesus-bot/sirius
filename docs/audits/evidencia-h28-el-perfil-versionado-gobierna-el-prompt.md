# Evidencia — H-28: la versión del perfil gobierna el prompt

Fecha: 2026-08-28. Rama `h28-el-perfil-versionado-gobierna-el-prompt`.
Nota de arranque: `arranque-h28-el-perfil-versionado-gobierna-el-prompt.md`.
Decisión de mecanismo: ADR-100.

## Qué se construyó

- `scripts/automation/prompts/manifiesto.json`: carriles `ejecucion` y
  `revision`, cada fila `rol@N` → fichero + sha256 de sus bytes. Filas
  iniciales: las únicas llaves que `TABLA_PERFILES` proyecta hacia estos dos
  workflows (implementer@1, documentalista@1; en revisión también
  investigador@1 → revisor documental).
- `scripts/automation/resolver_prompt.py`: stdlib pura; parsea `Perfil:` con
  `sirius_engine.profile_field` cargado por ruta (patrón H-13, una sola
  verdad); clave exacta, sha256 verificado, fail-closed con `::error::` y
  salida ≠ 0.
- Los dos workflows sustituyen `sed`+`case` por
  `PROMPT_ROL=$(python3 scripts/automation/resolver_prompt.py --carril …)`
  comprobando la salida. El `sed` de la PUERTA del implementador queda: es
  enrutado (qué workflow atiende, ADR-099), no elección de texto.

## Las cuatro preguntas del arranque

**1. ¿`Perfil: implementer@99` se ve FALLAR?** Sí. Las 12 pruebas nuevas de
`test_resolver_prompt.py` se escribieron primero y se vieron en rojo (5
failed + 7 errors sin el módulo; la de cableado, roja contra los workflows
REALES aún con `sed`+`case`). Tras el arreglo, 12 en verde, y la mutación M1
(reinsertar el defecto: la versión se tira) tumba exactamente
`test_una_version_desconocida_de_un_rol_conocido_para_en_rojo`.

**2. ¿El manifiesto no puede pudrirse?**
`test_cada_fila_del_manifiesto_apunta_a_un_fichero_real_con_su_sha256`
recalcula el sha256 de cada fila contra los bytes reales; la mutación M4
(una fila con sha ajeno) lo tumba. Además
`test_las_llaves_despachables_estan_en_el_manifiesto` importa la
`TABLA_PERFILES` real: si un perfil sube de versión sin fila nueva, el rojo
sale AQUÍ, no en producción.

**3. ¿Los workflows llaman al resolver DE VERDAD?**
`test_los_dos_workflows_invocan_al_resolver_y_el_case_viejo_no_existe`
cuenta la invocación exacta en líneas de CÓDIGO (receta de la familia vacua:
los comentarios no cuentan) y prohíbe `PROMPT_ROL=scripts/automation/prompts/`.
La mutación M3 (volver a la ruta a fuego en la línea de código) lo tumba.

**4. ¿Editar un prompt sin registrar versión pone el sistema en ROJO?**
`test_un_prompt_editado_sin_registrar_version_nueva_para_en_rojo` (manifiesto
y prompt en tmp, texto retocado → `ResolucionImposible` nombrando el remedio);
la mutación M2 (saltarse la verificación sha256) lo tumba. En el CLI:
`test_el_cli_para_en_rojo_con_version_desconocida` exige salida ≠ 0 y
`::error::`, que es lo que el workflow consume.

## Mutaciones, todas vistas caer y revertidas

| Mutación | Resultado |
| --- | --- |
| M1: la versión se tira (el defecto original, reinsertado) | CAE |
| M2: sin verificación sha256 | CAE |
| M3: el workflow vuelve a la ruta a fuego (línea de código, no comentario) | CAE |
| M4: una fila del manifiesto con sha ajeno | CAE |

## Guardianes existentes traídos delante (criterio (b) del arranque)

- `test_sirius_runner_python_compat.py`: el derivador exigió
  `resolver_prompt.py` en `SCRIPTS_RUN_ON_THE_RUNNER` (corre con el `python3`
  a secas del runner); `profile_field.py` entra como segundo módulo
  compartido compilado con la versión del runner (mismo razonamiento que
  `round_history.py` desde H-13).
- `test_sirius_review_workflow.py`: dos guardianes medían el mecanismo viejo
  (rutas alcanzables en el `run:`, `::error::` en el `case`); actualizados a
  la ley nueva — la alcanzabilidad la garantizan ahora las pruebas del
  manifiesto, y el `::error::` vive en el resolver, al workflow le toca no
  tragarse el fallo.

## Rondas

Ronda única de defectos propios: el cargador por ruta reventaba con
`@dataclass(slots=True)` (faltaba registrar el módulo en `sys.modules` antes
de `exec_module`) — arreglado y explicado en el propio código. El resto de
rojos intermedios eran los guardianes esperados pidiendo su actualización.
Sin familia repetida: no aplica la regla de parar.

## Estado final

`tests/automation`: en verde (incluido el registro con H-30 cerrado por
af8573b). ruff, format, mypy y suite completa: en el resumen de la PR.
