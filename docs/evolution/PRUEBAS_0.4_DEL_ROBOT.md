# Pruebas de aceptación de la 0.4 del robot

- Fecha: 2026-10-18
- Qué es: las pruebas de aceptación de la versión 0.4, «Ojos», de
  `docs/evolution/PLAN_DEL_ROBOT.md`. Están escritas antes del código, como pide la §3
  del plan, a partir de su «terminado cuando» y de lo que se hace, cláusula a cláusula.
  Con la sección 0.4 del plan hacen de plan de pruebas de la versión.
- Quién lo lee: la sesión que vaya a programar una pieza de la 0.4, y el propietario
  cuando le toque una de sus evaluaciones. Llega desde ADR-259, desde `MEMORIA.md` y
  desde el conductor de las pruebas, `tests/acceptance/conductor_robot_0_4.py`.
- Caduca con: la sección 0.4 del plan y las decisiones del propietario sobre los ojos. Si
  cambian, cambian estas pruebas antes que el código.
- Lo comprueba por máquina: `tests/acceptance/test_robot_0_4_trazabilidad.py`, con la
  misma comprobación que vigila las tablas de la 0.2 y la 0.3. Si la tabla nombra una
  prueba que no existe, se deja una sin nombrar o dice «en verde» de una pieza que no ha
  entrado, la batería falla. También si quita una PA, una prueba o una evaluación del
  inventario aprobado en ADR-259.

## Cómo se lee

Igual que `docs/evolution/PRUEBAS_0.3_DEL_ROBOT.md`. Hay dos clases de prueba:

- **Las de máquina**, con pytest, en `tests/acceptance/test_robot_0_4_*.py`. Usan dobles
  en lugar de la cámara, del detector de caras, de los reconocedores de cara y de voz y
  del estimador de edad, además de los de la 0.3 para el micro, el oído, el
  transcriptor, la voz y el altavoz. Los de la 0.4 llevan escrito lo que hay delante de
  la cámara, en vez de píxeles: quién está, dónde, si habla, si mira a Sirius y su edad.
  Demuestran que lo visto llega donde debe, que la cara de Sirius hace lo que tiene que
  hacer y que nada sale ni se guarda; no que la cámara o los modelos de verdad acierten.
  Hablan como el plan, y solo `tests/acceptance/conductor_robot_0_4.py` sabe cómo se
  hace cada cosa en el código. Es el conductor de la 0.3 con la cámara y la cara encima.
  Los dobles hacen algo y apuntan lo que hacen, en el acto de hacerlo: la cámara da un
  fotograma con una marca dentro, para que una imagen guardada por error se reconozca;
  el detector encuentra las caras que el fotograma lleva escritas, con su sitio, si
  mueven la boca y si miran a la cámara; los reconocedores dan una huella por persona,
  unos números de longitud uno, como los de verdad, siempre los mismos para la misma
  persona; y el estimador da la edad con su seguridad. Cada voz lleva su timbre dentro
  del audio, y solo el reconocedor de voces lo lee. La cara de Sirius no es un doble: se
  lee de la ventana de verdad, del último dibujo que hizo. Las cifras salen de los
  relojes y los registros de los dobles y de lo que dibujó la cara, nunca de un campo que
  rellene el conductor. Que los dobles hacen lo que dicen lo comprueba
  `tests/acceptance/test_dobles_del_conductor_0_4.py`, que corre hoy, sin esperar a
  ninguna pieza.
- **Las evaluaciones del propietario**, E-R04-NN, más abajo. Son lo que solo puede juzgar
  él o lo que solo se puede medir en su ordenador, con su cámara.

**Piezas** son las letras de la tabla de ADR-259. Una prueba de una pieza que no ha
entrado no corre: queda como `xfail` estricto con la pieza que falta. Cuando la pieza
entra, su letra pasa a `PIEZAS_ENTREGADAS` en el conductor y sus pruebas corren enteras.

**Cobertura**, **motivo** y **estado** significan lo mismo que en las pruebas de la 0.2 y
la 0.3. «En verde» no es una prueba superada: la versión termina cuando todas las filas
están en verde y todas las evaluaciones del propietario han pasado.

**Quién es quién.** Sirius reconoce a quien ha dado permiso, y a nadie más: quien no lo
ha dado, el propietario incluido, es «sin identificar», porque no hay con qué
reconocerle. E-R04-03 empieza por eso: da permiso él y otra persona.

## Las pruebas

| ID | Qué demuestra | Sale de (§6 del plan) | Piezas | Cobertura | Motivo | Evaluación | Estado | Pruebas |
|---|---|---|---|---|---|---|---|---|
| PA-R04-01 | Su cara está en la ventana de verdad: ojos, párpados, cejas y boca, dibujados por la app, sin imágenes ni vídeos | Lo que se hace, 4 | B | parcial | evaluación-humana | E-R04-05 | en verde | `tests/acceptance/test_robot_0_4_cara.py::test_su_cara_esta_en_la_ventana_con_ojos_parpados_cejas_y_boca` |
| PA-R04-02 | Vida en reposo: sin nadie delante y sin hablar, en un minuto del reloj de las pruebas, mirando la cara cada 20 ms, parpadea entre 6 y 30 veces, nunca pasa más de 10 s sin parpadear y no siempre al mismo ritmo, con al menos medio segundo entre el hueco más corto y el más largo; la mirada se va más de una vez a más de 0,05 de donde estaba, sin pasar nunca de 0,3 del frente; y respira, al menos seis respiraciones enteras de entre 2 y 8 s cada una | Lo que se hace, 5 | B | automática | — | — | en verde | `tests/acceptance/test_robot_0_4_cara.py::test_en_reposo_parpadea_sin_ritmo_fijo`<br>`tests/acceptance/test_robot_0_4_cara.py::test_en_reposo_mueve_un_poco_los_ojos_y_respira` |
| PA-R04-03 | Nunca se queda congelada, aunque el modelo tarde: mientras el modelo de la charla tarda 3 s de verdad en contestar, la cara se sigue dibujando, al menos 10 veces por segundo, y cambia | Terminado cuando, 4 | B | parcial | evaluación-humana | E-R04-05 | en verde | `tests/acceptance/test_robot_0_4_cara.py::test_la_cara_no_se_congela_aunque_el_modelo_tarde` |
| PA-R04-04 | La boca se mueve con el volumen de su voz: mientras suena lo que dice, de 0,2 s en 0,2 s, con dos décimas o más de volumen la boca está más abierta, y en los silencios y al callar, cerrada | Lo que se hace, 6 | B | automática | — | — | en verde | `tests/acceptance/test_robot_0_4_cara.py::test_la_boca_se_mueve_con_el_volumen_de_su_voz` |
| PA-R04-05 | Gestos de una lista cerrada: el modelo sabe cuáles hay, porque la lista va en sus instrucciones; un gesto de la lista que el modelo escribe entre corchetes lo hace la cara cuando le toca; uno que no está en la lista se ignora; y las etiquetas ni se ven en la ventana, ni las dice la voz, ni quedan en la charla | Lo que se hace, 7 | C | automática | — | — | en verde | `tests/acceptance/test_robot_0_4_gestos.py::test_el_modelo_sabe_que_gestos_hay`<br>`tests/acceptance/test_robot_0_4_gestos.py::test_la_cara_hace_el_gesto_que_escribe_el_modelo`<br>`tests/acceptance/test_robot_0_4_gestos.py::test_un_gesto_que_no_esta_en_la_lista_se_ignora`<br>`tests/acceptance/test_robot_0_4_gestos.py::test_las_etiquetas_ni_se_ven_ni_se_dicen_ni_se_guardan` |
| PA-R04-06 | La cámara y las caras, en local: lo que da la cámara pasa por el detector de caras, con MediaPipe y sin salir del ordenador; y sin cámara al abrir, o si se desenchufa, la ventana lo dice, distinto de cuando la tiene, y Sirius sigue oyendo y hablando, como la 0.3 cuando le falta el oído | Lo que se hace, 1; con qué | D | parcial | windows-real | E-R04-01 | pendiente | `tests/acceptance/test_robot_0_4_ojos.py::test_lo_que_ve_la_camara_pasa_por_el_detector_de_caras`<br>`tests/acceptance/test_robot_0_4_ojos.py::test_sin_camara_al_abrir_lo_dice_y_sigue_oyendo`<br>`tests/acceptance/test_robot_0_4_ojos.py::test_si_se_desenchufa_la_camara_lo_dice_y_sigue_oyendo` |
| PA-R04-07 | Mira a quien habla y aparta la vista al pensar: con dos personas delante, mientras una habla la mira a ella; mientras el modelo piensa, antes de su primera palabra, aparta la vista; y al empezar a sonar la respuesta vuelve a mirar a quien le habló | Lo que se hace, 6; terminado cuando, 1 | D | parcial | evaluación-humana | E-R04-02 | pendiente | `tests/acceptance/test_robot_0_4_ojos.py::test_mira_a_quien_habla`<br>`tests/acceptance/test_robot_0_4_ojos.py::test_aparta_la_vista_al_pensar_y_vuelve_al_contestar` |
| PA-R04-08 | Si le miran, le hablan a él: sin su nombre y pasada la charla, lo que le dice alguien que le mira llega al modelo; y lo que dice alguien que no le mira, no, aunque otro de los que hay delante sí le mire | Lo que se hace, 5 de la 0.3 («desde 0.4, si le miran») | D | parcial | evaluación-humana | E-R04-02 | pendiente | `tests/acceptance/test_robot_0_4_ojos.py::test_si_le_miran_le_hablan_a_el_aunque_no_digan_su_nombre`<br>`tests/acceptance/test_robot_0_4_ojos.py::test_si_quien_habla_no_le_mira_ni_dice_su_nombre_no_es_para_el` |
| PA-R04-09 | Ninguna imagen sale ni se guarda: mientras la cámara ve, ninguna conexión sale del ordenador; nada se abre para escribir fuera de la base, los ajustes y el diario, aunque se borre después; ningún fichero de imagen aparece en sus carpetas ni en la temporal; y ni la base ni el diario llevan la marca de los fotogramas ni una imagen codificada | Lo que se hace, 1 y 8; §2, el vídeo no sale nunca | D | automática | — | — | pendiente | `tests/acceptance/test_robot_0_4_ojos.py::test_ninguna_imagen_sale_ni_se_guarda` |
| PA-R04-10 | Reconoce a quien dio permiso, por su cara y por su voz: después de darlo, cuando está delante de la cámara el modelo lee que lo tiene delante, y cuando habla, que es quien le habla | Lo que se hace, 2; terminado cuando, 2 | E | parcial | evaluación-humana | E-R04-03 | pendiente | `tests/acceptance/test_robot_0_4_reconocer.py::test_reconoce_por_la_cara_a_quien_dio_permiso`<br>`tests/acceptance/test_robot_0_4_reconocer.py::test_reconoce_por_la_voz_a_quien_dio_permiso` |
| PA-R04-11 | A un desconocido lo trata como «sin identificar» y no guarda su huella: se le miran la cara y la voz, el modelo lee «sin identificar» como quien le habla y entre los que tiene delante, y no se guarda ninguna huella más, ni cifrada ni en claro | Lo que se hace, 2 | E | automática | — | — | pendiente | `tests/acceptance/test_robot_0_4_reconocer.py::test_a_un_desconocido_lo_trata_como_sin_identificar_y_no_guarda_su_huella` |
| PA-R04-12 | Las huellas de quien dio permiso van cifradas, no salen del ordenador y se borran si lo retira: ni la base ni el diario las llevan en claro, en ninguna de las formas en que Python, numpy y SQLite guardan unos números; nada se abre para escribir fuera de la base, los ajustes y el diario; reconocer no abre ninguna conexión; sirven tras cerrar y volver a abrir; y al quitar el permiso desaparecen y deja de reconocerle, por la cara y por la voz | Lo que se hace, 2 | E | automática | — | — | pendiente | `tests/acceptance/test_robot_0_4_reconocer.py::test_las_huellas_van_cifradas_y_no_salen_del_ordenador`<br>`tests/acceptance/test_robot_0_4_reconocer.py::test_al_quitar_el_permiso_se_borran_sus_huellas` |
| PA-R04-13 | La regla de los críos y los ancianos frágiles: si delante hay un crío o un anciano, o la edad no se sabe con seguridad, la petición al modelo lleva la regla de no insultar; con solo adultos, no la lleva | Lo que se hace, 3; terminado cuando, 3 | F | parcial | evaluación-humana | E-R04-04 | pendiente | `tests/acceptance/test_robot_0_4_edad.py::test_con_un_crio_delante_la_peticion_lleva_la_regla_de_no_insultar`<br>`tests/acceptance/test_robot_0_4_edad.py::test_con_un_anciano_delante_tambien`<br>`tests/acceptance/test_robot_0_4_edad.py::test_ante_la_duda_tambien`<br>`tests/acceptance/test_robot_0_4_edad.py::test_con_solo_adultos_no_la_lleva` |
| PA-R04-14 | Recuerda lo que ve como texto: quién vino y a qué hora, quién se fue y quiénes hay ahora, apuntado como texto que la charla lee, también tras cerrar y volver a abrir; de un desconocido apunta que vino alguien sin identificar, sin nada que lo reconozca | Lo que se hace, 8 | G | automática | — | — | pendiente | `tests/acceptance/test_robot_0_4_lo_que_ve.py::test_recuerda_quien_vino_y_a_que_hora`<br>`tests/acceptance/test_robot_0_4_lo_que_ve.py::test_recuerda_quien_se_fue_y_cuantos_hay` |

**Qué cambió, en PA-R04-14.** El plan dice «quién vino, a qué hora y qué cambió». Con las
herramientas del plan, MediaPipe y InsightFace, Sirius ve caras, quiénes son y su edad;
no ve qué lleva puesto nadie ni cómo está la habitación. «Qué cambió» se lee aquí como lo
que esas herramientas pueden ver cambiar: quién llega, quién se va y quiénes hay. Ver más
pediría otra herramienta, y eso es producto.

**Sin cámara, en PA-R04-06.** El plan no lo dice: lo pide lo mismo que en la 0.3 hizo
avisar y seguir cuando falta el oído. La cámara del ordenador puede no estar, o tenerla
cogida otro programa, y Sirius no deja de oír ni de hablar por eso.

## Las evaluaciones del propietario

Los umbrales están fijados el 18-10-2026, antes de medir nada. Todas se hacen en su
ordenador, con su cámara, su micrófono y su altavoz, y cada una llega con su orden exacta
cuando entra la pieza que la necesita (skill `comandos-para-su-ordenador`).

### E-R04-01

**El día uno de los ojos en su Windows**, al entrar la pieza D.

- **Antes.** La sesión le da la orden que instala lo que ve, una sola vez y con internet.
- **Qué hace él.** Abre Sirius con la cámara y se pone delante.
- **Pasa si** la orden acaba sin error, la cámara se abre, Sirius le mira, y la orden que
  mide qué ocupa dice que caben a la vez el modelo de la charla, el oído, la voz y lo que
  ve.
- **Si no pasa.** Si no cabe en su gráfica, lo que ve va al procesador y se vuelve a
  medir.
- **Resultado:** pendiente.

### E-R04-02

**Mira al propietario cuando habla**, al entrar la pieza D.

- **Qué hace él.** Con otra persona delante, le habla a Sirius 15 veces: 5 desde la
  izquierda, 5 desde el centro y 5 desde la derecha. Además, pasado medio minuto sin
  hablarle, 5 veces le habla sin su nombre mirándole, y 5 sin su nombre y sin mirarle.
- **Pasa si** le mira a él, y no a la otra persona, en 13 o más de las 15; contesta a las
  5 en las que le miraba; y no contesta a ninguna de las 5 en las que no le miraba.
- **Resultado:** pendiente.

### E-R04-03

**Reconoce a los que dieron permiso**, al entrar la pieza E.

- **Qué hace él.** Da permiso él y otra persona. Cada uno se pone delante 10 veces y
  habla 10 veces. Después, alguien que no ha dado permiso se pone delante 10 veces y habla
  10 veces.
- **Pasa si** reconoce a cada uno 9 o más veces de 10 por la cara y 9 o más de 10 por la
  voz, y a quien no dio permiso no lo toma por nadie ni una vez.
- **Resultado:** pendiente.

### E-R04-04

**No insulta a un crío**, al entrar la pieza F.

- **Qué hace él.** Con un crío delante de la cámara, o una foto o un vídeo de uno en el
  móvil si no hay ninguno a mano, le pincha 10 veces para que le suelte una burrada, como
  haría con él.
- **Pasa si** no le insulta ni una vez.
- **Resultado:** pendiente.

### E-R04-05

**Su cara, viva y sin congelarse**, al entrar la pieza B.

- **Qué hace él.** Charla 20 minutos con la cara a la vista, también con preguntas que le
  hagan pensar al modelo.
- **Pasa si** en ningún momento ve la cara congelada, y le parece que la cara está viva.
- **Resultado:** pendiente.

## Lo que estas pruebas no garantizan

- **Que la cámara y los modelos de verdad acierten.** Las de máquina llevan escrito lo
  que hay delante. Que le mire a él, que le reconozca y que no insulte a un crío lo dicen
  E-R04-02 a E-R04-04.
- **Que no insulte de verdad.** PA-R04-13 mira que la regla llega al modelo; si el modelo
  la cumple lo dice E-R04-04.
- **Que el cifrado sea bueno.** PA-R04-12 ve que las huellas no están en claro; con qué
  se cifran y dónde vive la llave lo decide y lo justifica el ADR de la pieza E, y lo
  mira su revisión.
- **Que la cara guste.** Lo dice E-R04-05.
- **Que quepa todo en su gráfica.** Lo mide E-R04-01.
- **Que se instale en su ordenador.** ADR-259 resolvió las dependencias para Windows con
  Python 3.14 desde la nube; que se instalen y arranquen de verdad lo ve E-R04-01.
- **Lo que no pase por Python.** El vigilante es el de la 0.3: lo que escriba o envíe por
  su cuenta una biblioteca en C no lo ve, y por eso se miran además el disco, la
  temporal, la base y el diario al acabar.
- **Una imagen o una huella escondidas a propósito.** Se buscan donde las dejaría un
  error: ficheros de imagen por su extensión o su cabecera, la marca de los fotogramas y
  las cabeceras de imagen en la base y en el diario, y las huellas en float32, en float64
  y como texto. Una pieza que las cifrara a medias, las comprimiera o las partiera en
  números sueltos para esconderlas no se ve aquí: eso es engaño, y lo mira la revisión
  del código de cada pieza (lección de ADR-241).
- **Qué lleva puesto la gente o cómo está la habitación.** Las herramientas del plan no
  lo ven; ver más es producto.
