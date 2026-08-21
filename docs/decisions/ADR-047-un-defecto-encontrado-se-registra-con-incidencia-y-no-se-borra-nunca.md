# ADR-047 — Un defecto encontrado se registra con incidencia y no se borra nunca

- Estado: APROBADO
- Fecha: 2026-08-21
- Aprobación: la fusión de la PR por el propietario
- Contexto: queja del propietario del 21-08-2026 y §5 de `docs/implementation/DONDE_ESTAMOS_2026-08-21.md`
- Relacionadas: ADR-001 (disciplina de evidencia), ADR-032 (registro de decisiones sin números repetidos)

## Contexto y problema

El propietario paró el trabajo con esto:

> «No me molesta que haya fallos, me molesta tenerlos que encontrar **yo**. Y muchos no los voy a encontrar y no me voy a dar cuenta.»

Tiene razón, y la parte de su queja que este ADR cubre es medible. El 20-08 una
auditoría encontró seis defectos y los dejó escritos en
`docs/audits/DEFECTOS_ENCONTRADOS_2026-08-20.md`, **en una rama sin fusionar**.
El 21-08:

```
$ git show origin/main:docs/audits/DEFECTOS_ENCONTRADOS_2026-08-20.md
fatal: path does not exist in 'origin/main'

$ uv run pytest -q
2846 passed, 6 skipped     ← con cuatro de esos defectos dentro
```

Cuatro seguían vivos en `main`, ninguna incidencia los seguía, y la batería
pasaba en verde. **Encontrarlos no sirvió de nada.** Si esa rama se hubiera
perdido, los cuatro habrían desaparecido del mapa sin que nadie lo notara.

Nótese qué clase de problema es: no es que falte una guarda que los detecte —esa
es otra conversación, la del §5 del documento de orientación—. Es que el
mecanismo que sí funcionó (una auditoría dedicada) **produjo un resultado que se
evaporó**.

## Criterio de parada (escrito ANTES de decidir)

Escrito antes de tocar nada, y es el criterio que ADR-001 pide de una guarda
nueva:

> Vale si, y solo si, **es determinista y no depende de ningún modelo**. Si para
> funcionar hace falta que alguien —o algo— razone, no sirve: el propietario ha
> declarado que su miedo es que el sistema solo aguante mientras pague un modelo
> caro. Y si una mutación evidente —borrar la fila incómoda— no rompe nada,
> tampoco vale: sería una lista decorativa.

Ambas condiciones se comprueban abajo.

## Opciones consideradas

1. Dejar el parte donde estaba y confiar en acordarse.
2. Traer el parte a `main` como documento y ya.
3. Traer el parte **y** un registro legible por máquina **y** una prueba que
   falle si el registro se pudre.

## Decisión

**La tercera.** Tres piezas, y ninguna sirve sin las otras dos:

- El parte entra en `main` con una cabecera de estado. El texto original queda
  intacto: es evidencia fechada, no se reescribe.
- `docs/audits/registro_defectos.yml` es la misma tabla, legible por máquina.
- `tests/automation/test_registro_de_defectos.py` rompe la batería si un
  defecto abierto se queda sin incidencia, si cita un fichero que ya no existe,
  si se cierra sin decir qué commit lo cerró, o **si alguien lo borra en vez de
  cerrarlo**.

Y la regla que da nombre al ADR: **un defecto nunca se borra del registro.** Pasa
a `estado: cerrado` con el commit que lo cerró. El historial de lo que falló vale
tanto como lo que falla hoy — y, sobre todo, borrar es la vía más rápida de poner
el registro en verde, que es justo lo que hay que impedir.

## Comprobación que la sostiene

### La primera condición del criterio: no depende de ningún modelo

La prueba lee un YAML y comprueba si unas rutas existen. No razona, no invoca
nada, no sale a la red:

```
$ uv run pytest tests/automation/test_registro_de_defectos.py -q
12 passed in 0.18s
```

Sigue funcionando igual el día en que el ciclo lo mueva un modelo pequeño y
barato, que es el requisito que puso el propietario.

### La segunda: las mutaciones, sembradas y vistas fallar

| Mutación | ¿La caza? |
| --- | --- |
| Quitar la incidencia de un defecto abierto | sí — 1 failed |
| Apuntar a un fichero que ya no existe | sí — 1 failed |
| **Borrar un defecto abierto en vez de cerrarlo** | sí — 1 failed |
| Cerrar sin decir qué commit lo cerró | sí — 1 failed |

La tercera es la que justifica la regla de «no se borra nunca», y la que no
existía en el primer intento de esta prueba: se añadió al comprobar que sin ella
la batería seguía verde tras borrar una fila. Se resolvió fijando los
identificadores por nombre, el mismo patrón que `DUPLICADO_HISTORICO` usa en
`test_registro_de_decisiones.py` (ADR-032).

### Validaciones obligatorias

```
uv run ruff format --check .   -> 431 files already formatted
uv run ruff check .            -> All checks passed!
uv run mypy src tests          -> Success: no issues found in 412 source files
uv run pytest tests/automation -> 501 passed, 3 skipped
git diff --check               -> limpio
```

## Consecuencias

- Los cuatro defectos vivos quedan seguidos por las incidencias #214, #215, #216
  y #217, abiertas el mismo día.
- Encontrar un defecto y no apuntarlo deja de ser posible en silencio: o entra en
  el registro con su incidencia, o la batería se pone roja.
- Un defecto cerrado conserva su fila y el commit que lo cerró, así que el
  registro sirve además como historia de qué clase de cosas fallan aquí.
- El coste de mantenimiento es real y conviene decirlo: mover código obliga a
  actualizar las rutas del registro. Es barato y es deliberado — una ruta que ya
  no existe significa que ese defecto ya no se puede ni comprobar.

## Alternativas descartadas y por qué

**Confiar en acordarse.** Es lo que se hizo, y produjo exactamente este ADR: seis
defectos encontrados, cuatro evaporados, cero avisos.

**Solo el documento, sin registro ni prueba.** Un documento en `main` sobrevive,
pero no obliga a nada: nadie se entera de que una fila lleva un mes sin
incidencia. Sin la prueba, esto es una lista que se pudre; con ella, es una
guarda.

**Que la prueba exija además que cada defecto abierto tenga una fecha límite.**
Descartada por ahora: pondría una fecha inventada en cada fila y el ruido
enseñaría a ignorar la prueba. Si algún día un defecto se enquista, esta sección
se enmienda.

## Lo que este ADR NO resuelve

Y conviene que quede escrito para no venderlo por más de lo que es: **esta prueba
no encuentra defectos.** Eso no lo hace una lista. Cubre la mitad del problema
—que uno ya encontrado no se pierda— y deja intacta la otra mitad, que es por qué
las guardas actuales solo cazan la violación de reglas que alguien ya escribió
después de tropezar. Esa mitad está descrita en §5 de
`docs/implementation/DONDE_ESTAMOS_2026-08-21.md` con tres guardas más
propuestas, y no se ha construido todavía.
