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
   se refleja; una entrada cuyo encargo no se pudo leer esta pasada se
   conserva tal cual. Un fichero que no tiene la forma se declara, no se lee
   como vacío.
2. `reflect_cli.py` recoge las divergencias de la pasada y los encargos
   ilegibles y, al terminar, escribe el fichero si cambió; en `--ensayo` dice
   cuántas hay y no escribe. Nada de la pasada cambia antes de eso:
   `reflect.py` no se toca.
3. `memoria.py` añade a `DESENLACES.md` la sección «Divergencias que el
   reflector aparta para una persona»: encargo, incidencia, motivo, primera y
   última vez, pasadas y **días parado** (del último suceso del encargo en el
   diario a la última pasada que lo apartó). Sin fichero, lo dice. La resta de
   fechas vive en `divergencias.py` porque la vista no puede ni nombrar el
   reloj (la guarda `test_el_generador_no_mira_el_reloj_ni_la_red_ni_git` lo
   impidió al primer intento, y bien).
4. El workflow `reflejar-desenlace.yml` no cambia: su paso «Confirmar el
   diario» hace `git add -A` en la rama de memoria, así que el fichero entra
   con el diario, y «Publicar la vista» ya corre después del reflejo.

## Comprobación que la sostiene

- `tests/engine/test_divergencias.py` (5 pruebas: nacimiento y repetición,
  retirada, conservación de la ilegible, ida y vuelta del fichero, fichero
  sin forma), `tests/engine/test_reflect_cli.py` (3: queda escrita junto al
  diario con el almacén intacto, el ensayo no escribe, la ilegible se conserva
  y la resuelta se retira) y `tests/engine/test_memoria.py` (1: la vista lista
  la divergencia con 26 días parado y, sin fichero, lo dice). Las de la escritura
  y la vista, vistas fallar contra el árbol anterior.
- Mutaciones, con los ficheros restaurados (`diff -q` limpio) y la batería en
  verde después:

| | Mutación | Resultado |
|---|---|---|
| M1 | la pasada no escribe el fichero | caen `test_una_divergencia_apartada_queda_escrita_junto_al_diario` y `test_una_divergencia_ilegible_se_conserva_y_una_resuelta_se_retira` |
| M2 | la vista ignora el fichero | cae `test_la_vista_de_desenlaces_lista_las_divergencias_apartadas_con_su_edad` |
| M3 | una incidencia ilegible borra la entrada | caen `test_una_entrada_cuyo_encargo_no_se_pudo_leer_se_conserva_tal_cual` y la de la ilegible en `test_reflect_cli.py` |
| M4 | el ensayo escribe el fichero | cae `test_el_ensayo_no_escribe_las_divergencias` |

- Baterías `test_divergencias.py`, `test_reflect_cli.py`, `test_memoria.py` y
  `test_reflect.py`: 137 en verde. `ruff format`, `ruff check` y `mypy` sobre
  los tres módulos y las pruebas, sin avisos.
- La medida del criterio de parada que no se puede tomar aquí: la primera
  pasada real de `reflejar-desenlace` tras la fusión escribirá
  `divergencias.json` con `WI-20260828-122242` y la vista mostrará sus días
  parado. Este entorno no tiene `gh` ni la rama de memoria; queda como
  observación pendiente, con la cifra prevista (34 el 01-10).

## Consecuencias

- Quien abra `DESENLACES.md` ve lo que el reflector aparta para una persona y
  desde cuándo, sin auditar. Lo que se cierra es el mecanismo (H-227: el motivo
  solo vivía en el log). **H-216 sigue abierto**: su hecho —`WI-20260828-122242`
  apartada sin que nadie decida— solo lo cierra una persona mirando #392 y
  dejando una sola etiqueta de estado, y el registro ata cada `pr:` a la PR que
  metió el ADR del defecto en `main` (ADR-222), así que cerrarlo desde esta PR
  tampoco cabría sin cambiar el esquema. Queda en la lista de decisiones del
  propietario, con dónde verlo.
- Un fichero más en la rama de memoria, que cambia solo cuando cambia lo que
  el reflector aparta (y en cada pasada que lo vuelve a ver, por la última
  fecha y las pasadas).
- H-227 en el registro de defectos; H-216 queda abierto hasta que una persona
  decida #392.

## Alternativas descartadas y por qué

Las opciones 1, 3 y 4 de arriba: la 1 porque repite la auditoría; la 3 porque
hace escribir en GitHub a un paso que solo lee y mete ruido; la 4 porque
adivina lo que ya está declarado y necesitaría el reloj en la vista.

## La lección

- familia: `regla-que-depende-de-que-alguien-se-acuerde`
- sin esto se repetiría: derivar una contradicción a «una persona» en el diseño y no dejar ningún sitio donde esa persona la encuentre: el motivo se imprimía en un log que nadie relee, y la memoria común la contaba como un encargo activo más.
- lo hace cumplir: `tests/engine/test_reflect_cli.py`
