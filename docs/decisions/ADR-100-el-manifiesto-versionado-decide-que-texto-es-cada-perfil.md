# ADR-100 — Fijar cada `rol@N` a un texto exacto con un manifiesto verificado por sha256

- Estado: APROBADO
- Fecha: 2026-08-28
- Aprobación: fase de corrección de la auditoría externa (#396), autorizada
  entera por el propietario; la fusión de la PR la confirma.

## Contexto y problema

H-28 (auditoría externa del 28-08-2026, F-3.2-01, CONFIRMADO): los workflows
del implementador y del revisor extraían el rol de `Perfil: rol@N` tirando la
versión (`sed` con `@.*`) y leían con `cat` el prompt vigente de main.
`implementer@1` podía significar dos textos distintos en dos Runs: la versión
se registraba en el cuerpo de la incidencia pero no gobernaba nada, así que la
trazabilidad («qué instrucciones ejecutó este Run») era una anotación, no un
hecho.

## Criterio de parada (escrito ANTES de decidir)

- Si la resolución versionada exigiera dependencias fuera de la stdlib en el
  runner (los jobs no instalan nada): parar y decidir delante.
- Si algún guardián existente chocara con el mecanismo: traerlo delante antes
  de romperlo, nunca esquivarlo.

## Opciones consideradas

1. Ficheros versionados por nombre (`implementer@1.md`, `implementer@2.md`…)
   y el workflow compone la ruta.
2. Manifiesto (`scripts/automation/prompts/manifiesto.json`) que mapea
   `rol@N` → fichero + sha256 de sus bytes, y un resolver que verifica antes
   de entregar.
3. Dejarlo estar y tratar la versión como decorativa (rechazada de plano: es
   el defecto).

## Decisión

Opción 2. `scripts/automation/resolver_prompt.py` (stdlib pura; parsea el
campo con `sirius_engine.profile_field` cargado por ruta, patrón H-13) recibe
el carril (`ejecucion` o `revision`, porque quién revisa depende de quién
implementó) y el cuerpo por `ISSUE_BODY`, resuelve la clave EXACTA `rol@N` en
el manifiesto, verifica el sha256 del fichero y solo entonces imprime la ruta.
Todo lo que no puede afirmar para en ROJO: campo ausente, rol desconocido,
versión desconocida, texto que ya no coincide (fail-closed: convierte «texto
distinto en silencio» en «parada que se ve»). Evolucionar un prompt publicado
= registrar `rol@N+1` en el manifiesto y subir `version:` en el perfil; una
versión publicada no se edita.

Sobre la opción 1: obligaba a renombrar ficheros referenciados desde fuera
(corrector, reanudación) y no impedía editar `implementer@1.md` en el sitio —
el nombre versionado sin hash sigue sin fijar el texto. El manifiesto fija
bytes, que es lo que el hallazgo pedía.

## Comprobación que la sostiene

`tests/automation/test_resolver_prompt.py` (12 pruebas, vistas FALLAR antes
del arreglo, incluida la de cableado contra los workflows reales) y cuatro
mutaciones vistas caer: la versión se tira (el defecto original, reinsertado),
sin verificación sha256, el workflow vuelve a la ruta a fuego, y una fila del
manifiesto podrida. Detalle en
`docs/audits/evidencia-h28-el-perfil-versionado-gobierna-el-prompt.md`.

## Consecuencias

- `implementer@1` significa UN texto, byte a byte, y el Run que lo declara lo
  ejecutó o paró en rojo.
- Editar un prompt sin registrar versión pone en rojo el guardián del
  manifiesto en Quality (y el workflow en producción, si llegara antes).
- La puerta del implementador conserva su `sed` de ENRUTADO (decidir qué
  workflow atiende, ADR-099): eso no elige texto y queda fuera de esta ley.
- `investigar-orden.yml` no ejecuta prompts de `prompts/` (su instrucción es
  la pregunta de la orden): sin cambio allí.

## Alternativas descartadas y por qué

Ver «Opciones consideradas»: la 1 por renombrados con onda expansiva y porque
un nombre versionado sin hash no fija bytes; la 3 porque es el defecto.
