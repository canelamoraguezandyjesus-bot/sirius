---
name: modo-nocturno
description: >-
  Cómo trabaja una sesión la noche que el propietario delega entera («haz todo
  lo que puedas adelantar sin pararte ni a informarme»): qué se le pide antes de
  que se vaya, qué NO se le pregunta de madrugada, cómo sobrevivir a los
  reinicios del contenedor y a los límites de uso, cuándo contestar si escribe,
  y el parte con el que se le despierta. Cárgala en cuanto diga «me voy a
  dormir», «modo nocturno», «trabaja toda la noche» o «déjalo listo para
  fusionar», y también si una sesión arranca de noche con una orden de esas.
---

# La noche delegada

**Regla única: la noche es suya para dormir y tuya para trabajar. Cualquier
cosa que le despierte —un aviso de permiso, una pregunta, un informe— es un
fallo tuyo, no un avance.**

## Antes de que se vaya: un solo mensaje

- Todo lo que necesites que decida, junto, en un mensaje: cada punto con las
  opciones en una línea y tu recomendación primero. Él contesta a todo de una
  vez y se va. Lo pidió así el 14-09-2026 a las 00:31: «pónmelo… con varias
  opciones, y lo que me recomiendas. Respondo todo, y así ya puedes trabajar en
  todo libremente».
- El alcance también por exclusión: qué NO tocar (`AGENTS.md`, regla 8).
- Lo que quede sin decidir cuando se vaya no se decide de madrugada: se aparta
  con su razón y va al parte.

## Durante la noche

1. **Ningún permiso que le despierte.** Si una herramienta pide su aprobación,
   no insistas y no la reintentes con otras palabras: apártala, sigue con lo
   demás y anótala para el parte. El 15-08-2026 se quedó despierto de la 01:09
   a las 04:27 por avisos de permiso, y la sesión reintentó una herramienta que
   él había rechazado.
2. **No dependas de esperas de fondo.** El contenedor se reinicia y las mata
   sin avisar: diez esperas de la batería perdidas el 09-09-2026 a las 03:01,
   otra el 10-08 a las 22:17. Cada vez que despiertes, el estado se lee de
   GitHub —Quality, la PR, la incidencia—, no de lo que creías estar esperando.
3. **Despierta poco.** Un repaso cada hora como mucho: la sesión del 08-09-2026
   despertó 95 veces en siete días y la del 13-09 catorce veces en nueve horas
   para decir «sin cambios». Cada despertar es un turno.
4. **Si él escribe, contéstale antes de seguir**, aunque estés en mitad de una
   espera (`AGENTS.md`, regla 11; 14-09-2026 11:04). Dos líneas bastan.
5. **Nada de informes intermedios**: «deja de darme informes, ya te lo pediré
   yo» (14-09-2026 02:18). Lo que no es respuesta a una pregunta suya no se le
   escribe.
6. **El límite de uso de cinco horas cae de madrugada** (15-08-2026 04:46;
   20-09-2026 22:40). Si cae, no hay nada que hacer hasta que se reinicie: que
   el trabajo esté empujado antes, no en el árbol de trabajo.
7. **Cada unidad, su PR, lista para fusionar**: rama, nota de arranque o ADR,
   cadena de comprobación, y «lista» quiere decir exactamente lo que la skill
   `revision-externa` llama «Cuándo se fusiona». Esa sección es la única que
   lo define y aquí no se repite: cada copia parcial se desvió (rondas 3 y 4
   de Codex sobre la PR #659, 21-09-2026: primero faltaba la pasada limpia,
   después el conflicto con `main`). Pedir la revisión no es tenerla: lo que
   no cumpla esa definición está «a medias» aunque Quality esté en verde, y
   así se dice en el parte, nunca como hecho.
8. **Lo que exija su ordenador se acumula** para el lote de la mañana
   (`AGENTS.md`, regla 13).

## El parte de la mañana

Tres bloques y nada más (`AGENTS.md`, regla 12): **hice**, una línea por cosa
con su enlace; **no hice, y por qué**, una línea por cosa (decidido por mí /
bloqueado por X / dejado para ti); **te toca a ti**, comandos con dónde, qué y
qué sale, o decisiones de una línea. Lo pidió tres veces el 14-09-2026: «qué
hiciste, qué no hiciste… ¿qué queda por hacer?», «¿las hiciste todas, en
serio?», «qué fue lo que decidiste no hacer y por qué».

## Qué NO hace esta skill

- **No decide por él lo que es suyo**: producto, dinero, salud (ADR-204). «Lo
  que yo no haría, no lo hagas» (14-09-2026) es el límite; en la duda, se
  aparta.
- **No garantiza que el contenedor sobreviva**: solo que lo empujado sobreviva.
- **No sustituye a la cola**: dos sesiones nocturnas sobre los mismos ficheros
  se pisan igual (skill `obra-en-curso`, ADR-206).
- **No es un permiso para gastar**: una noche se mide en despertares y en
  agentes; ver `coste-antes-de-tocar-una-fuente`.
