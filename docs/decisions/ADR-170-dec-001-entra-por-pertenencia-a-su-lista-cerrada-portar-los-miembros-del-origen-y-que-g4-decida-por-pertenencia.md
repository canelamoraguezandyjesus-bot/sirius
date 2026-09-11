# ADR-170 — DEC-001 entra por pertenencia a su lista cerrada: portar los miembros del origen y que G4 decida por pertenencia

- Estado: PROPUESTO
- Fecha: 2026-09-11
- Aprobación: la fusión de esta PR por el propietario.
- Esta ficha es además la **nota de arranque** de la rama (ADR-001, skill
  `disciplina-evidencia`): las cuatro preguntas, el criterio de parada y la
  **predicción** de abajo se escribieron y se publicaron **antes del primer
  commit de código** (commit de esta ficha sola, anterior a cualquier cambio
  en `src/` o en la fixture) y **antes de medir** el resultado.

## Contexto y problema

Hueco **H5 de ADR-148**, incidencia #582 (`WI-20260911-H5`). No lo nombra
ADR-148: se contaba dentro de los cinco de H1, y H1 (ADR-168) demostró
midiendo que la sexta ocurrencia de `B04-CA-22` no era de vigencia sino de
**ámbito**.

El caso es `B04-CA-22` («¿Qué decisiones eran válidas entre enero y marzo?»,
ámbito `PRJ-BETA`). Espera seis decisiones; tras H1 entran cinco y falta
`DEC-001`. Son **dos capas**, y hay que resolver las dos.

### Capa 1: el dato no llega, y existe

`DEC-001` es el único ítem `MULTI_PROYECTO_CERRADO` de los 97 del banco
(`project: LISTA-CERRADA-AB`, `ejes_p2.ambito: MULTI_PROYECTO_CERRADO`). La
fixture no declara miembros de lista cerrada en ningún ítem, y el cargador lo
dice en su propia nota (`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia
.py`, `_ejes_declarados`: `miembros_de_ambito=()`). `G4` recibe una lista sin
miembros y se niega con la razón correcta: «lista cerrada sin miembros
resueltos: la duda no abre ambito». La puerta está bien; le falta el dato.

El dato existe, estructurado, en el origen que la propia fixture cita
(`fuente.commit` = `dfdcdaff04dcba10939cc0b0569c55b6a636296f`, rama
`evidence/adr001-spikes`):

```python
# experiments/adr002/benchmark/build_corpus.py:82-88
{
    "id": "LISTA-CERRADA-AB",
    "nombre": "Lista cerrada Alfa+Beta v1",
    "tipo": "MULTI_PROYECTO_CERRADO",
    "miembros_lista_cerrada": ["PRJ-ALFA", "PRJ-BETA"],
},
```

Y la adjudicación del origen lo usa así: «pertenece a `LISTA-CERRADA-AB`;
Gamma no es miembro y no hereda» (`cases_v0_5.json`, CA-03, donde `DEC-001`
es señuelo fuera de ámbito). **Portar es restaurar, no inventar**: lo que se
perdió fue al proyectar a JSON (`experiments/adr002/projection/build.py` no
expone la tabla de membresía).

### Capa 2: aunque el dato llegara, `G4` lo excluiría

La rama multiproyecto de `_g4` (`src/sirius/domain/staged_engine_gates.py`)
decidía con `all(peticion.ambito.autoriza(m) for m in miembros)`:
**contención** —«todos los miembros de la lista caben en tu ámbito»—. Lo que
el origen describe es **pertenencia** —«tu ámbito es uno de los miembros»—.

| caso | `all()` | `any()` | lo que el origen adjudica |
|---|---|---|---|
| `B04-CA-22`, ámbito `PRJ-BETA` | False | True | debe entrar |
| ámbito Gamma (CA-03 del origen) | False | False | no debe entrar |

`any` reproduce la adjudicación en los dos sentidos; `all` falla el positivo.
`all` no era un descuido sino una postura de confidencialidad, coherente con
«la duda no abre ámbito»; por eso cambiarlo fue **decisión del propietario**
(11-09-2026) y no del ciclo. Lo que se conserva de esa postura es el caso sin
miembros: **sin miembros resueltos se sigue excluyendo**.

### La línea base, medida al empezar y no heredada

Sobre `5fc5fdc` (`main`), con
`uv run python scripts/diagnosticar_busqueda_del_banco.py`:

| Configuración | Exactas | De más | Hallados | Críticas perdidas |
|---|---|---|---|---|
| `--peticion` | 17/47 | 162 | 78/81 | 0 |
| `--ejes --peticion` | 21/47 | 144 | 78/81 | 0 |

Coincide con lo que la incidencia declara. **La que decide aquí es
`--ejes --peticion`**, y se dice por qué: es la única de las cuatro en la que
los ejes del corpus llegan al puerto, y sin eje de ámbito declarado `G4` ni
siquiera toma la rama de lista cerrada. Las cuatro mediciones **no se
comparan entre sí** (bitácora del ciclo, entradas 82-83).

Contra-medición de partida, ítem a ítem, con `--ejes --peticion` sobre
`5fc5fdc`: **`DEC-001` entra en 0 de los 47 casos** (guion de un solo uso que
reutiliza `_medir` del diagnóstico y no se confirma al árbol). Ese cero es el
«antes» de la transcripción de «de más».

## Criterio de parada (escrito ANTES de decidir y ANTES de medir)

1. Si con `--ejes --peticion` los hallados **no** pasan de `78/81` a `79/81`
   y las exactas de `21/47` a `22/47`, **se para** y se registra caso a caso
   qué pasó; no se ajusta el criterio al resultado.
2. Si `--peticion` **se mueve** en cualquier cifra, algo más ha cambiado:
   se para y se explica antes de seguir.
3. Si aparece **una sola** omisión crítica, se retira el cambio.
4. «De más» **no lleva listón a propósito** —`DEC-001` con pertenencia puede
   aparecer en casos de `PRJ-ALFA`/`PRJ-BETA` que no lo esperan—, pero se
   transcribe antes y después, y si aparece se dice en cuáles y por qué.
5. Dos rondas de revisión con defectos de la misma familia → parar y buscar
   la raíz (skill `disciplina-evidencia`, §2).

## Predicción (publicada ANTES de medir, ADR-001)

- `--ejes --peticion`: **78/81 → 79/81** hallados y **21/47 → 22/47** exactas
  (`B04-CA-22` tiene `extras=0` y pasa a exacta); **0 críticas perdidas**
  (`DEC-001` no es crítica: `nivel=None`).
- `--peticion`: **no se mueve** (17/47; 162; 78/81; 0).
- «De más»: sin listón; se transcribe.

## Las cuatro preguntas de la nota de arranque

1. **¿Dónde vive el fallo y dónde va el arreglo?** El fallo vive en dos
   sitios distintos del sitio donde se observa. Se observa en el recuento del
   banco; vive (a) en la fixture, que no porta la membresía que el origen sí
   declara, y (b) en `_g4`, que decide por contención donde el origen decide
   por pertenencia. El arreglo va en esos dos sitios, no en el recuento. La
   pregunta que caza la raíz —*¿puede el sitio del arreglo observar el fallo
   que arregla?*— se responde por separado: `_g4` sí puede observar el suyo
   (una prueba unitaria con miembros y tres ámbitos lo ve sin banco), y la
   fixture no puede observar nada, por eso su mitad se comprueba con una
   prueba del **cargador** que afirma qué llega al motor.
2. **¿Qué NO va a garantizar esto?** No garantiza que `DEC-001` entre **en
   producción**. El puerto real entrega todo ítem con `ejes=SIN_EJES`
   (`src/sirius/adapters/persistence/staged_engine_port.py:29`); sin ejes,
   `G4` toma la rama `ambito is None` y comprueba
   `autoriza('LISTA-CERRADA-AB')`, que no es ningún proyecto del ámbito:
   excluido. Lo que este trabajo cierra es **el techo del laboratorio**
   (`--ejes --peticion`) y **la semántica de `G4`** para cuando los ejes
   existan. Persistir los ejes es otra decisión y va por el Rector (deuda
   24). Afirmar más sería repetir el error de H1.
3. **Criterio de parada**: el de arriba, escrito antes de medir.
4. **¿Qué haría el fallo imposible en vez de improbable?** Que la membresía
   no pudiera perderse al portar: un porte automático desde el origen, o un
   invariante que exija miembros a todo ítem `MULTI_PROYECTO_CERRADO`. Lo
   primero está fuera de alcance (el origen es otra rama y este encargo solo
   autoriza añadir la pertenencia de `DEC-001`). Lo segundo se hace en la
   parte que sí cabe: la prueba del cargador afirma que los miembros llegan
   **leídos de la fixture**, no fijados en código, así que borrar el dato de
   la fixture pone la prueba en rojo. Lo que queda improbable y no imposible
   es que un ítem `MULTI_PROYECTO_CERRADO` **nuevo** entre sin miembros; se
   deja escrito aquí en vez de simularlo resuelto.

## Opciones consideradas

1. **Solo portar la membresía.** Insuficiente: con `all` y miembros
   `{PRJ-ALFA, PRJ-BETA}`, el ámbito `PRJ-BETA` de `B04-CA-22` sigue dando
   `False`. Es la capa 2 la que lo excluiría igual.
2. **Solo pasar `G4` a pertenencia.** Insuficiente: sin miembros, `_g4` corta
   antes, en «lista cerrada sin miembros resueltos».
3. **Las dos** (la decidida).
4. **Que el arnés invente la membresía en código.** Rechazada: sería el arnés
   fabricando el dato que decide la métrica, exactamente lo que la nota vieja
   de la fixture evitaba. La membresía se porta **verbatim del origen** y con
   su procedencia escrita.

## Decisión

1. `DEC-001` declara en la fixture `ejes_p2.miembros_lista_cerrada`, con el
   nombre y el valor **verbatim** de `build_corpus.py:87` en `dfdcdaff`, y la
   procedencia escrita en una nota nueva del fichero
   (`fuente.nota_incidencia_582`). Es el **único** cambio al corpus.
2. `_ejes_declarados` los lee de la fixture (tupla vacía si el ítem no los
   declara, que es el caso de los otros 96), en vez de fijar `()` en código.
3. `_g4` decide la rama multiproyecto por **pertenencia** (`any`), con el
   docstring y la **cadena de razón** reescritos para describir la regla que
   la puerta aplica ahora. La cadena llega a la explicación que ve el
   usuario: una razón que describa la regla vieja es la familia de
   `CLAUDE-R3-001` (ADR-168).

Lo que **no** cambia: sin miembros resueltos se sigue excluyendo; la puerta
`category_matching_enabled` sigue cerrada; los ejes siguen sin persistirse;
`criticidad.razon_segura` sigue sin leerse jamás.

## Comprobación que la sostiene

[Se completa tras medir. Predicción arriba, publicada antes.]

## Consecuencias

## Alternativas descartadas y por qué

Ver «Opciones consideradas».
