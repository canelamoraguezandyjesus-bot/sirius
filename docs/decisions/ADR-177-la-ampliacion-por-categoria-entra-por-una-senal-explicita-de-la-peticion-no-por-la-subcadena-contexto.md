# ADR-177 — La ampliación por categoría entra por una señal explícita de la petición, no por la subcadena «contexto»

- Estado: PROPUESTO
- Fecha: 2026-09-12
- Aprobación: el propietario, al fusionar la PR de la incidencia #581.

## Nota de arranque (escrita ANTES de tocar código)

Las cuatro preguntas de ADR-001, decididas antes de ver ningún resultado del
cambio:

1. **¿Qué afirmo?** Que la ampliación por categoría (el bloque `siembra`,
   M20/M14, `rank_relevant_knowledge`) puede pasar a activarse por un campo
   booleano propio de la `Peticion` **sin que cambie ni una de las peticiones
   que hoy la activan**: las 2 del banco (`B04-CA-33` y `B04-CA-34`, únicas
   con propósito `ensamblar_contexto_b05`) y todas las de producción salvo
   las no autorizadas.
2. **¿Con qué lo compruebo?** Con tres pruebas deterministas vistas fallar
   antes del cambio (un propósito con «contexto» y sin señal **no** amplía;
   la señal **sí** amplía con un propósito arbitrario; la traducción del
   banco enciende la señal exactamente para `ensamblar_contexto_b05` y
   `PERMISO_SIN_AUTORIZAR` la apaga) y con el recuento del banco
   `scripts/diagnosticar_busqueda_del_banco.py --peticion` antes y después.
3. **¿Qué resultado me haría estar equivocado?** Que el recuento del banco se
   mueva **en una sola cifra**. Esa es la predicción, publicada aquí antes de
   la segunda medición.
4. **¿Qué queda fuera?** Cambiar qué peticiones activan la ampliación
   (`B04-CA-30`/`MEM-001` es un hueco medido que el propietario decidió el
   12-09-2026 no pagar), abrir `category_matching_enabled`, los ejes y
   cualquier cambio de ranking.

## Criterio de parada (escrito ANTES de decidir)

Si el recuento `--peticion` posterior al cambio difiere del anterior en
cualquiera de sus cuatro cifras, **el cambio no es equivalente** y se para: no
se acomoda el criterio ni se reajusta la tabla cerrada para que cuadre, se
explica caso a caso qué peticion cambió de lado y por qué. Si dos rondas de
revisión traen defectos de la misma familia, se para y se busca la raíz.

## Contexto y problema

Pendiente de redactar con la evidencia del trabajo.

## Decisión

Pendiente.

## Comprobación que la sostiene

Pendiente.

## Consecuencias

Pendiente.

## Alternativas descartadas y por qué

Pendiente.
