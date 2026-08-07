# SIRIUS 0.2 — ADR-002 · Niveles 2 y 3 del banco, ejecutados

**Versión:** 1.0
**Estado:** **BANCO COMPLETO · ninguna alternativa elegida · `ADR-002` sigue sin poder cerrarse**
**Fecha:** 7 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**

**Autoridad:** el usuario, sobre la solicitud única del §8 de la corrección de la
recomendación: «**Si venga**».

**Artefacto:** `artifacts/adr002_round/niveles_2_y_3_v0.1.json`.

---

## 1. Qué faltaba, y ahora no

El banco tiene cuatro niveles. La ronda primaria ejecutaba **uno**:

| Nivel | Qué es | Cuándo se ejecutó |
|---|---|---|
| 1 | 50 casos canónicos `B04-CA-01..50` | las corridas `v0.1` y `v0.2` |
| 2 | 5 casos arquitectónicos `ARQ-CA-01..05` | **aquí**, los cinco |
| 3 | 7 ablaciones `AB-0..AB-6` | **aquí**, cuatro de siete |
| 4 | 1 discriminante relacional `N4-01` | el documento anterior |

Con esto el banco queda ejecutado salvo **tres ablaciones**. Una de ellas,
`AB-2`, no es que no se pueda: es que **la norma la prohíbe**. El §6 lo explica.

---

## 2. Nivel 2 · los cinco casos arquitectónicos

| | `ARQ-CA-01` regenerar | `ARQ-CA-02` purgar | `ARQ-CA-03` estabilidad | `ARQ-CA-04` ficha | `ARQ-CA-05` coste |
|---|---|---|---|---|---|
| | *puerta 5* | *puerta 5* | *puerta 4* | *puerta 7* | *puerta 7* |
| `T0-control` | PASA | n/a | PASA | n/a | n/a |
| `ADR002-A` | PASA | n/a | PASA | PASA | PASA |
| `ADR002-B` | PASA | **PASA** | PASA | PASA | PASA |
| `ADR002-C` | PASA | n/a | PASA | PASA | PASA |
| `ADR002-D` | PASA | **PASA** | PASA | PASA | PASA |

**Ninguna puerta nueva en rojo.** Las puertas 4, 5 y 7 quedan verdes para los
cuatro candidatos, medidas y no supuestas.

### 2.1 Lo que cada casilla significa de verdad

- **`ARQ-CA-01`** no es la puerta 5 que ya se midió. La ronda la adjudicaba con
  **un** ciclo y **solo** sobre el sidecar de `B` y `D`. Este caso pide **30/30**
  y habla de «todo índice derivado», y el `FTS5` —tablas virtuales, tablas sombra
  y triggers— **es** un índice derivado que los cinco usan. Aquí se ejecutan los
  30 ciclos completos sobre el `FTS5` de los cinco, y además sobre el sidecar de
  `B` y `D`. Es la comprobación que la ronda nunca hizo.
- **`n/a` no es un aprobado.** `A` y `C` no construyen índice derivado propio: no
  hay nada que purgar. Se registra `NO_APLICABLE`, no `PASA`, porque colapsarlo
  en aprobado sería regalar una puerta a quien no se presentó a ella. Y en la
  comparación **juega a favor de `C`**: no tener derivado propio es la forma más
  fuerte de que su purga sea completa.
- **Las tres `n/a` de `T0`** salen de exenciones que **su ficha ya declaraba antes
  de medir** —`limites_del_ciclo_de_indice`, `limites_locales_por_etapa`—, y se
  citan literalmente en el artefacto. No se le castiga por ser el control ni se
  le aprueba por serlo.

---

## 3. Nivel 3 · las ablaciones, y lo que enseñan

| Ablación | Qué apaga | `T0` | `A` | `B` | `C` | `D` |
|---|---|---|---|---|---|---|
| — | *nada (corridas publicadas)* | 1 | **23** | 21 | **23** | 21 |
| `AB-1` | todo salvo `E0`/`E1` | 1 | **24** | **24** | **24** | **24** |
| `AB-3` | la señal tardía | 1 | 23 | **23** | 23 | **23** |

(aciertos exactos sobre los 47 casos adjudicables)

`AB-6` no aparece en la tabla porque **no depende del participante**: es el azar,
y da **18/47** para cualquiera. Se emite una vez, no cinco veces la misma cifra.
El §3.3 lo desglosa.

### 3.1 El resultado que no esperaba: expandir **resta**

**`AB-1` —solo `E0` y `E1`— acierta más que el recorrido completo.** Los cuatro
candidatos suben a `24/47` cuando se les prohíbe pasar de `E1`.

| | Gana al restringirse a `E1` | Pierde |
|---|---|---|
| `A`, `C` | `CA-14`, **`CA-25`** | `CA-38` |
| `B`, `D` | `CA-08`, `CA-14`, **`CA-25`**, `CA-27` | `CA-38` |

Los cinco casos que se mueven **tienen contenido**: ninguno es de los dieciséis
que esperan el conjunto vacío, de modo que esto **no** es el artefacto de «quien
devuelve menos acierta más ausencias». Se comprobó expresamente porque era la
explicación alternativa obvia.

**Y `CA-25` es uno de los dos casos que mantienen roja la conformidad de etapa.**
La readjudicación concluyó, leyendo la traza, que `CA-25` declara `E1` y se
resolvió en `E3`, expandiendo de más. La ablación lo confirma **por otro camino**:
si se le prohíbe pasar de `E1`, lo acierta. Dos instrumentos independientes —la
traza de etapas y la ablación— señalan la misma causa.

`CA-38` es la excepción legítima: declara `E5`, y necesita el recorrido entero.

### 3.2 La señal vectorial, falsada por tercera vez y ahora aislada

`AB-3` apaga las señales tardías. `B` y `D` **suben** de 21 a 23 y **no pierden
ni un caso**: recuperan `CA-08` y `CA-27`, que la señal vectorial rompía.

Esto ya se había concluido dos veces por comparación entre candidatos. Ahora está
medido **por ablación sobre el mismo candidato**, que es la forma fuerte: no es
que `B` sea peor que `A`, es que **`B` sin su señal es mejor que `B` con ella**.

`C` no gana ni pierde nada al apagar la relacional, exactamente como las dos
corridas dijeron —y sin contradecir el nivel 4, donde esa misma señal es lo único
que resuelve el discriminante.

### 3.3 El suelo, y por qué `23/47` no es lo que parece

`AB-6` da **`18/47` por puro azar**. Antes de leer eso como «los candidatos apenas
superan al azar», el propio suelo se declara **generoso**: recibe la *cantidad* de
elementos que el caso espera, que ningún sistema real conoce. Y de los 47 casos,
**16 esperan el conjunto vacío**, donde conocer la cantidad *es* conocer la
respuesta. Separado:

| | casos de ausencia | casos con contenido |
|---|---|---|
| **suelo del azar** | 16/16 *(por construcción)* | **2/31** |
| `ADR002-A`, `ADR002-C` | 8/16 | **15/31** |
| `ADR002-B`, `ADR002-D` | 8/16 | 13/31 |
| `T0-control` | 0/16 | 1/31 |

La comparación informativa es la columna derecha: **15 de 31 frente a 2 de 31**.
Ahí la maquinaria paga con claridad. El `23/47` de titular mezclaba esa columna
con otra en la que el suelo gana por definición.

*(El `8/16` de ausencia no es nuevo: la ronda ya lo publicó como
`casos_con_ausencia_correcta`. Lo nuevo es el suelo que permite calibrarlo.)*

### 3.4 La métrica de orden **no informa nada** en este banco

En la segunda lectura de `AB-6` —«orden aleatorizado con semilla fija», que es su
texto literal— el azar acierta **19 de 19**. La razón no es la suerte de la
semilla: **17 de los 19 casos que declaran orden tienen un solo elemento**, y en
ellos no existe orden que equivocar. El suelo es del 100 % por construcción.

Conclusión: `casos_con_orden_exacto`, publicada en las dos corridas, **no
distingue a nadie de nada** sobre este banco. No es una cifra falsa; es una cifra
vacía, y conviene saberlo antes de apoyar una decisión en ella.

---

## 4. Lo que esto cambia en la recomendación: **nada, y sigue siendo `ADR002-C`**

| | Nivel 1 | Discriminante `N4-01` | Nivel 2 | `AB-3` | Almacenamiento |
|---|---|---|---|---|---|
| **`ADR002-C`** | **23/47** | **PASA** | 4 PASA + 1 n/a | sin cambio | **0 B** |
| `ADR002-D` | 21/47 | **PASA** | 5 PASA | **+2 al apagarla** | 35 016 704 B |
| `ADR002-A` | **23/47** | falla | 4 PASA + 1 n/a | sin cambio | 1 462 272 B |
| `ADR002-B` | 21/47 | falla | 5 PASA | **+2 al apagarla** | 35 016 704 B |

Los niveles 2 y 3 **no separan a `C` de `D` por puertas**: los dos pasan todo lo
que pasa el otro. Lo que hacen es reforzar por qué `C`:

1. `AB-3` mide, sobre el propio candidato, que la señal vectorial de `D` **resta
   dos casos**. `D` es `C` más algo que solo quita;
2. `C` no tiene derivado propio, de modo que `ARQ-CA-02` no le aplica **por no
   tener superficie que purgar**, que es mejor que purgarla bien;
3. y sigue costando `0 B` frente a los 35 MB de `D`.

---

## 5. Lo que sigue rojo, y sigue impidiendo cerrar

Nada de lo ejecutado aquí abre la puerta que falta:

- **La conformidad de etapa** sigue roja. `CA-25` y `CA-33` expandieron más allá
  de lo declarado y devolvieron mal. `AB-1` acaba de confirmar la causa de `CA-25`
  desde otro ángulo, lo que la hace **más** sólida, no menos.
- **El marcado de `M2`** —lo sustituido vuelve marcado y nunca como actual— sigue
  siendo una obligación canónica **sin métrica**.
- **`AB-4` no se ha podido ejecutar**, y es la ablación que el propio banco
  necesita para separar una señal de su validación.

---

## 6. Las tres ablaciones que no se ejecutaron, y por qué

No se fingieron. Se comprobó **contra el código**, y las pruebas lo fijan para que
la declaración no envejezca en un comentario. Las razones no son la misma:

### 6.1 `AB-2` — la norma prohíbe la ablación que el banco pide

`AB-2` manda «desactivar la etapa léxica de `RF-16`» **conservando las
posteriores**. Eso obliga a saltar de `E1` a `E3`, y **`B04-RF-14` prohíbe
exactamente ese salto**.

El motor lo hace cumplir: en cuanto una etapa no está autorizada,
`stops.parada_por_modo` devuelve `S2` y el bucle de `engine.py` **rompe**. Por
tanto `espacios_autorizados` autoriza **un prefijo** —«recorre hasta aquí»—, no un
conjunto al que quitarle una etapa de en medio.

De modo que `AB-2` no es una carencia del arnés: es una ablación que **solo podría
ejecutar un motor que incumpliese `RF-14`**. `AB-1`, en cambio, sí es un prefijo
—`E0`/`E1` y parar— y por eso sí se ejecuta.

### 6.2 `AB-4` y `AB-5` — falta maquinaria, y añadirla es un acto de gobierno

- **`AB-4`** —«desactivar la validación de polaridad, condición y tiempo
  **manteniendo la señal**»— necesita un interruptor que ningún candidato
  congelado tiene. Los dos que existen, `con_senal_relacional` y
  `con_senal_vectorial`, apagan **la señal entera**, que es justo lo contrario.
- **`AB-5`** —«puertas `G1-G12` desactivadas de una en una»— necesita una máscara
  de puertas que el motor común no tiene: `aplicar_previas` encadena `G1-G10` en
  orden fijo, y `aplicar_g11` y `aplicar_g12` tampoco aceptan selección.

Ejecutarlas exigiría **modificar código congelado y emitir fichas sucesoras**, y
eso es un acto de gobierno, no una decisión del arnés. Cuatro pruebas vigilan las
firmas y el `break` del motor: si alguien añadiese el interruptor, la máscara, o
hiciera que el motor saltara etapas, fallarían y dirían que la declaración ha
dejado de ser cierta.

**`AB-4` es la carencia que más pesa.** Es la única que separa lo que aporta una
señal de lo que aporta el filtro que la limpia. Sin ella no puede afirmarse cuál
de las dos cosas produce el resultado de `C` en el discriminante.

---

## 7. Dos defectos propios, corregidos antes de cerrar

### 7.1 El suelo tenía prestado el oráculo

La primera versión del suelo `AB-6` sorteaba entre los **elegibles del caso**. Como
el banco define para `EXHAUSTIVA` que `resultado_esperado == elegibles_semanticos`,
sacar `n` de `n` devolvía la respuesta **siempre**: el azar acertaba **47 de 47**.

Un suelo del 100 % habría hecho parecer que los candidatos no superan al azar,
cuando lo que pasaba es que al azar se le había prestado el oráculo. Se corrigió
—el universo es el canon entero— y el defecto quedó escrito como prueba.

### 7.2 `AB-2` era `AB-1` con otro nombre

La primera versión pedía `AB-2` con `espacios_autorizados = {E1, E3, E4}`, creyendo
que `E2` se saltaría. Lo que hace el motor es **parar** en `E2`. `AB-2` y `AB-1`
publicaron por eso la misma cifra exacta —`24/47`— y los mismos casos ganados y
perdidos, uno por uno.

**La coincidencia exacta fue lo que lo delató**, y conviene decirlo porque el
número no era absurdo: `24/47` es perfectamente creíble, y de no haber estado
`AB-1` al lado para compararlo, la cifra habría pasado como un resultado. Lo
descubierto al investigarla —que `espacios_autorizados` es un prefijo porque
`RF-14` prohíbe el salto— resultó ser más informativo que la ablación que se
pretendía correr.

---

## 8. Solicitud única

> **¿Se aprueba la ejecución de los niveles 2 y 3 como evidencia, y cuál de las
> dos vías se toma: cerrar `ADR-002` declarando las tres carencias del §5 —etapa
> roja, `M2` sin métrica, `AB-4` no ejecutable—, o levantar la congelación de los
> candidatos para poder ejecutar `AB-4` antes de decidir?**

No se elige alternativa en firme, no se cierra `ADR-002`, no se toca código
congelado y no se fusiona el PR #117.
