# Pruebas de aceptación de la 0.3 del robot

- Fecha: 2026-10-13
- Qué es: las pruebas de aceptación de la versión 0.3, «Voz», de
  `docs/evolution/PLAN_DEL_ROBOT.md`. Están escritas antes del código, como pide la §3
  del plan, a partir de su «terminado cuando» y de lo que se hace, cláusula a cláusula.
  Con la sección 0.3 del plan hacen de plan de pruebas de la versión.
- Quién lo lee: la sesión que vaya a programar una pieza de la 0.3, y el propietario
  cuando le toque una de sus evaluaciones. Llega desde ADR-241, desde `MEMORIA.md` y
  desde el conductor de las pruebas, `tests/acceptance/conductor_robot_0_3.py`.
- Caduca con: la sección 0.3 del plan y las decisiones del propietario sobre la voz. Si
  cambian, cambian estas pruebas antes que el código.
- Lo comprueba por máquina: `tests/acceptance/test_robot_0_3_trazabilidad.py`, con la
  misma comprobación que vigila la tabla de la 0.2. Si la tabla nombra una prueba que no
  existe, se deja una sin nombrar o dice «en verde» de una pieza que no ha entrado, la
  batería falla. También si quita una PA, una prueba o una evaluación del inventario
  aprobado en ADR-241, aunque quite a la vez la fila y sus pruebas: ese inventario vive
  en la propia comprobación.

## Cómo se lee

Igual que `docs/evolution/PRUEBAS_0.2_DEL_ROBOT.md`. Hay dos clases de prueba:

- **Las de máquina**, con pytest, en `tests/acceptance/test_robot_0_3_*.py`. Usan dobles
  en lugar del micrófono, del oído, del transcriptor, de la voz y del altavoz: llevan
  escrito lo que suena, en vez de ondas. Demuestran que lo oído llega donde debe, que lo
  que dice es lo que escribió y que nada sale ni se guarda; no que el oído o la voz de
  verdad acierten. Hablan como el plan, y solo `tests/acceptance/conductor_robot_0_3.py`
  sabe cómo se hace cada cosa en el código. Es el conductor de la 0.2 con el oído y la
  voz encima: la charla, la semilla, la memoria y la ventana son las de siempre.
  Los dobles hacen algo y apuntan lo que hacen: el micro lee, cada vez 32 000 bytes como
  los de un segundo de un micro de verdad, ruido con una marca en medio de cada 1 000
  bytes para que un audio volcado por error en el diario se reconozca, el oído dice cuándo acaba
  el turno, el transcriptor transcribe, la voz dice, el altavoz suena y el modelo
  contesta, y cada uno apunta lo que hizo, con su momento, en el acto de hacerlo. Con el
  altavoz sonando y devolviendo eco, lo que el propietario dice llega al micro en un
  mismo audio con el eco encima, como en un micrófono de verdad: la cancelación de eco
  tiene que apartar el eco de dentro del audio, no descartar audios enteros. El eco va
  por sucesos, no por tiempo: la copia de cada locución llega una vez justo detrás de
  sonar, siga sonando o no, y se cancela siempre; mientras siga sonando, va dentro de
  cada audio; al pararlo, llega una vez más con lo ya captado; y cuando su copia ya se
  vio y nada suena, lo que Sirius dijo alguna vez, dicho por el propietario, tiene que
  oírse. Las
  pruebas miran esos registros, que solo se leen, nunca una cifra o un recuento que dé
  el conductor, porque quien implementa una pieza escribe también su parte del
  conductor. Lo que la tubería recibe del micro no dice quién habló ni con qué voz: eso
  solo lo ve la prueba, así que el eco de Sirius solo se puede apartar cerrando el micro
  mientras habla (pieza C) o cancelándolo contra lo que suena (pieza E), nunca por una
  etiqueta. Que los dobles hacen lo que dicen, y que el conductor se construye y lee la
  base y la ventana de verdad, lo comprueba `tests/acceptance/test_dobles_del_conductor.py`,
  que corre hoy, sin esperar a ninguna pieza.
- **Las evaluaciones del propietario**, E-R03-NN, más abajo. Son lo que solo puede juzgar
  él o lo que solo se puede medir en su ordenador, con su micro y su altavoz.

**Piezas** son las letras de la tabla de ADR-241. Una prueba de una pieza que no ha
entrado no corre: queda como `xfail` estricto con la pieza que falta. Cuando la pieza
entra, su letra pasa a `PIEZAS_ENTREGADAS` en el conductor y sus pruebas corren enteras.

**Cobertura**, **motivo** y **estado** significan lo mismo que en las pruebas de la 0.2:
`automática`, `parcial` o `manual`; `proveedor-real`, `windows-real` o
`evaluación-humana`; `en verde` cuando todas las piezas de la fila han entrado y sus
pruebas pasan, `pendiente` mientras falte alguna. «En verde» no es una prueba superada:
la versión termina cuando todas las filas están en verde y todas las evaluaciones del
propietario han pasado.

## Las pruebas

| ID | Qué demuestra | Sale de (§5 del plan) | Piezas | Cobertura | Motivo | Evaluación | Estado | Pruebas |
|---|---|---|---|---|---|---|---|---|
| PA-R03-01 | Lo que el propietario dice por voz pasa por el micro y el transcriptor y entra en la charla como un mensaje más: la misma semilla, los mismos tres ejemplos y el mismo recordatorio que escrito, y Sirius contesta. El turno acaba cuando el detector de turno dice que ha terminado, no en el primer silencio ni en el segundo. Lo dicho por voz se guarda, y «olvida eso» dicho por voz lo olvida, también del diario | Lo que se hace, 1 y 2; memoria de la 0.2, paso 6 | B | parcial | evaluación-humana | E-R03-04 | pendiente | `tests/acceptance/test_robot_0_3_voz.py::test_lo_que_dice_por_voz_llega_a_la_charla_como_un_mensaje_mas`<br>`tests/acceptance/test_robot_0_3_voz.py::test_la_respuesta_a_lo_dicho_por_voz_pasa_por_la_misma_charla_que_lo_escrito`<br>`tests/acceptance/test_robot_0_3_voz.py::test_el_turno_acaba_cuando_el_detector_dice_que_ha_terminado_y_no_en_el_primer_silencio`<br>`tests/acceptance/test_robot_0_3_voz.py::test_olvida_eso_dicho_por_voz_olvida` |
| PA-R03-02 | Sirius habla con una voz de Piper en español de España y suena por el altavoz; empieza con la primera frase antes de que el modelo acabe; y dice todo lo que escribió y nada más, preparado para leerse, sin marcas ni código | Lo que se hace, 1 y 3; ya está hecho, preparar el texto | C | automática | — | — | pendiente | `tests/acceptance/test_robot_0_3_voz.py::test_empieza_a_hablar_con_la_primera_frase_antes_de_que_el_modelo_acabe`<br>`tests/acceptance/test_robot_0_3_voz.py::test_lo_que_dice_es_lo_que_escribio_sin_marcas_ni_codigo`<br>`tests/acceptance/test_robot_0_3_voz.py::test_habla_con_una_voz_de_piper_en_espanol_de_espana` |
| PA-R03-03 | Su propia voz no se toma por la del propietario: lo que suena por el altavoz y vuelve por el micro, perdido con el micro cerrado o leído y cancelado, no se transcribe ni empieza un turno, ni entonces ni en los silencios de después. Antes de la cancelación de eco (pieza C) porque mientras habla no escucha; con ella (pieza E), el micro sigue abierto, el eco entra, no le corta ni se transcribe, y la voz del propietario, que llega en un mismo audio con el eco encima mientras el altavoz sigue sonando, sí atraviesa y le calla sin esperar al fin del turno; el eco que ya estaba en el micro cuando paró sigue sin ser suyo, y lo que Sirius dijo alguna vez, dicho por el propietario con el altavoz callado, sí se oye | Lo que se hace, 6 | C, E | automática | — | — | pendiente | `tests/acceptance/test_robot_0_3_voz.py::test_su_propia_voz_no_empieza_un_turno`<br>`tests/acceptance/test_robot_0_3_voz.py::test_con_la_cancelacion_de_eco_su_propia_voz_sigue_sin_empezar_un_turno` |
| PA-R03-04 | Escucha siempre: al abrir la ventana escucha sin pulsar nada y lo dice; el botón de silencio cierra el micrófono y lo dice, y lo que sonó en silencio se pierde y no se atiende después; lo oído y lo contestado se ven en la ventana como la charla escrita, con sus dos botones; todo leído de la ventana de verdad | Lo que se hace, 4; EV-022; personalidad de la 0.2, paso 5 | D | parcial | windows-real | E-R03-01 | pendiente | `tests/acceptance/test_robot_0_3_ventana.py::test_al_abrir_la_ventana_escucha_sin_pulsar_nada_y_lo_dice`<br>`tests/acceptance/test_robot_0_3_ventana.py::test_el_boton_de_silencio_cierra_el_microfono_y_lo_dice`<br>`tests/acceptance/test_robot_0_3_ventana.py::test_lo_oido_y_lo_contestado_se_ven_en_la_ventana_con_sus_dos_botones` |
| PA-R03-05 | No guarda audio: desde que arranca hasta que cierra, nada abre para escribir ningún fichero que no sea su base, sus ajustes o su diario, comparados por su ruta de verdad, esté donde esté lo demás y aunque lo borre después; tras varios turnos no ha aparecido en sus carpetas ningún fichero que no sea suyo, ni audio en la temporal, y la base solo ha cambiado como cambia charlando, mirada al acabar y fila a fila mientras vivía, también lo que se borró antes, y el diario no guarda el audio del micro, que lleva una marca y se busca en las formas en que Python escribe unos bytes; lo que no era para él no se guarda ni como texto, tampoco en el diario | Lo que se hace, 4 y 5; §2, el audio no sale nunca; EV-022 | D | automática | — | — | pendiente | `tests/acceptance/test_robot_0_3_voz.py::test_tras_varios_turnos_de_voz_no_queda_ningun_audio_guardado`<br>`tests/acceptance/test_robot_0_3_voz.py::test_lo_que_no_era_para_el_no_se_guarda_ni_como_texto` |
| PA-R03-06 | Sabe cuándo le hablan a él: con su nombre, siempre; sin su nombre, solo mientras dura la charla, que dura entre 5 s y 2 min después de que Sirius calle; lo demás no llega al modelo ni se contesta | Lo que se hace, 5 | D | parcial | evaluación-humana | E-R03-05 | pendiente | `tests/acceptance/test_robot_0_3_voz.py::test_con_su_nombre_siempre_es_para_el`<br>`tests/acceptance/test_robot_0_3_voz.py::test_sin_su_nombre_es_para_el_solo_mientras_dura_la_charla`<br>`tests/acceptance/test_robot_0_3_voz.py::test_lo_que_no_es_para_el_no_llega_al_modelo` |
| PA-R03-07 | Se le puede cortar: si el propietario habla mientras Sirius habla, Sirius se calla en menos de medio segundo desde que el micro lee su voz, medido con los relojes de los dobles, sin esperar al fin del turno ni a tener la respuesta nueva, y atiende lo nuevo; y lo que iba a decir queda escrito entero aunque le corte con el modelo aún escribiendo | Lo que se hace, 1 y 6; terminado cuando, 2 | E | parcial | windows-real | E-R03-03 | pendiente | `tests/acceptance/test_robot_0_3_voz.py::test_si_el_propietario_habla_sirius_se_calla_y_atiende_lo_nuevo`<br>`tests/acceptance/test_robot_0_3_voz.py::test_lo_que_iba_a_decir_queda_escrito_entero_aunque_le_corten` |
| PA-R03-08 | Nada sale del ordenador: oye y habla con Silero, Smart Turn, faster-whisper y Piper, ninguna petición sale durante un turno de voz, el oído y la voz del robot solo pueden ir a este ordenador y, si falta un modelo, Sirius dice qué orden ejecutar, no contesta, no lanza ningún proceso y no lo baja él | Lo que se hace, 2 y 3; no se usa; §2 | B, C | automática | — | — | pendiente | `tests/acceptance/test_robot_0_3_voz.py::test_ninguna_peticion_sale_durante_un_turno_de_voz`<br>`tests/acceptance/test_robot_0_3_voz.py::test_el_oido_y_la_voz_del_robot_solo_pueden_ir_a_este_ordenador`<br>`tests/acceptance/test_robot_0_3_voz.py::test_si_falta_un_modelo_dice_que_orden_ejecutar_y_no_lo_baja_el`<br>`tests/acceptance/test_robot_0_3_voz.py::test_oye_y_habla_con_las_herramientas_locales_del_plan` |
| PA-R03-09 | La tubería de Sirius añade poco: con micro, oído, modelo y voz instantáneos, del último sonido con su voz que lee el micro al primero que suena por el altavoz pasan menos de 200 ms en el P95 de 20 turnos, medido con los relojes de los dobles; la charla escrita sola, que va dentro, tardó 34 ms en el P95 en la nube el 13-10-2026 (línea base) | Terminado cuando, 1 | C | parcial | windows-real | E-R03-02 | pendiente | `tests/acceptance/test_robot_0_3_voz.py::test_del_final_de_su_voz_al_primer_sonido_la_tuberia_anade_menos_de_200_ms` |
| PA-R03-10 | Elegir su voz a ciegas: 5 frases típicas, distintas, con 4 a 6 voces, entre ellas las de Piper y una de personaje con Chatterbox, barajadas y sin nombre; la hoja enseña cada etiqueta y cada frase, cada muestra salió de la voz, y escuchar cada muestra suena por el altavoz con la voz y la frase que dice; la elegida, sea cual sea, queda para hablar al volver a abrir Sirius y en el turno siguiente; no hay forma de clonar una voz | Lo que se hace, 7; enmienda del manual, §9.2 | F | parcial | evaluación-humana | E-R03-06 | pendiente | `tests/acceptance/test_robot_0_3_voz.py::test_la_prueba_de_voces_da_cinco_frases_con_cuatro_a_seis_voces_barajadas_y_sin_nombre`<br>`tests/acceptance/test_robot_0_3_voz.py::test_la_voz_que_elige_el_propietario_queda_para_hablar`<br>`tests/acceptance/test_robot_0_3_voz.py::test_no_hay_forma_de_clonar_una_voz` |

**Pendiente del propietario (13-10-2026).** PA-R03-07 fija que, si le cortan, lo que
Sirius iba a decir queda escrito entero en la charla, aunque solo haya sonado la primera
frase. El plan no lo dice: es una decisión de producto que las pruebas tomaron por él, y
hay otra lectura, guardar solo lo que llegó a decir, que es lo que hace Pipecat por
defecto. Se le pregunta; hasta que conteste, la prueba fija «entero».

## Las evaluaciones del propietario

Los umbrales están fijados el 13-10-2026, antes de medir nada. Todas se hacen en su
ordenador, con su micrófono y su altavoz, y cada una llega con su orden exacta cuando
entra la pieza que la necesita (skill `comandos-para-su-ordenador`).

### E-R03-01

**El día uno de la voz en su Windows**, al entrar la pieza B. Son las dos comprobaciones
que el plan pide al empezar la 0.3 (§10): que la tubería funcione en Windows y qué cabe
en su gráfica.

- **Antes.** La sesión le da la orden que instala la tubería y baja los modelos de oír y
  de hablar, una sola vez y con internet. Después de eso no hace falta internet.
- **Qué hace él.** Apaga el wifi, abre Sirius, dice cinco cosas y pega lo que sale de la
  orden que mide qué ocupan, cargados a la vez, el modelo de la charla, el oído y la voz.
- **Pasa si** la orden de instalar acaba sin error, Sirius le oye y le contesta las 5 de 5
  veces sin internet, y lo cargado cabe en los 6 GB de su gráfica. Si no cabe, no se para: el oído y
  la voz van al procesador, como dice el plan, y se anota.
- **Resultado:** pendiente.

### E-R03-02

**Los 1,5 s**, al entrar la pieza C.

- **Qué hace él.** Habla con Sirius 20 turnos seguidos. Una orden lee lo que Sirius
  apunta en cada turno, desde que acaba de hablar el propietario hasta el primer sonido,
  y pega lo que sale.
- **Pasa si** el P95 de los 20 turnos queda por debajo de 1,5 s.
- **Resultado:** pendiente.

### E-R03-03

**Cortarle**, al entrar la pieza E.

- **Qué hace él.** Diez veces, le pide a Sirius algo largo y le corta hablando encima.
  Con la cancelación de eco por software, nada de silenciar el micro a mano.
- **Pasa si** se calla en menos de medio segundo las 10 de 10 veces, atiende lo nuevo y
  no se contesta a sí mismo ninguna vez.
- **Si no pasa.** Es lo que el plan deja escrito: si la cancelación por software no
  basta, un micrófono con cancelación de eco de unos 60 €, que es dinero y se le
  pregunta.
- **Resultado:** pendiente.

### E-R03-04

**Veinte minutos de charla**, cuando estén las piezas B a E.

- **Qué hace él.** Charla con Sirius de lo que quiera durante 20 minutos seguidos, por
  voz, con la tele apagada. Al acabar dice si le ha cansado, y cuenta las veces que
  Sirius le cortó a destiempo y las veces que no le oyó.
- **Pasa si** dice que no le ha cansado, le ha cortado a destiempo como mucho 3 veces y no
  ha dejado de oírle más de 2 veces.
- **Resultado:** pendiente.

### E-R03-05

**La tele**, al entrar la pieza D.

- **Qué hace él.** Con Sirius escuchando y la tele a su volumen normal, un informativo o
  una tertulia, 10 minutos sin hablarle. Dentro de esos 10 minutos, una llamada de
  teléfono de al menos 2 minutos al lado, con el manos libres puesto para que se oiga a
  los dos; vale llamar a quien sea o escuchar un buzón de voz. Las dos cosas son
  obligatorias: la tele y el teléfono son las dos que el plan dice que no son órdenes.
  Después le llama por su nombre 5 veces.
- **Pasa si** en los 10 minutos, tele y llamada incluidas, Sirius no contesta ninguna vez,
  y al llamarle contesta las 5 de 5.
- **Resultado:** pendiente.

### E-R03-06

**Su voz, a ciegas**, al entrar la pieza F.

- **Antes.** La sesión prepara las candidatas: las voces masculinas de Piper en español de
  España y una voz de personaje propia con Chatterbox, generada aparte, que no imita a
  nadie. Con cada una, las cinco frases de la hoja: un saludo, una broma, una pregunta,
  una frase larga, y un número y una fecha.
- **Qué hace él.** Abre la prueba de voces en Sirius y escucha, por su altavoz, las
  frases de cada candidata, barajadas y sin nombre. Elige la que más le suena a Sirius,
  y dice si le suena masculina y de España.
- **Pasa si** elige, la elegida queda como la voz con la que habla Sirius y le suena
  masculina y de España. Si elige la de Chatterbox y no puede hablar en vivo con la
  charla cargada en su gráfica, se le dice con la cifra y se le pregunta, porque es
  producto.
- **Resultado:** pendiente.

## Lo que estas pruebas no garantizan

- **Que el oído y la voz de verdad acierten.** Las de máquina llevan escrito lo que
  suena. Que le entienda, que no le corte y que la voz le guste lo dicen E-R03-01 a
  E-R03-06.
- **Que la charla por voz tenga gracia.** Es de la 0.2: sus marcas (E-R02-02) y las ideas
  malas (E-R02-03) valen igual por voz.
- **Que le reconozca por la voz, ni que sepa si le miran.** Llegan en 0.4. En 0.3 sabe
  que le hablan a él por su nombre y por el contexto, y nada más.
- **Que distinga la tele de verdad.** Las pruebas miran la regla, el nombre y el contexto;
  una voz de la tele que diga «Sirius» dentro de la charla le llegará. Lo que pasa con una
  tele de verdad lo dice E-R03-05.
- **Que la cancelación de eco por software baste.** Lo mide E-R03-03. Si no basta, el
  micrófono con cancelación de unos 60 € es dinero y se le pregunta (plan, §5, dinero).
- **Lo que tarda el modelo de la charla.** PA-R03-09 mide solo lo que añade la tubería de
  Sirius, con dobles instantáneos. Los 1,5 s enteros, con su oído, su modelo y su voz, los
  mide E-R03-02.
- **Que quepa todo en su gráfica.** Es el riesgo del plan (§10): lo mide E-R03-01 y, si
  no cabe, el oído y la voz van al procesador.
- **Que todo se instale en su ordenador.** ADR-241 resolvió las dependencias para Windows
  con Python 3.14 desde la nube; que se instalen y arranquen de verdad lo ve E-R03-01.
- **Que lo que no pase por Python se vea.** El vigilante de PA-R03-05 y PA-R03-08 ve cada
  fichero que abre Python para escribir mientras el conductor vive, también los que se
  borran después, cada conexión, cada envío de red y cada resolución de nombre que pida
  Python (`getaddrinfo`, `gethostbyname`, la inversa y enlazar a un nombre), que ya sale
  del ordenador aunque la conexión no llegue, cada proceso lanzado, y, en cada conexión a
  SQLite que se abra por `sqlite3.connect` mientras vive, que es por donde conectan
  `sqlite3` y SQLAlchemy, cada sentencia que toque la estructura: un cambio de esquema
  fuera del arranque, otra base escrita, enganchar una base o abrir el esquema a mano,
  tocar las tablas del arnés, apagar los disparadores, y una sentencia que SQLite ejecute
  dentro de otra fuera de las sombras de los índices de texto. Una conexión que no pase
  por ahí, o con una fábrica que no sea una clase de conexión, queda apuntada como no
  seguida, y cuenta. Lo que escriba o envíe por su cuenta una biblioteca en C (Qt,
  PortAudio, libsndfile, una extensión de SQLite con su propia conexión) no lo ve, y por
  eso se miran además el disco y la base al acabar: en las carpetas de Sirius cuenta
  cualquier fichero nuevo que no sea su base, sus ajustes o su diario, lo haya escrito
  quien lo haya escrito y sea audio o no, como una base aparte; en la temporal del
  sistema, donde escribe todo el mundo, solo los de audio. La pareja de tomas que Python
  se fabrica en Windows conectándose a sí mismo, y que asyncio usa en cada bucle, no sale
  del ordenador y no cuenta. Que el vigilante ve lo que dice ver lo comprueba
  `tests/acceptance/test_vigilante_del_conductor.py` con escrituras, conexiones, envíos,
  resoluciones de nombre, procesos y sentencias de verdad.
- **Que la base no guarde audio disfrazado de charla.** `audio_en_la_base` no adivina qué
  es audio por su forma: comprueba que la base solo cambia como cambia charlando con la
  0.2, y lo mira dos veces, porque la foto final no ve lo que se escribe y se borra antes
  de acabar (ronda 6 de Codex). La foto: las tablas son las de la 0.2, con sus columnas;
  ningún BLOB en ninguna columna del modelo, porque el modelo de huellas de estas pruebas
  no da ninguna y la charla no escribe binario; en las sombras de los índices, binarias
  por construcción, ningún bloque de más de 16 KiB ni con cabecera de audio; ningún texto
  de más de 16 KiB; y ninguna tabla, sombras incluidas, crece más de mil filas desde
  antes de arrancar Sirius, que es menos que un segundo de muestras. Y las filas, mientras
  vivía: al acabar de arrancar Sirius, el conductor pone en cada tabla de la 0.2 un
  disparador por insertar, actualizar y borrar, que apunta todo BLOB y todo texto de más
  de 16 KiB con su tamaño, también el que había en la fila al actualizarla o borrarla, y
  cuenta las filas insertadas y el texto escrito por tabla, se escriba como se escriba:
  con un literal, con un parámetro, con una función de Python, desde otra tabla, desde
  una sentencia anidada o a trozos con `blobopen`. Lo que apuntan es dónde y cuánto, y la
  cabecera en hexadecimal, nunca el texto: lo que una pieza olvide no puede quedarse en
  las tablas del arnés (ronda 10 de Codex). Más de mil filas insertadas en una
  tabla o más de 512 KiB de texto en total desde el arranque cuentan; veinte turnos de
  charla escriben 61 filas y 5 590 caracteres (medido el 14-10-2026 con el modelo de
  mentira). Los disparadores viven en la base, no en una conexión, así que ven también lo
  que escriba una conexión que el vigilante no sigue; quitarlos o apagarlos lo ve el
  vigilante. No ve texto corto, de menos de 16 KiB por valor y 512 KiB en total, aunque
  sea audio en base64 o en una lista, ni hasta mil filas por tabla, ni lo que una extensión en C escriba por una conexión suya, ni a
  una pieza que llame a los métodos de `sqlite3.Connection` sin ligar para saltarse su
  propia clase, que ya no ataja: engaña al arnés. Por eso el vigilante mira además cada
  fichero que se abre y cada conexión.
- **Que la tubería no escriba en el diario lo que oye.** El diario sí puede escribirse;
  se mira que lo que no era para él y lo olvidado no estén en él al acabar, y que solo
  guarde mensajes del registro y no el audio del micro. El audio del micro de mentira
  lleva una marca en medio de cada 1 000 bytes, y se busca en el diario, rotaciones
  incluidas, en las formas en que Python escribe unos bytes sin que nadie se lo pida:
  como texto, que es como salen en su `repr`; en hexadecimal; en base64, partido en
  líneas o no y desde cualquier sitio de un grupo de tres bytes; y como lista de bytes o
  de muestras de 16 bits. No hay umbral de volumen ni de largo: los mensajes del
  registro, por muchos o largos que sean, no llevan la marca. Un trozo de audio de menos
  de un kilobyte puede no llevarla, y una frase oída, corta, escrita por error en un
  mensaje no se distingue de un mensaje; la frase concreta que no era para él sí se busca. El
  conductor lo configura como `sirius.main` y vuelve a encender los registradores
  `sirius.*` que la migración de Alembic apaga; lo que una pieza escriba por el suyo llega.
- **Que una pieza hecha para burlar al arnés no esconda audio.** Las pruebas de PA-R03-05
  vigilan que una pieza no guarde audio por error: un fichero, un binario o un texto
  largo en la base aunque lo borre después, filas o texto de más, el esquema, el audio
  del micro en el diario. Una pieza escrita para esquivar la
  vigilancia tiene escondites que ninguna prueba dentro del mismo proceso cierra del
  todo: muestras en una columna numérica que ya existe y que se reescribe una y otra vez,
  escrituras directas en las sombras de los índices de texto, escribir y borrar durante
  el arranque antes de que existan los disparadores, llamar a los métodos de
  `sqlite3.Connection` sin ligar, o transformar el audio para que la marca no se
  reconozca: comprimirlo, cifrarlo, o escribirlo en una forma que Python no usa por sí
  solo.
  Eso no lo prueba nada: se revisa en el código de cada pieza, con la revisión propia y
  la de Codex (ronda 7 de Codex, ADR-241).
- **Que un proceso lanzado sin pasar por Python se vea.** El vigilante ve `subprocess` y
  los `system`, `spawn`, `exec` y `fork` de `os`; `multiprocessing` en Windows y lo que
  lance una biblioteca en C no pasan por ahí.
- **Que las herramientas, los destinos, la voz y el aviso sean los que dice el conductor.**
  `herramientas()` y `destinos_posibles_de_la_voz()` los escribe la pieza que los trae,
  leyendo los módulos de lo que monta y los ajustes de la voz; el nombre de la voz con la
  que se pide cada frase es lo que la pieza le pasa a la voz; y la orden de instalar y el
  aviso de que falta un modelo los escribe la misma pieza. Una pieza que devolviera
  literales pasaría. Lo ve la revisión de esa PR, y E-R03-01, que oye y habla con el wifi
  apagado.
- **Que mientras habla no escuche, al principio.** Es el comportamiento de la pieza C
  hasta que entre la E, que lo sustituye por la cancelación de eco (§5, 6). La prueba de
  PA-R03-03 vale en los dos regímenes: el eco, perdido o leído, no se transcribe ni
  empieza un turno. Que la C cierre el micro mientras habla lo enseña su PR en su
  comprobación.
- **Que la hoja de voces se vea como dice.** `lo_que_ve_el_propietario` es el texto de la
  hoja que da el caso de uso, sin ventana; la hoja de verdad, con sus botones, la juzga
  E-R03-06.
- **Que no haya forma de clonar una voz, más allá de lo que mire la pieza F.** La prueba
  pregunta al conductor; la pieza F tiene que sostenerlo en su PR mirando los puertos de
  síntesis y la ventana: ningún parámetro ni botón que acepte un audio de referencia.
- **Que la tubería sea de Pipecat.** Es una decisión del plan («Con qué»), no un
  comportamiento: lo dirá el ADR de la pieza B y lo verá su revisión. Las pruebas miran
  que oiga, hable, espere al detector y se deje cortar, con quien sea.
- **Que la voz de personaje con Chatterbox pueda hablar en vivo.** Pesa más que Piper y
  pide la gráfica. Para la prueba a ciegas se genera aparte; si gana, se mide y se le dice
  (E-R03-06).
- **Que no se clone la voz de nadie sin su permiso.** En 0.3 no hay camino para clonar una
  voz, y una prueba lo mira (PA-R03-10). Si algún día lo hay, el permiso por escrito es
  del plan y lo guarda él; ninguna máquina lo mira.
- **Que Smart Turn acierte el 90 % de los finales de turno en español.** Es la cifra de
  quien lo hace. Lo que cuenta lo dicen E-R03-04 y E-R03-05.
- **Que escuche con la ventana cerrada.** Sirius es su ventana: sin ella no hay escucha,
  y el indicador visible de EV-022 vive en ella.
- **Que hable por iniciativa propia.** Es la §11 del Rector y no es de la 0.3.
- **Los gestos al pensar y la cara.** Llegan en 0.4; en 0.3 el indicador de la ventana es
  lo único que se ve.
- **Model Studio.** Se queda como está (plan, §11), con su voz por OpenAI y por turnos. Lo
  vigilan sus pruebas de 0.1, no estas. La voz del robot es otra y es solo local.
- **El dinero.** Con todo en local, la 0.3 no paga nada. Los modelos de oír y hablar se
  bajan una vez al instalar, con la orden que se le da, y nunca por su cuenta
  (PA-R03-08).
- **Las órdenes de memoria por voz, más allá de «olvida eso».** Pasan por la misma charla
  que escritas (PA-R03-01); las demás las vigilan las pruebas de la 0.2.

## Lo que vigila una guarda aparte

- Ninguna nueva. «No se usa: voz a voz en la nube» (§5) se mira como comportamiento en
  PA-R03-08: el oído y la voz del robot solo pueden ir a este ordenador y ninguna
  petición sale durante un turno de voz. Las bibliotecas que la memoria no usa las sigue
  vigilando `tests/automation/test_memoria_sin_bibliotecas_excluidas.py`.
