# Decisiones abiertas del propietario — al cierre del 20-09-2026

Las deudas de la bitácora son 44 y están mezcladas: unas son trabajo mío, otras
esperan una incidencia, y **cinco son decisiones que sólo puede tomar Andy**.
Esta hoja es únicamente esas cinco, con lo que mueve cada una y lo que cuesta.

**Ninguna está tocada.** Ninguna se toca sin que él lo diga.

Donde tengo una lectura fundada la escribo, marcada como **lo que dice la
evidencia** y separada de **lo que sólo puede pesar él**. La segunda parte no la
decido yo en ningún caso.

---

## D-1 · ¿Es un fallo entregar una crítica que no se pidió? *(deuda 43)*

**El choque.** El banco puntúa `aciertos_exactos`: el conjunto entregado tiene
que ser **idéntico** al esperado. ADR-128 manda entregar toda identidad
protegida que entre. Las dos reglas no pueden cumplirse a la vez.

| con la regla de hoy | perdonando **sólo** el exceso protegido |
|---|---|
| **29/47** | **36/47** |

Mismo sistema, mismo filtro, mismo día. **Siete casos** no les falta nada y no
meten basura: meten la crítica que el diseño les manda meter.

**Lo que dice la evidencia.** El exceso que *nadie* decidió es minúsculo: **2
casos y 17 elementos**, quince de ellos en `CA-35`. No hay un problema de ruido
escondido detrás de esta pregunta.

**Lo que sólo puede pesar él.** Qué le pasa a una persona real cuando Sirius le
saca una restricción esencial que no había pedido. Si le estorba, la regla de
hoy tiene razón y ADR-128 es demasiado caro. Si es justo lo que quiere, la regla
está llamando fallo a un acierto. **Eso no está en ningún fichero.**

**Es la primera de las cinco** porque las otras cambian de sentido según cómo se
resuelva.

---

## D-2 · ¿Qué cuenta como «protegida»? *(deudas 40 y 42, que son la misma)*

Hoy: `criticality is not None` — CRÍTICO **o** IMPORTANTE (19 identidades de 97).

| qué se protege | medido | techo |
|---|---|---|
| CRÍTICO + IMPORTANTE (hoy) | 29/47 | 34/47 |
| **sólo CRÍTICO** | **31/47** | **37/47** |

Lo mueve **una condición de una línea**. Los tres casos que desbloquea
(`CA-02`, `CA-26`, `CA-31`) los bloquea un único elemento: `MEM-001`, «prefiero
que redactes en tono directo y sin adornos» — **una preferencia de estilo
tratada como restricción protegida**.

**Lo que dice la evidencia.** Coste medido: **cero**. Donde `MEM-001` se espera,
el filtro la conserva igualmente. **Y ese cero no vale**: el banco tiene **una
sola** identidad IMPORTANTE, y un banco con un ejemplar de una clase no puede
medir una regla sobre esa clase.

**Lo que sólo puede pesar él.** ADR-128 eligió proteger las dos a propósito. Y
antes de decidir haría falta un banco con más de una IMPORTANTE — **que no
existe**. Mi lectura: esta decisión **no está madura**, y pedirla hoy sería
pedirle que apueste a ciegas.

**Si D-1 se resuelve perdonando el exceso protegido, D-2 desaparece**: el
candado deja de ser un techo.

---

## D-3 · La política de `limite.n` de los casos `ACOTADA` de tipo OBJETIVO *(deuda 38)*

Que «Prepara el contexto de planificación de Alfa» valga **10** no es inferible
de la pregunta: es política de producto, y no consta en ningún sitio. El banco
la declara y el intérprete no puede adivinarla.

**Lo que dice la evidencia.** Sin esa política, esos casos son **inalcanzables
para cualquier intérprete** y además distorsionan la medida del filtro
(`CA-34` aportaba 7 de los 11 «descartes» que me hicieron escribir que el filtro
no era seguro; no lo era el filtro, era el caso). Y `CA-30` enseña que la `n`
también decide **dónde para la búsqueda**: con `n=3` para en cuatro candidatas y
pierde `MEM-001`, que entra sin problema en otros siete casos.

**Lo que sólo puede pesar él.** Cuál es la política. No hay forma de deducirla.

---

## D-4 · El umbral de D7 punto 6 *(deuda 39)*

**Ya no está bloqueado**: la medición que faltaba existe — **49/95**.

**Lo que dice la evidencia.** Ese 49/95 mide **coincidencia con la regla de
palabras clave de ADR-116**, no con un criterio de producto. Es decir: mide
cuánto se parece el modelo a una regla vieja, no cuánto acierta.

**Lo que sólo puede pesar él.** Qué umbral quiere, sabiendo eso.

---

## D-5 · `B04-CA-29` no lo puede ganar nadie *(deuda 44)*

El caso espera `MEM-020`. `MEM-020` declara `confirmacion: "CANDIDATA"`, así que
el cargador la crea y **la archiva acto seguido**; archivada deja de ser
`CURRENT` y la recuperación no la ve nunca. **Entra en 0 de 47 casos** en las
tres configuraciones.

**Lo que dice la evidencia.** Es una contradicción **dentro del banco**: la
adjudicación espera un elemento que los campos de estado del mismo banco
declaran no vigente. Mientras no se resuelva, **el banco tiene un caso de 47 que
nadie puede ganar, nunca**, y el denominador real es 46.

**Lo que sólo puede pesar él.** Cuál de las tres está mal: el
`resultado_esperado` del caso, la `confirmacion` de `MEM-020`, o la regla «una
candidata no entra» —y en ese último caso el caso estaría probando algo bueno:
que Sirius sepa responder con lo no confirmado **marcándolo como tal**.

**No toco el corpus ni las adjudicaciones**, por regla dura y porque mover
cualquiera de las tres cambia la cifra sin que el sistema mejore.

---

## Y una que no es decisión, es un gesto

**#653 está en `ready-for-merge`** desde las 19:38, aprobada por los dos
revisores sobre `ca847501`, con la puerta previa corrida y publicada (pasa las
cinco comprobaciones). Espera un `fusiona` en un comentario de **la incidencia**.

Detrás van **dos encargos preparados, validados y sin lanzar**:

| encargo | qué hace | cuándo |
|---|---|---|
| `WI-20260920-MODO-Y-CORTE` | alinea `modo` y `corte_de_registro` con B04 §5; se lleva `CA-32`, uno de los cinco ganables | cuando #653 sea terminal |
| `WI-20260920-PERFIL-AL-ESCRIBIR` | que un cuerpo sin `Perfil: rol@N` se rechace **al escribirlo** en vez de matar el ciclo a los 6 segundos, como pasó con #653 | cuando él diga |

Los dos pasan **las dos** comprobaciones —`validate_issue_body.py` y
`resolver_prompt.py`—, que es la regla que #653 me enseñó por las malas.
