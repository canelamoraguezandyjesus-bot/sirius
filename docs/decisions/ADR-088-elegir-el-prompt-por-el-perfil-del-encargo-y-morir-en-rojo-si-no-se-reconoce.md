# ADR-088 — Elegir el prompt por el perfil del encargo, y morir en rojo si no se reconoce

- Estado: PROPUESTO
- Fecha: 2026-08-25
- Aprobación: la fusión de la PR por el propietario
- Relacionadas: ADR-066 (los dos perfiles documentales, que dejó este puente
  declarado como la incidencia siguiente), ADR-002 (la automatización no toca
  sus propios workflows), ADR-036 (una lectura caída no es una ausencia)

## Contexto y problema

`implement-sirius-work.yml` y `review-sirius-work.yml` insertaban el prompt con
un `cat scripts/automation/prompts/implementer.md` —y `reviewer.md`— **escrito
literalmente en el YAML**, sin leer nunca el campo `Perfil:` que el cuerpo de la
incidencia declara desde A4.

Consecuencia: los dos agentes documentales que ADR-066 escribió llevaban semanas
**mudos**, y la clase `documentacion` no podía dar una vuelta completa aunque se
la añadiera a las tablas del despachador.

**El hallazgo no es de esta sesión.** Se despachó el bloque C3 al ciclo
(incidencia #333) y el implementador **se detuvo sin escribir una línea**,
diciendo por qué:

> «Añadir únicamente las filas DOCUMENTACION a TABLA_ACTIVACION y TABLA_PERFILES
> sin el cableado de los workflows no cierra el bloque C3 […]: el ciclo
> arrancaría pero ejecutaría el prompt de programación, no el documental, lo que
> sería **una vuelta completa falsa**. No se ha creado rama, código ni PR.»

Y señaló correctamente que el cableado cae bajo ADR-002 y no es suyo.

## Criterio de parada (escrito ANTES de decidir)

**(a)** Si la solución permite que un encargo se ejecute con **el prompt de otro
rol sin que nadie se entere**, se para. Ese es el defecto que se viene a cerrar;
reintroducirlo por otra puerta sería peor que no tocar nada.

**(b)** Si obliga a **etiquetas de activación nuevas** para documentación, se
para. El bloque se titula «El mismo ciclo para documentos»: un ciclo con entrada
distinta no es el mismo ciclo, y duplicaría la máquina de estados sin que nadie
lo haya pedido.

**(c)** Si el cuerpo de la incidencia acaba **interpolado dentro del script**, se
para. Lo escribe quien abre la incidencia: es dato, y un dato que se sustituye
antes de que bash lea nada es código con los permisos del trabajo.

**(d)** Si la guarda que se rompa se **afloja** para que pase, se para. Una
guarda que estorba se sustituye por otra más fuerte o no se toca.

## Opciones consideradas

1. **Un workflow propio para documentación.** Descartada por el criterio (b):
   entrada distinta, máquina de estados duplicada, y dos sitios donde arreglar
   cada fallo futuro.
2. **Elegir el prompt por la etiqueta de la incidencia.** Descartada porque la
   etiqueta dice *en qué fase está* el trabajo, no *quién* debe hacerlo. Habría
   que inventar etiquetas por rol, que es (b) con otro nombre.
3. **Elegir el prompt por el campo `Perfil:` del cuerpo.** Es la elegida. Ese
   campo ya existe desde A4, ya lo escribe el despachador con la tabla de
   perfiles, y ya viaja en cada incidencia: no hay que inventar nada.

## Decisión

**Opción 3.** Los dos workflows leen `Perfil: <ref>@<version>` del cuerpo y
eligen:

| `Perfil` | Implementa | Revisa |
|---|---|---|
| `implementer` | `implementer.md` | `reviewer.md` |
| `documentalista` | `documentalista.md` | `revisor-documental.md` |

Y dos reglas que no son detalle:

**Un perfil no reconocido sale en ROJO** (criterio a). Ni repliegue silencioso ni
adivinar: `::error::` y `exit 1`. Ejecutar el prompt equivocado produce trabajo
que **parece** hecho y no lo está —y se publica con veredicto propio—; un
workflow fallido se arregla en un minuto y **se ve**. Es la misma regla que
ADR-036 fija para las lecturas: un hueco no es un valor por defecto.

**El cuerpo viaja por `env:`** (criterio c), nunca interpolado en el `run:`.

Las etiquetas de activación **no cambian** (criterio b): `documentacion` entra
por `sirius:planned` y `sirius:implement-requested`, igual que `programacion`.

## Comprobación que la sostiene

**La extracción, probada con el cuerpo real de #333** y con sus dos variantes:

```
implementer      -> implementer      OK
documentalista   -> documentalista   OK
(sin perfil)     -> (vacío, dará ERROR) OK
```

**La guarda se reforzó, no se aflojó** (criterio d).
`test_the_workflow_actually_feeds_the_reviewer_prompt` comprobaba una cadena
literal y se rompió con este cambio, haciendo bien su trabajo: existía para que
las pruebas del prompt no validaran un archivo muerto. Pasa de **una** aserción
a **cuatro**, y se añaden dos pruebas nuevas: que un perfil desconocido salga en
rojo, y que el cuerpo no se interpole.

```
uv run ruff check .            -> código 0
uv run pytest tests/automation -> 753 passed, 5 skipped
```

## Consecuencias

**Los dos agentes documentales dejan de estar mudos.** Eran la cuarta y la quinta
pieza correcta sin quien la llame que este repositorio se ha encontrado.

**C3 sigue sin cerrarse con esto solo**, y conviene no leerlo de más: falta la
mitad de `src/` —las filas `DOCUMENTACION` en las dos tablas—, que sí cae dentro
del alcance del ciclo y la cierra la propia incidencia #333 al reactivarse. El
bloque se cierra cuando una orden de documentación **dé la vuelta completa con
el prompt documental**, no antes.

**Aparece una dependencia nueva y conviene decirla:** el prompt que se ejecuta
depende ahora de un campo de texto del cuerpo. Si alguien edita ese campo a mano
en una incidencia viva, cambia quién la atiende. Hoy sólo lo escribe el
despachador; el día que eso deje de ser cierto, esto hay que releerlo.
