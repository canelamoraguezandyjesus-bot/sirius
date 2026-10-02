# Nota de arranque — un defecto se cierra desde la PR que mete el ADR que lo cierra

Rama `claude/un-defecto-se-cierra-desde-la-pr-que-mete-el-adr-que-lo-cierra`.
Fecha: 02-10-2026, 13:30 UTC. Viene de las consecuencias de ADR-227 (PR #674):
H-216 está arreglado y el registro no lo puede decir. Escrita antes de tocar la
guarda.

## La cifra de partida

- H-216 lo declaró ADR-216 (PR #663, incidencia #662): la contradicción de
  etiquetas de #392, apartada a propósito por el reflector, llevaba 27 días sin
  que nadie la mirara. El hecho quedó resuelto el 01-10-2026 (#392 con una sola
  etiqueta; el reflector entregó `WI-20260828-122242` a las 15:57Z) y el
  mecanismo que lo dejaba invisible lo corrige ADR-227 en la PR #674
  (`divergencias.json` junto al diario y la vista de desenlaces con su edad).
- La guarda de ADR-222
  (`test_cada_referencia_pr_es_una_pr_fusionada_en_main_cuando_hay_historia`)
  exige que el `pr:` de un defecto cerrado sea la PR cuyo commit de primer
  padre AÑADIÓ el ADR que lo declaró. Para H-216 eso es la #663, que no lo
  arregló; con `pr: 674` la guarda lo rechaza. ADR-227 lo deja escrito y remite
  a un ADR propio.
- Registro en `main` (`68d81c5f`): 3 defectos abiertos
  (H-202, H-203, H-216); H-216 es el único cuyo arreglo ya está en una PR
  distinta de la que lo declaró.

## Las cuatro preguntas y la predicción

1. ¿Puede cerrarse un defecto desde la PR del arreglo sin perder lo que ADR-222
   quería (que `pr:` lleve, desde un clon de `main`, a un ADR que cuenta el
   arreglo)? Predicción: sí, admitiendo además la PR que metió en `main` un ADR
   posterior que nombra el `H-NNN`; `git show origin/main:<ruta>` da el texto.
2. ¿La ampliación deja pasar una `pr:` cualquiera? Predicción: no. La PR tiene
   que estar fusionada y haber añadido un ADR posterior al declarante que
   nombre el defecto por palabra entera: una PR que no metió ningún ADR, un ADR
   que no lo nombra, un ADR anterior o `H-2160` por `H-216` no valen, y una
   prueba pura con dobles lo fija sin depender del entorno.
3. ¿Se conserva la comprobación fuerte y su anti-vacua? Predicción: sí: todo
   defecto con `pr:` cuyo ADR está en `main` se comprueba por una de las dos
   vías, y el recuento `fuertes == len(con_adr_en_main)` no cambia.
4. ¿Cuánto cuesta? Predicción: una función pura y una prueba nueva en el mismo
   fichero de la guarda, una línea en la skill `registro-de-defectos`, la
   entrada de H-216 cerrada (`cerrado_por: 27a1196b…`, `pr: 674`) y la de
   H-231. Sin tocar ningún workflow ni el generador de la memoria.

## Criterio de parada (antes de medir)

- Si la vía nueva obligara a leer el texto de todos los ADR en cada ejecución
  local y la batería del registro pasara de segundos a minutos, parar y buscar
  otra forma.
- Cuatro mutaciones tienen que caer: M1 la vía nueva no mira si el ADR nombra
  el defecto; M2 admite un ADR anterior al declarante; M3 reconoce el nombre por
  subcadena; M4 la vía de ADR-222 deja de valer.
- H-216 se cierra solo cuando la #674 esté en `main` y la guarda, con la
  historia real, acepte `pr: 674`; hasta entonces la PR lleva el ADR, la guarda
  y H-231.
- Dos rondas de revisión externa con defectos de la misma familia → raíz.
