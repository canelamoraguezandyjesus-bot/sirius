# Evidencia — H-25: el contador declara su precondición (§11.2)

Fecha: 2026-08-28. Rama `h25-el-contador-declara-su-precondicion`. Nota de
arranque: `arranque-h25-el-contador-declara-su-precondicion.md`. Decisión:
ADR-101. Incidencia: #376 (opción B con la raíz; (C) queda como bloque
propio).

## Las cuatro preguntas del arranque

**1. ¿El caso de producción se ve FALLAR primero?** Sí. Las 4 pruebas nuevas
de la sección H-25 de `test_projection_verifier.py` se escribieron antes del
cambio y fallaron (motor ACTIVE contra incidencia avanzada, clase sin estado
propio → hoy DIVERGENCIA/TypeError; después NO_COMPARABLE citando «§11.2»,
la clase y «no ha empezado»). La mutación M1 (tratar toda clase como
declarada) la tumba.

**2. ¿Una clase declarada conserva los dientes?** Sí:
`test_h25_una_clase_declarada_conserva_los_dientes` — MISMOS datos, clase en
el conjunto → DIVERGENCIA real en el eje estado. M2 (tratar toda clase como
no declarada) la tumba; M1 y M2 juntas demuestran que el conjunto gobierna en
las dos direcciones. Y de extremo a extremo:
`test_h25_declarar_una_clase_devuelve_la_comparacion_real_por_el_cli`
(monkeypatch de la constante = lo que hará el bloque (C)) → día verde por el
CLI real; M3 (el CLI puentea la constante declarando todas las clases) tumba
el test del CLI que ahora afirma NO_COMPARABLE.

**3. ¿El CLI pasa la constante real?** Probado por COMPORTAMIENTO, no por
grep: el test del punto 2 cambia la constante del módulo del CLI y el
resultado cambia — si el CLI no la leyera, el test no podría ponerse verde.
M3 lo confirma por el otro lado.

**4. ¿`evaluar_racha` y `authority_reversion` tratan NO_COMPARABLE como está
probado?** Sí, re-ejecutado aquí: `test_seven_day_streak.py`,
`test_seven_day_streak_cli.py` y `test_authority_reversion.py` en verde tras
el cambio (33 + 51 pruebas). NO_COMPARABLE no es día verde y no dispara
reversión. El criterio de parada (b) no se activó.

## Criterio de parada (a): el test que cambió de significado

`test_una_pasada_anade_una_linea_y_evalua_las_dos_clases_con_autoridad`
afirmaba `es_verde is True` con un espejo idéntico al motor. Esa verdad era
del instrumento SIN precondición: hoy la clase no tiene estado propio, así
que la pasada honesta registra la línea NO_COMPARABLE (§11.2) y el día no es
verde. Se trajo delante, se decidió con él y su cuerpo explica el cambio.
El camino verde no se perdió: vive en el test del punto 2, tras la
precondición cumplida.

## Mutaciones (ADR-001 §3), todas vistas caer y revertidas

| Mutación | Resultado |
| --- | --- |
| M1: la precondición trata toda clase como con-estado-propio | CAE |
| M2: la precondición trata toda clase como sin-estado-propio | CAE |
| M3: el CLI declara todas las clases (puentea la constante) | CAE |
| M4: las ventanas mandan sobre la precondición (orden invertido) | CAE |

## Estado final

`tests/engine`: 970 en verde (1 skip preexistente). Suite completa, ruff,
format y mypy: en el resumen de la PR. El conjunto declarado está VACÍO y su
prueba lo fija: quien lo amplíe sin traer el cableado de (C) y su evidencia
tendrá que editar esa prueba a conciencia, no de pasada.
