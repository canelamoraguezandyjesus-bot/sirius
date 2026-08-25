# ADR-087 — Dar nombre propio a los bloques del motor y exigir evidencia para cerrar uno

- Estado: PROPUESTO
- Fecha: 2026-08-25
- Aprobación: la fusión de la PR por el propietario
- Relacionadas: ADR-080 (el registro de defectos y su guarda), ADR-001
  (disciplina de evidencia), ADR-020 (el motor por verticales delgadas)

## Contexto y problema

El 25-08-2026 el propietario dijo, sobre su propio proyecto:

> «empezamos construyendo el bloque, diciendo que está terminado, hablando de
> bloques, y al final no está terminado»

Y venía de un malentendido concreto que **no fue mentira de nadie**. Preguntó si
estaban todos los bloques hechos; le dijeron que sí, y **era cierto**: los **16
bloques del producto** Sirius 0.1 quedaron cerrados el 10-08-2026, y
`V8_EXECUTION.md:28` lo dice con esas palabras. Él lo entendió como «todo».

**Porque nadie dijo de qué lista se hablaba.** Hay dos:

| Lista | Cuántos | Estado |
|---|---|---|
| Los bloques del **producto** (Sirius 0.1) | 16 | cerrados el 10-08-2026 |
| Los bloques del **motor** | 19 | 12 cerrados, 2 en curso, 4 pendientes, 1 fuera de alcance |

Y comparten identificador: **`B1` es un bloque del producto y un bloque del
motor**, dos cosas distintas. Es la misma enfermedad que ya costó un día entero
con la palabra «Sirius» —el producto y el motor compartiéndola— y hace el mismo
daño: se afirma algo verdadero de una cosa y se entiende de la otra.

## Criterio de parada (escrito ANTES de decidir)

**(a)** Si el arreglo se queda en **renombrar**, se para y se busca más. Un
cambio de nombre no impide volver a declarar terminado lo que no lo está: eso es
la mitad del problema que el propietario nombró, y la mitad menos importante.

**(b)** Si el registro **copia estados de la foto del 21-08** en vez de medirlos,
no vale. Un registro que hereda afirmaciones sin comprobarlas es exactamente el
mecanismo que se quiere cortar.

**(c)** Si la guarda **no se ve fallar** sobre un registro mutado a propósito, no
es una guarda: es decoración. Se prueba borrando la evidencia de un bloque
cerrado antes de darla por buena.

## Opciones consideradas

1. **Renombrar en los documentos donde se citan.** Descartada por el criterio
   (a): arregla la ambigüedad y deja intacta la costumbre de declarar terminado
   sin evidencia.
2. **Un documento en prosa con el estado de cada bloque.** Descartada porque
   caduca sin avisar: es exactamente lo que le pasó a `STATUS.md`, que estuvo
   quince días diciendo que 0.1 no estaba aceptado.
3. **Un registro con datos y una guarda que lo comprueba.** Es la elegida, y es
   la forma que este repositorio ya tiene probada para los defectos (ADR-080).

## Decisión

**Opción 3.** `docs/implementation/bloques_del_motor.yml` declara la lista con
nombre propio —`lista: bloques-del-motor`— y un campo `no_confundir_con` que
nombra la otra. `tests/automation/test_registro_de_bloques.py` impone dos reglas:

1. **Un bloque `cerrado` tiene que decir qué comprobación lo cierra.** Sin
   `evidencia`, la batería falla.
2. **Un bloque abierto tiene que decir qué lo cerraría.** Sin
   `que_lo_cerraria`, la batería falla. `fuera_de_alcance` queda exento: lo que
   no se va a hacer no necesita criterio para hacerse.

Más la propiedad que ADR-080 ya protege para los defectos: **un bloque conocido
no puede desaparecer del registro**. Se cierra cambiando su estado, nunca
borrándolo.

## Comprobación que la sostiene

**Los estados se midieron, no se copiaron** (criterio b). Dos salieron distintos
de lo que la foto del 21-08 dejaba suponer:

- **C3**: no es que «falte hacerlo». Es que los dos agentes de documentación
  están escritos y **no los llama nadie** —cero referencias a
  `documentalista.md` y `revisor-documental.md` en workflows y en scripts— y la
  clase `documentacion` no está en `TABLA_ACTIVACION`. Son dos cables, no uno.
- **D1**: sus tres mitades existen, pero `authority_reversion.py` **no lo llama
  nadie** fuera de sus pruebas. Es la salida de emergencia del contrato §11.4
  —lo que devuelve el mando si el motor se porta mal— construida, probada e
  inalcanzable. Sexta pieza correcta y muda de este repositorio.

**La guarda se vio fallar** (criterio c), y aquí está lo importante: **nació
vacua**. Borrada la evidencia de un bloque cerrado, pasó en verde:

```
=== y MUERDE de verdad? le quito la evidencia a un cerrado ===
28 passed
```

La causa: un campo vacío en YAML se lee como `None`, y `str(None)` es `"None"`,
cuatro caracteres que no están en blanco. Tras el arreglo, sobre el mismo
registro mutado:

```
FAILED test_todo_bloque_cerrado_dice_que_lo_demuestra
FAILED test_cada_bloque_del_registro_pasa_sus_dos_reglas[S3]
2 failed, 26 passed
```

Lo cazó **la mutación, no la lectura**, y queda fijado con su propia prueba y
escrito en el docstring. Una guarda contra afirmaciones sin evidencia que empezó
siendo ella misma una afirmación sin evidencia merecía quedar dicha, no
disimulada.

```
uv run ruff check .            -> código 0
uv run pytest tests/automation -> 749 passed, 5 skipped, código 0
```

## Consecuencias

**«Terminado» deja de poder afirmarse solo**, que es lo que el propietario pedía.
Y «falta» deja de ser una palabra suelta: cada bloque abierto dice qué lo
cerraría, así que nadie tiene que adivinar cuándo parar.

**Aparece una deuda que estaba escondida en la ambigüedad.** Doce cerrados de
diecinueve suena a casi hecho; los cuatro pendientes incluyen uno —D1— cuya
salida de emergencia no puede dispararse. Verlo escrito es incómodo y es el
punto.

**Esto NO garantiza que un bloque cerrado esté bien hecho.** Una lista no
comprueba trabajo. Garantiza que nadie pueda cerrarlo **sin decir qué lo
demuestra**, que es una cosa mucho más pequeña y la única que una lista puede
sostener. Confundir las dos sería repetir el error que este ADR corrige.

## Alternativas descartadas y por qué

- **Renombrar y nada más**: criterio de parada (a).
- **Prosa en vez de datos**: caduca sin avisar, como le pasó a `STATUS.md`
  durante quince días.
- **Extender el registro de defectos en vez de crear otro**: un defecto y un
  bloque no tienen los mismos campos ni el mismo ciclo, y mezclarlos habría
  obligado a que la guarda de ADR-080 aceptara filas que no son defectos.
