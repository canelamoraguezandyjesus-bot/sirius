# ADR-227 — Las divergencias que el reflector aparta para una persona quedan escritas junto al diario y la vista de desenlaces las enseña con su edad

- Estado: APROBADO
- Fecha: 2026-10-01
- Aprobación: la fusión de la PR #674 por el motor con aprobación dual (ADR-205).
- Nota de arranque:
  `docs/audits/arranque-2026-10-01-las-divergencias-que-el-reflector-aparta-se-ven-con-su-edad.md`,
  confirmada en `17b2d416` antes del primer commit de arreglo, con las cuatro
  preguntas, las predicciones y el criterio de parada.

## Contexto y problema

El reflector (`src/sirius_engine/reflect.py`) tiene una primera regla que no se
toca: ante una incidencia con etiquetas de estado que se contradicen no mueve
nada y devuelve el motivo (ADR-173 la dejó así a propósito; ADR-181 §3 la
protege como criterio de parada). Lo mismo hace ante un camino hacia atrás o
una parada sin permiso: devuelve una `divergencia` y sigue con el siguiente
encargo. El diseño dice «esto lo mira una persona».

Pero nada se lo ponía delante a ninguna persona. `sirius-reflejar` imprimía la
divergencia en el log del run (`reflect_cli.py`, una línea por pasada) y nada
más: ningún fichero la conservaba, y `DESENLACES.md` —la memoria común que el
motor escribe en `estado-del-motor` tras cada reflejo (ADR-171)— contaba el
encargo como «1 activo» sin decir que estaba apartado ni desde cuándo.
`WI-20260828-122242` (incidencia #392, cerrada con `sirius:failed-safely` y
`sirius:completed` a la vez) lleva así desde el 28-08-2026: se encontró
**auditando**, veintisiete días después (H-216, incidencia #662, entrada 38 de
la bitácora), y hoy lleva treinta y cuatro. La mina de septiembre lo lista como
mejora 4: «hoy 0 sitios lo muestran».

## Criterio de parada (escrito ANTES de decidir)

Copiado de la nota de arranque:

- Si conservar la divergencia exigiera tocar una regla de `reflect.py`, parar:
  ADR-181 §3.
- Si la vista necesitara leer GitHub para calcular la edad, parar: la vista se
  deriva solo de ficheros (ADR-171).
- Cuatro mutaciones tienen que caer: M1 la pasada no escribe el fichero; M2 la
  vista ignora el fichero; M3 una incidencia ilegible borra la entrada; M4 el
  ensayo escribe el fichero.
- Dos rondas de revisión externa con defectos de la misma familia → raíz.

Ninguna de las dos primeras paró: `reflect.py` no se toca y la vista solo lee
un fichero más junto al diario.

**Desviación, a la vista.** La predicción 3 de la nota decía que una entrada
se retira «solo cuando la pasada evaluó ese encargo y no vio divergencia (o el
encargo ya es terminal)». Lo implementado la retira también cuando el encargo
ya no está entre los que se reflejan por otra razón —clase que no se
despacha, sin episodio de despacho—: son encargos sobre los que el reflector
no va a volver, y una entrada suya sería un apartado para siempre. La
revisión independiente de la PR #674 lo señaló; queda dicho aquí.

## Opciones consideradas

1. Dejarlo: la persona a la que el diseño deriva la contradicción no existe, y
   la próxima se encontrará auditando.
2. **Conservar lo que la pasada declara, junto al diario, y enseñarlo en la
   vista con su edad** (la elegida). El reflector ya sabe el encargo, la
   incidencia y el motivo; solo faltaba escribirlo donde alguien lo lee.
3. Publicar un comentario en la incidencia (o abrir una) por cada divergencia.
   Descartada: el paso del reflejo tendría que escribir en GitHub (hoy solo
   lee), haría ruido en cada pasada, y la memoria común ya existe para esto.
4. Inferirlo en la vista desde el diario (un `active` sin suceso desde hace N
   días). Descartada: es adivinar lo que el reflector ya declara con su motivo,
   y la vista no puede ni mirar el reloj (ADR-171, criterio (a)).

## Decisión

1. Módulo nuevo `src/sirius_engine/divergencias.py`: `DivergenciaVista` (lo que
   la pasada declara), `DivergenciaApartada` (lo que se conserva: encargo,
   incidencia, motivo, primera vez, última vez, pasadas), `leer_divergencias`
   y `escribir_divergencias` sobre `divergencias.json` junto al diario, y la
   regla de retención `actualizar`, pura: una divergencia vista se escribe
   (primera vez conservada, última vez y pasadas al día); una entrada anterior
   se retira si la pasada evaluó el encargo sin divergencia o el encargo ya no
   se refleja; una entrada de un encargo del que la pasada no pudo concluir
   nada (`sin_evaluar`: incidencia ilegible, o pasada que murió antes de llegar
   a él) se conserva tal cual. El fichero se escribe entero o no se toca
   (temporal al lado y `os.replace`): una pasada que muera escribiendo no deja
   un JSON a medias que el paso de confirmar del workflow confirmaría. Un
   fichero que no tiene la forma, o que no es JSON, se declara con su ruta, no
   se lee como vacío.
2. `reflect_cli.py` lee el fichero anterior **antes** de tocar el almacén (si
   está roto, lo dice nombrándolo, sigue —el reflejo es lo primero— y lo
   reescribe con lo que observe), recoge las divergencias de la pasada y los
   encargos que no pudo evaluar y, al terminar, escribe el fichero si cambió.
   Si la pasada muere a medias por cualquier excepción, escribe igualmente lo
   observado hasta ahí, conserva las entradas de los encargos a los que no
   llegó y vuelve a lanzar la excepción: el paso de confirmar del workflow
   corre con `if: always()` y confirmaría el diario con un fichero viejo. En
   `--ensayo` dice cuántas hay y no escribe. `reflect.py` no se toca.
3. `memoria.py` añade a `DESENLACES.md` la sección «Divergencias que el
   reflector aparta para una persona»: encargo, incidencia, motivo, primera y
   última vez, pasadas y **días parado** (del último suceso del encargo en el
   diario a la última pasada que lo apartó). Sin fichero, lo dice. La resta de
   fechas vive en `divergencias.py` porque la vista no puede ni nombrar el
   reloj (la guarda `test_el_generador_no_mira_el_reloj_ni_la_red_ni_git` lo
   impidió al primer intento, y bien). Si el fichero no se puede leer, la
   vista lo declara en esa misma sección —con la ruta y el motivo— en vez de
   fallar: la vista se deriva del diario, y un fichero secundario roto no
   puede impedirla.
4. El workflow `reflejar-desenlace.yml` no cambia de comportamiento: su paso
   «Confirmar el diario» hace `git add -A` en la rama de memoria, así que el
   fichero entra con el diario, y «Publicar la vista» ya corre después del
   reflejo. Sus comentarios sí cambian: decían que sin sucesos nuevos en el
   diario la vista no cambia y no se confirma nada, y desde este ADR una
   divergencia que sigue apartada actualiza su última pasada en cada pasada,
   así que el fichero y la vista pueden cambiar sin sucesos nuevos.

## Comprobación que la sostiene

- `tests/engine/test_divergencias.py` (5 pruebas: nacimiento y repetición,
  retirada, conservación de la que no se evaluó, ida y vuelta del fichero sin
  temporal que sobreviva, fichero sin forma o que no es JSON),
  `tests/engine/test_reflect_cli.py` (6: queda escrita junto al diario con el
  almacén intacto, el ensayo no escribe, la ilegible se conserva y la resuelta
  se retira, una pasada que muere a medias conserva lo observado y lo no
  alcanzado, un fichero roto no para el reflejo y se reescribe, la entrada de
  un encargo resuelto o terminal se retira) y `tests/engine/test_memoria.py`
  (2: la vista lista la divergencia con 26 días parado y, sin fichero, lo
  dice; con un fichero ilegible lo declara sin caerse). Las de la escritura y
  la vista, vistas fallar contra el árbol anterior.
- Dos revisiones sobre la primera versión: Codex (ronda 1) y una revisión
  independiente encargada por la sesión. Entre las dos: la pasada que muere a
  medias y pierde lo observado, el fichero corrupto que mataba la pasada
  después de aplicar pasos y dejaba la vista sin regenerar en cada pasada
  siguiente, la escritura no atómica, dos mutaciones que sobrevivían (la
  entrada de un encargo terminal o resuelto conservada), la prosa del workflow
  y de la memoria que el cambio dejaba falsa, y la medida pendiente de abajo,
  que ya no se podía tomar. Todo corregido aquí.
- Mutaciones, con los ficheros restaurados (`diff -q` limpio) y la batería en
  verde después:

| | Mutación | Resultado |
|---|---|---|
| M1 | la pasada no escribe el fichero | caen `test_una_divergencia_apartada_queda_escrita_junto_al_diario` y `test_una_divergencia_ilegible_se_conserva_y_una_resuelta_se_retira` |
| M2 | la vista ignora el fichero | cae `test_la_vista_de_desenlaces_lista_las_divergencias_apartadas_con_su_edad` |
| M3 | una incidencia ilegible borra la entrada | caen `test_una_entrada_cuyo_encargo_no_se_pudo_leer_se_conserva_tal_cual` y la de la ilegible en `test_reflect_cli.py` |
| M4 | el ensayo escribe el fichero | cae `test_el_ensayo_no_escribe_las_divergencias` |
| M5 | una pasada que muere a medias no escribe nada | cae `test_una_pasada_que_muere_a_medias_conserva_lo_observado_y_lo_no_alcanzado` |
| M6 | la entrada de un encargo terminal se conserva | cae `test_una_entrada_de_un_encargo_resuelto_o_terminal_se_retira` |
| M7 | la entrada de un encargo evaluado sin divergencia se conserva | caen esa y `test_una_divergencia_ilegible_se_conserva_y_una_resuelta_se_retira` |
| M8 | un fichero roto para la pasada | cae `test_un_fichero_de_divergencias_roto_no_para_el_reflejo_y_se_reescribe` |
| M9 | un fichero roto tumba la vista | cae `test_la_vista_declara_un_fichero_de_divergencias_ilegible_sin_caerse` |

- Baterías `test_divergencias.py`, `test_reflect_cli.py`, `test_memoria.py` y
  `test_reflect.py`: 137 en verde. `ruff format`, `ruff check` y `mypy` sobre
  los tres módulos y las pruebas, sin avisos.
- La medida prevista en la nota —que la primera pasada real escribiera el
  fichero con `WI-20260828-122242` y la vista mostrara sus 34 días— **ya no se
  puede tomar**, y es buena noticia: el 01-10-2026, por delegación del
  propietario, se retiró de #392 la etiqueta falsa (`sirius:failed-safely`,
  aplicada a las 13:14Z del 28-08 por un run del corrector que ya estaba en
  cola, cinco minutos después de que el motor la cerrara como completada) y la
  pasada del reflector de las 15:57:31Z entregó el encargo (commit `0acc958a`
  de `estado-del-motor`). El diario real no tiene hoy ningún encargo apartado.
  Lo que sí se puede medir tras la fusión: `DESENLACES.md` muestra la sección
  nueva con «Ninguna», y la próxima divergencia que el reflector aparte
  aparecerá allí en su primera pasada, con sus días, en vez de 27 después.

## Consecuencias

- Quien abra `DESENLACES.md` ve lo que el reflector aparta para una persona y
  desde cuándo, sin auditar. Lo que se cierra aquí es el mecanismo (H-227: el
  motivo solo vivía en el log). El hecho de H-216 quedó resuelto el 01-10-2026
  (#392 con una sola etiqueta y el encargo entregado por el reflector), pero
  **H-216 sigue abierto en el registro**: la guarda de ADR-222 ata cada `pr:` a
  la PR que metió en `main` el ADR que declaró el defecto, y la de H-216 fue la
  #663, así que un cierre desde otra PR no cabe sin ampliar esa guarda. Es una
  limitación de ADR-222 —un defecto declarado abierto en una PR y arreglado en
  otra posterior no se puede cerrar— y va en su propio ADR; H-216 se cierra
  allí.
- Un fichero más en la rama de memoria, que cambia solo cuando cambia lo que
  el reflector aparta (y en cada pasada que lo vuelve a ver, por la última
  fecha y las pasadas).
- H-227 en el registro de defectos; H-216 queda abierto hasta el ADR que
  amplíe la guarda de ADR-222.

## Alternativas descartadas y por qué

Las opciones 1, 3 y 4 de arriba: la 1 porque repite la auditoría; la 3 porque
hace escribir en GitHub a un paso que solo lee y mete ruido; la 4 porque
adivina lo que ya está declarado y necesitaría el reloj en la vista.

## La lección

- familia: `regla-que-depende-de-que-alguien-se-acuerde`
- sin esto se repetiría: derivar una contradicción a «una persona» en el diseño y no dejar ningún sitio donde esa persona la encuentre: el motivo se imprimía en un log que nadie relee, y la memoria común la contaba como un encargo activo más.
- lo hace cumplir: `tests/engine/test_reflect_cli.py`
