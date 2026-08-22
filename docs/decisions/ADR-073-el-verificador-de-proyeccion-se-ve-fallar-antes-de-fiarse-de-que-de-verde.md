# ADR-073 — El verificador de proyección se ve fallar antes de fiarse de que dé verde

- Estado: APROBADO
- Fecha: 2026-08-22
- Aprobación: fusión de la PR por el propietario

## Contexto y problema

El contrato §11.2 fija la condición de conmutación de canonicidad de la vía
GitHub en siete días continuos en verde. Para que ese dato exista hace falta
un verificador que compare, ejecución tras ejecución, lo que el motor tiene
con lo que su incidencia proyecta -y que registre cada comparación-. El
riesgo real (incidencia #250, hallazgo H-C) no es que el verificador falle:
es que **dé verde sin comprobar nada** y autorice la conmutación con eso. La
nota de arranque de la incidencia #265 ya fija el criterio de parada de este
bloque; este ADR registra la decisión de diseño resultante, no lo repite.

## Criterio de parada (escrito ANTES de decidir)

Los tres de la nota de arranque de la incidencia #265:

1. Si un eje resulta ser `f(x) == f(x)` -comparar algo consigo mismo- se
   retira, no se documenta como cobertura.
2. Si hace falta **inventar** un número -una ventana de tolerancia, un
   margen- se para: se deriva de los `timeout-minutes` reales, como
   `RECON-STUCK-006`, o no se pone.
3. Si hace falta cambiar la proyección, el espejo o el dominio para que el
   verificador funcione, se para.

## Opciones consideradas

- **A. Cuatro ventanas no comparables como un único "apagón" que silencia los
  dos ejes diarios (fase y estado) a la vez.** Más simple de implementar,
  pero examinar el dominio (`activate()`, `pause()`) muestra que las
  ventanas 1 y 2 solo impiden expresar el **estado** en el vocabulario de
  etiquetas -`activate()` y `pause()` no tocan `fase`-, así que silenciar
  también `fase` durante esas dos ventanas escondería divergencias reales de
  fase detrás de una ventana que no las protege. Descartada: habría hecho el
  eje `fase` menos sensible de lo que el propio dominio permite.
- **B. Ventanas no comparables por eje, derivadas de la semántica real de
  cada transición del dominio (`work_item.py`) en vez de una lista plana.**
  La elegida: ventanas 1 y 2 solo aplican a `estado`; la 3 (fusión sin pasar
  por `ready-for-merge`) y la 4 (residencia de etiqueta de máquina) aplican a
  los dos, porque estructuralmente pueden divergir en cualquiera de los dos.
- **Ventana de tolerancia (4): número fijo a mano vs. derivado del YAML.**
  Escribir un número fijo fue exactamente el criterio de parada (2). Se
  derivó en su lugar con el mismo criterio de margen que
  `RECON-STUCK-006` -el doble del `timeout-minutes` más largo real de
  `.github/workflows/*.yml`-, leído en tiempo de llamada por
  `ventana_tolerancia_etiqueta_maquina()`, nunca escrito en el código.
- **Ventana 3 (fusión sin `ready-for-merge`): flag explícito del llamador vs.
  condición estructural.** Se descartó pedir al llamador un flag
  `fusion_sin_ready_for_merge: bool` -habría sido un dato inventado que este
  módulo no puede verificar por sí mismo-. La condición
  `espejo.estado is DELIVERED and motor.fase is not ENTREGAR` ya identifica
  el caso sin dato adicional: solo puede darse cuando `sirius:completed` se
  aplicó sin que el motor pasara por `approve_review`, porque `deliver()`
  exige `fase == ENTREGAR` antes de aceptar la entrega.

## Decisión

Un módulo nuevo, `src/sirius_engine/projection_verifier.py`, con tres ejes
declarados (`EJE_FASE`, `EJE_ESTADO`, diarios; `EJE_FIDELIDAD_PROYECCION`, una
vez al despachar) y cuatro ventanas no comparables reconocidas por su
condición estructural o temporal -nunca por una etiqueta inventada-, cada una
produciendo `NO_COMPARABLE` con motivo, nunca `COINCIDE`. La ventana de
residencia de etiqueta de máquina se deriva del YAML real de los workflows
con el mismo criterio que `RECON-STUCK-006`. No conmuta nada, no toca la
proyección, el espejo, el dominio ni el vocabulario de etiquetas: recibe las
dos lecturas ya hechas (`WorkItem`, `MirroredWorkItem`) y compara.

## Comprobación que la sostiene

- `uv run ruff format --check .` → `478 files already formatted`.
- `uv run ruff check .` → `All checks passed!`.
- `uv run mypy src tests` → `Success: no issues found in 455 source files`.
- `uv run pytest -q` → `3386 passed, 8 skipped`.
- `git diff --check` → sin salida (sin restos de conflicto ni espacios en
  blanco al final de línea).
- `tests/engine/test_projection_verifier.py` (23 pruebas): cada eje declarado
  tiene un caso rojo (`test_cada_eje_declarado_tiene_su_caso_rojo`), ningún
  eje es `f(x) == f(x)` (un par que diverge y otro que coincide por eje), las
  cuatro ventanas producen `NO_COMPARABLE` -nunca `COINCIDE`- con su motivo,
  la ventana de tolerancia cambia si cambia el YAML
  (`test_ventana_tolerancia_no_esta_escrita_a_mano`) y coincide con una
  lectura independiente del YAML real del repositorio
  (`test_ventana_tolerancia_atada_al_yaml_real_del_repositorio`), un día con
  ventanas no comparables no cuenta como verde
  (`test_linea_es_verde_solo_si_todos_los_ejes_coinciden`), y la fidelidad de
  la proyección detecta otro `work_id`, objetivo o alcance.

## Consecuencias

- El registro que produce `verificar_dia`/`verificar_despacho` (vía
  `formatear_linea`) es la materia prima para contar los siete días del
  contrato §11.2, pero ese conteo -y la conmutación misma- quedan fuera de
  este bloque, para el acto de conmutación del propietario.
- El eje de fidelidad de la proyección no se repite a diario: queda a cargo
  de quien orqueste el despacho invocar `verificar_despacho` una vez, con el
  `WorkItem` que el motor tenía en ese instante y lo que `leer_cuerpo_declarado`
  devuelva de la incidencia recién publicada.
- La ventana de tolerancia (4) depende de `.github/workflows/*.yml` en tiempo
  de llamada: si algún día ese directorio quedara vacío o ilegible, la
  función lanza `ValueError` en vez de fingir un número -mismo criterio que
  `RECON-STUCK-006`-, así que quien la invoque debe tratar esa excepción como
  una señal real, no un caso de borde a silenciar.

## Alternativas descartadas y por qué

- **Comparar los diez campos del `WorkItem` que el cuerpo no lleva.**
  Explícitamente fuera de alcance (nota de arranque, pregunta 2): el cuerpo
  no declara `peticion_original`, `prioridad`, `clase`, `version`,
  `created_at`, `updated_at`, `evidencia`, `resultado`, `diagnostico` ni
  `paused_from`, y `leer_cuerpo_declarado` (#263) ya documenta esa ausencia
  como deliberada.
- **Repetir la fidelidad de la proyección a diario.** Nada en el repositorio
  edita el cuerpo de una incidencia tras publicarlo; comparar cada día sería
  constante contra constante, el mismo defecto tautológico que el criterio de
  parada (1) prohíbe para los otros dos ejes.
