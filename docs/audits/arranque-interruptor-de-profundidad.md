# Nota de arranque — el interruptor de profundidad

Fecha: 2026-08-28. Publicada ANTES del primer cambio de código (ADR-001).
Orden del propietario, con sus palabras: «quiero tener la opción de poder
cambiar investigación profunda en una investigación normal de veinte o treinta
fuentes […] poder acotar la investigación a lo que estoy pidiendo».

## Lo medido que lo motiva

- La profunda (`deep`) gasta ~40–60 créditos del buscador y ~25 min; la normal
  (`research_report`) dio 22–33 fuentes, ~5–10 créditos y ~7 min. El buscador
  son 1.000 créditos/mes y NVIDIA limita a ~40 llamadas/minuto: el propietario
  tiene razón en que «todo a fondo» no es sostenible.
- Desde la PR #391 TODAS las órdenes iban en profundo: el interruptor no
  existía.

## Lo que se decide construir

El tipo lo decide EL TEXTO DE LA ORDEN, que es la única interfaz que el
propietario usa:

- «Investiga a fondo …» / «en profundidad» / «investigación profunda/exhaustiva»
  → `deep`.
- «Investiga …» a secas → `research_report` (la normal, 20–30 fuentes).

En el código: `tipo_por_pregunta(pregunta)` en `atender_orden.py`, y el
workflow pasa `--tipo auto` (que significa «decide por el texto»). Un `--tipo`
explícito distinto de `auto` sigue mandando, para poder forzar cualquiera de
los dos sin tocar código. La detección normaliza acentos: «a fondo» y
«profundidad» tienen que funcionar aunque el propietario escriba deprisa.

## Las cuatro preguntas

1. ¿«Investiga cómo conectar un Arduino…» sale NORMAL e «Investiga a fondo…»
   sale PROFUNDA, con el tipo retratado en el argv del hijo real?
2. ¿Las variantes sin tilde y en mayúsculas funcionan? Escribir deprisa no
   puede cambiar el gasto en silencio.
3. ¿Un `--tipo` explícito sigue mandando sobre el texto?
4. ¿El workflow pasa `auto` de verdad? Si siguiera clavado en `deep`, el
   interruptor sería una función sin llamante (la enfermedad de la casa).

## Criterio de parada

- (a) La palabra que activa lo profundo tiene que ser INTENCIONAL («a fondo»,
  «profunda»…): ante la duda, NORMAL, que es el camino barato. Equivocarse
  hacia barato se corrige repitiendo la orden con «a fondo»; hacia caro, no.
- (b) Regla de las dos rondas (ADR-001).

## Lo que NO se toca

Ni el banco, ni los modelos, ni los plazos (la normal cabe de sobra en los de
la profunda).
