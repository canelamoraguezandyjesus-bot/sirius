# SIRIUS 0.2 — ADR-002 · Ronda primaria repetida: contraste y recomendación final

**Versión:** 1.0
**Estado:** **EJECUTADA · contrastada · ninguna alternativa elegida**
**Fecha:** 7 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**

**Autoridad:** `SIRIUS_0.2_ADR_002_REAPROBACION_SUCESORAS_TRAS_CORRECCION_v1.0.md`.

**Artefactos:** `ronda_primaria_v0.2.json` y `ronda_primaria_v0.2_evidencia.json`.
La corrida `v0.1` **se conserva íntegra**: sin ella, la corrección sería una
promesa en vez de una diferencia medida.

---

## 1. La repetición fue el mismo acto sobre otro código

Mismo arnés, sin tocar: once sesiones en once procesos, cien repeticiones tras
diez de warm-up descartadas, una pasada completa por los cincuenta casos, orden
intercalado y rotado, semilla `20260726`, reloj `time.perf_counter_ns`, el mismo
fichero para los cinco. **1 100 muestras por participante.** Válida a la
primera: la repetición única del §6.8 no llegó a ejercitarse, y los diez
controles internos salieron en verde.

Lo único que cambió entre las dos corridas es lo que la corrección cambió, y las
fichas lo declaran: `A` v6, `B` v8, `C` v3, `D` v3.

---

## 2. Contraste `v0.1` → `v0.2`

| | Contaminación | Fuga | **Fusión** | Lectura invertida | Etapa | Exactos |
|---|---|---|---|---|---|---|
| `T0-control` | 16 → **16** | 1 289 → **1 289** | 2 480 → **2 480** | 0 → **0** | 0/46 → **0/46** | 1/47 → **1/47** |
| `ADR002-A` | 5 → **3** | 0 → 0 | 38 → **0** | 66 → **0** | 30 → **32**/46 | 20 → **23**/47 |
| `ADR002-B` | 5 → **3** | 0 → 0 | 38 → **0** | 66 → **0** | 29 → **30**/46 | 19 → **21**/47 |
| `ADR002-C` | 5 → **3** | 0 → 0 | 38 → **0** | 66 → **0** | 30 → **32**/46 | 20 → **23**/47 |
| `ADR002-D` | 5 → **3** | 0 → 0 | 38 → **0** | 66 → **0** | 29 → **30**/46 | 19 → **21**/47 |

**La puerta de confusión de polaridad pasa a verde para los cuatro.** Era una de
las tres de fallo duro.

### 2.1 El control no se movió ni un dígito

`T0` da **exactamente** las mismas cifras en las dos corridas, hasta el último
recuento. No es una casualidad afortunada: las tres correcciones viven en la
capa que los candidatos usan y `T0` no usa ninguna, de modo que su invariancia
es la comprobación de que la corrección **no se filtró al control**. Si `T0`
hubiera cambiado, habría que sospechar del arnés antes que de los candidatos.

### 2.2 La latencia no pagó por la corrección

| | `v0.1` `P50` | `v0.2` `P50` |
|---|---|---|
| `T0-control` | 1 570–1 734 ms | 1 540–1 705 ms |
| `ADR002-A` | 226,5–251,4 ms | 221,5–261,5 ms |
| `ADR002-C` | 225,5–246,7 ms | 222,6–259,0 ms |
| `ADR002-D` | 238,6–268,3 ms | 234,7–293,3 ms |
| `ADR002-B` | 245,3–273,4 ms | 241,1–290,3 ms |

Las bandas se solapan por completo con las de la corrida anterior. Leer el
alcance de una negación en vez de su presencia, y consultar dos ejes más por
elemento, **no cuesta tiempo medible**.

---

## 3. Lo que sigue en rojo, y por qué

Dos de las cinco puertas siguen sin pasar para todos.

### 3.1 Contaminación: **3**, y son los dos casos declarados no corregibles

Los cuatro contaminan lo mismo, en dos casos, y son exactamente los que el
paquete de corrección declaró que **no** iba a tocar y por qué:

| Caso | Qué aparece | Por qué no se corrigió |
|---|---|---|
| `B04-CA-04` | `MEMORIA:906`, `MEMORIA:925` | son `DISTRACTOR_RUIDO`: llevan los términos de la consulta y sus ejes son los de un elemento legítimo. Lo único que los distingue es una etiqueta de la adjudicación, que es **oráculo** |
| `B04-CA-05` | `DECISION:3` | el caso espera que `M2` **excluya** la decisión vigente. `M2` está definido como el modo que **admite** las no vigentes; que además excluya las vigentes es una lectura más fuerte que no encuentro escrita |

La tercera contaminación de `v0.1` —`MEMORIA:112`, vigente desde mayo en una
consulta de abril— **desapareció**: la puerta del tiempo la detiene.

### 3.2 Conformidad de etapa: 32/46, y la mayoría son resoluciones **tempranas**

De los 14 casos no conformes de `A`, once son «resuelto en `E1` y el caso
declara `E3`/`E4`»: el candidato encuentra en la etapa exacta lo que la
referencia esperaba que exigiera expansión. Y **cuatro de esos catorce devuelven
el resultado exacto**.

Eso deja una pregunta abierta que no me corresponde cerrar: cuando un candidato
devuelve **el conjunto correcto** en una etapa **anterior** a la declarada, ¿es
un incumplimiento de `RF-14` o es que la etapa declarada del caso presuponía una
maquinaria concreta? El §6.1 dice que `C-17` es fallo duro «aunque el resultado
final sea correcto», pero se refiere al **salto** —resolver saltándose etapas—,
y aquí no hay salto: hay parada temprana, que es lo que la política escalonada
manda. La instanciación del campo 12 es uno de los defectos que el §0.1 de la
especificación dejó abiertos, y esto lo toca de lleno.

---

## 4. Las señales tardías, con la base ya limpia

La corrección mejoró a los cuatro por igual, de modo que el contraste entre
ellos es ahora **más limpio que antes**, no menos.

### 4.1 La señal relacional sigue sin cambiar **ni un solo resultado**

`ADR002-C` devuelve exactamente lo mismo que `ADR002-A` en los cincuenta casos.
Cero diferencias, igual que en `v0.1`. Latencia indistinguible. Almacenamiento
**cero**.

### 4.2 La señal vectorial ahora rompe **dos** casos que `A` acierta exactos

En `v0.1` rompía uno; con la base corregida, `A` acierta los dos y `B` y `D` los
rompen los dos:

| Caso | `A` y `C` | `B` y `D` |
|---|---|---|
| `B04-CA-08` | **exacto** | añaden `DECISION:13`, que no está en el conjunto esperado |
| `B04-CA-27` | **exacto** | añaden `DECISION:13`, que no está en el conjunto esperado |
| `B04-CA-34` | no exacto | `B` añade además `MEMORIA:25` |

**Ninguna adición del vector está en ningún conjunto esperado, en ninguna de las
dos corridas.** Su aportación medida sigue siendo negativa, y ahora cuesta dos
casos exactos en vez de uno.

### 4.3 El balance completo

| | Exactos | Etapa | `P50` | Almacenamiento |
|---|---|---|---|---|
| `ADR002-A` | **23/47** | **32/46** | 221–262 ms | 1 462 272 B |
| `ADR002-C` | **23/47** | **32/46** | 222–259 ms | **0 B** |
| `ADR002-B` | 21/47 | 30/46 | 241–290 ms | 35 016 704 B |
| `ADR002-D` | 21/47 | 30/46 | 235–293 ms | 35 016 704 B |
| `T0-control` | 1/47 | 0/46 | 1 540–1 705 ms | no declarado |

La condición que el §8 escribió **por adelantado** para `AB-3` se cumple dos
veces seguidas, sobre dos bases distintas:

> «Si desactivar la señal tardía no degrada materialmente ninguna métrica de
> puerta, `ADR002-A` no es un control degradado: **es la respuesta**.»

Y la puerta 7 —«el coste adicional no produce mejora material»— actúa **a favor
de `A`**, como el §9 previó.

### 4.4 Lo que esto **no** demuestra

Sigue sin demostrarse, y lo repito porque es lo más fácil de olvidar cuando dos
corridas dicen lo mismo: **este corpus tiene diez relaciones**. Que `C` no cambie
ni un resultado describe la superficie relacional del banco tanto como al
candidato. Las pruebas funcionales de `C` y `D` **sí** exhiben el discriminante
relacional, sobre un fixture construido para exhibirlo.

- **Demostrado**: sobre el corpus de conformidad vigente, y con la capa común ya
  corregida, ninguna señal tardía paga su coste, y la vectorial resta.
- **No demostrado**: que ocurriría lo mismo sobre un corpus con densidad
  relacional realista, que este benchmark no tiene.

---

## 5. Recomendación final

**Recomiendo `ADR002-A`, y recomiendo no cerrar `ADR-002` todavía.**

No son contradictorias, y esta es la razón de cada una.

### 5.1 Por qué `ADR002-A`

1. **Iguala o supera a las otras tres en todas las métricas**: mismas cinco
   puertas, más resultados exactos que `B` y `D`, empatada con `C`, y mejor
   conformidad de etapa que `B` y `D`.
2. **Con la menor maquinaria.** `C` empata con ella y consume menos
   almacenamiento —cero frente a 1,4 MB—, pero **no aporta nada** que `A` no
   tenga: cero diferencias en cincuenta casos. Entre dos que hacen lo mismo, la
   que tiene menos partes es la que hay que preferir, y la señal relacional de
   `C` es una parte que no se ha visto actuar.
3. **La evidencia contra las señales tardías es doble**, sobre dos bases
   distintas, y en la segunda es más fuerte que en la primera.

### 5.2 Por qué no cerrar todavía

**Ninguna alternativa pasa las cinco puertas**, y las puertas son de
cumplimiento obligatorio. Recomendar a `A` no es declararla conforme: es decir
que, de las cuatro, es la que mejor responde y la que menos cuesta. Cerrar
`ADR-002` con una alternativa que no pasa las puertas sería aprobar por
comparación lo que el contrato exige aprobar por cumplimiento.

Lo que queda en rojo **no es de los candidatos**:

- las dos contaminaciones que restan son un caso que parece no superable sin el
  oráculo y otro que pide una lectura de `M2` que no está escrita;
- la conformidad de etapa depende de una instanciación del campo 12 que la
  propia especificación declara incompleta.

Las tres son cuestiones **del banco y del canon**, no de la arquitectura.

### 5.3 El siguiente movimiento único que se recomienda

Resolver esas tres preguntas —dos del corpus y una de `B04`—, y **no** repetir
la ronda hasta tenerlas resueltas: una tercera corrida sobre las mismas
preguntas abiertas daría las mismas cifras y no añadiría nada.

---

## 6. Solicitud única

> **¿Se aprueba `ronda_primaria_v0.2` como evidencia, se acepta la
> recomendación de `ADR002-A` como alternativa preferida sin declararla
> conforme, y se autoriza abrir el paquete que resuelva las tres preguntas
> abiertas —los dos distractores de `CA-04`, la lectura de `M2` de `CA-05` y la
> etapa declarada del campo 12— antes de cerrar `ADR-002`?**

Hasta que eso se decida no se elige alternativa en firme, no se cierra
`ADR-002`, no se empieza otro ADR y no se fusiona el PR #117.
