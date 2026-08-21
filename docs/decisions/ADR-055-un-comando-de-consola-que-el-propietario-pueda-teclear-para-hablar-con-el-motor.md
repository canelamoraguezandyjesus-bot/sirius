# ADR-055 — Dar al motor un comando de consola que conversa y consulta, y que no puede crear trabajo

- Estado: PROPUESTO
- Fecha: 2026-08-21
- Aprobación: la fusión de la PR por el propietario

## Nota de arranque (publicada ANTES de escribir una línea de código)

Este apartado se confirmó en su propio commit, antes que el arreglo, para que
la fecha del `git log` lo sostenga y no haya que creerme.

**1. ¿Dónde vive el fallo y dónde va el arreglo?**

El fallo es una **ausencia**, y vive en dos sitios a la vez:

- `pyproject.toml`, `[project.scripts]`: tres entradas, ninguna del motor.
- `src/sirius_engine/session.py`: `SesionCLI` existe y funciona, pero nadie
  fuera de `tests/` la construye nunca.

El arreglo NO vive dentro de lo que falla: va en un módulo nuevo
(`src/sirius_engine/cli.py`) más una entrada nueva en `[project.scripts]`.
La pregunta que caza la raíz —*¿puede el sitio del arreglo observar el fallo
que arregla?*— aquí se responde que sí, y de la única forma que vale: una
prueba puede leer `pyproject.toml`, resolver la entrada declarada e
**invocarla**. Si mañana alguien borra la entrada, o renombra el módulo, la
prueba cae. Una prueba que solo importara el módulo no observaría el fallo:
el fallo es «no hay comando», no «no hay código».

**2. ¿Qué NO va a garantizar esto?** (escrito antes, no como excusa después)

- **No permite dar órdenes.** Crear trabajo desde este comando queda fuera a
  propósito (requisito del encargo y primera propiedad de A5). El comando
  declina las órdenes en vez de ejecutarlas.
- **No consulta incidencias ni PR de GitHub**: eso exige red, y el encargo la
  prohíbe. Las consultas se responden con el árbol del repositorio y el
  historial de `git`. El comando lo **dice** en su salida: «no pude leerlo»
  nunca se disfraza de «no hay» (ADR-036).
- **No mejora al intérprete de intención v0.** Hereda sus límites: si la
  heurística clasifica mal un mensaje, el comando clasificará igual de mal.
- **No hace que M1 esté vivido.** Eso lo hace el propietario tecleando. Lo
  que esto hace es que pueda.
- **No decide dónde vive el almacén para siempre.** D2 fija la representación
  física (ADR-019, ADR-029); aquí solo se elige un sitio por defecto y se deja
  cambiar sin tocar código.

**3. Criterio de parada** (decidido antes de ver ningún resultado)

Se para cuando se cumplan las tres, y no antes:

1. El comando **declarado en `[project.scripts]`** —no un `python -m` ni un
   `import` desde una prueba— se ejecuta de verdad, y la sesión real queda
   pegada en este ADR y en el cuerpo de la PR.
2. Existe prueba automática que parte de `pyproject.toml` y llega a invocar
   el punto de entrada.
3. Cada mutación prevista hace caer al menos una prueba, **o** se declara
   equivalente y se explica por qué; ninguna se tapa inventando una prueba.

Y se para **antes** de terminar, escalando en vez de seguir, si aparece
cualquiera de estas dos:

- No consigo impedir que el comando cree trabajo sin reimplementar
  `SesionCLI` (el encargo prohíbe reimplementarla).
- Dos rondas seguidas de defectos de la misma familia (regla de las dos
  rondas, ADR-001).

**4. ¿Qué haría el fallo IMPOSIBLE en vez de improbable?**

Son dos fallos distintos y se responden por separado.

- *«M1 vuelve a quedarse sin comando»*: lo hace imposible que la prueba del
  punto de entrada corra en Quality **sobre el árbol fusionado**. Ninguna
  fusión en verde puede volver a dejar el motor sin comando. Esto se hace.
- *«El comando crea trabajo»*: lo haría imposible un envoltorio de solo
  lectura del `WorkEngineStore`, que levantara ante cualquier método de
  escritura. **No se hace**, y la razón irá escrita en «Alternativas
  descartadas»: el puerto tiene decenas de métodos y el envoltorio sería más
  código que el propio comando, con su propio riesgo de desincronizarse del
  puerto. Lo que se hace en su lugar irá en «Decisión».
