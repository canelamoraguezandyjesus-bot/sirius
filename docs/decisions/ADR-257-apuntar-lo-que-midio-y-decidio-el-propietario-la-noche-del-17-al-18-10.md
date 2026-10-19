# ADR-257 — Apuntar lo que midió y decidió el propietario la noche del 17 al 18-10

- Estado: APROBADO
- Fecha: 2026-10-18
- Aprobación: las decisiones son del propietario, dichas en la sesión de la madrugada del
  18-10-2026, y este registro lo aprueba la fusión de la PR que lo introduce (ADR-205).

## Contexto y problema

La noche del 17 al 18-10-2026, con la #698 fusionada, el propietario pasó en su ordenador
cinco de sus evaluaciones de la 0.2 y la 0.3. Dejó de hacer las demás, decidió que una
no se hace como estaba escrita, y pidió seguir con el plan. Lo que mide y decide en una
conversación se pierde si no se escribe.

## Criterio de parada (escrito ANTES de decidir)

No hay decisión de la sesión: se apunta lo que él midió y decidió, con sus palabras.

## Opciones consideradas

Ninguna: es un registro.

## Decisión

Pasan E-R02-04 y E-R02-05, y E-R02-03 no pasa. La prueba sin internet no se hace, y la 0.4
empieza sin esperar a sus pruebas.

**Sus resultados**, apuntados también en las pruebas de cada versión:

- **E-R02-05, buscar en la memoria.** Pasa. Con 10.000 recuerdos de prueba, P95 de
  93 ms, frente a los 170 ms del 16-10-2026; con su memoria, de 1 recuerdo, 60 ms. El
  límite es 150 ms.
- **E-R02-04, el banco de memoria.** Pasa: 93 de 100 con embeddinggemma, frente a 77 el
  16-10-2026, con 14 de 14 en «olvida eso» y en «quién dijo qué». «Cosas que cambian» se
  queda en 8 de 14.
- **E-R02-01, la prueba a ciegas.** Eligió gemma3:4b en 16 de 20 preguntas; qwen3:4b-instruct
  en 4 y mistral:7b en ninguna. De los tres dijo que se inventan cosas, que se quedan
  escribiendo respuesta tras respuesta y que dicen frases sin sentido. Lo de quedarse
  escribiendo lo ataja ADR-256. Que el ganador quedara como modelo de la charla no lo
  confirmó.
- **E-R03-06, su voz a ciegas.** Eligió una voz. Cuál, y si le suena masculina y de
  España, no lo dijo, así que no se da por pasada. De las voces dijo que se nota que son
  de máquina.
- **E-R02-03, las preguntas trampa.** Según sus marcas, le lleva la contraria en 38 de 40,
  y el juez dice otra cosa que él en 2. No pasa: tenía que llevársela en las 40. Dijo que
  marcó a voleo, y que la prueba cuenta y está hecha.

**Sus decisiones:**

- **La prueba sin internet no se hace.** E-R03-01 pedía apagar el wifi para ver que la
  voz funciona sin internet. Su respuesta: «no vamos a hacer ningún día apaga el wifi».
  Esa condición sale de su evaluación; lo demás de E-R03-01 y E-R03-02 sigue pendiente.
- **Se sigue con el plan sin esperar a sus pruebas.** Sus palabras: «sigue por lo que nos
  falta… Las pruebas y todo ya me encargaré yo». El plan decía que sin la prueba suya no
  se pasa a la siguiente versión (§2). Desde hoy, la 0.4 empieza antes de que él acabe
  las de la 0.2 y la 0.3, que hará cuando quiera. Una versión sigue sin darse por
  terminada hasta que pasan.
- **La cabeza en la nube, sin decidir.** Se le preguntó si se probaba la charla con
  OpenAI, dentro de los 20 dólares al mes que ya aprobó para Sirius. Dijo «Ya se verá».

## Comprobación que la sostiene

Las cifras son las que pegó de su terminal y de sus capturas, en esta misma sesión:

- `scripts/medir_busqueda_de_memoria.py`: «Tu memoria, 1 recuerdo: P50 32 ms, P95 60 ms»
  y «10000 recuerdos de prueba: P50 59 ms, P95 93 ms», «Pasa: sí.».
- `scripts/pasar_el_banco_de_memoria.py`: las siete familias, «En total: 93 de 100, con el
  modelo de huellas embeddinggemma.», «Pasa.».
- La hoja de la prueba a ciegas: «Has elegido gemma3:4b en 16 de 20 preguntas
  (gemma3:4b: 16, mistral:7b: 0, qwen3:4b-instruct: 4).».
- La hoja de las preguntas trampa: «Te lleva la contraria en 38 de 40.» y «El juez dice
  otra cosa que tú en 2 de 40».
- La revisión de la #701, que lo trajo: la ronda 1 de Codex no encontró nada de este ADR, y
  la ronda 2, sobre `4d32f5ef`, fue limpia. Se fusionó aplastada el 19-10-2026 en
  `5931f80e`.

## Consecuencias

- E-R02-04 y E-R02-05 pasan en su ordenador.
- E-R02-01, E-R02-03 y E-R03-06 tienen resultado; solo E-R02-03 está decidida, y no pasa.
  E-R02-02 y las de la voz, de E-R03-01 a E-R03-05, siguen pendientes.
- La 0.4 se empieza ya. La 0.2 y la 0.3 no se dan por terminadas.

## Alternativas descartadas y por qué

Ninguna.

## La lección

- ninguna: apunta lo que el propietario midió y decidió; no hay ningún fallo que repetir.
