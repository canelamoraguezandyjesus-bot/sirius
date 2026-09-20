---
name: registro-de-defectos
description: >-
  Anotar un defecto en `docs/audits/registro_defectos.yml` con los campos y el
  identificador correctos, y cerrarlo con el commit que lo arregló, resolviendo
  el pez que se muerde la cola de «cerrado necesita un sha que todavía no
  existe». Cárgala cuando encuentres un defecto, cuando arregles uno, y
  SIEMPRE que escribas un ADR con una `familia:` en su bloque `## La lección`:
  desde ADR-182 ese ADR no pasa la batería sin su entrada aquí.
---

# Anotar y cerrar un defecto

**Regla única: un defecto encontrado y no anotado se evapora.** Hasta el
21-08-2026 vivían en un documento de una rama sin fusionar: cuatro de seis
seguían vivos en `main` semanas después, con la batería en verde.

## La entrada

```yaml
  # ADR-NNN: dos o tres líneas contando qué pasaba de verdad, en pasado.
  - id: H-NNN
    titulo: Una frase, sin tildes en el YAML de los comentarios
    bloque: documentacion            # o el bloque del motor que sea
    gravedad: baja | media | media-baja | alta
    estado: cerrado
    cerrado_por: <sha de 40 caracteres del commit que lo arregló>
    adr: NNN
    ficheros:
      - la/ruta/que/toca.py
```

Obligatorios siempre: `id`, `titulo`, `bloque`, `gravedad`, `estado`,
`ficheros`. Y además, según el estado:

- **`abierto`** exige `incidencia: <número>`. Sin incidencia que lo siga, un
  defecto abierto se olvida, y la batería lo rechaza.
- **`cerrado`** exige `cerrado_por: <sha>`. Un sha de verdad, de 40
  caracteres, que exista en la historia.

**El identificador no se elige**: desde ADR-192, si el defecto viene de un ADR
igual o posterior al 174, `id` es `H-` más el número de ese ADR. `adr: 211` →
`id: H-211`. Ni el siguiente libre, ni el que quedaba bonito.

## El pez que se muerde la cola, y cómo se resuelve

Cerrar exige el sha del commit que arregla, y ese commit todavía no existe
cuando escribes la entrada. Abrir exige una incidencia que no vas a abrir para
algo que ya está arreglado. La salida es el orden:

1. **Commit 1**: el arreglo y su ADR. Todavía sin entrada en el registro.
2. `git log -1 --format=%H` para leer el sha.
3. **Commit 2**: la entrada, con `estado: cerrado` y ese sha en `cerrado_por`.

Es el orden que siguieron H-204 a H-210 el 20-09-2026. No intentes hacerlo en
un solo commit: no hay forma.

## Un defecto no se borra nunca

Se cierra y se queda. El historial de lo que falló vale tanto como lo que falla
hoy, y la guarda lo comprueba: una entrada que desaparece rompe la batería.

## Lo que lo hace cumplir

`tests/automation/test_registro_de_defectos.py`. No encuentra defectos nuevos
—eso no lo hace una lista— y no pretende hacerlo: garantiza que uno encontrado
no se pierda, que lo abierto tenga quien lo siga y que lo citado exista.

## Qué NO hace este registro

- **No es el tablero de incidencias.** Aquí va el defecto técnico; el trabajo
  pendiente va a GitHub.
- **No mide nada.** No hay estadística de defectos por bloque ni la habrá
  mientras nadie la use para decidir.
- **No cubre lo que se encontró y no se escribió.** El caso del 23-08-2026
  —`#137` cerrada sin dejar entrada— no está aquí, y por eso la auditoría lo
  marca como pérdida en la ficha PROC-016.
