# ADR-NNN — [Título en imperativo: «Usar X para Y»]

- Estado: PROPUESTO | APROBADO | RECHAZADO | SUPERADO por ADR-NNN
- Fecha: AAAA-MM-DD
- Aprobación: [quién y cómo; en este repositorio, la fusión de la PR por el propietario]

## Contexto y problema

## Criterio de parada (escrito ANTES de decidir)

[Qué resultado hará parar o cambiar de rumbo, decidido antes de ver ninguno.
Lo que ata no es tenerlo: es haberlo publicado.]

## Opciones consideradas

## Decisión

## Comprobación que la sostiene

[Evidencia concreta: comandos ejecutados, resultados, enlaces exactos. Sin
esta sección, el ADR afirma más de lo que el dato sostiene.]

## Consecuencias

## Alternativas descartadas y por qué

## La lección

[Obligatoria desde ADR-174. El criterio de captura es de Compound Engineering y
lo comprueba `tests/automation/test_mina_de_lecciones.py`: se escribe una
lección **solo si sin ella alguien repetiría el error**. Si no la hay, se dice,
que también es una respuesta:

- ninguna: [por qué nadie podría repetir nada a partir de este ADR]

Y si la hay, las tres líneas, con el encabezado `## La lección` EXACTO:

- familia: [identificador en minúsculas y con guiones, p. ej. `pieza-sin-lector`.
  Es lo que permite contar cuántas veces ha mordido lo mismo; reutiliza una
  familia ya declarada en `MEMORIA.md` antes de inventar otra]
- sin esto se repetiría: [el error concreto, en una frase]
- lo hace cumplir: [la ruta de la prueba que lo hace imposible, o
  `ninguna prueba: <razón>` si de momento es solo prosa]]
