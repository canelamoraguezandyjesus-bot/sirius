# La cardinalidad no se deriva del conjunto esperado — 20-09-2026

Responde a
`arranque-se-puede-derivar-la-cardinalidad-del-conjunto-esperado.md`, escrita
antes de mirar los datos. Determinista, sin Ollama. Solo se leen
`peticion_p2.cardinalidad` y `resultado_esperado`.

## El resultado

Regla A —**`EXACTA` si y solo si `len(resultado_esperado) == 1`**—:
**32/47**. Por debajo del suelo de 35 que la nota de arranque fijó.

Y los fallos explican por qué ninguna regla de tamaño va a funcionar:

**Diez casos `EXACTA` y seis `EXHAUSTIVA` tienen el conjunto esperado vacío.**
Son los casos de ausencia. Ahí el tamaño no lleva ninguna señal, por
construcción.

Quitando los vacíos, los tamaños **se solapan**:

```
EXACTA      {1, 1, ..., 1, 2, 2, 3}     (16 unos, dos doses, un tres)
EXHAUSTIVA  {1, 1, 2, 2, 2, 5, 6}
ACOTADA     {3, 5, 10, 10, 11}
```

`EXACTA` y `EXHAUSTIVA` comparten los tamaños 1 y 2. El tamaño **no separa**.

## El par que lo deja desnudo

| caso | consulta | cardinalidad | esperados |
|---|---|---|---|
| `B04-CA-08` | «¿Cuál es **el** presupuesto de Beta?» | **EXHAUSTIVA** | 2 |
| `B04-CA-50` | «¿Qué **condiciones** de acceso al almacén hay?» | **EXACTA** | 1 |

Están **al revés** de lo que la gramática sugiere y al revés de lo que el
tamaño sugiere. El singular con artículo definido es exhaustivo; el plural
indefinido, exacto.

Y son exactamente dos de los casos que el modelo falla, en sentidos opuestos.
El modelo no se equivoca por torpeza: aplica el criterio que le damos.

## Respuesta a la pregunta que decidía

**¿Es el criterio enunciable a un intérprete que solo ve la pregunta?**

**No, con lo que consta.** No se deriva de la forma de la pregunta (el par
CA-08/CA-50 lo refuta) ni del tamaño del conjunto esperado (32/47). La lectura
que queda en pie —y es **hipótesis, no conclusión**— es que depende del
**contenido de la memoria**: si para «presupuesto de Beta» hay dos elementos y
la respuesta debe cerrarlos, es exhaustiva; si para «condiciones de acceso» hay
un único elemento canónico, es exacta.

Si esa hipótesis fuera cierta, tendría una consecuencia que excede esta
investigación y que **solo el propietario puede resolver**: el intérprete de
ADR-164 produce la `Peticion` **desde la pregunta sola**, y al menos uno de sus
campos dependería de lo que hay guardado. Eso no se afirma aquí. Se señala.

## Lo que dice el criterio de parada, escrito antes

Decía: si ninguna regla simple pasa de 35/47, se registra que la cardinalidad
no se deriva del conjunto esperado y **el encargo sobre la instrucción queda
BLOQUEADO** hasta que §15.2 entre en el repositorio o el propietario enuncie el
criterio.

32 < 35. **El encargo queda bloqueado.** No se lanza.

## Contraste con la predicción

| predicción | resultado |
|---|---|
| la regla del tamaño acierta entre 38 y 43 de 47 | **FALLADA** — 32/47 |
| los fallos serán los tres `EXACTA` de varios elementos y algún `ACOTADA` | **FALLADA** — son sobre todo los 16 casos de conjunto vacío |
| la respuesta a «¿es enunciable al intérprete?» será NO, y el encargo quedará bloqueado (65%) | **ACERTADA** |

## El resultado útil de esta investigación es no haber trabajado

La nota de arranque lo dejó escrito antes de empezar: «si acierto en esto
último, el resultado útil de la noche es **haber evitado el encargo**, no
haberlo lanzado».

Sin esta comprobación, el siguiente paso obvio era un encargo que reescribiera
la instrucción del intérprete «alineándola con §15.2». Habría costado un ciclo
completo, habría tocado producción, y la medición que lo juzgara la habría
tenido que correr el propietario en su máquina — para descubrir entonces que la
regla que se pretendía enunciar **no se puede enunciar con lo que consta**.

## Lo que hace falta, y es decisión del propietario

Una de estas dos, y ninguna la puedo tomar yo:

1. **Que §15.2 entre en el repositorio** (o la parte que define la
   cardinalidad), para poder alinear la instrucción con el criterio real.
2. **Que el propietario enuncie el criterio**, aunque sea en una frase. La
   pregunta concreta que lo resuelve es el par de arriba: *¿por qué «¿cuál es
   el presupuesto de Beta?» es EXHAUSTIVA y «¿qué condiciones de acceso al
   almacén hay?» es EXACTA?*

Con cualquiera de las dos, el encargo se desbloquea y el alcance ya está
acotado por la entrada 117: ataca los ~13 casos de confusión
`EXACTA`/`EXHAUSTIVA`, y excluye `CA-26` y `CA-34`, que son cuota de producto y
no inferencia.
