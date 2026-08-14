# ADR-016 — El estado del proyecto se lee de `main`, nunca de la rama de trabajo

- Estado: PROPUESTO
- Fecha: 2026-08-14
- Aprobación: la fusión de esta PR por el propietario

## Incumplimiento de ADR-001, dicho antes que nada

ADR-001 pide la nota de arranque **antes del primer commit**. Esta llega después
de nueve, y no se maquilla como si se hubiera escrito antes: parte de lo que
sigue está reconstruido.

El motivo no es una excusa, es el hallazgo: **ADR-001 no existía en la copia que
esta rama estaba leyendo**. La rama arrancó de un `main` de hacía 28 commits, y
ni la skill ni el empujón de cierre estaban en ella. Aparecieron al fusionar
`main`, al final del trabajo.

Que la disciplina de evidencia se escapara justamente por leer una copia
atrasada es el mismo defecto que este ADR registra.

La nota no se pudo escribir en `.claude/evidencia/` —el entorno de esta sesión
no da permiso de escritura ahí, igual que en ADR-009—, así que vive aquí.

## Contexto y problema

ADR-005 declaró `docs/implementation/V8_EXECUTION.md` como **único registro de
estado** de V8. La declaración es correcta y no se toca. Lo que no dijo, porque
parecía obvio, es **desde dónde** se lee ese registro.

En la rama `feat/b13-reproducible-windows-package` se produjeron cinco
afirmaciones falsas sobre el estado del proyecto. Las cinco de la misma familia:
leer `V8_EXECUTION.md` desde la propia rama y tratarlo como el estado real.

| # | Afirmación | Realidad en `main` |
|---|---|---|
| 1 | «El plan no fija ningún umbral de rendimiento» | PA-025 fija inicio ≤3 s P95 y operaciones ≤300 ms P95 |
| 2 | «Nadie mide PA-025» | Lo mide `tests/integration/test_local_performance.py` (B12c, ADR-007) |
| 3 | «B12 está pendiente», y se encargó su implementación en la incidencia #165 | B12a y B12c fusionados desde hacía días (ADR-006, ADR-007, ADR-008) |
| 4 | «`clcache` lo instaló otra sesión en el `PATH`» | Nuitka trae su propia copia y la activa sola en MSVC |
| 5 | «`get_supported_schema_version()` es un camino sensible sin cubrir» | Usa el mismo `ScriptDirectory` que `upgrade_to_head`, ya demostrado compilado |

Las dos primeras son especialmente instructivas: la 2 fue **la corrección de la
1**, hecha con el mismo mecanismo de error. La regla de las dos rondas de ADR-001
debió dispararse ahí. No se disparó, y las tres siguientes salieron gratis.

La serie no la paró quien la produjo. La paró la condición de parada escrita en
la incidencia #165 —«si la clasificación resulta contradicha por la evidencia en
más de cinco entradas, informar y parar»—, que el implementador respetó al
encontrar seis contradicciones contra `main`, sin crear rama ni tocar un archivo.

Coste: una incidencia de trabajo encargada para construir algo ya construido, dos
correcciones encadenadas sobre la misma fila de un documento, y una tarde de
reconciliación documental hecha sobre una copia caducada.

## Criterio de parada (reconstruido, marcado como tal)

1. **Se para y se escala** si una comprobación de B13 o B14 no se puede ejecutar
   en Windows real. *Se honró cuatro veces: el build se paró en cada fallo, se
   diagnosticó con el log delante y no se simuló ninguna ejecución.*
2. **Se para** si una partida exige tocar la credencial real del usuario.
   *Se honró: la partida 3 de B14 quedó aplazada por decisión del propietario y
   no se escribió ningún procedimiento que escriba en la bóveda.*
3. **Se para y se replantea** si dos rondas seguidas dan defectos de la misma
   familia. *No se honró a tiempo, y es el motivo de este ADR.*

## Decisión

**Toda afirmación sobre el estado de un bloque, un defecto o una prueba se
comprueba contra `origin/main` antes de escribirse**, no contra la copia de la
rama de trabajo.

En la práctica, dos comandos antes de afirmar:

```
git fetch origin main
git rev-list --count HEAD..origin/main
```

Si el segundo devuelve algo distinto de cero, la copia local del registro **no
es el estado del proyecto** y no puede citarse como tal. O se pone la rama al
día, o se lee con `git show origin/main:<archivo>`.

Esto aplica igual a los contratos de trabajo: una incidencia que cite evidencia
debe citar archivos que existan **en su rama base**. El contrato de la #165 citó
`scripts/verify_windows_no_network.ps1`, que solo existe en la rama de B13, y por
eso el implementador no pudo verlo.

## Alternativas descartadas

- **Una puerta mecánica que bloquee el commit si la rama va por detrás.** Se
  descarta por el mismo motivo que ADR-001 retiró la suya: una rama puede ir
  legítimamente por detrás mientras no afirme nada sobre el estado. La puerta
  castigaría el caso común para atrapar el raro.
- **Prohibir editar `V8_EXECUTION.md` fuera de `main`.** Haría imposible
  registrar evidencia en la misma PR que la produce, que es donde ADR-001 quiere
  que esté.

## Comprobación que la sostiene

Este ADR no introduce mecanismo, así que no hay prueba automática que lo fije.
Lo que lo sostiene es la evidencia de los cinco casos de arriba, cada uno con su
corrección registrada:

- La corrección de las afirmaciones 1 y 2 vive en la partida 8 de
  `docs/implementation/B14_WINDOWS_SIN_CLAVE.md`, con las **dos** correcciones a
  la vista en vez de disimuladas.
- La corrección de la 3 vive en el cierre de la incidencia #165.
- La corrección de la 4 se publicó en el momento, antes de tocar el arreglo.
- La corrección de la 5 se publicó antes de escribir el work item que dependía
  de ella, y evitó escribirlo.

## Consecuencias

Aceptadas: dos comandos más antes de afirmar sobre el estado, y la obligación de
citar evidencia visible desde la rama base de cada contrato.

No resuelve: que varias sesiones trabajen a la vez sobre el mismo repositorio
sigue produciendo divergencia. Este ADR reduce el daño de leerla mal; no reduce
la divergencia.
