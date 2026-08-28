# Evidencia — B1: investigar desde una orden

Fecha: 2026-08-28. Nota de arranque:
`docs/audits/arranque-b1-investigar-desde-una-orden.md`. Decisión: ADR-099.

## Las cuatro preguntas, con su mutación vista caer

| pregunta | prueba | mutación |
|---|---|---|
| 1. la fila entra con las mismas etiquetas | `test_b1_investigacion_recibe_las_mismas_etiquetas_que_programacion` (vista FALLAR con `ClaseNoDespachableError` antes de la fila) | M1: quitar la fila |
| 2. la exclusión va ANTES de consumir | `test_el_implementador_excluye_al_investigador_antes_de_consumir` (lee los DOS YAML y compara índices de pasos) | M2: moverla detrás |
| 3. el documento pasa su guardián | `test_el_documento_pasa_el_guardian_de_caducidad` (con el MISMO parser del guardián) | — (cubierta por la familia M4/M5) |
| 4. el provisional antes de nada | `test_el_provisional_se_escribe_antes_de_nada` (el hijo LEE el veredicto mientras corre) | M4: quitar el provisional |
| (ciclo) veredicto con `always()` | `test_el_veredicto_se_aplica_siempre_que_la_puerta_dejara_pasar` | M3: quitar el always() |
| (regla) sin fuentes no se publica | `test_el_hijo_no_publica_un_informe_sin_fuentes` (hijo REAL, herramienta fingida) | M5: publicar igual |

## Dos defectos propios cazados por el método, en esta misma rama

1. **M5 pasó en verde la primera vez**: las pruebas del padre fingían al hijo
   entero, así que la regla «sin fuentes no se publica» -que vive en el hijo-
   no la ejecutaba nadie. La mutación existió para esto: se añadió la pareja de
   pruebas del hijo real (regla + anti-vacua) y M5 muerde.
2. **El guardián vacuo, dentro de mi propio guardián**: el selector del paso
   del veredicto buscaba el NOMBRE del guion y lo encontró en un comentario del
   paso de la PR. Corregido a buscar la INVOCACIÓN. Y al restaurar M5 se
   comprobó otra vez que `git checkout --` no restaura un fichero sin
   confirmar: la mutación se quedó dentro y la delató la línea de base en rojo;
   revertida a mano con el diff delante.

## Actualizaciones honestas de guardianes viejos

- `test_clase_fuera_de_la_tabla_no_se_despacha` vigilaba con `investigacion`;
  pasa a `CONSULTA_LARGA` con la historia en su docstring.
- La reproducción CLI de H-17 pasa a LABORATORIO (señal forzada a
  consulta-larga): con la fila nueva, el intérprete v0 ya no produce NINGUNA
  clase no despachable con texto real, y ese hecho queda escrito.

## Criterio de parada, revisado al cierre

- (a) Ningún marcador nuevo: `PR abierta:`, veredicto del implementador,
  `sirius_apply_verdict.sh` con rol `implementer`. Cumplido.
- (b) Tope del ejecutor: 30 min (≤ 85). Guardián propio y los del contador en
  verde.
- (c) Claves: NVIDIA + Tavily, ninguna prohibida. Guardián propio.
- (d) Dos rondas: los dos defectos de arriba son de familias distintas
  (cobertura fingida de más; selector vacuo). No se alcanzó la segunda ronda de
  ninguna familia.

## Lo que queda EXPRESAMENTE abierto

B1 NO se cierra en el registro con esta PR: falta la vuelta entera en el
servidor con una orden real -mismo criterio que C2 con la #331-. El plan: tras
fusionar, despachar «Investiga…» real, ver incidencia → informe → PR → revisión,
y cerrar B1 con esa evidencia.
