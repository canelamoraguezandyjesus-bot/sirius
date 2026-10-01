# El mismo defecto en los demás campos de la instrucción — 20-09-2026

Continúa `hallazgo-b04-15-2-encontrado-el-encargo-se-desbloquea.md`. Con B04
delante, se revisa si el patrón —**nuestra instrucción reduce la definición del
canon**— se repite en los campos que la cardinalidad deja fuera.

**Se repite.** Y explica buena parte de los 23 casos que fallan.

## `modo` — 40/47, siete fallos

B04 §5, «Modos de recuperación y elegibilidad»:

| modo | canon | nuestra instrucción | qué se pierde |
|---|---|---|---|
| **M1 · Ordinario** | «Responder o continuar trabajo **en el tiempo objetivo solicitado**» + «"Ahora" es el valor por defecto» | «responder **ahora** con lo que está vigente. Es el modo por defecto» | confunde el **valor por defecto** con la **definición** |
| **M2 · Histórico explícito** | «Consultar qué era válido, qué se decidió o qué se sabía antes» + «separa **tiempo válido** de **corte de registro**» | «revisar el historial, lo que se decidió o se usaba ANTES, lo ya sustituido o archivado» | la separación de los dos tiempos |
| **M3 · Verificación de fuente** | «Comprobar origen, **literalidad, matiz** o contradicción» | «verificar de dónde viene algo, quién lo dijo o en qué se apoya» | **literalidad** y **matiz** |
| **M4 · Gestión de memoria** | «Inspeccionar candidatas, rechazadas, suprimidas, restringidas o sin soporte» | «administrar la propia memoria (qué hay guardado, borrar, corregir)» | los estados concretos |
| **M5 · Revisión de conflicto** | «Examinar **afirmaciones incompatibles y soportes**» | «revisar una contradicción entre **dos cosas recordadas**» | el conflicto **documento contra memoria** |

**Y encaja caso por caso con lo medido:**

- `CA-18` «¿Qué **dice** el anexo técnico requerido?» → canon `M3`, modelo `M1`.
  **Literalidad pura**, y nuestra redacción de M3 no la menciona.
- `CA-28` «¿Qué se **dijo** en la sesión no guardada?» → canon `M3`, modelo
  `M2`. Lo mismo.
- `CA-27` «¿Qué presupuesto aplico en Beta **según el documento**?» → canon
  `M5`, modelo `M1`. Es un conflicto **documento contra memoria**, y nuestra
  redacción de M5 lo excluye al decir «entre dos cosas recordadas».

Tres de los siete fallos de `modo` tienen su causa en una palabra que el canon
dice y nosotros no.

## `corte_de_registro` — 42/47

La semántica **sí coincide**: el canon dice «Fecha hasta la que se considera lo
que Sirius había registrado; permite "qué sabía Sirius el día T"», y nuestra
instrucción dice lo mismo con otras palabras.

**Lo que falta no es semántica, es una convención.** `CA-32` «¿Qué sabía Sirius
sobre el aforo el 1 de marzo?» espera `2026-03-01T00:00:00` y el modelo
devuelve `2026-03-01T23:59:59.999999`. **Nunca le hemos dicho si "el día T" es
el principio o el final del día.** Es un fallo de una línea.

## `tiempo_objetivo` — 41/47

El canon dice «Momento **o intervalo** respecto del cual debe ser aplicable la
información. Por defecto es ahora, pero puede ser futuro o pasado». Nuestra
instrucción colapsa el intervalo a su extremo final.

**Eso no es una reducción nuestra: es una traducción registrada.** ADR-111 la
heredó literal del `_traducir` del laboratorio («tiempo en intervalo → extremo
final»). Está documentada y es deliberada.

**Pero hay algo que no cuadra y queda como pregunta abierta, no como
conclusión**: `CA-22` «¿Qué decisiones eran válidas entre enero y marzo?»
espera `2026-03-20`, que **no es** el extremo final del intervalo (sería el 31
de marzo). O la regla del extremo final no se aplicó a ese caso, o el valor
sale de otro sitio. No se resuelve aquí y no se inventa una explicación.

## Lo que esto suma

El defecto que motivó #653 **no es de la cardinalidad: es de toda la
instrucción**. Se escribió parafraseando el canon de memoria en vez de
citarlo, y cada paráfrasis perdió el matiz que el banco puntúa.

| campo | aciertos | causa identificada |
|---|---|---|
| `cardinalidad` | 30/47 | criterio gramatical en vez del del canon — **#653** |
| `modo` | 40/47 | M3 sin «literalidad», M5 limitado a memoria-contra-memoria |
| `corte` | 42/47 | convención de hora no enunciada |
| `limite` | 42/47 | tres `OBJETIVO` no inferibles — **techo duro** |
| `tiempo_objetivo` | 41/47 | traducción registrada de ADR-111; un caso sin explicar |

## Qué se hace con esto, y qué no

**No se lanza un segundo encargo ahora.** #653 está en el ciclo y dos encargos
en paralelo doblan el gasto de revisión, que es justo lo que dejó al
propietario bloqueado varios días en septiembre. El cuerpo del segundo queda
preparado y se lanza cuando #653 llegue a estado terminal.

**Y no se toca `tiempo_objetivo`** hasta entender el caso `CA-22`: cambiar una
traducción registrada en un ADR por una corazonada es exactamente lo que esta
disciplina prohíbe.
