# Nota de arranque — atestar al buscador antes de gastar en medirlo

Fecha: 2026-08-28. Publicada ANTES del primer cambio de código (ADR-001).

## Lo medido que motiva esto

Pasada 4 del banco (run 33135502242), la primera con la clave de Tavily puesta.
El log del trabajo demuestra que la clave llegó (`TAVILY_API_KEY: ***` en el
`env:` del paso) y aun así:

```
nvidia: medida — 2/7, fuentes medias 0,3
  [NO] P1 fuentes=0 ... [ok] P4 fuentes=1 ... [ok] P6 fuentes=1 ... [NO] P7 fuentes=0
```

**Idéntico a la pasada sin Tavily.** El buscador nuevo no aportó ni una fuente.
Algo entre la herramienta y Tavily no funciona, y desde esta máquina no se puede
preguntar (curl denegado): la única vía con red y con clave son los runners.

## La hipótesis que hay que comprobar (no asumir)

`gpt-researcher` 0.15.1 manda la clave de Tavily **en el cuerpo** de la petición
(`"api_key": ...`, leído en su `retrievers/tavily/tavily_search.py`), no en
cabecera `Authorization`. Si Tavily dejó de aceptar esa forma, la herramienta se
queda sin fuentes con la clave BIEN puesta — indistinguible de un buscador roto
salvo que alguien le haga al servidor esta pregunta exacta. También puede ser
una clave mal copiada, o resultados vacíos por otra causa: **el detalle de la
respuesta HTTP distingue los tres casos**, y hoy nadie lo mira.

Es la escalera de ADR-095 aplicada al buscador: existe la clave → ¿responde el
servidor? → ¿responde A LA LLAMADA QUE HACE LA HERRAMIENTA? La tercera pregunta
es la que nadie hizo.

## Lo que se construye

`preflight.py` gana el atestado del buscador: UNA búsqueda real a Tavily con la
MISMA forma de llamada que usa la 0.15.1 (clave en el cuerpo, sin cabecera de
autorización), con los tres estados de siempre —USABLE / OCUPADO / NO RESPONDE—
y el detalle de la respuesta en el informe. Sin clave: `sin_clave`, informativo,
no un error. Y el paso de atestado del banco lo exige ANTES de gastar los 25
minutos: buscador NO RESPONDE = no se mide.

## Las cuatro preguntas

1. ¿Una respuesta 200 con resultados da USABLE, y el detalle dice cuántos?
2. ¿Un transitorio (503/429) da OCUPADO —«no cambies nada, vuelve a probar»— y
   NUNCA NO RESPONDE? Es la lección de la PR #374, aplicada aquí desde el día uno.
3. ¿Un 4xx definitivo da NO RESPONDE **con el cuerpo de la respuesta visible**?
   Ese texto es la respuesta que buscamos (clave inválida vs forma de
   autenticación rechazada).
4. ¿`main` llama al atestado del buscador de verdad y su veredicto cuenta en el
   código de salida? La pieza sin cable es la enfermedad de esta casa: octavo
   caso si se repite.

## Criterio de parada

- (a) La comprobación cuesta 1 crédito de 1000/mes. Si costara cuota de las APIs
  de modelos, se replantea.
- (b) `sin_clave` NO puede poner rojo el preflight de quien no usa Tavily: la
  clave es opcional en todo el diseño (PR #380) y esto no la vuelve obligatoria.
- (c) Regla de las dos rondas (ADR-001).

## Lo que NO se toca

Ni el banco, ni la regla `fuentes > 0`, ni los modelos, ni la forma en que la
herramienta llama a Tavily (eso, si está rota, es la decisión SIGUIENTE, con la
respuesta del servidor delante).
