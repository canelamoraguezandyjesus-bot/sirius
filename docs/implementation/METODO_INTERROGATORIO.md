# Método de interrogatorio

**Regla única: el propietario decide QUÉ quiere; la sesión decide CÓMO se hace.
Cada pregunta que se le haga sobre el cómo es un fallo de la sesión.**

Nació de una observación suya, y conviene no suavizarla: *«al final tú tomas las
decisiones en cierto modo»*. Es verdad. Él firma, pero firma sobre un juicio
ajeno. Este método existe para devolverle el volante sin obligarle a escribir
especificaciones.

## 1. La forma de cada pregunta

**Una. Cada. Vez.** Y se espera su respuesta antes de la siguiente. Un muro de
veinte preguntas no es un interrogatorio: es un formulario, y se contesta a
desgana o no se contesta.

Cada pregunta tiene exactamente tres partes y ninguna más:

```
**Pregunta N de ~T** — [la pregunta, en una frase, sin jerga]

**Mi propuesta:** [la mejor respuesta que se te ocurra, concreta]

**Por qué, y qué me haría cambiar:** [una o dos frases; y qué dato o
preferencia suya te haría proponer otra cosa]
```

Así solo tiene que corregir. Y **la tercera parte no es adorno**: sin ella, un
«sí» suyo no es una decisión, es rendirse ante la propuesta — que es justo el
problema que este método viene a resolver.

Se dice siempre **cuántas preguntas quedan aproximadamente**. Saber que son seis
y no sesenta cambia si contesta con ganas o con prisa.

## 2. Qué NO se puede preguntar

- **Nada que se pueda averiguar leyendo.** El repositorio, los ADR, las
  incidencias, el código. Preguntar lo que se tiene delante quema su paciencia
  en algo que es trabajo de la sesión. Leer primero, preguntar después.
- **Nada técnico.** Qué biblioteca, qué patrón, cómo estructurarlo, si conviene
  un puerto o un adaptador. Eso lo decide la sesión y responde de ello.
  Preguntarlo es pasarle el trabajo propio.
- **Nada cuya respuesta no cambie nada.** Antes de cada pregunta hay que poder
  decir en qué se distingue lo que se construiría con una respuesta y con la
  otra. Si no se sabe decir, no es una pregunta: es relleno. Se decide y se
  sigue.

## 3. Qué SÍ hay que preguntar

Lo que solo él sabe, y que ningún análisis del repositorio va a dar:

- **Para qué es y para quién.** No «qué hace», sino qué problema suyo
  desaparece.
- **Qué NO debe hacer nunca.** Los límites duros. Suele ser lo más valioso y lo
  que menos se pregunta.
- **Cómo sabremos que está terminado.** Algo que se pueda mirar y decir sí o no.
  Si su respuesta es difusa, esa es la conversación importante.
- **Qué sacrificaría si hubiera que elegir.** Rapidez, alcance, seguridad,
  dinero. Le obliga a ordenar, y evita construir lo que no prioriza.
- **Qué le haría tirarlo a la basura.** El fracaso, dicho antes de empezar.

## 4. Cuándo parar

Se para cuando **lo que queda por saber ya no cambia lo que se construiría**. Es
un criterio comprobable: si se puede escribir el plan entero y ninguna respuesta
pendiente movería una línea, se ha terminado de preguntar.

Dos cosas que NO son motivo para seguir:

- Que quede algo por decidir. Muchas cosas quedan; las decide la sesión.
- Que la respuesta parezca poco meditada. Si preocupa, se dice en el plan como
  supuesto explícito, no con otra pregunta.

Y una que sí obliga a parar **antes**: si contesta «decide tú», se toma y se
sigue. No se le vuelve a preguntar lo mismo con otras palabras.

## 5. Qué se entrega al terminar

**No un `PLAN.md` genérico.** En este repositorio el plan tiene que poder
consumirlo algo:

- Si es un bloque de trabajo del ciclo → el cuerpo de la incidencia, con las
  once secciones obligatorias, validado con
  `uv run python scripts/automation/validate_issue_body.py <fichero>` antes de
  publicarlo.
- Si es una decisión de diseño → un ADR con la skill `adr`.
- Si es algo más grande que un bloque → un documento en `docs/implementation/`,
  con la secuencia y sus dependencias.

El plan lleva, **separadas y con esos nombres**:

- **Lo que decidió él**, con sus palabras cuando se pueda.
- **Lo que decidió la sesión**, y por qué. Para que pueda discutirlo después.
- **Los supuestos**: lo que se dio por bueno sin preguntar.

Esa separación es la que hace que el método sirva de algo. Sin ella el plan
vuelve a ser de la sesión y él solo lo habrá visto pasar.

## 6. Cómo hablarle

Sin jerga, y si un término técnico es inevitable, se explica en la misma frase.
Él lo ha dicho: *«yo no sé muchas veces ni lo que me dices»*. Que no entienda una
pregunta es un fallo de quien la redactó, nunca suyo.

Frases cortas. Sin párrafos de contexto antes de la pregunta. Si hace falta
media pantalla para preguntar algo, la pregunta no está madura.

## 7. Los tres modos en que esto fracasa

1. **Preguntar de más.** Se nota porque las preguntas empiezan a sonar a examen.
   Se corta y se decide.
2. **Proponer sin decir qué haría cambiar de opinión.** Entonces contesta «sí» a
   todo y el plan vuelve a ser de la sesión con su firma encima. Es el fracaso
   silencioso, y el peor, porque parece que funcionó.
3. **Preguntar lo que se debería haber leído.** Se nota porque la respuesta está
   en un fichero del repositorio. Es la forma más rápida de que deje de
   contestar.

## 8. Relación con el resto del método del repositorio

El interrogatorio produce el **encargo**. No sustituye a nada de lo que viene
después:

- La `disciplina-evidencia` sigue rigiendo la ejecución: nota de arranque,
  criterio de parada escrito antes de ver resultados, regla de las dos rondas y
  prueba por mutación.
- Las decisiones que se tomen durante el interrogatorio se registran igual, con
  la skill `adr`.
- Si el encargo acaba siendo un bloque del ciclo, entra por la máquina de
  estados como cualquier otro.
