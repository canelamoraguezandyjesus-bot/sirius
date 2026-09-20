# ADR-190 — La guarda de citas no sale de docs/decisions/: medidas 590 citas y 23 rotas fuera del registro, cero son defectos de este árbol

- Estado: APROBADO
- Fecha: 2026-09-14
- Aprobación: la fusión de la PR por el propietario
- Contexto: incidencia #619 (WI-20260914-010842), criterio de medir antes de
  fijar de la incidencia #267 tal como lo escribió ADR-078
- Relacionadas: ADR-052 (la guarda de citas y su diseño conservador), ADR-001
  (la disciplina de evidencia), ADR-078 (medir un criterio antes de fijarlo),
  ADR-177 (el hueco declarado: «lo hace cumplir: ninguna prueba»),
  `tests/automation/test_citas_de_los_adr.py`

## Nota de arranque (ADR-001, escrita ANTES de clasificar y de decidir)

Esta sección es la nota de arranque de la rama. El contrato del implementador
solo autoriza un comentario en la incidencia (`PR abierta: <URL>`), así que se
publica aquí, que es la otra sede que la skill `disciplina-evidencia` admite.

Lo que ya estaba visto al escribirla: **la medición en bruto y nada más**. La
incidencia ordena reproducirla antes de tocar nada, así que al redactar estas
cuatro respuestas ya se conocían el recuento (132 ficheros, 590 citas, 23 rotas
en 17 ficheros) y la lista de pares `documento → cita`. **Ningún veredicto
estaba escrito todavía**: la clasificación de las 23 se hizo después de
publicar el criterio de parada, que es lo que el método exige.

1. **¿Dónde vive el fallo y dónde va el arreglo?** El hueco vive en la prosa de
   `docs/`: ADR-177 lo declara en su bloque de lección («lo hace cumplir:
   ninguna prueba … nada en este repositorio vigila la coherencia de la prosa
   de `docs/` con el árbol»). El sitio candidato del arreglo es
   `tests/automation/test_citas_de_los_adr.py`, que hoy barre solo
   `docs/decisions/`. ¿Puede el sitio del arreglo **observar** el fallo que
   arregla? Sí, y sin rodeos: la guarda lee ficheros del árbol y comprueba si
   una ruta se puede abrir; ampliar el barrido es hacerle mirar donde hoy no
   mira. No es el caso del proceso que no puede informar de su propia muerte.
2. **¿Qué NO va a garantizar esto?** No garantiza que la prosa de `docs/` sea
   cierta: solo que las rutas que cita se puedan abrir. Sigue sin mirar dentro
   de los bloques de código ni las citas sin una raíz del repositorio delante
   —ADR-052 midió esa renuncia en 18 de 156—. No dice nada de `docs/canonical/`
   ni de la Arquitectura Técnica, que esta incidencia deja fuera de alcance. Y
   sobre una cita a otro repositorio no puede afirmar nada: como mucho, callar.
3. **Criterio de parada.** Publicado aquí antes del primer veredicto:
   - (a) Las 23 se clasifican una a una. **Defecto real** = la prosa afirma
     algo falso sobre ESTE árbol en este commit (el fichero se movió o se borró
     y la frase se quedó atrás). **Falso positivo** = la prosa es correcta y lo
     que falla es la guarda (rama de origen sin fusionar, repositorio ajeno,
     ruta elidida con `…`, ruta propuesta, nombre de rama, artefacto efímero).
   - (b) Si los falsos superan a los ciertos, la guarda **no entra tal cual**:
     se cambia su forma y se vuelve a medir. Es literalmente el criterio (a) de
     la nota de arranque de la incidencia #277, que ADR-078 dejó escrito.
   - (c) Si después de cambiarle la forma los defectos reales cazados siguen
     siendo **cero**, no se amplía. Una guarda cuya única cosecha medida son
     excepciones escritas a mano no caza nada, y sí deja permisos permanentes
     que hay que vigilar con más pruebas.
   - (d) Si ampliar exigiera tocar `docs/canonical/`, la Arquitectura Técnica,
     el contrato operativo o `.github/**`, se para.
   - (e) Si ampliar exigiera **debilitar** el barrido de `docs/decisions/`
     —renunciar a algo que hoy sí mira—, se para.
4. **¿Qué haría el fallo imposible en vez de improbable?** Que una cita no
   fuera texto: un enlace resuelto al construir el documento, que no compila si
   el destino no existe. Eso cambia el formato de toda la documentación del
   repositorio y ni esta incidencia lo autoriza ni el alcance permitido lo
   cubre. Se hace, por tanto, lo improbable-pero-medible: mirar, o decidir con
   la medida delante que mirar no sale a cuenta.

## Contexto y problema

`tests/automation/test_citas_de_los_adr.py` comprueba desde ADR-052 que una
ruta citada por un ADR se puede abrir. Barre `docs/decisions/`, y solo eso: el
14-09-2026, 184 ficheros. Fuera quedan 132 documentos `.md` del resto de
`docs/`, y ADR-177 dejó ese hueco declarado en su bloque de lección — «lo hace
cumplir: ninguna prueba: nada en este repositorio vigila la coherencia de la
prosa de `docs/` con el árbol». Es el único hueco declarado de la mina.

La incidencia #619 no encarga taparlo: encarga **medir primero** si taparlo
sale a cuenta, con el criterio que ADR-078 escribió para la incidencia #267 —
una comprobación entra solo si caza más defectos reales que falsos positivos, y
eso se mide antes de decidir su forma final.

## Criterio de parada (escrito ANTES de decidir)

Publicado en la nota de arranque de arriba, en el commit `c238a7c`, antes de
escribir el primer veredicto. Los cinco puntos, en corto: se clasifica una a
una; si los falsos superan a los ciertos la guarda no entra tal cual y se le
cambia la forma; si tras cambiársela los ciertos siguen siendo **cero**, no se
amplía; se para si hiciera falta tocar `docs/canonical/`, la Arquitectura
Técnica, el contrato operativo o los workflows; y se para si ampliar exigiera
debilitar el barrido de `docs/decisions/`.

Se disparó el tercero. Ninguno de los otros cuatro.

## La medida

Reproducida con la propia `citas_de` del módulo sobre los 132 documentos de
`docs/` que quedan fuera de `docs/decisions/`:

```
ficheros: 132
citas:    590
rotas:     23, repartidas en 17 ficheros
```

La incidencia publicaba 133 ficheros, 595 citas y 23 rotas en 17 ficheros. La
diferencia de tres citas y un fichero es el propio movimiento de `main` entre
una medida y otra; el número que importa —23 rotas en 17 ficheros— coincide, y
lo que se clasifica abajo es **esta** medida, no aquella.

Por subárbol, que es lo que enseña dónde está la heterogeneidad:

```
docs/audits            124 citas    7 rotas
docs/canonical           3 citas    0 rotas
docs/evolution         210 citas    4 rotas
docs/implementation    211 citas    6 rotas
docs/investigaciones    13 citas    6 rotas   <- 46 %
docs/operations         29 citas    0 rotas
docs/robotics            0 citas    0 rotas
```

## La clasificación: las 23, una a una

Defecto real = la prosa afirma algo falso sobre este árbol en este commit.
Falso positivo = la prosa acierta y la que se equivoca es la guarda. La tabla
vive además como dato ejecutable en `MEDICION_FUERA_DEL_REGISTRO`, dentro de
`tests/automation/test_citas_de_los_adr.py`, para que estos veredictos no se
queden viejos en silencio.

```
CATEGORÍA                              N   VEREDICTO
rama-del-repositorio                   2   falso positivo
ruta-elidida                           4   falso positivo
rama-de-origen-no-fusionada            4   falso positivo
adr-citado-por-su-numero               3   falso positivo
ruta-propuesta-todavia-no-creada       2   falso positivo
directorio-efimero-de-la-construccion  1   falso positivo
arbol-de-otro-proyecto                 6   falso positivo
sustituido-a-proposito                 1   falso positivo
                                      --
defectos reales                        0
falsos positivos                      23
```

Una a una, con el porqué:

1. `rama-del-repositorio` (2). `AUDITORIA_INTEGRAL_INCORPORACION_CLAUDE_2026-07.md`
   escribe la rama de trabajo «docs/claude-project-onboarding-20260720», y
   `SIRIUS_AUDITORIA_MODEL_STUDIO_2026-08.md` la rama «docs/model-studio-ui-001»
   de la PR #128. Las dos frases dicen literalmente «rama». Empiezan por
   `docs/` por casualidad: es el prefijo que este repositorio usa para nombrar
   ramas de documentación, y `RAICES_DEL_REPOSITORIO` no puede distinguirlo.
2. `ruta-elidida` (4). La prosa abrevió la ruta a propósito: «tests/.../…»
   en la mina de 2026-08, y los tres cortes con el carácter de elisión en
   `evidencia-cerrar-b1.md`, `SIRIUS_WORK_ENGINE_ARQUITECTURA_MINIMA.md` y
   `SIRIUS_WORK_ENGINE_PLAN_IMPLEMENTACION.md`. No hay ninguna ruta concreta
   que abrir, igual que en un globo o en una plantilla de la API.
3. `rama-de-origen-no-fusionada` (4). `DEFECTOS_ENCONTRADOS_2026-08-20.md` cita
   la auditoría que —lo dice en la misma frase— «solo vive sin fusionar a
   `main`» en su rama; `evidencia-experimento-filtro-fiel-al-laboratorio.md` y
   `SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md` citan dos rutas del
   laboratorio de `evidence/adr001-spikes`. Es exactamente la categoría que
   ADR-105 ya reconoció para los ADR, aquí fuera del registro.
4. `adr-citado-por-su-numero` (3). Los tres documentos de `docs/evolution/`
   escriben la misma frase: «ADR-002 de la rama de evidencia, **no** el
   «docs/decisions/ADR-002» de `main`». El ADR-002 de `main` existe
   (`ADR-002-permisos-de-la-automatizacion-sobre-workflows.md`); lo que la
   prosa cita es su número, que es como se le llama en todo el repositorio.
5. `ruta-propuesta-todavia-no-creada` (2). `AGENT_OPPORTUNITY_MATRIX.md`
   propone un registro «en «docs/implementation/agent_runs/» **o similar**», y
   `SIRIUS_0.2_ADR001_PAQUETE_OPERATIVO_SPIKES_v1.0.md` autoriza «crear, **si
   no existen**, únicamente estas rutas nuevas». La ausencia no invalida la
   frase: es la frase, igual que en `TODAVIA_NO_EXISTEN`.
6. `directorio-efimero-de-la-construccion` (1). `B13_PACKAGING.md` describe que
   `pyside6-deploy` «impone su propio directorio intermedio en
   «src/sirius/deployment/»» y que el build lo borra. Vive dentro de un
   worktree temporal y nunca llega al árbol confirmado: la prosa es cierta
   precisamente porque el directorio no está.
7. `arbol-de-otro-proyecto` (6). Las dos investigaciones del 11-09-2026 citan
   cinco rutas del repositorio de Claude Code y una de la documentación de
   Codex, tal como existen **en esos repositorios**. Es la categoría que no
   existe en `docs/decisions/` —un ADR cita este árbol— y que aparece en cuanto
   la guarda sale a `docs/investigaciones/`, donde 6 de 13 citas son de otros
   árboles.
8. `sustituido-a-proposito` (1). `SIRIUS_MODEL_STUDIO_RECONCILIACION_v1.0_PROPUESTA.md`
   pide «sustituir «src/sirius/presentation/studio_mode_widget.py» por el
   paquete `src/sirius/presentation/model_studio/`». La sustitución se hizo: el
   paquete existe y el widget no. Exigir que exista sería exigir que la
   corrección que el documento pide no se hubiera aplicado.

## Decisión

**La guarda de citas no sale de `docs/decisions/`.** Con 0 defectos reales y 23
falsos positivos, el criterio de la incidencia #267 no se salva cambiándole la
forma a la comprobación: se pueden escribir las reglas que callan cada familia
—la elisión es una línea, el árbol ajeno es un cuarto diccionario de excepción—
pero la cosecha medida seguiría siendo cero. Lo único que la ampliación
produce hoy, medido, es trabajo de excepciones: 23 permisos escritos a mano,
cada uno un agujero permanente que además hay que vigilar con más pruebas para
que no se pudra.

La causa se ve en el desglose por subárbol y es la que hace que el criterio no
se traslade: `docs/decisions/` es un corpus **homogéneo** —un ADR cita este
árbol para sostener lo que afirma— y `docs/` no lo es. Contiene
investigaciones que comparan repositorios ajenos, instantáneas fechadas de
auditorías de ramas sin fusionar y propuestas que nombran dónde iría algo. Ahí,
«la ruta no se puede abrir» deja de ser señal de defecto.

Se decide además, para que la próxima medida no tenga que decidirlo otra vez:
**si algún día la ampliación entra, los diccionarios de excepción se indexan
por la ruta del documento relativa a la raíz del repositorio**, no por el
nombre suelto del ADR. Un nombre solo identifica un documento mientras todos
vivan en la misma carpeta; en cuanto el que cita puede estar en
`docs/audits/` o en `docs/investigaciones/`, dos documentos de carpetas
distintas pueden llamarse igual y una excepción escrita para uno autorizaría
al otro en silencio. La migración de las entradas existentes es parte de esa
ampliación, no de esta decisión: hacerla hoy tocaría los tres diccionarios sin
que nada la necesite.

## Lo que esta decisión acepta a cambio

Que una cita se rompa mañana en `docs/` fuera del registro y no lo vea nadie.
Queda escrito aquí y en el propio fichero de la guarda, para que sea una
renuncia medida y no un descuido: es el mismo tipo de renuncia que ADR-052 ya
hizo al no mirar dentro de los bloques de código.

Lo que sí queda fijado en pruebas es la decisión misma:

- `test_cada_cita_clasificada_por_adr_190_sigue_siendo_la_que_se_midio` (23
  casos) comprueba que cada fila de la tabla sigue siendo una cita que el
  documento hace y que sigue sin resolverse. **No es la guarda ampliada**: no
  se rompe porque aparezca una cita rota nueva —eso es justo lo que aquí se
  decide no vigilar—, se rompe si el ADR empieza a mentir sobre su propia
  medida.
- `test_la_medicion_no_admite_una_categoria_sin_veredicto` impide que entre una
  fila con una categoría que nadie juzgó, y fija los dos números publicados
  (23 citas, 17 ficheros).
- `test_la_guarda_sigue_barriendo_solo_el_registro_de_decisiones` se pone rojo
  si alguien amplía el barrido, y le manda a volver a medir. No prohíbe
  ampliar: exige que la ampliación traiga su medida.
- `test_la_guarda_sigue_cazando_una_cita_rota_sembrada_en_un_adr_de_verdad`
  es la prueba que la incidencia pide de que las 184 comprobaciones siguen
  cazando lo que cazaban.

## Comprobación que la sostiene

Medida y mutaciones, todas sobre esta rama:

```
$ uv run python /tmp/medir.py          # citas_de sobre docs/ menos docs/decisions/
ficheros: 132 · citas: 590 · rotas: 23 en 17 ficheros

$ uv run pytest tests/automation/test_citas_de_los_adr.py -q
243 passed in 0.60s                     # 184 ADR + 23 filas de la tabla + 36
```

Cinco mutaciones sembradas y vistas caer (ADR-001), cada una contra la prueba
que debe cazarla:

```
M1  una fila apunta a una cita que el documento no hace
    -> test_cada_cita_clasificada_...            1 failed, 22 passed
M2  una fila con categoría sin veredicto
    -> test_la_medicion_no_admite_...            1 failed
M3  el barrido sale a docs/ (la ampliación que esto declina)
    -> 18 failed, 360 passed
M4  la guarda desarmada (_rotas devuelve siempre [])
    -> test_..._sembrada_en_un_adr_de_verdad     1 failed
M5  el corpus de fuera del registro deja de leerse
    -> test_el_corpus_..._se_sigue_pudiendo_medir  1 failed
```

**M3 es la medida entera en una línea.** Al ampliar el barrido a los `.md` de
`docs/`, la batería no caza un solo defecto: se pone roja 17 veces —una por
cada fichero de la tabla de arriba— y las 17 son falsas. Es la ampliación
ingenua ejecutada, no argumentada.

## Alternativas descartadas y por qué

- **Ampliar y escribir las 23 excepciones.** Es lo que M3 deja a medio camino.
  Compra una batería verde que hoy no caza nada y 23 permisos permanentes.
  Descartada por el punto (c) del criterio de parada, publicado antes de ver
  ningún veredicto.
- **Ampliar solo a un subárbol favorable.** Se buscó: no lo hay. `docs/audits`,
  `docs/evolution` e `docs/implementation` dan 0 ciertos y 17 falsos entre los
  tres; `docs/canonical`, `docs/operations` y `docs/robotics` dan 0 y 0, y las
  dos primeras están además fuera de alcance. Ninguna partición cambia el
  saldo, porque el numerador es cero en todas.
- **Añadir la regla de la elisión a `NO_ES_UNA_RUTA_CONCRETA`.** Es correcta y
  barata —una ruta con `…` no es concreta, igual que un globo—, pero cambia el
  comportamiento del barrido de `docs/decisions/` que esta incidencia manda
  dejar exactamente igual, y su única cosecha medida está fuera del registro,
  donde ya se decidió no mirar. Se deja escrita aquí para quien vuelva a medir.
- **Convertir las citas en enlaces que el documento resuelva al construirse.**
  Lo único que haría el fallo imposible en vez de improbable, y por eso está en
  la nota de arranque. Cambia el formato de toda la documentación: no lo
  autoriza esta incidencia.

## Consecuencias

- El barrido sigue en 184 ficheros y ninguna de sus comprobaciones cambia.
- La mina de lecciones mantiene el hueco que ADR-177 declaró, pero deja de ser
  un hueco sin mirar: es una renuncia con su medida y su fecha.
- Quien vuelva a proponer la ampliación se encuentra la prueba en rojo y esta
  tabla, en vez de la intuición de que «faltaba vigilar `docs/`».

## La lección

- familia: `guarda-ampliada-a-un-corpus-que-no-es-el-suyo`
- sin esto se repetiría: llevar una comprobación al sitio donde el hueco está declarado sin medir antes qué cosecharía allí, y pagar la ampliación con excepciones escritas a mano; aquí el criterio calibrado sobre `docs/decisions/` —un corpus homogéneo, donde un ADR cita este árbol— habría gritado 17 veces en falso y cazado cero defectos al salir a `docs/`, donde una investigación cita los árboles de otros repositorios.
- lo hace cumplir: `tests/automation/test_citas_de_los_adr.py`
