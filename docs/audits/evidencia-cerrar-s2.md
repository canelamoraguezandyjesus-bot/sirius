# Evidencia — cerrar S2

Fecha: 2026-08-28. Esta rama no cambia comportamiento: registra un resultado.
Su evidencia es la pasada que lo produjo, y aquí queda atada.

## La afirmación

S2 pedía: *«una pregunta de respuesta conocida contestada de verdad»* y el
criterio del propietario, *«por lo menos un 80 %»*. Se afirma: **7/7 (100 %)
con fuentes reales en las siete**.

## La comprobación que la sostiene

Run **33141864710** (pasada 6 del banco, 28-08-2026, `main` en `15066b4`),
veredicto `MEDIDA ÚNICA`, código de salida 0 leído por el paso Veredicto:

```
[ok] P1 fuentes=24 s=48.7   [ok] P2 fuentes=30 s=71.3   [ok] P3 fuentes=20 s=33.8
[ok] P4 fuentes=17 s=56.7   [ok] P5 fuentes=31 s=44.8   [ok] P6 fuentes=21 s=40.3
[ok] P7 fuentes=19 s=31.8
nvidia | nvidia/nemotron-3-nano-30b-a3b | 7/7 | 100.0 | 327.4 s | 23.1 fuentes/pregunta
servidor declarado: https://integrate.api.nvidia.com/v1
```

El artefacto `medicion-investigador` (id 9674333442) guarda el JSON con los
siete informes completos, para quien quiera leer las respuestas en vez de
creerse el porcentaje.

## Por qué el número es creíble (las guardas que lo vigilaban)

- El atestado comprobó ese mismo día, ANTES de gastar, que el modelo, la
  vectorización y el buscador respondían (preflight + atestado en la propia
  pasada).
- `fuentes > 0` impide aprobar de memoria; las siete aprobaron con 17–31
  fuentes, no con el mínimo.
- El conteo mira los DOS registros de la herramienta (PR #382), con la fuente
  fantasma descartada por mutación M3.
- `MEDIDA ÚNICA` con cero medidas está descartado por mutación (PR #383, M2):
  este verde no puede salir de una pasada vacía.

## Criterio de parada, escrito antes de mirar el registro de la pasada

- (a) Si la pasada 6 hubiera dado <80 %, S2 NO se cerraba: se registraba el
  número y la decisión siguiente (subir de modelo con la misma clave) quedaba
  para el propietario. No hizo falta.
- (b) El cierre no puede afirmar más de lo medido: la comparación con las
  investigaciones profundas de ChatGPT/Claude queda EXPLÍCITAMENTE fuera -es el
  examen de B1, informes lado a lado- y así lo dice la entrada del registro.

## Lo demás de la rama

El aviso de caducidad de la investigación del 27-08 (dos defectos propios por
el camino: el aviso tras el título en vez de antes -lo cazó su guardián- y un
duplicado al recolocarlo -cazado releyendo el fichero-, los dos corregidos en
esta misma rama). Y una línea del eco del workflow que decía «dos
configuraciones» para un código 0 que ya puede ser MEDIDA ÚNICA.
