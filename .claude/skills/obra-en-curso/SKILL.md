---
name: obra-en-curso
description: >-
  Comprobar, ANTES de tocar un solo fichero, que no hay otra sesión trabajando
  sobre los mismos, y declarar la tuya para que las demás te vean (ADR-206).
  Cárgala al empezar cualquier trabajo sobre este repositorio, antes del primer
  cambio, y también cuando te encuentres algo que no cuadra con lo que dice
  `main`: puede que lo esté haciendo otra sesión ahora mismo. El repositorio es
  la única pizarra compartida y cada sesión la lee desde su rama.
---

# ¿Hay otra sesión en mis ficheros?

**Regla única: no saber no es un permiso.** Si no puedes AFIRMAR que no hay
solape, no empieces.

## Los tres pasos, en orden

**1. Lista las obras vivas.** Las pull requests abiertas con los ficheros que
tocan. Eso lo haces tú —ahí viven el token y los reintentos—, y produces un
JSON como este:

```json
[
  {"pull_request": "#652", "titulo": "La auditoría de la forma de trabajar",
   "ficheros": ["AGENTS.md", "docs/audits/AUDITORIA_FORMA_DE_TRABAJO_2026-09.md"]}
]
```

**2. Pregunta.** El guion solo compara; no sale a la red y no escribe nada:

```bash
uv run --no-sync python scripts/automation/sirius_obra_en_curso.py \
  --obras obras.json --fichero AGENTS.md --fichero src/sirius_engine/memoria.py \
  --excluir "#652"
```

Tres respuestas, y solo una deja empezar:

| Código | Significa | Qué haces |
|---|---|---|
| 0 | libre | empieza |
| 1 | solape | **no empieces**: dilo, y espera o cambia de vertical |
| 2 | no lo sé | **no empieces**: es fail-closed a propósito |

El código 2 sale de cualquier cosa que impida afirmar lo contrario: un listado
que no es JSON válido, una obra sin `pull_request`, o no haber declarado ni un
fichero. Un listado vacío por error de lectura es indistinguible de «no hay
nadie», y confundirlos es lo que costó la tarde del 14-08-2026.

**3. Declara la tuya.** Abre tu pull request en cuanto tengas el primer commit,
aunque sea borrador. **Mientras no exista, nadie puede verte**, y el guion que
acabas de ejecutar habría dicho «libre» a la otra sesión.

## Por qué existe esto, con fechas

- **14-08-2026**: una sesión «reconcilió» el registro de estado sobre una rama
  28 commits por detrás de `main` y encargó al motor construir un bloque que
  otra sesión había cerrado cuatro días antes (#165). Una tarde entera en
  balde, y el modelo lo escribió: «me he pasado la tarde arreglando deriva
  documental en una copia caducada».
- **Los dos ADR-016** del registro nacieron ese mismo día en ramas distintas.
  De ahí ADR-180: el número de un ADR se calcula contra las ramas del remoto,
  no contra el árbol local.
- **20-09-2026, primer uso real**: al ir a traer la bitácora del ciclo a
  `main`, la comprobación encontró que su rama tenía un commit de hacía ocho
  minutos y que el documento citaba siete hermanos que solo viven allí. No se
  copió nada; se escribió un puntero. La guarda pagó su coste el primer día.

## Cuando el solape es tuyo de todos modos

Si la otra obra es tuya (otra sesión del mismo trabajo), `--excluir` con su
pull request. Si es ajena y aun así tienes que tocar el fichero, **no lo
resuelvas en silencio**: dilo en tu pull request, nombra la obra con la que
chocas y di qué hiciste. Una colisión anunciada se arregla en un merge; una
callada se descubre cuando ya está fusionada.

## Qué NO hace esto

- **No es un cerrojo.** No guarda estado, no hay nada que soltar, y si tu
  sesión muere no deja ningún turno pillado.
- **No busca las obras**, las recibe. Leer GitHub es de quien llama.
- **No ve lo que no está en una pull request**: trabajo en local sin empujar,
  cambios hechos a mano en la máquina del propietario, o una sesión que aún no
  ha abierto su borrador. Por eso el paso 3 no es opcional.
- **No decide si puedes empezar.** Dice si hay solape; la decisión es tuya y se
  escribe.
