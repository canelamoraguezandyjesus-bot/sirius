# Sirius 0.2 · ADR-002 · La última omisión, y el atajo que no se usa

**Estado:** evidencia dentro de ADR-002. No abre ADR nuevo. PR #117 sigue abierta y sin fusionar.

**Importa porque** el acta de cierre dejó ADR-002 sin poder cerrarse por una sola obligación, y
esa obligación es justo la que se ha estado desatascando toda la semana.

---

## Lo que ADR-002 tenía atascado

`SIRIUS_0.2_ADR_002_CIERRE_v1.0.md` lo dice sin ambigüedad:

> `B04-M01 · Recall crítico`, umbral **100 % por caso**.
> `§14 · R1`: «una omisión crítica reproducible **elimina la alternativa**».
>
> «Vale **16** para los cuatro candidatos, en **seis casos**: `N1-02`, `N1-30`, `N1-31`, `N1-33`,
> `N1-34` y `N1-44`.»

**Esos seis casos son los que se han estado arreglando**, sin que nadie hubiera hecho la conexión:

| caso | estado | qué lo resolvió |
|---|---|---|
| `N1-02` | **resuelto** | la categoría buscable |
| `N1-31` | **resuelto** | la categoría buscable |
| `N1-44` | **resuelto** | la regla de las críticas |
| `N1-33` | **resuelto** | la siembra al ensamblar contexto |
| `N1-34` | **resuelto** | la siembra al ensamblar contexto |
| `N1-30` | **abierto** | — |

**Cinco de seis.** Y como la puerta es del 100 %, ese uno decide si ADR-002 puede cerrarse o no.

---

## El que queda

**`N1-30`** · «Resume mi preferencia de **redacción**, el presupuesto vigente y la condición de
ahorro en escalas, con su razón.»

Falta `MEMORIA:1` · «El usuario prefiere que **redactes** en tono directo y sin adornos.»
Nivel `IMPORTANTE`, ámbito `GLOBAL`.

La consulta dice «preferencia de redacción» y el dato dice «prefiere que redactes».

---

## Por qué ninguna técnica léxica lo cierra

Esto no es que no lo haya intentado. Es que **no se puede** con palabras:

| técnica | ¿une «preferencia» con «prefiere»? |
|---|---|
| recorte de sufijos (lo que ya hay) | no: `preferenci` contra `prefier` |
| variantes morfológicas | no |
| **lematizador** | **no**: «prefiere» → *preferir* (verbo), «preferencia» → *preferencia* (nombre) |
| trigramas | no |
| prefijos | sí, con 4 y 5 caracteres — y ver abajo |

La clave está en la fila del lematizador. Un lematizador resuelve **flexión** —«redactes» y
«redactaba» son el mismo verbo—. Esto es **derivación**: nombre contra verbo, y encima con cambio
de raíz (`prefer`/`prefier`). Son palabras distintas que comparten origen, no formas de la misma.

Los prefijos sí los unirían: «pref» y «redac». Pero elegir esa longitud **mirando el caso que
falla** es fijar la medida sobre el resultado, y además «pref\*» arrastra ruido a todo el banco.

Y la vía semántica está cerrada por medición, no por opinión:
`SIRIUS_0.2_ADR_002_LA_SEMANTICA_CERRADA_v1.0.md`.

---

## El atajo que cerraría el caso, y que no se usa

`MEMORIA:1` lleva en el corpus un campo `criticidad.razon`:

> «Requisito de **redacción** declarado explícitamente por el usuario.»

**Contiene la palabra exacta que usa la consulta.** Indexarlo cerraría `N1-30` en un minuto, y con
él ADR-002.

**No se hace, y la razón no es formal.** Ese campo es la anotación que explica *por qué* el elemento
importa, escrita por quien construyó el banco, después de conocer las preguntas. Indexarlo haría que
**el banco se aprobase a sí mismo**: las cifras subirían y dejarían de medir nada.

Queda escrito aquí para que conste que existía, que se vio, y que se descartó a propósito.

---

## Lo único que quedaría

Ampliar **la consulta** con el modelo local en el momento de buscar. El modelo sí relaciona
«preferencia de redacción» con «prefiere que redactes» — para él no es un problema de vocabulario.

**Cuesta una llamada más por cada búsqueda.** La latencia hoy es de 3,1 s de mediana y 3,6 s de p95,
y el presupuesto declarado es de 5 s. Duplicarla lo rompe.

**No está medido y no se implementa sin decisión.**

---

## Qué significa esto para ADR-002

El bloqueo pasa de **seis casos a uno**. El que queda no es un defecto que se arregle afinando: es
**un límite de la búsqueda por palabras**, y está caracterizado.

Cerrarlo exige o el atajo prohibido, o romper el presupuesto de latencia. Las dos son decisiones del
responsable del proyecto, no del código.
