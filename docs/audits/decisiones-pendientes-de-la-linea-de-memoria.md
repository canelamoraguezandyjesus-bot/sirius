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
