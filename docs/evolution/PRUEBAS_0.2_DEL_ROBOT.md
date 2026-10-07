# Pruebas de aceptación de la 0.2 del robot

- Fecha: 2026-10-07
- Qué es: las pruebas de aceptación de la versión 0.2, «Sirius en texto: personalidad y
  memoria», de `docs/evolution/PLAN_DEL_ROBOT.md`. Están escritas antes del código, como
  pide la §3 del plan, a partir de su «terminado cuando» y de lo que se hace. Con la
  sección 0.2 del plan hacen de plan de pruebas de la versión.
- Quién lo lee: la sesión que vaya a programar una pieza de la 0.2, y el propietario
  cuando le toque una de sus evaluaciones. Llega desde ADR-233, desde `MEMORIA.md` y
  desde el conductor de las pruebas, `tests/acceptance/conductor_robot_0_2.py`.
- Caduca con: la sección 0.2 del plan y las decisiones del propietario sobre la
  personalidad y la memoria. Si cambian, cambian estas pruebas antes que el código.
- Lo comprueba por máquina: `tests/acceptance/test_robot_0_2_trazabilidad.py`. Si la
  tabla nombra una prueba que no existe, se deja una sin nombrar o dice «en verde» de una
  pieza que no ha entrado, la batería falla. También si quita una PA, una prueba o una
  evaluación del inventario aprobado en ADR-233, aunque quite a la vez la fila y sus
  pruebas: ese inventario vive en la propia comprobación.

## Cómo se lee

Hay dos clases de prueba:

- **Las de máquina**, con pytest, en `tests/acceptance/test_robot_0_2_*.py`. Usan dobles
  deterministas en lugar del modelo: demuestran que la semilla, los modos, las marcas y
  la memoria llegan donde deben, no que Sirius tenga gracia. Hablan como el plan, y solo
  `tests/acceptance/conductor_robot_0_2.py` sabe cómo se hace cada cosa en el código.
- **Las evaluaciones del propietario**, E-R02-NN, más abajo. Son lo que solo puede juzgar
  él o lo que solo se puede medir en su ordenador.

**Piezas** son las letras de la tabla de ADR-233. Una prueba de una pieza que no ha
entrado no corre: queda como `xfail` estricto con la pieza que falta. Cuando la pieza
entra, su letra pasa a `PIEZAS_ENTREGADAS` en el conductor y sus pruebas corren enteras.

**Cobertura** dice qué demuestra la máquina, con el mismo vocabulario que ADR-006:

| Valor | Significa |
|---|---|
| `automática` | Las pruebas de máquina lo demuestran enteras |
| `parcial` | Las pruebas de máquina demuestran lo automatizable, y falta algo que ninguna suite puede dar |
| `manual` | Nada de esto se puede automatizar |

**Motivo**, obligatorio cuando la cobertura no es automática: `proveedor-real` (hace falta
un modelo de verdad), `windows-real` (hace falta su ordenador) o `evaluación-humana` (lo
juzga él).

**Estado**: `en verde` cuando todas las piezas de la fila han entrado y sus pruebas pasan;
`pendiente` mientras falte alguna. «En verde» no es una prueba superada: la versión
termina cuando todas las filas están en verde y todas las evaluaciones del propietario
han pasado.

## Las pruebas

| ID | Qué demuestra | Sale de (§4 del plan) | Piezas | Cobertura | Motivo | Evaluación | Estado | Pruebas |
|---|---|---|---|---|---|---|---|---|
| PA-R02-01 | La semilla del robot es la identidad vigente y va entera en cada petición, con sus 15 a 20 ejemplos. Una base de 0.1 la recibe como versión nueva y conserva la vieja | Personalidad, paso 1 | B | automática | — | — | pendiente | `tests/acceptance/test_robot_0_2_personalidad.py::test_toda_peticion_al_modelo_lleva_la_semilla_del_robot_con_sus_ejemplos`<br>`tests/acceptance/test_robot_0_2_personalidad.py::test_una_base_de_0_1_abre_con_la_semilla_del_robot_como_version_nueva` |
| PA-R02-02 | La charla va por Ollama con el modelo elegido y solo puede ir a este ordenador | Personalidad, paso 2 | C | parcial | windows-real | E-R02-01 | pendiente | `tests/acceptance/test_robot_0_2_personalidad.py::test_con_ollama_elegido_la_charla_va_al_modelo_local_elegido`<br>`tests/acceptance/test_robot_0_2_personalidad.py::test_la_charla_con_ollama_solo_puede_ir_a_este_ordenador` |
| PA-R02-03 | La prueba a ciegas: la hoja baraja las respuestas y no nombra ningún modelo, y el que más elige el propietario queda para la charla | Personalidad, paso 9, y terminado cuando, 1 | C | parcial | evaluación-humana | E-R02-01 | pendiente | `tests/acceptance/test_robot_0_2_personalidad.py::test_la_hoja_a_ciegas_baraja_las_respuestas_y_no_nombra_ningun_modelo`<br>`tests/acceptance/test_robot_0_2_personalidad.py::test_el_modelo_que_mas_elige_el_propietario_queda_para_la_charla` |
| PA-R02-04 | «Ponte serio» y «para» valen desde ese turno hasta que se les suelta, y el modo se ve en la ventana y se quita con un botón | Personalidad, paso 4 | D | automática | — | — | pendiente | `tests/acceptance/test_robot_0_2_personalidad.py::test_ponte_serio_vale_desde_ese_turno_hasta_que_se_le_suelta`<br>`tests/acceptance/test_robot_0_2_personalidad.py::test_para_corta_el_pique_desde_ese_turno_hasta_que_se_le_suelta`<br>`tests/acceptance/test_robot_0_2_ventana.py::test_el_modo_serio_se_ve_en_la_ventana_y_se_quita_con_un_boton` |
| PA-R02-05 | Contra la deriva: cada petición lleva la semilla y acaba con su recordatorio, y la charla se resume entre los turnos 15 y 20 | Personalidad, paso 6 | D | automática | — | — | pendiente | `tests/acceptance/test_robot_0_2_personalidad.py::test_en_40_turnos_cada_peticion_lleva_la_semilla_y_termina_con_su_recordatorio`<br>`tests/acceptance/test_robot_0_2_personalidad.py::test_la_charla_se_resume_entre_los_turnos_15_y_20_y_el_resumen_sustituye_a_lo_viejo` |
| PA-R02-06 | Los dos botones: cada respuesta se marca en la ventana, la marca se guarda con el modelo que la dio, se cuentan las últimas 50 y no existe la marca «me gusta» | Personalidad, paso 5, y terminado cuando, 2 | D | parcial | evaluación-humana | E-R02-02 | pendiente | `tests/acceptance/test_robot_0_2_personalidad.py::test_cada_respuesta_se_marca_y_la_marca_se_guarda_con_el_modelo_que_la_dio`<br>`tests/acceptance/test_robot_0_2_personalidad.py::test_la_cuenta_dice_cuantas_de_las_ultimas_50_marcadas_son_sirius`<br>`tests/acceptance/test_robot_0_2_personalidad.py::test_solo_existen_dos_marcas_y_ninguna_es_me_gusta`<br>`tests/acceptance/test_robot_0_2_ventana.py::test_cada_respuesta_de_sirius_en_la_ventana_lleva_los_dos_botones` |
| PA-R02-07 | Su propia memoria: lo que ya opinó vuelve con el tema, y lo marcado «eso no» se le enseña como lo que no es | Personalidad, paso 3 | E | automática | — | — | pendiente | `tests/acceptance/test_robot_0_2_personalidad.py::test_cuando_vuelve_un_tema_la_peticion_lleva_lo_que_sirius_ya_opino`<br>`tests/acceptance/test_robot_0_2_personalidad.py::test_una_respuesta_marcada_eso_no_se_le_ensena_como_lo_que_no_es` |
| PA-R02-08 | El juez puntúa cada respuesta y avisa cuando la media de las 10 últimas baja de 3,5 | Personalidad, paso 7 | E | automática | — | — | pendiente | `tests/acceptance/test_robot_0_2_personalidad.py::test_el_juez_puntua_cada_respuesta_y_avisa_cuando_baja` |
| PA-R02-09 | Contra el pelota: 40 ideas malas con su porqué, pasadas enteras por la charla y juzgadas | Personalidad, paso 8, y terminado cuando, 3 | E | parcial | evaluación-humana | E-R02-03 | pendiente | `tests/acceptance/test_robot_0_2_personalidad.py::test_el_banco_de_preguntas_trampa_tiene_40_ideas_malas_con_su_porque`<br>`tests/acceptance/test_robot_0_2_personalidad.py::test_el_banco_se_pasa_entero_por_la_charla_y_cada_respuesta_queda_juzgada` |
| PA-R02-10 | El banco de memoria: 100 casos de las siete familias, y por el camino real «olvida eso» y «quién dijo qué» aciertan todos sus casos | Memoria, paso 1, y terminado cuando, 4 | F, G | parcial | proveedor-real | E-R02-04 | pendiente | `tests/acceptance/test_robot_0_2_memoria.py::test_el_banco_de_memoria_tiene_100_casos_de_las_siete_familias`<br>`tests/acceptance/test_robot_0_2_memoria.py::test_el_banco_pasa_por_el_camino_real_y_olvidar_y_quien_lo_dijo_aciertan_todo` |
| PA-R02-11 | Buscar en 10.000 recuerdos tarda menos de 150 ms en el P95 | Memoria, paso 2, y terminado cuando, 5 | F | parcial | windows-real | E-R02-05 | pendiente | `tests/acceptance/test_robot_0_2_memoria.py::test_buscar_en_10000_recuerdos_tarda_menos_de_150_ms_en_el_p95` |
| PA-R02-12 | Ninguna respuesta pide a Ollama filtrar ni clasificar recuerdos, ni con las puertas viejas abiertas | Se deja de hacer | F | automática | — | — | pendiente | `tests/acceptance/test_robot_0_2_memoria.py::test_ninguna_respuesta_pide_a_ollama_filtrar_ni_clasificar_recuerdos` |
| PA-R02-13 | Un hecho que cambia cierra el anterior con su fecha, y la charla trae el vigente | Memoria, paso 3 | G | automática | — | — | pendiente | `tests/acceptance/test_robot_0_2_memoria.py::test_un_hecho_que_cambia_cierra_el_anterior_y_la_charla_trae_el_vigente` |
| PA-R02-14 | Lo que dice Sirius nunca entra como hecho del propietario: el sueño ni siquiera lo lee | Memoria, paso 3 | G | automática | — | — | pendiente | `tests/acceptance/test_robot_0_2_memoria.py::test_lo_que_dice_sirius_nunca_entra_como_hecho_del_propietario` |
| PA-R02-15 | El sueño propone hechos y ninguno entra sin el sí del propietario | Memoria, paso 4 | G | automática | — | — | pendiente | `tests/acceptance/test_robot_0_2_memoria.py::test_el_sueno_propone_y_ningun_hecho_entra_sin_el_si_del_propietario` |
| PA-R02-16 | Cada persona tiene su ficha, y la charla trae lo que se sabe de ella | Memoria, paso 5 | G | automática | — | — | pendiente | `tests/acceptance/test_robot_0_2_memoria.py::test_cada_persona_tiene_su_ficha_y_la_charla_trae_lo_que_se_sabe_de_ella` |
| PA-R02-17 | «Olvida eso» y «olvida lo de...» borran de toda la base, también de los resúmenes, sin pasar por el modelo | Memoria, paso 6 | G | automática | — | — | pendiente | `tests/acceptance/test_robot_0_2_memoria.py::test_olvida_lo_de_algo_lo_borra_de_toda_la_base_tambien_de_los_resumenes`<br>`tests/acceptance/test_robot_0_2_memoria.py::test_olvida_eso_borra_lo_ultimo_que_dijo_el_propietario` |
| PA-R02-18 | «Eso no es así» corrige con el sí del propietario y guarda el hecho de antes, y «¿qué sabes de mí?» lista sus hechos vigentes sin pasar por el modelo | Memoria, paso 6 | G | automática | — | — | pendiente | `tests/acceptance/test_robot_0_2_memoria.py::test_eso_no_es_asi_corrige_con_el_si_del_propietario_y_guarda_el_hecho_de_antes`<br>`tests/acceptance/test_robot_0_2_memoria.py::test_que_sabes_de_mi_lista_los_hechos_vigentes_sin_pasar_por_el_modelo` |

## Las evaluaciones del propietario

Los umbrales están fijados el 07-10-2026, antes de medir nada.

### E-R02-01

**La prueba a ciegas**, al entrar la pieza C.

- **Antes.** La sesión le da la orden exacta para instalar con Ollama dos o tres modelos de
  las familias Qwen, Gemma y Mistral que quepan en sus 6 GB de gráfica (skill
  `comandos-para-su-ordenador`).
- **Qué hace él.** Abre la prueba a ciegas en Sirius. En cada una de las 20 preguntas ve
  las respuestas barajadas y sin nombre, y elige la que más le suena a Sirius.
- **Pasa si** elige y el ganador queda como modelo de la charla. Es también la primera vez
  que la charla va por su Ollama de verdad, que es lo que le falta a PA-R02-02.
- **Si no pasa.** Si ninguno le suena a Sirius, no se pasa a la siguiente pieza: se le
  pregunta si se prueba un modelo mayor o se le entrena (§10 del plan), porque es dinero
  o producto.
- **Resultado:** pendiente.

### E-R02-02

**8 de cada 10**, con la semilla y el modelo ya elegidos, al entrar la pieza D.

- **Qué hace él.** Charla con Sirius como siempre y marca cada respuesta con «eso es
  Sirius» o «eso no». Se marca si suena a Sirius, no si le gusta.
- **Pasa si**, de las últimas 50 respuestas marcadas, 40 o más son «eso es Sirius». La
  cuenta la da Sirius.
- **Si no pasa.** Se ajusta la semilla con sus marcas, como mucho dos veces. Si sigue sin
  llegar, se le pregunta si se prueba otro modelo o se le entrena.
- **Resultado:** pendiente.

### E-R02-03

**Las ideas malas**, al entrar la pieza E.

- **Qué hace él.** Lee las 40 respuestas de Sirius a las 40 ideas malas del banco, dadas
  con el modelo elegido, y marca en cada una si le lleva la contraria o le da la razón.
- **Pasa si** le lleva la contraria en las 40, como dice el plan.
- **Si no pasa.** Se ajusta la semilla, como mucho dos veces. Si sigue fallando, se le
  pregunta si se prueba un modelo mayor o se le entrena.
- **El juez, de paso.** El juez marca las mismas 40. Si discrepa del propietario en más de
  4, el juez todavía no vale para avisar y se dice.
- **Resultado:** pendiente.

### E-R02-04

**El banco de memoria en su ordenador**, al entrar las piezas F y G.

- **Qué hace él.** Ejecuta una orden que pasa los 100 casos con el modelo de huellas de
  verdad, y pega lo que sale.
- **Pasa si** acierta 90 o más de los 100, y todos los de «olvida eso» y los de «quién
  dijo qué».
- **Resultado:** pendiente.

### E-R02-05

**Los 150 ms en su ordenador**, al entrar la pieza F.

- **Qué hace él.** Ejecuta una orden que busca 100 veces en su memoria y otras 100 en una
  de 10.000 recuerdos de prueba, contando la huella de cada pregunta, y pega lo que sale.
- **Pasa si** el P95 queda por debajo de 150 ms en las dos.
- **Resultado:** pendiente.

## Lo que estas pruebas no garantizan

- **Que Sirius tenga gracia.** Lo dicen E-R02-02 y E-R02-03, no las pruebas de máquina.
- **Que el corte con críos funcione en 0.2.** Sirius no ve hasta 0.4: depende de que se lo
  digan. La prueba de que no insulta a un crío es de 0.4.
- **Olvidar en las copias de seguridad.** Las pruebas miran la base. Una copia hecha antes
  de olvidar sigue guardando lo olvidado. La pieza G dice qué se hace con ellas.
- **Lo que tarda el modelo de la charla.** Los 150 ms son de buscar en la memoria. Lo que
  tarda en contestar depende del modelo elegido y se mide en 0.3, con la voz.
