# Evidencia — H-18: el recordatorio de evidencia pedía un sitio imposible

Rama `abrir-claude-para-h18`, 26-08-2026. No hay decisión nueva que registrar:
el arreglo es el propuesto en la incidencia #311 y aceptado ahí. Esto es el
hecho medido que lo sostiene, junto al registro que gobierna ADR-080 — que es
exactamente el sitio que este arreglo enseña al hook a reconocer.

## Afirmación

El hook `recordar_parada.py` daba falsos positivos por partida doble: ofrecía
`.claude/evidencia/` como sitio válido cuando `Edit(./.claude/**)` está en la
lista `deny` (nadie puede escribir ahí), y no reconocía
`docs/audits/evidencia-*.md`, donde vive la evidencia de un defecto medido.

## Criterio de parada (antes de tocar nada)

- Si en `.claude/evidencia/` hubiera ficheros de evidencia reales, o alguna
  rama viva los usara, el reconocimiento del sitio viejo se conserva. Medido:
  `git ls-files .claude/evidencia/` → solo `.gitignore` y `README.md`; ninguna
  rama sin fusionar toca ese directorio. Se retira.
- Ninguna prueba nueva vale sin haberse visto FALLAR contra el hook sin
  arreglar.

## Comprobación

Las tres pruebas nuevas, contra el hook viejo (el arreglado aún no estaba en
disco, la puerta seguía cerrada):

```
FAILED test_la_evidencia_de_un_defecto_en_docs_audits_silencia_el_empujon
FAILED test_el_sitio_denegado_ya_no_cuenta_como_evidencia
FAILED test_el_empujon_ya_no_ofrece_el_sitio_denegado
3 failed, 7 passed
```

Las siete de siempre pasan con las dos versiones: el comportamiento que no se
quería cambiar no cambia. Tras aplicar el arreglo, las diez en verde (la salida
queda en la PR).

## Lo que este arreglo NO hace

No garantiza que la evidencia sea buena: el hook sigue midiendo presencia y
sustancia mínima (3 líneas útiles, 120 caracteres), no calidad. Y el aviso
sigue siendo un empujón único por rama, no una puerta: eso es ADR-001 y no
cambia aquí.
