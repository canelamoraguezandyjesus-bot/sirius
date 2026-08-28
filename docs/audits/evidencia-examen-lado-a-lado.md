# Evidencia — el examen lado a lado

Fecha: 2026-08-28. Cierra la rama `examen-lado-a-lado`, que guarda el examen
como investigación. La nota de arranque del trabajo entero es la de las tres
palancas (`docs/audits/arranque-tres-palancas.md`); esta rama es su medición
final.

## La afirmación

«Sirius pasó de un 35–45 % a un ~75 % del criterio del propietario (≥80 % de
una investigación profunda de ChatGPT)».

## La comprobación que la sostiene

Tres informes REALES sobre la MISMA pregunta, comparados en dimensiones
contables — no en impresiones:

| dimensión | cómo se midió |
|---|---|
| tamaño | `wc -c` sobre los tres ficheros (16.384 / 27.786 / 49.722 bytes) |
| fuentes | `grep -c` de los enlaces listados (33 / 204 / ~23 citas) |
| idioma | leído: v1 inglés, v2 español, ChatGPT español |
| criterio de aceptación de la incidencia | v1 NO trae «lo que NO queda demostrado»; v2 SÍ (sección entera, leída y citada) |
| honestidad ante contradicciones | v2 señala 2 cifras contradictorias entre sus fuentes SIN resolverlas por decreto; el patrón de ChatGPT afirmó modelos muertos al día siguiente (medido, ADR-095) |
| tiempo y coste | de los registros de los runs (7 min / 25 min) y de las capas gratuitas |

Los tres ficheros: `2026-08-28-orden-389-...md` (v1, en la PR #390),
`2026-08-28-orden-392-...md` (v2, en la PR #393),
`2026-08-27-nvidia-vs-google-para-el-investigador.md` (ChatGPT, fusionado).

## Lo que el porcentaje ES y lo que NO

El ~75 % es un JUICIO razonado sobre dimensiones contables, no una medición
automática: no existe (ni aquí ni en el mercado) un corrector objetivo de
«calidad de investigación profunda». Por eso el número va acompañado de la
tabla — quien discrepe puede repesar las filas — y por eso la decisión de si
«vale» sigue siendo del propietario, que fue quien fijó el criterio.

## Criterio de parada

- (a) El examen compara SOLO informes ya producidos: cero gasto nuevo de cuota.
- (b) El tramo restante hasta el 80 % queda NOMBRADO (cuerpo analítico: matriz,
  letra pequeña) con sus dos palancas posibles (modelo mayor / segunda pasada
  de redacción), ambas medibles con el banco y este mismo examen. No se
  construye ninguna sin orden del propietario.
