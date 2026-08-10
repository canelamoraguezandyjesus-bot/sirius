# ADR-002 — No conceder a la automatización permiso sobre sus propios workflows

- Estado: PROPUESTO
- Fecha: 2026-08-09
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario

## Contexto y problema

La incidencia #140 pedía arreglar un defecto en `.github/workflows/repair-sirius-work.yml`.
Se activó la automatización y el implementador **completó el trabajo entero**
—arreglo, cuatro pruebas verificadas por mutación, validaciones en verde— y
después no pudo publicarlo. GitHub rechazó el push:

```
refusing to allow a Personal Access Token to create or update workflow
.github/workflows/repair-sirius-work.yml without workflow scope
```

La credencial con la que corre la automatización **no tiene permiso para
escribir bajo `.github/workflows/`**. El implementador se detuvo con
`BLOCKED_BY_DECISION` y dejó el diagnóstico y las opciones.

Esa parada, por sí sola, fue el primer recorrido completo del ciclo desde que
existe: las dos tentativas anteriores (5 y 7 de agosto) murieron sin escribir
veredicto, que es el defecto que la PR #136 corrigió.

## Criterio de parada (escrito ANTES de decidir)

Si la única forma de que la automatización complete una incidencia es ampliar
sus credenciales, **no se amplían sin decisión explícita del propietario**, y la
alternativa se busca fuera del alcance de la propia automatización.

## Opciones consideradas

1. **Conceder el alcance `workflow`** a la credencial de la automatización.
2. **Ejecutar en sesión interactiva** las incidencias cuyo alcance toca
   `.github/workflows/`, con el propietario fusionando como siempre.
3. Excluir del catálogo las incidencias que tocan workflows.

## Decisión

**Opción 2.** No se amplía la credencial.

Un agente con permiso para reescribir los workflows que lo gobiernan puede
desactivar sus propias salvaguardas: el veto de merge automático, la puerta de
activación, el presupuesto de tiempo, el filtro de autor de confianza. La
frontera no es incidental —es la que hace que el resto del contrato signifique
algo— y ampliarla por comodidad convertiría todas las demás reglas en
recomendaciones.

La opción 3 se descarta porque no resuelve nada: el trabajo sigue haciendo
falta, solo dejaría de estar registrado.

En consecuencia, las incidencias cuyo **alcance permitido** incluya archivos
bajo `.github/workflows/` se ejecutan en sesión interactiva. La automatización
conserva íntegro el trabajo sobre código de producto, que es su caso normal.

## Comprobación que la sostiene

- El rechazo de GitHub está citado literalmente arriba, del veredicto publicado
  por el implementador en la incidencia #140.
- La automatización **no perdió el trabajo en silencio**: publicó su veredicto
  con el diagnóstico completo, que es exactamente la propiedad que la PR #136
  vino a garantizar.
- El arreglo técnico de la #140 acompaña a este ADR, hecho en sesión según la
  decisión que aquí se registra: `parada()` fija ahora un plazo propio
  (`_sirius_now() + 120`) en lugar de soltar el que tenía, y cuatro pruebas
  (GATE-001..004) lo fijan ejecutando la función **extraída del YAML**, no una
  copia. Verificadas por mutación en las dos direcciones: devolver el `unset`,
  desbordar el presupuesto y publicar con el plazo heredado hacen fallar cada
  una su prueba.

## Consecuencias

- El ciclo autónomo **no puede cerrar por sí solo** las incidencias que tocan
  workflows: el push será rechazado.
- **Cómo se detenga NO está garantizado por el repositorio.** En la #140 salió
  `BLOCKED_BY_DECISION`, que es el desenlace correcto, pero fue una elección del
  agente y no una regla impuesta: la puerta de activación comprueba estado,
  etiquetas y completitud del cuerpo, y ni ella ni el prompt reconocen el
  alcance «toca workflows». Otro intento podría acabar en `FAILED_SAFELY` o sin
  veredicto. Decirlo de otro modo sería prometer un determinismo que el código
  no da.
- Por eso lo que sigue es un **procedimiento operativo manual**, no una
  garantía: al abrir una incidencia, mirar si su alcance toca
  `.github/workflows/` y, en ese caso, resolverla en sesión en vez de activarla.
  Si el olvido llega a ser frecuente, la corrección de raíz es que la puerta de
  activación reconozca ese alcance y rechace antes de arrancar; queda anotado
  como trabajo pendiente, no como algo ya hecho.
- Lo que esto **no** hace: no reduce lo que la automatización puede hacer sobre
  código de producto, ni cambia el contrato operativo, ni afecta a la revisión
  dual.
- Si algún día el volumen de incidencias sobre workflows lo justifica, la
  alternativa a estudiar **no** es ampliar la credencial del agente, sino un
  cauce con revisión humana intermedia. Queda dicho para que no se reabra por
  la vía cómoda.

## Alternativas descartadas y por qué

- **Ampliar el alcance de la credencial**: convierte al agente en editor de sus
  propias reglas y vacía de contenido el resto de salvaguardas.
- **Buscar o sustituir el token por otro con más alcance**: es sortear la
  restricción, no resolverla. El propio implementador lo señaló y se detuvo, que
  es lo que debía hacer.
- **Reducir el cambio para no tocar el workflow**: dejaría sin corregir el
  defecto que la incidencia pide arreglar, que está justamente en ese archivo.
