---
name: coste-antes-de-tocar-una-fuente
description: >-
  Qué se hace ANTES de gastar en grande —leer una fuente de muchos megas,
  lanzar un workflow de agentes, pedir a decenas de sesiones un turno cada una,
  repetir una batería de doce minutos—: poner en una línea el coste y lo que se
  espera sacar, elegir la fuente más barata que conteste y decidir la parada
  antes de empezar. Cárgala cuando vayas a lanzar más de tres agentes, a leer
  más de un megabyte, a gastar turnos de sesiones del propietario o cuota suya,
  o cuando un trabajo lleve más de una hora sin entregarle nada visible.
---

# El coste, antes

**Regla única: lo caro se toca solo si lo barato no contesta, y el coste se
dice antes de gastarlo, no después.**

## Las cuatro veces que salió caro, con cifras

| Fecha | Qué se gastó | Qué se sacó |
|---|---|---|
| 28-07-2026 | un workflow de 23 agentes | 12 murieron por «session limit» a mitad de la auditoría |
| 11-08-2026 | una auditoría con 21 subagentes | «¿y qué resolviste? Nada» (él, a las 11:57); de ahí el tope de diez agentes |
| 19-08-2026 | dos workflows, de 13 y 6 agentes, 2,8 millones de tokens en una tarde | un informe que concluyó «todavía no»; a los 78 minutos, sin nada visible: «¿pero dónde está el informe?» |
| 20 y 21-09-2026 | 33 sesiones de la nube gastando un turno cada una, un día de trabajo y medio uso del propietario | un paso de auditoría que confirmó lo que el anterior ya decía, más tres reglas |

Ninguna de las cuatro tuvo delante, antes de empezar, la línea de coste y de
rendimiento esperado. Es dinero suyo (ADR-204): se le dice antes.

## Los cuatro pasos

1. **La línea de coste, escrita antes de tocar nada**: qué se va a gastar
   (agentes, tokens, turnos de sesiones, cuota suya, horas) y qué se espera
   obtener que no se tenga ya. Si el gasto toca su cuota o sus sesiones, esa
   línea se le envía a él y se espera su sí; si es solo tuyo, va en la nota de
   arranque.
2. **La fuente más barata primero.** ¿Lo que buscas está ya en `MEMORIA.md`, en
   los ADR, en `docs/audits/AUDITORIA_FORMA_DE_TRABAJO_2026-09.md` o en fichas
   que se leen sin gastar? El 20-09-2026 las fichas de las 35 sesiones se
   leyeron gratis y contestaron casi todo; las transcripciones costaron un día
   y añadieron tres reglas.
3. **Parada escrita antes de empezar** (skill `disciplina-evidencia`): cuántos
   agentes como mucho —nunca más de diez, regla del propietario del
   14-08-2026—, cuánto tiempo sin entregar nada visible (una hora), y qué
   resultado hace que se pare aunque quede fuente.
4. **Entrega parcial visible antes de la hora.** Un trabajo largo entrega algo
   legible a la hora de empezar aunque no haya terminado; el silencio de 78
   minutos del 19-08-2026 es lo que hay que evitar.

## Qué NO hace esta skill

- **No calcula dinero exacto**: no hay instrumento (ficha PROC-021 de la
  auditoría). Da órdenes de magnitud y las pone delante.
- **No prohíbe gastar**: prohíbe gastar sin haberlo dicho.
- **No decide por el propietario**: si la línea toca su cuota, la decisión es
  suya; esta skill solo obliga a preguntarlo antes y no después.
- **No sustituye a la disciplina de evidencia**: la parada es la de siempre;
  aquí solo se añade el coste a la nota de arranque.
