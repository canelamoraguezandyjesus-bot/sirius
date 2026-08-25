# Evidencia — H-17

## Las cuatro preguntas, decididas ANTES de medir

1. ¿Una orden rechazada por clase no despachable escribe algo en el diario durable?
2. Si escribe, ¿en qué estado queda el WorkItem?
3. ¿Repetir la misma orden la bloquea por idempotencia, o acumula?
4. ¿Lo arregla #307, que toca justo ese camino?

## Criterio de parada, escrito antes de ver resultados

- Si el diario queda **vacío** tras un rechazo, no hay defecto y no se registra nada.
- Si escribe pero el WorkItem queda **cerrado o cancelado**, no es huérfano: se
  anota como observación, no como defecto.
- Si el arreglo cabe dentro del alcance de #305, **no se abre incidencia nueva**:
  se pide allí. Abrir una segunda incidencia por algo que cabía en la primera es
  fabricar trabajo.

## Afirmación

Una orden de clase `documentacion` con `--ejecutar` sale con código 5 y **deja
el WorkItem escrito en `active`**, para trabajo que no se puede despachar. No
hay bloqueo por idempotencia: repetirla crea otro WorkID y acumula.

## Comprobación que la sostiene

Ejecutado contra `dd3084f` —la punta de #307, no contra `main`— con un escritor
de GitHub que lanza `AssertionError` si alguien lo llama, para que un fallo de
escritura no se confunda con el rechazo:

```
codigo: 5 | diario creado? True | bytes: 2337
work_item | estado=planned
work_item | estado=active
```

Repetida sobre el mismo diario:

```
segunda vez, codigo: 5
lineas en el diario ahora: 4
```

## Cómo respondió cada pregunta

1. **Sí escribe**: 2337 bytes.
2. **`active`**, no cerrado. Es huérfano de verdad.
3. **No bloquea**: WorkID nuevo por intento, acumulación sin límite en un diario
   append-only.
4. **No lo arregla #307**: re-medido contra su punta después de su segundo
   commit, mismo resultado. Y hace bien en no arreglarlo — su «Fuera de alcance»
   se lo prohíbe.

El criterio de parada decidió el desenlace en el punto 4: como el arreglo **no**
cabía en el alcance de #305, se abre incidencia aparte (#308) en vez de pedirlo
allí.

## Qué lo escondía

La prueba de ensayo comprueba `assert not diario.exists()`. La de `--ejecutar`
**no comprueba el diario**. Esa aserción ausente es exactamente el hueco por el
que cabía el defecto, y por eso #308 la pide explícitamente.

## Por qué esto no lleva ADR

No hay decisión que registrar. Un defecto medido no es una elección entre
opciones: es un hecho, y su sitio es el registro que gobierna ADR-080. El ADR
tocará cuando se decida **cuál** de los dos arreglos posibles se toma —rechazar
antes de crear el WorkItem, o cerrarlo al rechazar—, y esa decisión es del
bloque que atienda #308, con su medición delante. Decidirlo aquí sería decidir
sin haber medido las dos opciones.
