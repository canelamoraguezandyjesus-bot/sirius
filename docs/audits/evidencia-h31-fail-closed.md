# Evidencia — H-31: behind_by ilegible bloquea

Nota de arranque: `docs/audits/arranque-h31-fail-closed.md`. Auditoría: #396.

| pregunta | comprobación |
|---|---|
| 1. la prueba invertida cae contra lo viejo | vista FALLAR (2 pruebas rojas) antes del cambio |
| 2. 0 pasa, >0 bloquea | batería completa del merge en verde (22), y M2 (el atraso conocido deja de bloquear) tumba la suya |
| 3. vacío/null/no-numérico bloquean con reintento | `case` cerrado: solo `0` pasa; pruebas de null y vacío; el mensaje dice «reintentar» y la prueba lo exige (criterio (a)) |

M1 (volver al fail-open) tumba las dos pruebas nuevas. La decisión anterior y
su motivo quedan citados en el comentario del guion y en el docstring de la
prueba invertida: no se borra historia, se revoca con la autorización del
propietario y el argumento de la auditoría delante.
