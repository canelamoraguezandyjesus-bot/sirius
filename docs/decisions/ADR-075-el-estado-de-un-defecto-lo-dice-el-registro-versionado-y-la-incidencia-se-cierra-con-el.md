# ADR-075 — El estado de un defecto lo dice el registro versionado y la incidencia se cierra con el

- Estado: PROPUESTO
- Fecha: 2026-08-22
- Aprobación: la fusión de la PR #271 por el propietario

## Contexto y problema

El 22 de agosto de 2026, en un recuento de estado, se le presentaron al propietario
**siete defectos abiertos**: H-1, H-2, H-5, H-6, H-8, H-9 y H-10. Él respondió que
creía que esos ya se habían arreglado.

Tenía razón. **No había ninguno abierto.** Los doce defectos del registro estaban
arreglados y fusionados en `main`.

El número salió de listar las incidencias abiertas de GitHub y tratar «abierta»
como sinónimo de «sin arreglar». No lo es, y en este repositorio hay un motivo
estructural para que no lo sea: cuando un defecto se arregla, el trabajo se
encarga **en una incidencia nueva** —la del bloque de corrección— y la PR se
fusiona por squash citando esa incidencia. La del defecto nunca aparece en la
frase que GitHub interpreta, así que el cierre automático no dispara sobre ella.

Ocurrió incluso cuando el commit lo pedía explícitamente: `f3fa32c` contiene
`Cierra #219` y la #219 siguió abierta, porque el squash se hizo desde otra rama.

Al mismo tiempo, el registro versionado `docs/audits/registro_defectos.yml` —que
existe precisamente para no depender del estado de las incidencias— daba H-11 por
`abierto` cuando su arreglo se había fusionado en `18b4f2a` (#248) y C2 lo había
consumido después en `fc11c08` (#252).

Es decir: **las dos fuentes fallaron a la vez, por motivos distintos**, y ninguna
sostenía la afirmación que se hizo.

## Criterio de parada (escrito ANTES de decidir)

Decidido antes de comprobar ningún defecto:

- **(a)** Si al comprobarlos resulta que alguno **sí** está abierto de verdad, no
  hay decisión que tomar: hay un defecto que arreglar, y este ADR no se escribe.
- **(b)** Si la discrepancia está solo en las incidencias y el registro versionado
  era correcto, tampoco hay decisión: hay que cerrar incidencias y ya está.
  Este ADR solo tiene sentido si **ambas** fuentes fallaron, porque solo entonces
  el problema es cuál manda y no quién se despistó.
- **(c)** Si arreglar esto exige tocar `.github/**` —por ejemplo, un workflow que
  cierre incidencias automáticamente—, se para: ADR-002 lo prohíbe a la
  automatización, y convertir una corrección de dato en un cambio de disparadores
  es exactamente la clase de ampliación que este método no permite.

## Opciones consideradas

1. **Cerrar las siete incidencias y no escribir nada.** Rápido y deja el árbol
   limpio hoy, pero no impide que vuelva a pasar: el mecanismo que las dejó
   abiertas sigue intacto y el próximo recuento volverá a contarlas.
2. **Hacer que la incidencia del defecto sea la fuente de verdad**, y exigir que
   cada arreglo se encargue desde ella. Alinea las dos fuentes, pero rompe el
   flujo real: un defecto y su corrección son trabajos distintos, con contratos
   distintos, y forzarlos a compartir incidencia mezcla el hallazgo con el encargo.
3. **Declarar autoritativo el registro versionado**, y tratar el estado de la
   incidencia como una proyección que puede quedarse atrás. Es lo que el registro
   ya pretendía ser; solo faltaba decirlo y actuar en consecuencia.

## Decisión

**El estado de un defecto lo dice `docs/audits/registro_defectos.yml`.** El estado
de la incidencia de GitHub es una proyección, y una proyección que se quede atrás
no es evidencia de nada.

De ahí, tres reglas:

1. **Ningún recuento de defectos se hace listando incidencias abiertas.** Se lee
   el registro. Una incidencia abierta cuyo defecto figura `cerrado` en el registro
   está huérfana, no rota.
2. **Cerrar un defecto en el registro incluye cerrar su incidencia**, citando el
   commit que lo arregló. Es un gesto de la sesión que fusiona, no de un workflow:
   ADR-002 mantiene `.github/**` fuera del alcance de la automatización, y el
   criterio de parada (c) de este ADR lo confirma.
3. **El campo `cerrado_por` no es decorativo.** Es lo que convierte «cerrado» en
   una afirmación comprobable: sin el SHA, «cerrado» es una palabra que alguien
   escribió.

Esto **no** cambia el formato del registro ni añade ninguna comprobación nueva a
CI. Es una regla sobre qué fuente se consulta.

## Comprobación que la sostiene

Cada defecto se comprobó contra el commit fusionado en `main`, no contra el estado
de su incidencia:

```
$ git log origin/main --oneline --extended-regexp --grep="(^|[^0-9-])H-8([^0-9]|$)"
f3fa32c Las ocho operaciones con guarda de estado entran en la tabla (H-8) (#235)
```

| defecto | incidencia que seguía abierta | arreglo fusionado en |
|---|---|---|
| H-1 | #215 | `e52507a` (#222) |
| H-2 | #214 | `415c663` (#227) |
| H-5 | #216 | `9d79d7c` (#221) |
| H-6 | #217 | `b45fed8` (#226) |
| H-8 | #219 | `f3fa32c` (#235) |
| H-9 | #224 | `4018d01` (#234) |
| H-10 | #236 | `646578b` (#239) |

Y el estado del registro tras corregir H-11:

```
$ python3 -c "import yaml; d=yaml.safe_load(open('docs/audits/registro_defectos.yml')); \
items=next(v for v in d.values() if isinstance(v,list)); \
print('abiertos:', [i['id'] for i in items if i.get('estado')!='cerrado'] or 'NINGUNO')"
abiertos: NINGUNO
total: 12
```

El criterio de parada se resolvió por **(c-no aplica)**: ninguno estaba abierto de
verdad, y ambas fuentes fallaron —las incidencias por el squash desde otra rama,
el registro por H-11 sin actualizar—, que es la condición bajo la cual el criterio
(b) decía que este ADR sí tiene sentido.

## Consecuencias

- El recuento de estado se vuelve barato y fiable: un `yaml.safe_load` en vez de
  una lista de incidencias que hay que interpretar.
- Queda **una deuda declarada**: cerrar la incidencia sigue dependiendo de que
  alguien lo haga al fusionar. Este ADR no lo mecaniza, y por tanto no afirma que
  no vuelva a pasar — solo que, cuando pase, el recuento ya no se equivocará,
  porque no mira ahí. Mecanizarlo es candidato para la incidencia #267.
- El campo `cerrado_por` pasa a ser obligatorio de hecho para cualquier defecto que
  se marque cerrado. Hoy lo cumplen los doce.

## Alternativas descartadas y por qué

- **La opción 1 (cerrar y callar)** se descarta porque el defecto no era que siete
  incidencias estuvieran abiertas: era que se afirmó un número sin comprobarlo, y
  eso se repite mientras la fuente consultada siga siendo la equivocada.
- **La opción 2 (la incidencia manda)** se descarta porque obligaría a que el
  arreglo de un defecto se encargue desde la incidencia del defecto, mezclando el
  hallazgo con el contrato de trabajo. ADR-010 ya separó esas dos cosas a
  propósito: un hallazgo no se convierte en encargo automáticamente.
- **Un workflow que cierre la incidencia al fusionar** se descarta aquí, no por
  mala idea, sino por el criterio de parada (c): tocaría `.github/**`. Si se
  quiere, es un trabajo aparte y con su propia decisión.
