# Nota de arranque — un buscador que devuelva fuentes

Fecha: 2026-08-27. Publicada ANTES del primer cambio de código (ADR-001).

## Lo medido que motiva esto

Pasada 3 del banco (run 33088012637), desglose de NVIDIA:

```
[NO] P1 fuentes=0   [NO] P2 fuentes=0   [ok] P3 fuentes=1   [ok] P4 fuentes=1
[NO] P5 fuentes=0   [NO] P6 fuentes=0   [NO] P7 fuentes=0
```

Cinco de siete fallos son `fuentes=0`: DuckDuckGo, desde las IP de los runners
de GitHub, devuelve vacío casi siempre (2 búsquedas con resultados de 7). Con la
regla `fuentes > 0` —irrenunciable— cada búsqueda vacía suspende aunque la
respuesta sea correcta. **El 80 % de S2 no se puede medir con este buscador.**

## Lo que se decide construir

1. `RETRIEVER: "tavily,duckduckgo"` en las DOS configuraciones (la comparación
   sigue teniendo una sola variable: el modelo). Comprobado en el código de
   `gpt-researcher` 0.15.1: sin `TAVILY_API_KEY`, su buscador captura la
   excepción y devuelve lista vacía —queda INERTE y DuckDuckGo se comporta como
   hoy—; con la clave, aporta fuentes. Es decir: esto no cambia nada hasta que
   el propietario ponga la clave, y lo cambia todo cuando la ponga.
2. Claves OPCIONALES en el esquema de configuraciones: hoy el esquema admite
   exactamente UNA clave (`variable_de_clave`/`clave_destino`), y el guardián
   anti-secretos rechaza —con razón— cualquier nombre `*_API_KEY` en `entorno`.
   La clave de Tavily necesita una vía declarada: `claves_opcionales`, que si la
   variable no está en el entorno del padre, se omite en silencio (opcional
   significa opcional: sin estado `sin_clave`).
3. El workflow pasa `TAVILY_API_KEY` desde el secreto
   `SIRIUS_INVESTIGADOR_TAVILY_KEY` (vacío si no existe; el paso de claves
   obligatorias NO lo exige).

## Las cuatro preguntas

1. ¿La prueba nueva se ve FALLAR antes: una configuración con clave opcional
   presente la entrega al hijo, y sin ella no rompe nada?
2. ¿El guardián anti-contaminación sigue mordiendo? Una clave opcional NO
   declarada que aparezca en el entorno del hijo tiene que seguir siendo
   ConfiguracionInvalida.
3. ¿`sin_secretos` tapa también el valor de las claves opcionales en la salida
   capturada y en el JSON?
4. ¿Las dos configuraciones declaran el MISMO buscador? Si difieren, la
   comparación tendría dos variables y el número no diría de cuál viene.

## Criterio de parada

- (a) Si la clave opcional exigiera cuenta de OpenAI o Anthropic, se para.
  Tavily no lo es.
- (b) Si «opcional» acabara significando «la medición pasa aunque el buscador
  pedido no exista», se para: no puede haber verde construido sobre una pieza
  ausente. La regla `fuentes > 0` ya cubre esto —sin fuentes no hay acierto—.
- (c) Regla de las dos rondas (ADR-001).

## Lo que NO se toca

Ni el banco de preguntas, ni la regla `fuentes > 0`, ni los modelos, ni el
atestado. Y la tensión detectada en P1/P2 (preguntas «de memoria» cuyo propósito
diagnóstico queda anulado por `fuentes > 0`) se DEJA ESCRITA y no se arregla
aquí: tocar la regla del acierto es otra decisión, con su propia nota.
