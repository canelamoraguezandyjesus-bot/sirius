---
name: traspaso-a-otra-sesion
description: >-
  Cómo se escribe el mensaje con el que una sesión le deja el trabajo a otra —o
  al propietario para que lo pegue en otra— de modo que la siguiente arranque
  sin preguntar: el sha de main y de la rama, las PR e incidencias vivas, las
  decisiones ya tomadas con su ADR, lo que él ya dijo que no quiere y qué mandos
  tendrá la sesión nueva. Cárgala cuando él diga «dame un prompt para la otra
  sesión», «genera un informe para pasarlo» o «me voy a dormir, déjalo para la
  siguiente», cuando el contexto vaya a compactarse, y al abrir una sesión que
  empieza con un traspaso pegado.
---

# El traspaso a otra sesión

**Regla única: la sesión siguiente no tiene tu memoria ni la suya. Lo que no
esté en el traspaso o en el repositorio no existe para ella.**

## Por qué existe, con fechas

- 08-08-2026: «genera un prompt adecuado para dejar esto funcionando, que me
  voy a dormir»; el modelo lo redactó y él lo pegó de vuelta.
- 19-08-2026 00:03: «necesito solo que me des un informe… para pasarlo a la
  sesión de Claude donde estoy haciendo eso».
- 24-08-2026 15:12: una sesión arrancó con un traspaso pegado que había escrito
  la anterior: «Sigue con Sirius. main está en 009895e… Ahí lo tienes todo. En
  la sesión nueva tendrás los mandos de GitHub otra vez». Funcionó a la primera.
- 13-09-2026 14:35: lo que se decidió el 20-08 en otra sesión era invisible:
  «lo de Hermes… ¿ya no te acuerdas?… otra vez a investigar, otra vez a
  mirar, otra vez a hablar».
- 14-09-2026 21:24: «M17 se decidió que no se iba a hacer… no me acuerdo por
  qué… queda vigente lo que ya había dicho, solo que no sabía lo que había
  dicho».

## Lo que lleva, en este orden y en una pantalla

1. **Dónde está todo**: sha de `main`, rama y su sha, si está empujada, y si
   hay PR abierta (número y estado de Quality).
2. **Qué queda por hacer**, en orden, una línea por cosa, con el enlace de la
   PR o la incidencia. Lo hecho no se cuenta: está en el árbol.
3. **Lo ya decidido**, con su ADR, y **lo que el propietario vetó**, con sus
   palabras y su fecha, para que nadie se lo vuelva a proponer.
4. **Lo que la sesión nueva tendrá o no**: mandos de GitHub, permisos
   denegados, si habrá Windows real, si hay una revisión externa en curso.
5. **El criterio de parada vigente** (skill `disciplina-evidencia`).
6. **La primera acción concreta**, para que no empiece preguntando la vertical.

Nunca lleva secretos ni claves, ni rutas personales que no hagan falta.

## Antes de escribirlo: lo que debe ir al repositorio, no al traspaso

Una decisión va a un ADR (skill `adr`); una idea que no se hace ahora, al
registro de ideas (ADR-208); un defecto, al registro de defectos. El traspaso
**apunta** a eso, no lo contiene: lo que solo viva en el traspaso se pierde a
la segunda sesión igual que se perdió lo de Hermes.

## Al recibir uno

Se comprueba antes de creerlo: el sha de `main` que cita frente al real, la
rama, la PR. El estado se lee de `main`, no de la copia (ADR-016): el
14-08-2026 una sesión reconcilió el registro desde una rama 28 commits atrás y
encargó al motor un bloque que otra había cerrado cuatro días antes (#165), una
tarde en balde. Y se pasa `obra-en-curso` antes de tocar nada.

## Qué NO hace esta skill

- **No sustituye a `MEMORIA.md`**, que es lo primero que lee una sesión
  (ADR-171): el traspaso es para lo que aún no ha llegado ahí.
- **No garantiza que él lo pegue en la sesión correcta** (28-07-2026,
  13-09-2026): por eso el primer punto es el sha, que delata el error.
- **No transporta contexto que debería ser un ADR**: si el traspaso crece más
  de una pantalla, es que falta escribir decisiones.
