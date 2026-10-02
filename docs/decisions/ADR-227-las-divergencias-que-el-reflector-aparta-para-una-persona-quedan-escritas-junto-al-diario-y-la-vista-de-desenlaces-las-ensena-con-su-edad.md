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
   incidencia, motivo, primera vez, última vez, pasadas), `Instantanea` (lo
   que la última pasada dejó escrito **y cuánto se puede fiar uno de ello**:
   `interrumpida`, `sin_evaluar`, `perdida_posible`; `completa` cuando no hay
   nada de eso), `leer_instantanea` y `escribir_instantanea` sobre
   `divergencias.json` junto al diario, `cerrar_pasada` (la instantánea que
   deja una pasada, pura) y la regla de retención `actualizar`, pura: una divergencia vista se escribe
   (primera vez conservada, última vez y pasadas al día); una entrada anterior
   se retira si la pasada evaluó el encargo sin divergencia o el encargo ya no
   se refleja; una entrada de un encargo del que la pasada no pudo concluir
   nada (`sin_evaluar`: incidencia ilegible, o pasada que murió antes de llegar
   a él) se conserva tal cual. El fichero se escribe entero o no se toca
   (temporal al lado y `os.replace`): una pasada que muera escribiendo no deja
   un JSON a medias que el paso de confirmar del workflow confirmaría. Un
   fichero que no tiene la forma, o que no es JSON, se declara con su ruta, no
   se lee como vacío; y un fichero ausente es `None` —nadie ha escrito
   todavía—, no «ninguna». `perdida_posible` nace cuando el fichero anterior
   era ilegible, se hereda mientras las pasadas sigan incompletas y solo la
   apaga una pasada completa, que rehace el conjunto entero.
2. `reflect_cli.py` lee el fichero anterior **antes** de tocar el almacén (si
   está roto, lo dice nombrándolo, sigue —el reflejo es lo primero— y lo
   reescribe con lo que observe), recoge las divergencias de la pasada y los
   encargos que no pudo evaluar y, al terminar, cierra la instantánea con
   `cerrar_pasada` y la escribe si cambió —también la primera pasada completa
   sin divergencias, para que «ninguna» tenga quien la afirme—. Si la pasada
   muere a medias por cualquier excepción, escribe igualmente lo observado
   hasta ahí, conserva las entradas de los encargos a los que no llegó, deja
   escrito que se interrumpió y vuelve a lanzar la excepción: el paso de confirmar del workflow
   corre con `if: always()` y confirmaría el diario con un fichero viejo. En
   `--ensayo` dice cuántas hay y no escribe. `reflect.py` no se toca.
3. `memoria.py` añade a `DESENLACES.md` la sección «Divergencias que el
   reflector aparta para una persona»: encargo, incidencia, motivo, primera y
   última vez, pasadas y **días parado** (del último suceso del encargo en el
   diario a la última pasada que lo apartó). Sin fichero dice **sin dato**:
   ninguna pasada ha escrito todavía. **«Ninguna» solo lo afirma una pasada
   completa**; una incompleta dice antes de la tabla qué encargos no evaluó,
   si se interrumpió y, si un fichero anterior fue ilegible, que puede faltar
   algo hasta que una pasada completa rehaga el conjunto. La resta de
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

- `tests/engine/test_divergencias.py` (8 pruebas: nacimiento y repetición,
  retirada, conservación de la que no se evaluó, ida y vuelta del fichero sin
  temporal que sobreviva y sin fichero `None`, fichero sin forma o que no es
  JSON, y las tres de `cerrar_pasada`: una pasada completa es entera aunque el
  fichero anterior fuera ilegible, una incompleta sobre un fichero ilegible
  deja dicho que pudo perderse, la duda se hereda hasta la primera pasada
  completa), `tests/engine/test_reflect_cli.py` (8: queda escrita junto al
  diario con el almacén intacto, el ensayo no escribe, la ilegible se conserva
  y la resuelta se retira, una pasada que muere a medias conserva lo
  observado y lo no alcanzado y lo deja escrito como interrumpida, un fichero
  roto no para el reflejo y se reescribe entero, fichero roto más pasada
  incompleta deja dicho que lo anterior pudo perderse y una completa lo
  apaga, la primera pasada completa sin divergencias deja el fichero escrito
  y una igual después no reescribe, la entrada de un encargo resuelto o
  terminal se retira) y `tests/engine/test_memoria.py` (3: la vista lista la
  divergencia con 26 días parado y, sin fichero, dice «sin dato»; distingue
  «ninguna» de «no se sabe»; con un fichero ilegible lo declara sin caerse).
  Las de la escritura y la vista, vistas fallar contra el árbol anterior.
- Dos revisiones sobre la primera versión: Codex (ronda 1) y una revisión
  independiente encargada por la sesión. Entre las dos: la pasada que muere a
  medias y pierde lo observado, el fichero corrupto que mataba la pasada
  después de aplicar pasos y dejaba la vista sin regenerar en cada pasada
  siguiente, la escritura no atómica, dos mutaciones que sobrevivían (la
  entrada de un encargo terminal o resuelto conservada), la prosa del workflow
  y de la memoria que el cambio dejaba falsa, y la medida pendiente de abajo,
  que ya no se podía tomar. Todo corregido aquí.
- Ronda 2 de Codex sobre `fcd0f822`: dos hallazgos **de la misma familia que
  la ronda 1** —conocimiento incompleto enseñado como limpio—: con el fichero
  roto, una pasada que no podía leer una incidencia o moría a medias lo
  sustituía por un fichero válido y vacío, y la vista leía «ninguna»; y con el
  fichero ausente, una pasada que abortaba antes de evaluar todo no escribía
  nada, y la vista también leía «ninguna». Dos rondas de la misma familia es
  la señal de parar y buscar la raíz (ADR-001), y la raíz era que el fichero
  no sabía cuánto de entero era y la vista deducía «ninguna» de la ausencia o
  del vacío. Lo que cambia es eso, no un parche por hallazgo: la instantánea
  lleva `interrumpida`, `sin_evaluar` y `perdida_posible`; la pasada lo dice
  en su resumen; la vista distingue «sin dato», «conocimiento incompleto» y
  «ninguna», y «ninguna» solo lo afirma una pasada completa.
- Ronda 3 de Codex sobre `5f59c614`, dos remates de lo mismo: lo no alcanzado
  por una pasada interrumpida se deriva ahora de **todos los encargos
  conocidos** (antes solo de los que ya tenían entrada, así que una pasada que
  moría en el primero no podía decir qué no miró; la vista nombra los ocho
  primeros y cuenta el resto), y `leer_instantanea` exige el tipo exacto de
  los metadatos (`bool`, `bool`, lista de encargos) en vez de coercionarlos:
  `""` se leía como `False` y como `()` y una pasada corrupta pasaba por
  completa. Pruebas: la de la pasada que muere a medias exige `WI-3` (sin
  entrada previa) en `sin_evaluar`; cinco formas mal tipadas en la
  parametrizada de los ficheros sin forma; la vista con doce sin evaluar.
- Ronda 4 de Codex sobre `cdaa5ce8`, el mismo defecto en las entradas: `int(True)`
  era la incidencia 1, `int(1.5)` una pasada y `str(None)` el motivo «None».
  `_desde_json` exige ahora el tipo exacto de cada campo (textos no vacíos,
  incidencia entero o `null`, pasadas entero mayor que cero, instantes ISO con
  la primera no posterior a la última) y lo demás es un fichero sin forma.
- Ronda 5 de Codex sobre `c9349caf`: (1) los instantes exigen zona y se
  conservan convertidos a UTC, que es lo que la vista rotula (dos instantes
  sin zona pasaban, la vista los rotulaba «UTC» y `dias_parado` devolvía «?»;
  un desfase distinto se rotulaba UTC sin convertir); (2) el aviso de un
  `divergencias.json` sin forma en `--ensayo` ya no promete una reescritura
  que el ensayo nunca hace.
- Ronda 6 de Codex sobre `026c373a`: (1) un fichero con `interrumpida: false`,
  `sin_evaluar: []` y `perdida_posible: true` pasaba la validación y, como
  `completa` no mira `perdida_posible`, la vista decía «Ninguna» donde el propio
  fichero avisaba; la invariante «una pasada completa no deja `perdida_posible`»
  vive ahora en el tipo (`Instantanea.__post_init__`), así que ni el lector ni
  el escritor pueden construir la contradicción y el lector la declara como
  fichero mal formado; (2) solo `JSONDecodeError` tomaba el camino del fichero
  roto: unos bytes que no son UTF-8 salían sin la ruta y un fallo de lectura
  (un directorio en su sitio, que además `is_file()` leía como «no hay
  fichero») mataba la pasada antes del primer encargo y la vista con ella.
  `leer_instantanea` declara igual todo lo que no se puede leer, con su ruta, y
  solo «no existe» sigue siendo «no hay instantánea». Pruebas: el caso
  contradictorio en la parametrizada de los ficheros sin forma,
  `test_una_instantanea_completa_no_puede_decir_que_lo_anterior_pudo_perderse`,
  `test_un_fichero_que_no_se_puede_leer_se_declara_como_uno_sin_forma`, y las
  del reflector y la vista con el fichero roto parametrizadas con bytes
  ilegibles. Y de una revisión propia antes de la ronda 7: dos entradas con el
  mismo encargo —que `actualizar` nunca produce— se declaran como fichero sin
  forma en vez de publicarse las dos (caso nuevo en la misma parametrizada).
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
| M10 | la vista enseña «Ninguna» con el fichero ausente | cae `test_la_vista_de_desenlaces_lista_las_divergencias_apartadas_con_su_edad` |
| M11 | `cerrar_pasada` da por entera toda pasada | caen `test_una_pasada_incompleta_sobre_un_fichero_ilegible_deja_dicho_que_pudo_perderse`, `test_la_perdida_posible_se_hereda_hasta_la_primera_pasada_completa`, `test_una_pasada_que_muere_a_medias_conserva_lo_observado_y_lo_no_alcanzado`, `test_fichero_roto_mas_pasada_incompleta_deja_dicho_que_lo_anterior_pudo_perderse` |
| M12 | la duda no se hereda entre pasadas incompletas | cae `test_la_perdida_posible_se_hereda_hasta_la_primera_pasada_completa` |
| M13 | la primera pasada completa sin divergencias no escribe | cae `test_la_primera_pasada_completa_sin_divergencias_deja_el_fichero_escrito` |
| M14 | lo no alcanzado se deriva solo de las entradas anteriores | cae `test_una_pasada_que_muere_a_medias_conserva_lo_observado_y_lo_no_alcanzado` |
| M15 | los metadatos se coercionan (`bool(...)`, `tuple(str(...))`) | caen cinco casos de `test_un_fichero_que_no_tiene_la_forma_se_declara_en_vez_de_leerse_como_vacio` |
| M16 | las entradas se coercionan (`int(...)`, `str(...)`) | caen los dieciséis casos de `test_una_entrada_con_un_campo_mal_tipado_se_declara_en_vez_de_inventarse` |
| M17 | `_instante` acepta instantes sin zona | cae el caso de los dos instantes sin zona de la misma parametrizada |
| M18 | los instantes se conservan sin convertir a UTC | cae `test_un_instante_con_otro_desfase_se_conserva_convertido_a_utc` |
| M19 | el aviso del fichero roto promete reescribirlo también en `--ensayo` | cae `test_en_ensayo_el_aviso_del_fichero_roto_no_promete_reescribirlo` |
| M20 | `Instantanea` admite `perdida_posible` en una pasada completa | caen el caso contradictorio de `test_un_fichero_que_no_tiene_la_forma_se_declara_en_vez_de_leerse_como_vacio` y `test_una_instantanea_completa_no_puede_decir_que_lo_anterior_pudo_perderse` |
| M21 | solo `JSONDecodeError` toma el camino del fichero roto | caen `test_un_fichero_que_no_se_puede_leer_se_declara_como_uno_sin_forma` y los casos de bytes ilegibles del reflector y de la vista |
| M22 | las entradas repetidas se aceptan | cae el caso de las entradas repetidas de `test_un_fichero_que_no_tiene_la_forma_se_declara_en_vez_de_leerse_como_vacio` |

- Baterías `test_divergencias.py`, `test_reflect_cli.py`, `test_memoria.py` y
  `test_reflect.py`: 179 en verde. `ruff format`, `ruff check` y `mypy` sobre
  los tres módulos y las pruebas, sin avisos.
- La medida prevista en la nota —que la primera pasada real escribiera el
  fichero con `WI-20260828-122242` y la vista mostrara sus 34 días— **ya no se
  puede tomar**, y es buena noticia: el 01-10-2026, por delegación del
  propietario, se retiró de #392 la etiqueta falsa (`sirius:failed-safely`,
  aplicada a las 13:14Z del 28-08 por un run del corrector que ya estaba en
  cola, cinco minutos después de que el motor la cerrara como completada) y la
  pasada del reflector de las 15:57:31Z entregó el encargo (commit `0acc958a`
  de `estado-del-motor`). El diario real no tiene hoy ningún encargo apartado.
  Lo que sí se puede medir tras la fusión: la primera pasada completa escribe
  `divergencias.json` vacío y `DESENLACES.md` pasa de «sin dato» a «Ninguna:
  la última pasada completa…», y la próxima divergencia que el reflector
  aparte aparecerá allí en su primera pasada, con sus días, en vez de 27
  después.

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
