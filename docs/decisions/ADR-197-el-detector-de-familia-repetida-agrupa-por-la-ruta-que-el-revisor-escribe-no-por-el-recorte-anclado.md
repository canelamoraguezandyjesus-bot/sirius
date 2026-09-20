# ADR-197 — El detector de familia repetida agrupa por la ruta que el revisor escribe, no por el recorte anclado

- Estado: APROBADO
- Fecha: 2026-09-14
- Aprobación: el propietario, fusionando la PR de esta rama. La decisión de fondo
  —medir el detector antes de darle autoridad— la tomó él el 14-09-2026; este ADR
  arregla lo que esa medida encontró de paso.

## Contexto y problema

`sirius-familia-repetida` (ADR-078, cableado como aviso por ADR-121) mira si un
mismo archivo recibe hallazgos en **3 rondas consecutivas**, que es la señal de
que la corrección de una ronda no cierra el problema sino que abre la siguiente
variante del mismo.

La mina de septiembre lo midió sobre datos reales
(`docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-09-14.md`, §4):

| | |
|---|---|
| Avisos emitidos | 8 casos distintos |
| Acertados / falsos | **8 / 0** (12 / 0 sumando ADR-078) |
| **Familias reales que NO vio** | **6**, en 5 incidencias |

**Cuando avisa, acierta; pero deja pasar casi tantas como señala.** Y las seis por
la misma causa, que es una línea:

```python
# src/sirius_engine/round_history.py
LOCATION_LINE_RE = re.compile(r":\d+(?:-\d+)?$")
```

Anclada al final: solo recorta el sufijo de línea cuando la cadena **termina** en
él. En la incidencia #601 el mismo fichero aparece en tres rondas seguidas como
`…/intent_interpreter.py`, como `…:153 y :181 (_NEGADORES 156-184)` y como
`…:185-205 y :230`. La tercera no acaba en `:NNN`, cuenta como otro archivo, el
tramo se rompe y el aviso no sale.

**La pieza que lo resuelve ya existe en este árbol.**
`parse_archivo_location` (`src/sirius_engine/drip_guard.py`) se construyó para la
incidencia #523/G3 porque el guardián de goteo se topó con exactamente esto —su
ADR se titula «el guardián de goteo entiende las citas tal como los revisores las
escriben de verdad»—. El detector de familia siguió con el recorte estrecho.

Es la variante de «pieza sin llamante» que la guarda de ADR-179 **no** puede ver:
aquí la pieza sí tiene llamante, pero no el que la necesita.

### Y ya estaba escrito en la suite, aceptado como limitación

`test_detecta_la_incidencia_246_seis_rondas_sobre_el_mismo_archivo` llevaba desde
la #277 este párrafo:

> La ronda 4 no cuenta para este archivo: su hallazgo lleva la anotación de la
> revisora pegada al nombre… así que normaliza a una ubicación distinta
> —**limitación conocida y aceptada**—.

Era este mismo defecto, sobre un caso real de **seis** rondas, documentado como
si fuera el precio de hacer negocios. Con este cambio, esa prueba pasa a afirmar
las seis rondas, que es lo que la #246 fue de verdad.

## Criterio de parada (escrito ANTES de tocar nada)

En `docs/audits/arranque-el-detector-de-familia-agrupa-por-la-ruta.md`. Lo que
quedó prohibido de antemano, y por qué importa:

- **`_normalize_location` no se cambia.** La comparte
  `sirius_convergence.fingerprint`, que es el mecanismo de *sin-progreso*, otro
  distinto. Cambiarla movería la huella de convergencia sin haberla medido: sería
  arreglar una cosa rompiendo otra a ciegas.
- **No se duplica el parser.** Una pieza copiada es la familia que este
  repositorio lleva cerrando.
- **La prueba del `python3` desnudo tiene que seguir pasando**, sin retocarla para
  que quepa el cambio.
- **Los seis casos que la mina nombra tienen que pasar a detectarse**, y los dos
  que declaró falsos positivos tienen que seguir saliendo: si el arreglo caza más
  de lo medido, hace otra cosa distinta de la que se midió.

## Decisión

**El detector agrupa por la ruta que encabeza la cita**, extraída con
`parse_archivo_location`, y normalizada con `_normalize_text` para que la
comparación siga siendo insensible a mayúsculas y espacios.

```python
def _ruta_del_hallazgo(valor: object) -> str:
    ruta, _ = parse_archivo_location(valor)
    return _normalize_text(ruta)
```

**Fallo abierto por construcción:** cuando el parser no reconoce ninguna ruta
devuelve el texto entero, así que una cita rara se agrupa consigo misma —que es
lo que hacía el recorte anterior— en vez de desaparecer del recuento y llevarse
un tramo real por delante.

**El radio de acción es mínimo:** una cita que ya terminaba en `:NNN` se agrupaba
igual antes y después. Lo único que cambia son las citas que **no** acaban en el
número, que es exactamente donde estaba el defecto.

### La mitad que no es obvia y sin la cual esto no funciona en producción

`scripts/automation/sirius_convergence.py` corre con el **`python3` desnudo del
runner, sin el proyecto instalado**, y carga `round_family_detector.py` por ruta
registrando a mano en `sys.modules` un paquete `sirius_engine` simulado que
**solo** contenía `round_history`. El import nuevo moría ahí con
`ModuleNotFoundError` —en producción, y con las pruebas del proyecto instalado en
verde—.

El simulacro pasa a registrar también `sirius_engine.drip_guard`, cargado por
ruta como los otros y deshecho al terminar igual que ellos. `drip_guard.py` solo
importa biblioteca estándar, así que no arrastra nada más.

Esto no se descubrió probando: **la nota de arranque lo escribió antes de tocar
una línea**, y la prueba que ya existía
(`test_cli_family_check_runs_under_the_bare_system_python_without_the_project_installed`)
lo confirmó cayendo en cuanto se hizo el cambio.

## Comprobación que la sostiene

Dos guardas nuevas, las dos con **las citas literales** que la mina midió:

- `test_agrupa_por_la_ruta_aunque_la_cita_no_acabe_en_el_numero_de_linea` — las
  tres formas reales de la #601, que hoy no se detectan y pasan a detectarse.
- `test_una_cita_que_no_tiene_ruta_reconocible_se_agrupa_consigo_misma` — el
  fallo abierto.

Y una prueba vieja cambia de significado:
`test_detecta_la_incidencia_246_…` pasa de afirmar el tramo 1-3 a afirmar el
1-6, con el porqué escrito donde estaba la «limitación aceptada».

**Tres mutaciones, las tres vistas caer:**

| | Mutación | Resultado |
|---|---|---|
| M1 | volver al recorte anclado | caen las dos: la de la #601 y la de la #246 |
| M2 | el simulacro deja de registrar `drip_guard` | caen 3 de `test_sirius_convergence`, entre ellas la del `python3` desnudo |
| M3 | agrupar por ruta **y línea** (el error ingenuo) | caen 5, entre ellas la del fallo abierto |

## Lo que este ADR NO hace

- **No da autoridad al detector**, que es la otra mitad de la decisión del
  propietario. Va aparte por dos razones: la autoridad se cablea en la puerta del
  veredicto (`sirius_apply_verdict.sh`), que es la maquinaria más delicada del
  ciclo y merece poder revertirse sola; y porque **la tasa que sostenía aquella
  decisión cambia con este arreglo**.
- **No toca el umbral de 3 rondas** (ADR-078).
- **No caza las familias que se mueven de fichero entre rondas.** La #545 tiene
  una, entre `mirror_projection.py` y `reflect.py`. El 6 es un suelo, como
  declara la propia mina.
- **No unifica las dos formas de leer una cita.** Quedan dos —el recorte anclado
  para la huella de convergencia y el parser tolerante para todo lo demás—, cada
  una con su dueño declarado. Unificarlas exige volver a medir el `sin-progreso`
  entero y es otra decisión.

## El número que la decisión de autoridad necesita

El propietario decidió: *«sí a darle autoridad, pero con la medida de septiembre
delante; si la tasa aguanta, dársela»*. La medida que le llegó era **8 de 8, cero
falsos**. Ese número está tomado **con el agrupamiento viejo**.

Con el nuevo, las seis detecciones que se añaden traen **2 falsos positivos**
(#566 y #579, que la mina clasificó uno a uno):

| | Aciertos | Falsos | Total |
|---|---|---|---|
| Agrupamiento viejo | 8 | 0 | 8 |
| Lo que añade este arreglo | 6 | 2 | 8 |
| **Con el agrupamiento nuevo** | **14** | **2** | **16** |

Sigue siendo un saldo favorable por el criterio de la #267, y el modo de fallo es
barato: un aviso con autoridad detiene el ciclo, y de ahí se sale con
`sirius-decidir --continuar` (ADR-189), sin perder trabajo. Pero **el número
cambió**, y quien decidió sobre el viejo tiene derecho a ver el nuevo antes de
que la autoridad entre.

## La lección

- familia: `pieza-correcta-a-la-que-no-llama-quien-la-necesita`
- sin esto se repetiría: dos piezas del mismo árbol leen la misma clase de dato
  —una cita `fichero:línea` escrita por un revisor— con criterios distintos, y la
  que necesita el tolerante usa el estrecho; el detector de familia dejó pasar 6
  familias reales de cada 14 durante meses, y la propia suite documentaba el
  defecto como «limitación conocida y aceptada».
- lo hace cumplir: `tests/engine/test_round_family_detector.py`
