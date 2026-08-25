# Evidencia — H-23

## Las cuatro preguntas, decididas ANTES de medir

1. ¿Se puede reanudar un bloque parado reponiendo su etiqueta de activación?
2. ¿Se puede reanudar con la orden `continua`?
3. Si ninguna vale, ¿es un caso alcanzable o un laboratorio?
4. ¿Puede arreglarlo el ciclo, o hace falta sesión interactiva?

## Criterio de parada, escrito antes de ver resultados

- Si **alguna** de las dos vías funciona, no hay defecto: hay un manual mal
  leído, y lo que toca es escribirlo mejor, no registrar nada.
- Si fallan las dos pero el caso **sólo se alcanza forzándolo**, se anota como
  observación y no como defecto: un callejón que nadie pisa no cuesta nada.
- Si el arreglo vive en `.github/`, la incidencia nace **sin etiquetas de
  activación**: despacharla sólo produciría un rechazo.

## Afirmación

Un bloque que se detiene con `sirius:blocked-decision` **antes de crear rama o
PR** queda sin salida. Las dos vías de reanudación fallan, cada una por su
motivo, y ninguna es un descuido: son dos diseños correctos que no se solapan.

## Comprobación que la sostiene

Sobre la incidencia #333, que se paró al ver que completar su encargo exigía
tocar `.github/workflows/**` —prohibido para ella por ADR-002—.

**Vía 1, reponer la etiqueta de activación:**

```
Implementar bloque Sirius · run 32877801973 · conclusion: failure
  paso 6  «Verificar precondiciones de activación» -> success
  paso 7  «Consumir el evento y marcar en curso»   -> FAILURE
  paso 8  «Preparar instrucciones»                 -> skipped
```

No es una sorpresa: la cabecera de `resume-sirius-on-command.yml` ya lo decía
—«reponer la etiqueta disparadora volvía a bloquear en el acto»— y ese workflow
existe precisamente porque esa vía no vale.

**Vía 2, la orden `continua`:**

```
🛑 No he podido reanudar el ciclo
No he encontrado ninguna PR asociada a esta incidencia, así que no puedo
saber sobre qué head autorizas continuar.
```

## Cómo respondió cada pregunta

1. **No.** El paso que consume el evento falla sobre una incidencia ya
   consumida.
2. **No.** `continua` necesita una PR sobre la que autorizar un head, y aquí no
   hay ninguna.
3. **Es alcanzable, y se alcanzó sin forzar nada.** #333 llegó ahí obedeciendo:
   se detuvo antes de escribir para no violar ADR-002.
4. **Sesión interactiva.** El arreglo vive en `.github/`, luego la incidencia
   #337 nace sin etiquetas de activación (criterio de parada aplicado).

## Por qué esto importa más de lo que parece

La parada temprana es **la conducta correcta**. El implementador vio que hacer
sólo la mitad que sí podía habría producido «una vuelta completa falsa» —sus
palabras— y se detuvo sin crear nada.

Si la única salida de esa conducta es que la incidencia muera, el sistema
**castiga lo que debería premiar**. Con el tiempo eso enseña a no pararse, que
es exactamente la enfermedad que este repositorio lleva semanas tratando.

## Lo que esta evidencia NO dice

Cuál de los dos arreglos posibles es el bueno —que `continua` acepte una
incidencia sin PR, o una orden distinta para esta parada—. No se han medido las
dos, así que elegir aquí sería decidir sin datos.
