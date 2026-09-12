# ADR-174 — La mina en dos pasadas: la lección se declara en el ADR que la produce y las familias se cuentan solas

- Estado: PROPUESTO
- Fecha: 2026-09-12
- Aprobación: la fusión de la PR por el propietario

## Nota de arranque (escrita ANTES de tocar una línea de código)

### Lo medido antes de escribir esta nota

El repositorio tiene DOS sitios donde debería caer una lección, los dos con su
regla escrita y los dos muertos:

| Sitio | Qué guarda | Regla que declara | Último cambio |
|---|---|---|---|
| `.claude/skills/disciplina-evidencia/patrones.md` | 8 patrones de fallo | «un patrón ENTRA cuando ha mordido dos veces; se PODA lo que lleve un trimestre sin invocarse. La revisión es trimestral, de quince minutos, y decide el propietario» | **2026-08-31** (`5cc3f18`) |
| `docs/audits/registro_defectos.yml` | 32 defectos, **los 32 cerrados**, ninguno abierto | «un defecto NUNCA se borra de aquí: pasa a `estado: cerrado` con el commit que lo cerró» | **2026-08-31** (`5cc3f18`) |

Los dos se tocaron por última vez **el mismo día y en el mismo commit**. Desde
entonces han nacido **48 ADR** —ADR-124 a ADR-173—, con sus correcciones, sus
rondas de revisión y sus raíces encontradas. **Cero lecciones capturadas. Cero
defectos registrados.** Los 8 patrones del catálogo salen todos de dos PR de
agosto, la #136 y la #139.

Y la familia más vieja de la casa siguió mordiendo mientras tanto:

- `AGENTS.md:17-20` dice, a mano: *«ha aparecido seis veces una pieza correcta
  a la que no llamaba nadie, y una séptima casi se construye por duplicado el
  25-08»*.
- El informe de la mina del 31-08 la registra como familia **F3** y cuenta
  *«ya mordió 7 veces documentadas»*.
- **Hoy, 12-09-2026, mordió la octava**: `MirroredWorkItem.cerrada`, calculado
  por el espejo en cada pasada desde que se escribió y leído por nadie en todo
  `src/` y `scripts/` (ADR-173). Nadie va a actualizar el «seis veces» de
  `AGENTS.md`, igual que nadie lo actualizó a siete.

Y el detalle que decide el diseño: **esa familia YA se convirtió en prueba** —
`tests/automation/test_piezas_con_llamante.py`— y aun así mordió. Porque esa
prueba es un **diccionario escrito a mano de cuatro módulos**
(`authority_reversion`, `seven_day_streak`, `projection_verifier`,
`supervisor`): cubre las cuatro instancias que alguien se acordó de añadir, no
la familia. Un campo de un `dataclass` como `cerrada` le es invisible por
construcción.

### 1. ¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo OBSERVAR el fallo?

**El fallo no es que falte un sitio donde escribir lecciones: hay dos. Es que
capturar depende de que alguien se acuerde**, y en doce días de trabajo denso
nadie se acordó ni una vez. Un catálogo cuya regla de entrada dice «cuando haya
mordido dos veces» exige que alguien lleve la cuenta, y la cuenta la llevaba un
número escrito a mano en `AGENTS.md`.

El arreglo va donde algo **sí ocurre siempre**: el ADR. Nacen 48 en doce días,
los crea un guion desde una plantilla, y hay una batería de pruebas que ya los
mira uno a uno (`tests/automation/test_citas_de_los_adr.py`).

**¿Puede ese sitio observar el fallo que arregla?** Sí para la mitad que
importa: si la lección es un **bloque declarado** del ADR, su ausencia es un
hecho que una prueba ve, y la batería se pone roja sin ella. No puede observar
la otra mitad —si la lección escrita vale algo— y eso se declara abajo en vez
de prometerlo.

### 2. ¿Qué NO va a garantizar esto?

- **No juzga si una lección es buena.** Una máquina ve que está; no ve que sea
  verdad. Contra eso solo hay revisión humana, y este ADR no la inventa.
- **No rellena los 173 ADR anteriores.** La obligación empieza en ADR-174. Los
  anteriores quedan exentos, y la vista nace casi vacía a propósito: prefiero
  una vista que crece de verdad a una rellenada a posteriori de memoria.
- **No normaliza el significado de una familia.** Si un ADR declara
  `familia: otra-cosa` para lo que en realidad es «pieza sin lector», la cuenta
  sale mal. La vista enseña cada familia con sus ADR para que un humano vea el
  solape; ninguna máquina puede hacer más que eso aquí.
- **No arregla `test_piezas_con_llamante.py`.** Que su lista sea a mano y no vea
  un campo es un trabajo propio; esto solo hace que la familia se cuente.
- **No poda.** La regla «se poda lo que lleve un trimestre sin invocarse»
  necesita medir «invocada», y nada mide eso. Queda fuera, dicho.
- **No inventa una pasada periódica que alguien tenga que ejecutar.** Si la
  revisión dependiera de que el propietario se siente quince minutos cada
  trimestre, este ADR estaría repitiendo el fallo que dice arreglar.

### 3. Criterio de parada (decidido ANTES de ver ningún resultado)

- **(a)** Si capturar la lección no se puede hacer sin pedirle al propietario
  que haga algo, **se para**: sería el mismo defecto con otro nombre.
- **(b)** Si la vista no se puede generar del árbol y solo del árbol —sin
  reloj, sin red y sin `git`, como exige ADR-171—, **se para**. Antes nada que
  una vista curada.
- **(c)** Si hacer obligatorio el bloque exigiera tocar ADR ya fusionados,
  **se para** y la obligación se restringe a los nuevos.
- **(d)** Ninguna prueba nueva se da por buena sin haberla visto fallar contra
  una versión rota a propósito (ADR-001 §3).

### 4. ¿Qué haría el fallo IMPOSIBLE en vez de improbable?

Que **no capturar ponga la batería en rojo**. No un recordatorio, no una
costumbre, no una casilla en una plantilla que se borra sin que nadie se
entere: una prueba que mira cada ADR nuevo y falla si no trae su bloque. Eso
convierte «acordarse» en «no poder seguir sin decidirlo», que es la única forma
que ha funcionado en este repositorio.

Y para la segunda pasada, lo equivalente: **que la cuenta de cuántas veces ha
mordido una familia no la lleve nadie**. Se genera del árbol, como `MEMORIA.md`,
y una prueba falla si la vista confirmada no coincide con lo que el generador
produce. Un número escrito a mano caduca en silencio; uno generado no puede.

Lo que esto NO hace imposible, dicho arriba: que la lección escrita sea mala.

## Contexto y problema

La investigación del 11-09-2026 sobre flujos reales de agentes dejó esta fila
sin marcar: *«Aprendizaje en dos pasadas: capturar tras una solución
verificada; revisar después lo capturado contra el código, con
Keep/Update/Consolidate/Replace/Delete (Compound) — la mina es UN informe
(31-08-2026), sin pasada periódica; no se captura ninguna lección tras cada
corrección»*. Y avisaba de la trampa: *«una mina que solo añade texto acumula
contradicciones»*.

Lo que la medida de arriba añade a eso es el diagnóstico: **no faltaba el
sitio, faltaba que capturar no dependiera de acordarse.** Los dos sitios
existen, los dos llevan su regla escrita dentro, y los dos llevan 48 ADR
parados.

## Opciones consideradas

1. **Revivir `patrones.md` con una revisión trimestral del propietario.** Es lo
   que el catálogo ya declara y lleva doce días —y 48 ADR— sin ocurrir.
   Descartada: apoyarse otra vez en que alguien se acuerde es repetir el fallo
   con otro nombre. Y el propietario ha dicho explícitamente que no quiere
   mantener nada a mano.
2. **Un fichero nuevo de lecciones, `LECCIONES.md`, escrito a mano.**
   Descartada por lo mismo, y porque sería el tercer sitio muerto.
3. **Declarar la lección en el ADR que la produce y generar la cuenta** (la
   elegida).
4. **Derivar las familias automáticamente de los textos de los ADR** con
   análisis de lenguaje. Descartada: exige un modelo, y la vista de ADR-171 se
   genera del árbol y solo del árbol, sin red. Una familia mal derivada es peor
   que ninguna, porque nadie la revisaría.

## Decisión

**Uno. La lección se declara en el ADR que la produce**, en un bloque
`## La lección` con tres líneas —`familia`, `sin esto se repetiría`,
`lo hace cumplir`— o con `ninguna: <razón>`, que es una respuesta legítima y
frecuente. El criterio de captura es el de Compound Engineering: se escribe
**solo si sin ella alguien repetiría el error**.

Se declara ahí y no en un catálogo aparte porque el ADR es lo único que en este
repositorio ocurre siempre: 48 en doce días, creados por un guion desde una
plantilla y vigilados uno a uno por una batería que ya existe.

**Dos. No declararla pone la batería en rojo.**
`tests/automation/test_mina_de_lecciones.py` recorre cada ADR desde el 174 y
falla si el bloque falta, si la familia no es un identificador estable, si
falta cualquiera de las tres líneas, o si la prueba que dice hacerla cumplir no
existe en el árbol. La obligación **no se aplica hacia atrás**: rellenar los 173
anteriores hoy sería escribir de memoria lo que en su día no se capturó.

**Tres. La segunda pasada es una vista generada, no una reunión.**
`uv run sirius-memoria conocimiento` añade a `MEMORIA.md` la sección **«Las
lecciones, por familia»**: cada familia, cuántas veces ha mordido, si todas sus
lecciones tienen una prueba que las haga cumplir, y el detalle por ADR. La
cuenta no la lleva nadie, y el guardián de ADR-171 —que falla si el fichero
confirmado no coincide con lo generado— se encarga de que no se quede vieja.

**Cuatro. El detector vive en producción, no en la batería.**
`sirius_engine.memoria.problemas_de_la_leccion` es la única definición de qué
es una lección bien declarada, y la usan las dos cosas: la vista y las pruebas.
Es la lección de ADR-172, que costó tres rondas: una guardia que no ejecuta el
detector que dice probar no prueba nada.

## Qué pasa con los dos sitios que ya había

Esto es lo que impide que la mina sea «solo añadir texto»:

- **`patrones.md`** (en la skill `disciplina-evidencia`) sigue siendo lo que
  siempre fue: la prosa larga de cada patrón —las formas que toma, la pregunta
  que lo caza en el minuto uno, el antídoto—. Lo que deja de ser es el sitio
  donde se lleva la cuenta, porque nunca la llevó. El puente entre los dos es
  el nombre: **si un patrón del catálogo describe tu fallo, usa su nombre como
  `familia`**, y así la prosa y la cuenta hablan de lo mismo. Este ADR no lo
  toca —`.claude/**` no se edita desde una sesión de agente— y ese puente queda
  como convención, no como mecanismo.
- **`docs/audits/registro_defectos.yml`** no cambia: registra **defectos**, con
  su incidencia y su commit de cierre, no lecciones. Son cosas distintas y
  tener las dos no es duplicar. Que lleve desde el 31-08 sin una entrada es un
  problema suyo, y no lo arregla este ADR.

## Comprobación que la sostiene

**Seis mutaciones, sembradas en el detector y vistas caer**, con las 47 pruebas
de `test_mina_de_lecciones.py` y `test_memoria.py` corriendo en cada una:

| Mutación | Pruebas que caen |
|---|---|
| El detector nunca señala nada (`return ()` al entrar) | **10** |
| La lección se busca por todo el fichero en vez de dentro de su sección | 2, entre ellas la de «escrita fuera no cuenta» |
| No se valida la forma de la familia | la del identificador estable |
| No se comprueba que la prueba citada exista | la de la prueba inventada |
| Se admite declarar lección y `ninguna` a la vez | la de «a la vez» |
| La vista deja de listar las lecciones | el guardián de `MEMORIA.md` de ADR-171 |

Con el código restaurado, 47 en verde. La primera mutación es la que importa:
tumba diez pruebas porque **todas ejecutan el detector**, que es exactamente lo
que a la guardia de ADR-172 le faltaba en su segunda ronda.

Y dos pruebas que existen para que esta batería no pase en vacío: una falla si
no hay ningún ADR obligado (la cuarta forma de prueba vacua de `patrones.md`:
una puerta parametrizada sobre una lista vacía siempre está verde), y otra falla
si TODOS los ADR anteriores al corte ya declararan su lección, porque entonces
el corte no separaría nada y habría que bajarlo.

## La revisión del 12-09-2026, y lo que se coló en la primera versión

Un hallazgo, cierto, con las dos mitades reproducidas antes de tocar nada:
**la validación aceptaba cosas que no son pruebas.**

- `lo hace cumplir: tests/automation` pasaba, porque solo se comprobaba que la
  ruta **existiera**, y una carpeta existe siempre. El daño no es cosmético: la
  columna «hay prueba que la haga cumplir» de `MEMORIA.md` salía en **sí** para
  una lección que no tiene ninguna, que es exactamente el dato para el que esa
  columna existe. Una mina que miente sobre lo que está cubierto es peor que no
  tener mina.
- `ninguna prueba` **a secas** también pasaba, dejando una lección sin prueba y
  sin explicación de por qué no la tiene. La razón es lo único que permite
  volver dentro de un mes y decidir si ya se puede escribir.

Ahora: lo que hace cumplir una lección tiene que ser **un fichero**, y estar
**en `tests/`** —en este repositorio lo que hace imposible un fallo es una
prueba de la batería, no un módulo de producción—; y declarar que no hay prueba
obliga a decir por qué. Las tres mutaciones correspondientes caen cada una en
su prueba.

Es la misma forma que el propio ADR-174 nombra: **una comprobación más débil de
lo que su línea promete.** La declaraba yo dos secciones más arriba y la había
escrito igualmente.

## Consecuencias

- **Todo ADR nuevo cuesta tres líneas más**, y el coste cae sobre quien escribe
  el ADR —una sesión de agente—, no sobre el propietario. `PLANTILLA.md` las
  trae ya, con el criterio de captura escrito al lado.
- **La vista nace con una sola familia.** Es lo correcto: crece desde cero con
  lo que de verdad se capture, en vez de nacer rellenada de memoria. Quien la
  lea dentro de un mes verá cuántas veces ha mordido cada cosa sin que nadie
  haya llevado la cuenta.
- **El número de `AGENTS.md` se corrige a ocho y se dice de dónde sale la cuenta
  a partir de ahora.** Llevaba desde agosto diciendo seis.
- **`ninguna: <razón>` va a ser la respuesta más frecuente**, y está bien. Un
  ADR que elige entre dos diseños igual de válidos no deja lección; obligar a
  inventarla llenaría la mina de ruido, que es justo lo que el criterio de
  Compound existe para evitar.
- **Nada poda todavía.** La regla «se poda lo que lleve un trimestre sin
  invocarse» necesita medir «invocada», y nada lo mide. Queda fuera, dicho.

## Alternativas descartadas y por qué

Las cuatro de arriba. Y una quinta que se consideró: **convertir cada lección
en una prueba obligatoriamente**. Descartada porque no siempre se puede —la
familia «pieza sin lector» tiene ya su prueba,
`tests/automation/test_piezas_con_llamante.py`, y sigue siendo un diccionario
escrito a mano de cuatro módulos que no ve un campo de un `dataclass`—. Exigir
lo imposible produce pruebas de mentira. Lo que sí se exige es **declarar si la
hay o no**, y la vista lo enseña por familia: una familia que ha mordido varias
veces y sigue sin prueba que la haga cumplir se lee de un vistazo, que es
información que hoy no existe en ninguna parte.

## La lección

- familia: `regla-que-depende-de-que-alguien-se-acuerde`
- sin esto se repetiría: escribir la regla de captura en un catálogo y dar por hecho que alguien la aplicará; los dos sitios de lecciones de este repositorio llevaban 48 ADR sin una sola entrada, con sus reglas escritas dentro.
- lo hace cumplir: `tests/automation/test_mina_de_lecciones.py`
