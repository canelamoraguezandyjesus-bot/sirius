# La mina v2: informe de aprendizaje sobre la ola de criticidad (M18 → M21b)

Muestra: las ocho incidencias de la ola de criticidad, del 2026-09-02 al
2026-09-03 (#507, #508, #510, #512, #514, #516, #518, #520) y sus PR
(#509, #511, #513, #515, #517, #519, #521). Siete fusiones en `main`, de
`9ad873a` a `dc731d4`.

## Nota de método (antes de los resultados)

La nota de arranque se escribió el 2026-09-03 a las 18:50 UTC, antes de
mirar ningún dato, y se reproduce literalmente:

> ### Cuatro preguntas y su predicción
>
> 1. **Rondas y goteo.** ¿Cuántas rondas de revisión por encargo, y qué
>    fracción de los hallazgos de rondas N>1 es goteo (fichero y líneas
>    citadas sin cambio desde el head de la ronda 1)? Predicción: goteo
>    ≥ 30 % en los hallazgos de CLAUDE y < 10 % en los de CODEX, como en la
>    mina de agosto (30,6 % frente a 2,2 %).
> 2. **Familias.** ¿Qué familia de defecto se repite en más encargos
>    distintos? Predicción: «estado de la interfaz frente a transiciones
>    asíncronas» (M21b, cuatro rondas) y «adaptador calcado sin sus guardas»
>    (M21a: ruta relativa, sin `think: false`), y en tercer lugar «suelo de
>    prueba que no puede fallar» (M20).
> 3. **Muertes del corrector.** ¿Cuánto costó cada ejecución del corrector
>    que terminó sin commit, y qué condición las predice? Predicción: las
>    muertes ocurren solo en rondas con dos o más hallazgos que exigen
>    pruebas de interfaz (Qt); cero muertes en rondas sin interfaz.
> 4. **Guardianes mecánicos.** ¿Qué comprobación simple (grep o prueba
>    automática) habría cazado más defectos reales de esta ola con menos
>    falsos positivos? Predicción: (a) «constante `_MINIMO_*` a 0 o aserción
>    `>= 0`», (b) «adaptador Ollama sin `think: false` o con ruta relativa a
>    `base_url`», (c) «orden que dice 'calcado de X' sin enumerar las guardas
>    de X».
>
> ### Criterio de parada (escrito antes de decidir)
>
> - Toda cifra del informe cita el comentario, commit o run concreto del que
>   sale; una cifra sin cita se descarta, no se estima.
> - Toda afirmación de goteo o de muerte del corrector la verifican dos
>   agentes independientes con instrucción de refutarla; si uno la refuta con
>   evidencia, se elimina del cómputo y se registra como refutada.
> - Si los datos brutos no cubren un encargo (comentarios truncados, runs
>   fuera de la ventana), el informe declara el hueco; no se rellena.
> - Las propuestas se ordenan por (defectos reales cazados − falsos positivos
>   estimados) sobre ESTA muestra; ninguna se implementa en la mina.
> - Si la extracción de dos agentes sobre la misma incidencia difiere en el
>   número de rondas o de hallazgos, se para y se resuelve a mano antes de
>   agregar.

### Cómo se ejecutó, y qué parte quedó sin hacer

Un flujo de agentes: uno por incidencia leyendo sus comentarios y la PR
(ocho, completos), dos refutadores por incidencia sobre los goteos y las
muertes (dieciséis, completos), un agrupador de familias y su crítico
(completos). Los agentes de guardianes, jueces, coste e informe **no
llegaron a ejecutarse**: el flujo se cortó tres veces por el límite de
sesión del plan del propietario (19:12, 20:53 y 06:10 UTC). Esas cuatro
secciones las escribe el propietario a mano sobre los datos verificados, y
así se marca en cada una. La medición de los guardianes se hizo con `grep`
sobre `origin/main` en `dc731d4` (§6).

### Predicción frente a lo medido

| # | Predicción | Medido | ¿Acertada? |
|---|---|---|---|
| 1 | goteo ≥ 30 % en CLAUDE, < 10 % en CODEX | 9 candidatos de 22 hallazgos en rondas N>1; tras refutar quedan 5: cuatro de CLAUDE, uno de CODEX | Parcial: la dirección sí (CLAUDE 4 de 5), el umbral no se puede afirmar con 5 casos |
| 2 | la familia más extendida sería «estado de la interfaz frente a transiciones» | Esa familia tiene 8 hallazgos pero en **un solo encargo**. La más extendida es «prueba que no puede fallar»: 7 hallazgos en **4 encargos** | **Fallada** |
| 3 | muertes solo en rondas con 2+ hallazgos de interfaz | 3 muertes: #518 r1 (3 hallazgos, **sin** interfaz Qt) y #520 r2 y r3 (4 y 2 hallazgos, con interfaz) | **Fallada**: #518 la refuta |
| 4 | (a), (b) y (c) cazarían más con menos falsos | Medidas en §6: (b) neto 2, (a) neto 1, (c) neto 1 | Parcial: útiles, pero el orden es otro |

Dos de las cuatro predicciones estaban equivocadas. Es el resultado que
justifica escribir las predicciones antes.

## 1. Distribución de hallazgos

35 hallazgos en 22 rondas de revisión sobre 8 incidencias.

| fuente | total | severidades |
|---|---|---|
| CLAUDE | 17 | alta 3, media 3, baja 9, menor 1, P2 1 |
| CODEX | 18 | P1 3, P2 13, P3 2 |

Por tipo de fichero citado: `src/` 18, `tests/` 9, `docs/` 7, otro 1.

Distribución muy desigual entre encargos: #520 (M21b) concentra 15 de los
35 hallazgos y 5 de las 22 rondas; #512 (M19a) pasó a la primera sin ningún
hallazgo; #507 (M18) murió antes de tener PR.

## 2. Rondas por incidencia

| inc | clave | rondas | hallazgos | corrector: arregló / murió / adoptó | corrigió el propietario | carreras de Quality | min. implementación | min. totales |
|---|---|---|---|---|---|---|---|---|
| #507 | M18 | 0 | 0 | 0 / 0 / 0 | — | 0 | n/a | n/a |
| #508 | M18a | 6 | 10 | 4 / 0 / 1 | 1 ronda | 1 | 80,3 | 223,9 |
| #510 | M18b | 2 | 2 | 1 / 0 / 0 | — | 0 | 24,1 | 62,8 |
| #512 | M19a | 1 | 0 | 0 / 0 / 0 | — | 0 | 30,6 | 46,6 |
| #514 | M19b | 4 | 4 | 2 / 0 / 1 | 1 ronda | 1 | 28,3 | 130,7 |
| #516 | M20 | 2 | 1 | 1 / 0 / 0 | — | 0 | 34,8 | 85,3 |
| #518 | M21a | 2 | 3 | 0 / 1 / 0 | 1 ronda | 0 | 15,7 | 116,2 |
| #520 | M21b | 5 | 15 | 1 / 2 / 1 | 3 rondas | 2 | 28,7 | 226,0 |

«Adoptó» = el corrector encontró en la rama el arreglo ya empujado por el
propietario, lo verificó y no empujó nada (#508 r3, #514 r3, #520 r4).

El propietario intervino con una corrección propia en 6 de las 22 rondas y
publicó 11 observaciones antes del veredicto; en 3 de ellas el revisor
independiente llegó al mismo hallazgo (#514 r3, #516 r1 y una de las tres
de #518).

Cuatro carreras de Quality: un verde llegó mientras la incidencia estaba en
`repairing` o `reviewing` y no se consumió, y hubo que relanzar el run
(#508 `a5badd9`, #514 run 33707833916, #520 runs 33783164462 y 33787682688).

## 3. Goteo por revisor

Definición: hallazgo de una ronda N>1 cuyo fichero y líneas citadas no
cambiaron entre el head de la ronda 1 y el head de esa ronda.

9 candidatos, cada uno pasado por dos refutadores independientes con
instrucción de refutar. **4 refutados**: #514 r2 CODEX-001 (el fichero sí
cambió), y en #520 CLAUDE-REV-R2-002 (ADR), CLAUDE-REV-R4-001 (cita código
introducido en la ronda 3, no preexistente) y el CODEX-002 de la ronda 4.
**5 sostenidos**: #508 CLAUDE-M18A-003 y CLAUDE-REVISOR-001; #514
CLAUDE-REVISOR-001 (r2) y CODEX-001 (r3); #520 CLAUDE-REV-R2-001.

Reparto por revisor de los sostenidos: **CLAUDE 4, CODEX 1**. La dirección
coincide con la mina de agosto (CLAUDE gotea más), pero con 5 casos no se
puede afirmar un porcentaje; declarado como hueco.

Discrepancia resuelta a mano, como exige el criterio de parada: el crítico
de familias contaba 5 sostenidos y las tablas del propietario 4, por contar
distinto el caso de #514 r3. Recuento final: **5**.

## 4. Familias de defecto

Agrupamiento hecho por un agente y corregido por un crítico adversario.
Cinco familias y dos hallazgos sin familia.

| familia | hallazgos | encargos | raíz probable |
|---|---|---|---|
| **Prueba que no puede fallar** | 7 | 4 (#508, #516, #518, #520) | La prueba se escribe para que pase y no se ve fallar por mutación, pese a que ADR-001 lo exige. Ni el implementador, ni el corrector, ni el propietario en sus arreglos de raíz ejecutaron la mutación que la habría puesto en rojo |
| **Descripción del diseño desincronizada del código** | 7 | 3 (#508, #510, #514) | Quien cambia el código no relee la prosa que lo describe, y esa prosa está repetida en varios sitios (ADR-128 lo dice en tres). Los «límites de corrección» del veredicto acotan al corrector a las líneas señaladas |
| **Calco de un patrón hermano sin sus guardas** | 7 | 3 (#510, #518, #520) | La orden nombra el original a calcar pero no enumera sus guardas; el implementador copia la forma y hereda incluso los defectos del original |
| **Estado de la propuesta frente a transiciones asíncronas** | 8 | 1 (#520) | Un worker calcado añade estado que el hermano no tiene (caché, rechazo, propuesta pendiente, época) a un widget cuya máquina de estados nunca se enumeró; cada ronda parcheó la transición nombrada |
| **Cifra escrita a mano que no cuadra** | 4 | 2 (#508, #520) | Un número (cita `fichero:línea` o recuento de pruebas) que ninguna herramienta re-deriva, ni al escribirlo ni tras cada edición |

Sin familia: el G12 con predicado booleano de #514 r1 (raíz única: un
contrato de tres niveles representado como booleano, elegido así en la
propia orden) y el suelo `xfail` del banco de latencia de #508 r1.

**Respuesta a la pregunta 2, con su salvedad declarada:** la familia más
extendida entre encargos distintos es «prueba que no puede fallar» (4
encargos). Si se unieran «prosa desincronizada» y «cifras a mano» —comparten
el síntoma, no la raíz—, esa unión también daría 4 y empataría. El crítico
recomendó separarlas porque la de cifras tiene guardián mecánico y la de
prosa no; el informe mantiene la separación y lo declara.

## 5. Muertes del corrector

Tres ejecuciones del corrector terminaron sin publicar corrección, las tres
sostenidas por ambos refutadores:

| incidencia | ronda | run | duración | quién corrigió después |
|---|---|---|---|---|
| #518 | 1 | 33759989103 | 31,0 min (hasta «The action has timed out») | propietario |
| #520 | 2 | 33776378064 | 31,9 min | propietario |
| #520 | 3 | 33782613151 | 23,7 min | propietario |

**La predicción 3 falla**: #518 r1 no tenía ni un hallazgo de interfaz (los
tres eran del adaptador de Ollama, del caso de uso y de una prueba
unitaria). La condición que sí distingue en esta muestra: las tres muertes
ocurren en rondas cuyo arreglo exige **reescribir un contrato completo y sus
pruebas** (el contrato HTTP de Ollama en #518; la máquina de estados de la
propuesta en #520 r2 y r3), no en rondas de arreglos locales. Las 12 rondas
en que el corrector sí terminó duraron entre 9,1 y 22,2 minutos.

Ninguna muerte dejó diagnóstico: la acción oculta la salida («full output
hidden for security»), así que turnos, tokens y coste no son medibles; los
dos runs de #520 terminan con `success` a nivel de workflow pese al
`FAILED_SAFELY`. La cuarta ejecución sobre #520 (ronda 4, run 33786663722)
hizo lo correcto: encontró el arreglo del propietario ya en la rama, lo
verificó con la suite completa y no empujó nada.

## 6. Guardianes mecánicos

Medidos por el propietario con `grep` sobre `origin/main` en `dc731d4`; los
agentes de esta fase no llegaron a ejecutarse. Detalle y comandos literales
en `guardianes_medicion_propietario.md`.

| guardián | comprobación | cazados | falsos positivos | neto |
|---|---|---|---|---|
| **(b) Adaptador de Ollama sin contrato validado** | por cada `src/sirius/adapters/ollama_*.py`: que exista `"think"`, que la URL sea absoluta a `_OLLAMA_LOCAL_BASE_URL` y que pase `follow_redirects=False` | 2 (#518 CODEX-001 P1 y CLAUDE-M21A-001) | 0 | **2** |
| **(a) Suelo de prueba que no puede fallar** | `_MINIMO_*: Final[int] = 0` o `assert … >= 0` en `tests/acceptance` | 1 (#516 CODEX-001) | 0 | **1** |
| **(c) Orden que calca sin enumerar guardas** | en el cuerpo del encargo, «calcad…» presente y «guarda» ausente | 2 (#518, #520 r1) | 1 (#510, que calcó sin ese defecto) | **1** |

El guardián (b) sigue disparando hoy: `ollama_category_classifier.py` no
tiene `think`, ni URL absoluta, ni `follow_redirects=False`. Es la deuda ya
registrada en ADR-130 y en la bitácora, y este informe la confirma como
único positivo vivo en `main`.

Nota de medición para (b): el `grep` ingenuo de la URL absoluta da cero en
los dos adaptadores correctos porque la llamada está partida en dos líneas;
la comprobación debe buscar `_OLLAMA_LOCAL_BASE_URL}/api` en cualquier
línea del fichero, no en la de `post(`.

## 7. Huecos declarados

1. **Cuatro secciones sin agente**: guardianes, jueces, coste e informe se
   escribieron a mano tras tres cortes por límite de sesión. Los jueces
   adversarios de los guardianes no llegaron a correr, así que los netos de
   §6 no tienen contraste independiente.
2. **Ningún comentario `CORRECCION_APLICADA` trae el id de su run**: los ids
   del corrector se atribuyeron por correlación temporal con la lista de
   `repair-sirius-work.yml` (único run no omitido en cada ventana).
3. **La salida del implementador y del corrector está oculta**: de una
   muerte solo se conoce la duración del run.
4. **#507 no tiene PR ni fusión**: sus tiempos se miden de creación a
   `failed-safely` (36,6 min) y a cierre (281 min).
5. **Defecto de método propio**: el guion pasaba a los refutadores la
   extracción recortada a 12 000 caracteres; la de #520 llegó truncada a
   mitad de la ronda 3. Los dos refutadores lo declararon y recontaron por
   su cuenta (5 pasadas, 15 hallazgos, 6+4+2+3), y sus recuentos cuadran con
   la extracción completa, pero el dato se salvó por mérito suyo.
6. **Coste en tokens y dinero**: no medido para ninguna ejecución del motor.

## 8. Propuestas, ordenadas por neto

Ninguna se implementa aquí. Todas requieren la aprobación del propietario.

1. **Guardián del contrato de Ollama** (neto 2). Una prueba automática en
   `tests/automation` que, por cada `src/sirius/adapters/ollama_*.py`, exija
   `think`, URL absoluta a localhost y `follow_redirects=False`. Cazaría hoy
   el clasificador de categoría. No toca `.github/**`.
2. **Guardián del suelo muerto** (neto 1). Una prueba que falle si en
   `tests/acceptance` aparece una constante `_MINIMO_*` a 0 o una aserción
   `>= 0` sin una segunda aserción viva en la misma prueba. No toca
   `.github/**`.
3. **Regla de redacción de órdenes** (neto 1, proceso). Cuando una orden
   diga «calcado de X», debe enumerar las guardas de X y lo que hay que
   adaptar. Es una regla para quien escribe los encargos —hoy el
   propietario—, no código.
4. **Mutación obligatoria declarada por hallazgo** (familia mayor, 7
   hallazgos en 4 encargos; sin guardián mecánico posible). El veredicto ya
   pide «demostrar la corrección con una prueba»; la propuesta es exigir que
   el corrector publique la mutación concreta que vio fallar, con su salida.
   Afecta al texto del revisor y del corrector, dentro de `.github/**`:
   **requiere la mano del propietario** (ADR-002).
5. **Re-derivar las cifras escritas a mano** (neto 4 en su familia). Ampliar
   el guardián de citas de fichero (`tests/automation/test_citas_de_los_adr.py`)
   para que compruebe que `fichero:línea` apunta a lo que el texto dice, y
   dejar de escribir recuentos de pruebas en los ADR. No toca `.github/**`.
6. **Registrar el id del run en cada `CORRECCION_APLICADA`** y escribir un
   diagnóstico al morir. Elimina el hueco 2 y el 3 de este informe. Está en
   `.github/**`: **requiere la mano del propietario**.
7. **Cerrar la carrera de Quality** (4 casos en esta ola). Que el verde se
   consuma también si llega en `repairing`/`reviewing`, o que `reconcile`
   corra más a menudo. Está en `.github/**`: **requiere la mano del
   propietario**.

## Materia prima

`scratchpad/mina/`: `nota_de_arranque.md`, `resultados/extracciones.json`
(8), `resultados/refutaciones.json` (8 refutadores, 28 refutaciones),
`resultados/familias.json` y `familias_corregidas.json`,
`tablas_base_propietario.md`, `guardianes_medicion_propietario.md`,
`datos_para_el_informe.txt`, `diario.jsonl` y `racha_siete_dias.jsonl` de la
rama `estado-del-motor`, y `mina_2026-08.md` como plantilla de estructura.
Incidencias #507, #508, #510, #512, #514, #516, #518, #520 y PR #509, #511,
#513, #515, #517, #519, #521 del repositorio.
