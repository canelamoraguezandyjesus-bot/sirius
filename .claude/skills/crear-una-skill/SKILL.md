---
name: crear-una-skill
description: >-
  Cuándo algo que acaba de pasar merece convertirse en una skill de este
  repositorio, cuándo NO, y cómo se escribe para que sirva y no se pudra.
  Cárgala al cerrar cualquier trabajo en el que hayas tenido que averiguar dos
  veces lo mismo, cuando una skill existente se te haya quedado corta, o cuando
  el propietario pida que aprendamos de cómo trabajamos. El propósito es suyo,
  del 20-09-2026: «que se creen skills para no tener que buscar mil veces cómo
  hacer la misma tarea y poder aprender día a día de lo que hacemos».
---

# Cuándo algo se convierte en skill

**Regla única: una skill se escribe cuando el conocimiento ya costó dos veces,
no la primera vez que se aprende.**

## Las tres condiciones, y hay que cumplir las tres

1. **Se repite.** Al menos **dos ocurrencias fechadas** en el árbol, en los ADR
   o en la auditoría. Una impresión no cuenta.
2. **Tiene fricción medida.** Un número, una fecha o un defecto registrado que
   diga qué costó hacerlo mal o buscarlo otra vez. Sin fricción medida no hay
   nada que ahorrar.
3. **La decisión no es del propietario.** Es técnica o de orden, y por tanto se
   resuelve sin preguntarle (ADR-204). Lo que él decide no se convierte en
   skill: se convierte en pregunta.

## Lo que NO es una skill

| Caso | Dónde va |
|---|---|
| Pasó una sola vez | un ADR, y ya |
| Ya lo hace una herramienta sola | nada: la fricción no existe |
| Repite palabra por palabra lo que dice `AGENTS.md` | es un puntero, no una skill: se borra |
| Es una idea que quizá algún día | `docs/ideas/registro_de_ideas.yml` (ADR-208) |
| Es una decisión del propietario | se le pregunta (ADR-204) |

## Cómo se escribe

Una carpeta en `.claude/skills/<nombre>/` con un `SKILL.md`, y el nombre de la
carpeta igual que el campo `name`.

**La descripción es lo único que se lee para decidir si cargarla.** Es la
pieza más importante del fichero y la que casi siempre se escribe mal. Tiene
que decir **cuándo** cargarla, con los verbos de la situación real («cárgala
antes de confirmar», «cuando la batería te rechace algo»), no de qué trata. Una
descripción de una línea que solo repite el título no la carga nadie.

El cuerpo, corto y en este orden:

1. **La regla única**, en negrita, en una frase.
2. **Los pasos o comandos exactos**, copiables.
3. **Por qué existe, con fechas**: la fricción medida. Es lo que impide que
   alguien la borre por parecer obvia.
4. **`## Qué NO hace`**, obligatoria. Una skill que no declara sus límites
   acaba usándose como garantía de algo que no garantiza.

## Cómo crece una skill

Cuando lo mismo vuelve a morder, **la skill gana una línea; no nace otra
skill**. Dos skills que se solapan se leen menos que una. El catálogo de
patrones de `disciplina-evidencia` ya declara el criterio y vale para todas:
**entra un patrón cuando ha mordido dos veces, y se poda lo que lleve un
trimestre sin invocarse.**

Podar es archivar, nunca borrar (ADR-195).

## La guarda

`tests/automation/test_skills.py` impide lo mecánico: que falte el nombre o la
descripción, que el nombre no coincida con la carpeta, que la descripción sea
demasiado corta para decir cuándo cargarla, que falte la sección de límites, y
que una skill cite una ruta o un ADR que no existen. Esa última es la que
importa: un documento sin dueño se pudre en silencio, y de eso hay medida en
esta casa —la base de conocimiento se quedó nueve versiones de contrato atrás
sin que nadie lo notara (ficha PROC-010 de la auditoría)—.

## Qué NO hace esta skill

- **No obliga a nadie a cargar nada.** Quien decide es el modelo, leyendo la
  descripción. No hay puerta, igual que no la hay para `AGENTS.md`.
- **No garantiza que el texto esté al día**, solo que lo que cita existe. Una
  skill puede tener todas sus rutas vivas y la prosa caducada; contra eso solo
  hay revisión, y es trimestral.
- **No mide si ahorran tiempo.** No hay instrumento para eso en este
  repositorio.
- **No decide qué es importante.** Si dudas entre escribirla o no, no cumple
  la condición 2.
