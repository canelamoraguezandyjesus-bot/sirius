<!-- Informe para el propietario. Las cuatro decisiones del 11-09 quedaron TOMADAS (bloque de arriba). Hay UNA NUEVA pendiente, D1, más abajo. -->

# DECIDIDAS el 11-09-2026 — las cuatro, por la vía recomendada

El propietario decidió las cuatro desde fuera de casa, sin poder ejecutar nada;
lo que sigue es lo que se hace con cada una **sin él**:

| decisión | qué eligió | qué se hace ahora |
|---|---|---|
| **H5 — `DEC-001`** | restaurar los miembros de la lista cerrada **y** pasar `G4` de contención a pertenencia | **encargo**, auditado contra el árbol antes de lanzar |
| **H3 — `MEM-020`** | sí: lo no confirmado de fuente externa **sale, marcado como no confirmado** | **encargo**, con la parte de presentación como diseño explícito |
| **H4 — `MEM-001`** | sustituir la subcadena «contexto» por una **señal explícita** | **encargo**, el más pequeño; primero |
| **Ejes** | sí **en principio**: guardarlos; formalizar por el Rector | **no se lanza**: es cambio de esquema y §17 del Rector exige definición y arquitectura aprobadas. Se prepara la nota para ese proceso |

Lo que **no** cambia con esto: la puerta `category_matching_enabled` sigue
cerrada; el modelo mayor y la prioridad de la línea siguen siendo decisiones
suyas; y la medición con Ollama real sigue caducada desde el 02-09 y solo la
puede correr él.

---

# DECIDIDA el 12-09-2026 — (A) SÍ se acepta perder por uno el suelo de «elementos de más»

> El propietario eligió **(A) aceptar**. Queda registrada en la incidencia #582
> como comentario `DECISIÓN DEL PROPIETARIO` antes de cualquier fusión. Lo que
> sigue es el informe con el que se decidió.

## El informe original

**Qué ha pasado.** La PR de H5 (#583, ADR-170) hace exactamente lo que
decidiste: los miembros de la lista cerrada vuelven al corpus, portados del
origen, y `G4` decide por pertenencia. La predicción se cumple al dígito
(`--ejes --peticion`: `21/47; 144; 78/81; 0` → `22/47; 146; 79/81; 0`; el
control `--peticion` intacto). **El precio, medido**: `DEC-001` entra también
en `B04-CA-43` («¿Quién valida los entregables de calidad?», ámbito
`PRJ-ALFA`, miembro de la lista), donde no se le espera. En el arnés del motor
portado eso lleva «elementos de más» de 21 a 22 sobre la población del umbral
D1, y **el suelo D1 (≤21), alcanzado desde ADR-115 el 31-08, deja de
alcanzarse por uno.** La PR no lo maquilla: lo dice en el ADR, en el cuerpo de
la PR y en la prueba, y lo deja para ti.

**Lo que no te dije antes de que decidieras, y debí**: que la pertenencia
podía costar ese suelo. No lo medí; lo midió la implementación. Por eso esta
decisión es nueva y no está incluida en la del 11-09.

**Tres matices que pesan** (verificados por mí sobre el head `3b64c55f`):

1. El 22 sale de un arnés **sin filtro de relevancia**: usa el veredicto
   congelado del laboratorio ítem a ítem y **deja pasar lo que el laboratorio
   nunca examinó**. `DEC-001` en `B04-CA-43` es exactamente eso. En el único
   caso donde el laboratorio sí lo examinó (`B04-CA-14`), su filtro lo quitó.
   Si el filtro real lo quitaría en `B04-CA-43` solo lo mide Ollama en tu
   máquina (`scripts/medir_banco_con_ollama_real.py --diagnostico`), y esa
   medición está caducada desde el 02-09. No se puede afirmar en ningún
   sentido.
2. El 21 lo publicó una corrida del laboratorio que en `B04-CA-22` recuperaba
   **uno de seis** y que no traía `DEC-001` en ningún caso. El motor portado
   ahora recupera los seis ahí. Ya no se persigue «igualar al laboratorio»:
   tu decisión lo hace divergir a propósito.
3. El encargo dejó «de más» sin listón a propósito, pero el suelo D1 es una
   cota publicada aparte (ADR-113/115; la Arquitectura 0.2 dice que M17 la
   evalúa «registrando el resultado real —alcanzado o no— sin maquillarlo»).
   Aceptar la regresión es coherente con ese texto; lo que no sería
   aceptable es no decirlo, y la PR lo dice.

**Opciones**

- **(A) Aceptar** — *recomendada*. El suelo de «elementos de más» queda
  formalmente «no alcanzado desde ADR-170, por uno, por un ítem nombrado». Se
  fusiona #583 cuando el ciclo cierre. Coste real: uno, y visible. Lo que te
  compra: la semántica que decidiste, y `B04-CA-22` completo.
- **(B) Aceptar con condición**: que la prueba que hoy se llama «alcanza el
  suelo D1» diga en su nombre lo que afirma (que no lo alcanza). Es (A) más
  una corrección de forma, que puede salir de la revisión o quedar como
  deuda. No la he inyectado al ciclo.
- **(C) No aceptar.** Entonces H5 no puede fusionarse como está, porque el
  extra es consecuencia necesaria de «pertenencia»: cualquier ámbito miembro
  recibe `DEC-001` cuando su texto coincide. Mantener el 21 exige o volver a
  contención (deshacer tu decisión) o un listón sobre «de más» que el encargo
  prohibió. (C) es revertir el 11-09, no afinarlo.

**Lo que hago sin ti**: acompañar el ciclo hasta `ready-for-merge` y **no
fusionar** sin tu sí. Te lo pregunto cuando el ciclo cierre, con las cifras
del head final.

---

# DECIDIDA el 12-09-2026 — (A) NO se paga `MEM-001` en `B04-CA-30`

> El propietario eligió **(A) dejarlo**: queda como hueco medido, con su precio
> escrito, reabrible el día que haya una señal más fina que el propósito. El
> encargo recortado de #581 ya estaba escrito para no cambiar qué peticiones
> activan la ampliación, así que no hay que tocarlo.

## El informe original

**Qué ha pasado.** El primer intento de H4 (#581) murió a los 60 minutos sin
dejar nada. Antes de relanzarlo medí lo que el encargo daba por hecho: que
existía una regla de activación que recuperase `MEM-001` en `B04-CA-30`
(`responder_al_usuario`) sin empeorar el banco. **No existe entre las reglas
de clase de propósito.** Sobre `main` (`5fc5fdc`), etapa de búsqueda con
peticiones reales, cambiando solo la regla en el consumidor real:

| regla | sin ejes | con ejes |
|---|---|---|
| hoy (subcadena «contexto») | 17/47; 162; 78/81; 0 | 21/47; 144; 78/81; 0 |
| `responder_al_usuario` o la de hoy | 7/47; 309; 79/81; 0 | 8/47; 293; 79/81; 0 |
| siempre | 0/47; 368; 79/81; 0 | 0/47; 352; 79/81; 0 |

`MEM-001` entra con las dos reglas nuevas; el precio es pasar de 17 a 7
exactas y de 162 a 309 elementos de más (sin ejes), por un hallado más.

**Lo que hice sin ti.** Relancé H4 recortado a lo que decidiste —la señal
explícita, sin subcadena— **sin cambiar qué peticiones la activan hoy**. Su
predicción es que el banco no se mueve. Eso cierra el mecanismo; no cierra
`B04-CA-30`.

**Opciones**

- **(A) Dejarlo así** — *recomendada ahora*. `MEM-001` en `B04-CA-30` queda
  como hueco medido y nombrado: recuperarlo cuesta lo de la tabla. La
  adjudicación del corpus lo espera, pero ninguna regla de clase lo paga.
- **(B) Pagarlo con una regla de clase**: activar la ampliación para
  `responder_al_usuario`. Es la fila 2 de la tabla, y la etapa de búsqueda no
  es lo que se entrega (el filtro quita después), pero el filtro real solo lo
  mide Ollama en tu máquina. No lo recomiendo sin esa medición.
- **(C) Buscar una regla más fina** que no dependa del propósito: los otros
  campos declarados de la petición (modo, cardinalidad, permiso) o la
  intención que infiere el intérprete de ADR-164. **No está medido.** Si lo
  quieres, mido primero cuántos casos separa cada campo y qué cuesta, y solo
  después se escribe un encargo.

Si no dices nada, sigue (A): H4 cierra el mecanismo y `B04-CA-30` queda en la
lista de huecos con su precio escrito.

---

# Cuatro decisiones tuyas, y una consecuencia que cambia el criterio de la línea

**Estado al 08-09-2026, 18:50 UTC.** Nada de esto bloquea el trabajo: la
palanca 3 puede lanzarse sin que decidas ninguna. Lo que sí decides es **hasta
dónde puede llegar la línea de memoria**, y esa parte ya no depende de
ingeniería.

## La consecuencia, primero, porque es la que importa

Tras H1, **la etapa de búsqueda** da `17/47 exactas; 162 de más; 78/81
hallados; 0 críticas perdidas` (medido por mí sobre el head de H1,
reproduciendo la PR al dígito).

**Cuidado con esa cifra, y lo digo porque yo mismo la usé mal hace un rato**:
sale del diagnóstico que imprime `SIN FILTRO`, o sea **sin el filtro de
relevancia**. Es el **techo que el filtro recibe**, no lo que el sistema
entrega. La vía completa la mide otro test, y su fila final publica `29/47; 50;
0; 63/81`, que **ya alcanza el suelo D1** (`29/47, ≤21, ≤1, ≥63/81`). Tu
criterio para abrir la puerta es mucho más estricto que D1 —`47/47`, `0` de
más, `81/81`, `0` críticas, con Ollama de verdad— y ésa es la medición que
manda.

**Una condición más sobre esa cifra, descubierta en la ronda 2 de H1 y que
también afecta a lo que puedas concluir de ella**: en el banco, el cargador
escribe `ejes_p2.valid_from` dentro de `created_at`, así que las dos son la
misma fecha ítem a ítem. Cualquier medición apoyada en `created_at` **parece
medir vigencia y mide registro**, porque en producción `created_at` lo pone el
reloj al proponer. No invalida ninguna cifra; invalida leerlas como prueba de
que el motor entiende la vigencia. Está en la bitácora como deuda 27, y es de
toda la línea, no de H1.

**Las tres ocurrencias que faltan son las tres decisiones de abajo.** Ninguna
es trabajo pendiente de nadie. Y esto **no** depende de qué medición se mire:
el filtro solo puede quitar, nunca añadir, así que lo que falta en el techo
falta también abajo. O sea:

> **La columna de «hallados» está terminada por parte del ciclo. `81/81` no se
> alcanza escribiendo código: se alcanza decidiendo tres cosas.**

Lo que sigue abierto a trabajo son **exactas** y **de más**, y a eso apunta la
palanca 3.

---

## 1. H5 — `DEC-001`: la lista cerrada perdió sus miembros al portar el corpus

**Nueva hoy. ADR-148 no la nombra**: se contaba dentro de los cinco de H1, y H1
demostró midiendo que no era de vigencia sino de ámbito.

**Crédito donde toca**: el veredicto exacto de la puerta lo identificó el
implementador de H1, leyendo los seis ítems uno a uno —su parte cita literal
«lista cerrada sin miembros resueltos» con ejes—, y lo dejó registrado caso a
caso en ADR-168. Lo que añado yo son las dos cosas de abajo: que **el origen sí
declaraba la pertenencia** y el porte la perdió, y que **aun teniéndola `G4`
seguiría excluyéndolo**. Lo primero convierte «el corpus está incompleto» en
«nuestro porte perdió un dato»; lo segundo dice que arreglar solo el dato no
bastaría.

`B04-CA-22` («¿Qué decisiones eran válidas entre enero y marzo?», ámbito
`PRJ-BETA`) espera seis decisiones. Entran cinco. `DEC-001` no entra **en
ninguna configuración**, ni siquiera con los ejes del corpus inyectados, así
que no es el problema de la palanca 2.

**Son dos capas, y las dos hay que resolverlas para que entre:**

- **El dato no llega.** `DEC-001` es el único ítem `MULTI_PROYECTO_CERRADO` de
  los 97, con `project: LISTA-CERRADA-AB`. La fixture portada **no tiene campo
  de pertenencia** —ninguna clave con «miembro» en ningún ítem—, así que `G4`
  se niega con la razón correcta: «lista cerrada sin miembros resueltos: la
  duda no abre ámbito». **Y el dato existía en el origen**: la adjudicación de
  la rama `evidence/adr001-spikes` (commit `dfdcdaff`, el que la fixture cita
  como fuente) dice literalmente **«pertenece a LISTA-CERRADA-AB; Gamma no es
  miembro y no hereda»**. La semántica del origen es deliberada; se perdió al
  portarla.
- **Y aunque llegara, `G4` seguiría excluyéndolo.** Su rama multiproyecto exige
  `all(...)` —**contención**: «no te enseño algo que también vive en un
  proyecto que no puedes ver»—, y lo que el origen describe es
  **pertenencia**. Simulado con los miembros que el origen implica:

  | caso | `all()` | `any()` | lo que el origen dice |
  |---|---|---|---|
  | `B04-CA-22`, ámbito `PRJ-BETA` | **False** | **True** | debe entrar |
  | caso con ámbito Gamma | False | False | no debe entrar |

  `any` reproduce la adjudicación en los dos sentidos; `all` falla el positivo.

**Por qué es tuya y no mía.** La primera capa toca la fixture del banco, que
tengo prohibido modificar —y la prohibición es buena: si yo pudiera añadir
datos al corpus, el banco dejaría de ser un juez—. La segunda cambia una regla
con forma de privacidad, y `all` no es un descuido: es una postura
conservadora, la misma que «la duda no abre ámbito».

**Opciones**: (a) que el porte lleve la pertenencia como dato **y** `G4` pase a
intersección — es lo único que llega a `81/81`; (b) aceptar `80/81` como techo
y reescribir el criterio de la línea; (c) que la puerta derive los miembros del
nombre `LISTA-CERRADA-AB`, que es inventarse datos — **no la recomiendo**.

## 2. H3 — `MEM-020`: ¿lo CANDIDATA de fuente externa se recupera?

`B04-CA-29` («¿Cuál es el plazo legal de entrega?», ámbito `PRJ-ALFA`) espera
solo `MEM-020`: «La fuente externa afirma que el plazo legal de entrega es de
30 días». **No entra nada en absoluto**, aunque la coincidencia léxica es
perfecta.

**Mecanismo, comprobado**: `_vigente` del arnés exige las tres a la vez, y la
primera es `confirmacion == "CONFIRMADA"`. `MEM-020` es **`CANDIDATA`**
(`autoridad: FUENTE_EXTERNA`), así que se carga como **no vigente** y nunca
llega a ser candidata. No es la ordenación ni una puerta: es el modelo.

**Medido** (sonda que trata lo candidato como vivo; ancla anterior a H1, suelo
de entonces `17/47; 162; 74/81; 0`): pasa a **`17/47; 165; 75/81; 0`**. O sea
**+1 hallado a cambio de +3 de más**, sin perder críticas.

**La pregunta es de producto, no de motor**: ¿tiene Sirius sitio para una
memoria **no confirmada** de fuente externa, y debe salir cuando el usuario
pregunta directo? El corpus dice que sí. Si la respuesta es «sí pero marcada
como sugerencia», eso es diseño y hay que encargarlo aparte.

## 3. H4 — `MEM-001`: la ampliación depende de que un texto libre contenga «contexto»

El detalle completo está en `decision_h4.md`. En corto:

- `B04-CA-30` espera `DEC-003`, `MEM-001` y `MEM-016`; entran dos.
- `MEM-001` **no llega por la búsqueda**: llega por la ampliación por categoría
  (M14), que corre solo si `category_matching_enabled` **y**
  `pide_contexto(proposito)`.
- `pide_contexto` es una **comprobación de subcadena**: `"contexto" in
  proposito.casefold()`. El propósito de la política uniforme contiene
  «contexto»; el que el caso declara, `responder_al_usuario`, no.
- **Toda la diferencia es esa subcadena**, y decide si se enciende un camino de
  recuperación entero. Es la deuda 2 en un sitio con mucho más peso.

Además exige `category_matching_enabled`, que es **la puerta final de la
línea**: hoy cerrada en producción, y `MEM-001` es inalcanzable por ese camino
mientras lo esté, sea cual sea el propósito.

## 4. La pregunta de esquema que dejó la palanca 2

La palanca 2 se cerró con negativo medido: derivar los ejes de las columnas de
hoy **empeora** el suelo, y con los ejes puestos su rama y `main` dan
exactamente lo mismo — o sea que **el andamiaje ya existe y lo que falta son
los ejes**. La distancia entre lo derivado y lo declarado quedó en **5 exactas
y 20 de más**.

La pregunta que eso deja no es una palanca: **¿se guardan esos ejes en el
esquema en vez de derivarlos?** Es una decisión sobre el modelo de datos. La
rama `feature/ejes-derivados-en-el-puerto-real` no se ha borrado.

Y nótese que **H5 es la misma pregunta en pequeño**: un eje que el origen
declara y el esquema portado no guarda.

---

## Lo que hago mientras no decidas

Nada de esto me para. Sigo con la palanca 3 en cuanto H1 se fusione; su encargo
ya está auditado contra el árbol y corregido.
