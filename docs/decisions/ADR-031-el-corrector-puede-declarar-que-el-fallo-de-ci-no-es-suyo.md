# ADR-031 — Un rol necesita un veredicto para cada desenlace real, incluido «esto no lo he roto yo»

- Estado: PROPUESTO
- Fecha: 2026-08-18
- Aprobación: la fusión de la PR de esta rama por el propietario.
- Completa: [ADR-030](ADR-030-una-parada-se-levanta-con-una-orden-no-con-cirugia.md), que cubrió el
  tercero de los tres atascos del ciclo de A2. Este cubre los otros dos.

## Contexto y problema

El ciclo de A2 se detuvo tres veces. ADR-030 resolvió la tercera. Las otras dos son **la misma**,
y ocurrieron **dos veces el mismo día con dos pruebas inestables distintas**:

- **Qt** (`test_streaming_message_grows_without_overlapping_neighbours`, incidencia #186): Quality
  en rojo. El corrector había pasado la suite entera en verde en su propio runner minutos antes
  (2529 passed). No tocó la prueba ajena —**correctamente**: estaba fuera de su alcance— y emitió
  `FIXED` sin empujar nada.
- **SQLite** (`test_restore_backup_rejects_a_tampered_backup_without_modifying_data`, PR #191):
  mismo patrón. Verde en el segundo intento **sobre el mismo commit**, lo que confirma la
  intermitencia.

`FIXED` presupone un push. Sin push no hay evento `pull_request`, sin evento no hay Quality, y
`sirius:ci-pending` no es terminal: nadie avisa. La primera vez costó **45 minutos de silencio y
una persona pulsando «Re-run failed jobs»**.

El corrector no se equivocó. **Se le obligó a elegir entre veredictos que no describían su
situación**: `FIXED` era falso (no arregló nada), `FAILED_SAFELY` habría detenido una incidencia
sana, y `BLOCKED_BY_DECISION` habría inventado una decisión que nadie tenía que tomar.

`reconcile-sirius-states.yml` cubre parcialmente el caso (Caso B, cada 6 h), pero con Quality en
rojo **solo avisa**, deliberadamente, para no recetar una corrección sin causa demostrada.

## Criterio de parada (escrito ANTES de decidir)

Publicado en la nota de arranque
([#190, comentario 5331033482](https://github.com/canelamoraguezandyjesus-bot/sirius/issues/190#issuecomment-5331033482)),
antes del primer commit. Alcance: el prompt del corrector, `sirius_apply_verdict.sh`, sus pruebas y
este ADR. **Parar y entregar para pegar si hiciera falta tocar permisos de un workflow** — no hizo
falta: el paso que aplica el veredicto ya recibe el PAT. Pruebas verificadas por mutación,
incluida una que demuestre que la cota existe.

## Opciones consideradas

1. **Que el corrector arregle la prueba ajena**: descartada, y es la tentación fácil. Debilitar un
   `assert` ajeno pone todo en verde y destruye una comprobación que no es suya. El corrector
   acertó al no hacerlo; el sistema no debe empujarle a lo contrario.
2. **Que `FIXED` sin push reejecute automáticamente**: descartada. «Sin push» es ambiguo — también
   ocurre cuando el corrector cree haber arreglado algo y no llegó a escribirlo. Inferir la
   intención de una ausencia es justo lo que produce diagnósticos falsos. Explícito sobre
   implícito.
3. **Bajar la cadencia del reconciliador**: descartada. Reduce la latencia, no el trabajo manual, y
   multiplica el coste de una red de seguridad que hoy cuesta ~120 min/mes.
4. **Un veredicto nuevo, `CHECKS_UNRELATED`**: elegida.

## Decisión

1. **`CHECKS_UNRELATED`** entra en el conjunto del corrector: *esta ronda la disparó un
   `CI_FAILURE`, lo investigué, el fallo no es atribuible a este trabajo y no he empujado nada.*
2. **`sirius_apply_verdict.sh` lo verifica antes de actuar**, y las tres condiciones son lo que
   distingue el veredicto de una excusa:
   - **(a)** tiene que haber un `CI_FAILURE` registrado **para el head actual**; si la ronda la
     disparó la revisión, no hay comprobaciones que reejecutar;
   - **(b)** **una sola reejecución por commit**. Si el mismo head vuelve a fallar, ya no es
     intermitencia: es reproducible, y para para decisión humana (`ci-ajeno-reincidente`);
   - **(c)** el run que reejecutar sale del propio comentario `CI_FAILURE`, que ya publica su URL.
3. **La reejecución usa el PAT**, no el `GITHUB_TOKEN`: un `workflow_run` emitido por este último
   no despertaría a `advance-sirius-after-quality.yml` (regla anti-recursión de GitHub) y la
   incidencia quedaría igual de muda que sin este veredicto. El paso ya recibía el PAT, así que
   **no hubo que tocar ningún workflow ni ningún permiso**.
4. **La cota vive en el dato publicado** —el marcador con el head—, no en una variable del proceso:
   el corrector es otro proceso en cada ronda y no recuerda nada.
5. **Regla general que este caso deja escrita**: *el conjunto de veredictos de un rol debe cubrir
   sus desenlaces reales*, y una prueba ata lo que el prompt ofrece con lo que el guion acepta, en
   las dos direcciones. Hoy esa correspondencia se mantenía a mano en dos ficheros.

## Comprobación que la sostiene

- **Prueba por mutación (ADR-001 §3)**:

  | Mutación | Resultado |
  |---|---|
  | quitar el veredicto del guion (queda solo en el prompt) | **fallan 2** |
  | quitar el veredicto del prompt (queda solo en el guion) | **fallan 2** |
  | quitar la cota de una reejecución por commit | **falla** la prueba de la cota |
  | aceptar el veredicto sin exigir un `CI_FAILURE` previo | **falla** la misma |

  Las dos primeras cubren la desincronización en **las dos direcciones**. La peligrosa es la
  segunda: un veredicto que el guion acepta y el prompt no ofrece nunca se usa, y el desenlace
  sigue sin cubrir sin que nada lo delate — que es exactamente cómo vivió este agujero hasta hoy.
- Diagnóstico tomado de los dos casos reales, con sus pruebas, sus runs y sus tiempos.
- Suite completa: **2550 pasan, 3 se saltan**.

## Consecuencias

- Un fallo de CI ajeno deja de costar una parada muda: se reejecuta solo, **sin intervención
  humana**. Es el primero de los tres atascos que se cierra del todo.
- Una construcción realmente rota no puede convertirse en un bucle: la segunda vez sobre el mismo
  commit para.
- **Lo que esto NO afirma**: que el corrector acierte al juzgar si un fallo es ajeno. Eso lo decide
  él leyendo el log; este cambio solo le da dónde decirlo, y la cota limita el daño si se equivoca
  — un `CHECKS_UNRELATED` equivocado retrasa una ronda el diagnóstico, no lo evita.
- **Debilidad conocida y declarada**: las dos pruebas inestables que destaparon esto **siguen
  siendo inestables**. Este ADR evita que cuesten una parada; no las arregla. La de SQLite, además,
  manipula el cifrado sustituyendo el último carácter por `"A"`, lo cual no garantiza manipular
  nada — es frágil por construcción, aunque no se ha demostrado que sea la causa de su fallo. Van
  aparte.

## Alternativas descartadas y por qué

Las cuatro de arriba. Además: **reejecutar sin cota** — descartada por razones obvias, pero merece
constar, porque es la versión de este cambio que «funciona» en la demo y convierte cualquier
construcción rota en un bucle infinito el día que de verdad importa.
