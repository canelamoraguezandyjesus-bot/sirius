# ADR-095 — La escalera de cuatro preguntas, y el atestado que impide medir un modelo muerto

- Estado: PROPUESTO
- Fecha: 2026-08-27
- Aprobación: la fusión de la PR por el propietario
- Contexto: S2/B1, incidencia #258. Nace de cuatro rondas fallidas en una noche
- Relacionadas: ADR-001 (disciplina de evidencia), ADR-020 (GPT Researcher),
  ADR-091 (buscar antes de responder), ADR-093, ADR-094

## Contexto y problema

La noche del 26 al 27 de agosto de 2026, con las dos claves de API ya puestas, se
intentó configurar el investigador **cuatro veces** y las cuatro fallaron:

| ronda | de dónde salió el nombre | qué pasó |
|---|---|---|
| 1 | el plan y el spike I2 | `text-embedding-004` y `nv-embedqa-e5-v5`: **muertos** |
| 2 | una investigación profunda con fuentes oficiales, de ese mismo día | sus sustitutos **ni siquiera estaban en el catálogo** |
| 3 | el catálogo real del servidor | los tres **404 al usarlos** |
| 4 | seis candidatos del catálogo | los seis eran de la misma sub-familia y ninguno servía |

### La raíz, y no es «los catálogos cambian»

Eso es cierto y **no explica nada de lo ocurrido después de las 03:29**, que es
cuando la clave ya funcionaba y el catálogo estaba en la mano.

La raíz es ésta:

> **Cada ronda se contestó la pregunta más barata que se podía responder sin
> llamar al proveedor, se declaró por escrito la pregunta que faltaba, y se
> entregó igual.**

El apartado «lo que esto NO garantiza» —que este repositorio usa para no
prometer de más— **funcionó como permiso de entrega en vez de como freno**. El
fallo siguiente quedó escrito, de puño propio, minutos antes de ocurrir:

- `configuraciones.yml:29` decía *«los nombres de abajo NO se han comprobado
  contra los catálogos reales»*. Dos horas después, tres de cuatro estaban
  muertos.
- `evidencia-preflight-investigador.md:55` decía *«tampoco comprueba que esté
  incluido en la cuota gratuita — eso solo se sabe usándolo»*. Una hora después,
  404 por cuota.
- `evidencia-modelos-vivos.md:37` decía *«eso solo se sabe usándolos, y es lo
  siguiente»* **en el mismo commit que cambiaba los tres nombres**. Quince
  minutos.

Y hay un error de cálculo escrito con todas las letras en
`configuraciones.yml:34`: *«corregir el nombre aquí es un cambio de una línea»*.
Ahí está entero. Con el coste del error modelado como **una línea**, adivinar es
racional y comprobar es un lujo. El coste real fue **una noche**.

### El agravante

Esta misma raíz ya estaba nombrada **24 horas antes**, en este repositorio, en
`evidencia-medir-investigador.md:113`: *«el arnés medía lo que se le PEDÍA, nunca
lo que OCURRÍA»*. Adivinar un nombre contra un documento en vez de contra el
servidor **es esa raíz con otro disfraz**. Las cuatro rondas de esta noche no son
la primera y la segunda: son la tercera, cuarta, quinta y sexta de una familia
que ADR-001 §2 obligaba a parar el día antes.

## Criterio de parada (escrito ANTES de decidir)

**(a)** Si el arreglo se queda en «a partir de ahora compruebo antes», no vale.
Eso es pedir más cuidado, que es la ausencia de una regla — y además ya se pidió,
por escrito, cuatro veces, en los propios ficheros que fallaron.

**(b)** Si el arreglo deja el resultado de una comprobación **solo en la cola de
un log**, tampoco. Hoy cada llamada muere ahí y en prosa de `docs/audits/`:
**ningún programa puede leerlo**, así que ningún guardián puede exigirlo.

**(c)** Si tras el arreglo sigue siendo posible que el banco de medición corra
sobre un modelo muerto, se para y se piensa otra cosa. La pregunta 4 de la nota
de arranque de ADR-001 pide lo imposible, no lo improbable.

## Decisión

### 1. La escalera de cuatro preguntas queda escrita

Son cuatro preguntas distintas, cada una más cara que la anterior, y **ninguna
sustituye a la de abajo**:

| pregunta | quién la contesta | coste | qué tumbó esta noche |
|---|---|---|---|
| ¿qué modelo pongo? | un documento | gratis | tres nombres muertos |
| ¿existe? | el catálogo del servidor | 13 s | `gemini-2.5-flash` figura y no sirve |
| ¿me responde? | una llamada real | céntimos | uno de cuatro |
| ¿responde BIEN? | el banco de preguntas | minutos y cuota | **el único que importa** |

**Un documento no es una fuente sobre el estado de un servicio externo.** Ni un
plan, ni un spike, ni una investigación profunda del mismo día. Sirven para
decidir qué preguntar, nunca para responder.

### 2. El atestado: la memoria que no existía

`scripts/investigacion/modelos_atestiguados.yml`, escrito **solo** por
`preflight.py --atestiguar` y nunca a mano. Por modelo: si existe, si responde,
el código HTTP, el error y la fecha en UTC.

Esto convierte el resultado de una llamada en **un dato que un programa puede
leer**, que es lo que exige el criterio (b). Hasta hoy moría en un log.

### 3. El guardián que lo hace imposible

`comparar_investigadores.py` se niega a medir —código de salida propio— si algún
modelo de `configuraciones.yml` no tiene atestado `usable: true` con fecha
reciente. Y el workflow del banco gana un paso de preflight del que depende.

Con eso, «33 guardianes en verde midiendo un cadáver» deja de ser improbable y
pasa a ser **imposible**, que es lo que pedía el criterio (c).

## Comprobación que la sostiene

Todo lo de arriba está medido, no razonado:

```
grep -rln preflight tests/                       -> vacío (CERO guardianes)
grep -c preflight .github/workflows/medir-...    -> 0 (el banco no depende de él)
ADR escritos en la noche del 26-08               -> 0
_candidatos(google, catalogo, 'gemini', 4)       -> 3 de 4 son la generación 2.5,
                                                    que el servidor ya declaró muerta
```

Los cuatro modelos que **sí responden**, encontrados probándolos:

```
CANDIDATO OK  models/gemini-3.5-flash          CANDIDATO OK  nvidia/nemotron-3-nano-30b-a3b
CANDIDATO OK  models/gemini-embedding-001      CANDIDATO OK  nvidia/llama-nemotron-embed-vl-1b-v2
```

## Consecuencias

**Configurar un modelo cuesta ahora una llamada más.** Ése es el precio
deliberado, y el cálculo que lo justifica es el que estaba mal: no cuesta «una
línea», cuesta una noche.

**El banco no puede correr sobre lo no atestiguado.** Si el atestado falta o está
viejo, se para en vez de dar un número. Un número sobre un cadáver es peor que no
tener número, porque se cree.

**Lo que este ADR NO arregla, y hay que decirlo sin adornos:** no impide que yo
vuelva a escribir «lo que esto no garantiza» y entregue igual. Eso es conducta y
no se comprueba por programa —igual que ADR-091—. Lo único que se puede hacer es
quitarle el sitio: por eso el arreglo no es una promesa, es un fichero que un
guardián lee.

## Alternativas descartadas y por qué

- **«Comprobar siempre antes de configurar».** Criterio (a). Ya estaba escrito
  cuatro veces en los ficheros que fallaron.
- **Dejar el resultado en el log y leerlo a mano.** Criterio (b). Lo que no puede
  leer un programa no lo puede exigir un guardián.
- **Fijar los modelos y no volver a tocarlos.** Los proveedores retiran modelos:
  `gemini-2.5-flash` entero murió en semanas. Congelar es elegir la fecha del
  próximo fallo, no evitarlo.
