# ADR-093 — El registro de la racha vive en la rama de memoria, no en `main`

- Estado: PROPUESTO
- Fecha: 2026-08-25
- Aprobación: la fusión de la PR por el propietario
- Contexto: D1, incidencia #268. Afina **ADR-074**, que llamó al registro «dato
  versionado» sin decir de qué rama
- Relacionadas: ADR-074 (el contador), ADR-083 (la memoria del motor),
  ADR-082 (el motor dentro de Actions), ADR-002, ADR-001

## Contexto y problema

`sirius-racha` está construido, probado y con tres ADR escritos sobre él
(074, 077, 084). **No lo llamaba nadie.** Comprobado el 25-08-2026 buscando en
todo el árbol: ni un `schedule`, ni un `workflow_dispatch`, ni un script.

No fue un olvido. ADR-074 lo dejó escrito en sus alternativas descartadas:

> **Cablear `sirius-racha` a un `workflow_dispatch`/`schedule` en esta misma
> incidencia.** Prohibido por el propio alcance del bloque y por ADR-002: el
> punto de entrada se entrega ejecutable; engancharlo a un reloj es un acto
> aparte.

Ese acto aparte necesitaba permiso sobre `.github/**`, y el propietario lo abrió
hoy. Es la **cuarta** pieza correcta a la que no llamaba nadie en este
repositorio: antes fueron el despachador, H-13 y el propio supervisor.

Al cablearlo aparece la pregunta que ADR-074 no tuvo que contestar: **dónde se
guarda el registro**. Lo llamó «dato versionado» y lo puso en
`docs/operations/racha_siete_dias.jsonl`, que es una ruta de `main`.

**Y a `main` ya no se puede empujar.** El propietario activó un ruleset el
24-08-2026 que exige pull request; es exactamente el problema que ADR-083
resolvió para el diario del motor, cuatro semanas de trabajo antes.

## Criterio de parada (escrito ANTES de decidir)

**(a)** Si la solución **abre un permiso sobre `main`**, se para. Mismo criterio
que ADR-083(a), y por el mismo motivo: la protección se puso hace un día.

**(b)** Si exige **tocar `src/`**, se para y se despacha por la tubería. La
puerta abierta es para `.github/`, no una excusa para saltarse el ciclo.

**(c)** Si el registro puede quedarse **en una PR sin fusionar**, se descarta sin
más análisis: la pasada del día siguiente lee el registro para contar la racha
hacia atrás, así que un registro rezagado no cuenta despacio — **cuenta mal**.

## Decisión

El registro vive en la **rama de memoria** (`estado-del-motor`), junto al diario
del motor y al del despachador, y el workflow lo pasa por `--registro`.

La opción existía sin tocar código: `sirius-racha` ya acepta `--registro`, así
que el criterio (b) se cumple sin esfuerzo. La ruta por defecto
(`docs/operations/racha_siete_dias.jsonl` bajo la raíz) se queda como está para
quien ejecute una pasada en local.

**El fichero vacío de `main` se queda, y no por comodidad.** La primera
versión de esta decisión lo borraba: un `racha_siete_dias.jsonl` de cero bytes
que nunca se va a escribir es justo la trampa contra la que `AGENTS.md` avisa
desde hoy —un documento de estado caducado que hace concluir «esto no ha corrido
nunca» a quien lo mire—.

**Lo impidió un guardián, y tenía razón.** `test_citas_de_los_adr.py` exige que
toda ruta citada por un ADR exista, y **ADR-074 cita esa ruta**. Borrar el
fichero obligaba a editar el texto de ADR-074 para que la prueba pasara, es
decir, a **reescribir un registro histórico para acomodar una decisión
posterior**. Eso es peor que un fichero vacío: convierte el archivo de
decisiones en algo que se retoca, y entonces deja de servir para saber qué se
decidió y cuándo.

Así que se queda, y el aviso se pone donde sí se lee: en la tabla de
`AGENTS.md`, que dice desde hoy dónde vive cada cosa. Quien busque la racha
encontrará la rama de memoria antes que el fichero vacío.

## Comprobación que la sostiene

**La pieza no la llamaba nadie** — no supuesto, buscado en todo el árbol
(`grep -rn "sirius-racha\|seven_day_streak_cli"`): las únicas apariciones fuera
de su propio módulo son sus pruebas, `pyproject.toml`, tres ADR y un fichero de
texto de una prueba de serialización. Ningún workflow.

**La hora se derivó, no se eligió** (`sirius-racha --hora-recomendada`):

```
03:24 UTC — punto medio del mayor hueco libre de disparos periódicos
            (345 min, tras las 00:32 UTC)
```

**El margen real, medido**, y es el hallazgo que más pesa de este bloque:

```
tolerancia   = max(timeout-minutes) x 2 = 85 x 2 = 170 min
tranquilidad = 00:32 -> 03:24                    = 172 min
margen                                           =   2 min
```

**La pasada, ejecutada de verdad contra el diario real del motor** (sin `gh` en
la sesión, que es por lo que las lecturas caen — en Actions sí lo hay):

```
WI-20260825-144242: no pude leer la incidencia #333 ... No se registra línea
                    esta pasada: no es que no hubiera nada.
[... seis trabajos ...]
Pasada registrada: 0 línea(s) nueva(s).
programacion (7 días requeridos): no cumple — sin línea registrada el 2026-08-25
auditoria    (7 días requeridos): no cumple — sin línea registrada el 2026-08-25
Esta pasada no conmuta nada (contrato §11.3): solo mide y registra.
```

Se confirma de paso que el comando **se niega a inventar una línea** cuando no
puede leer, y que devuelve 0 igualmente.

**El guardián, visto FALLAR en las dos direcciones** (`test_contador_de_siete_dias.py`):

```
mutación 1 — cron a las 00:33, pegado al motor:
  AssertionError: ... solo deja 1 min tranquilos ...   assert 1 >= 170

mutación 2 — un timeout-minutes de 85 a 87 en OTRO workflow:
  AssertionError: ... la tolerancia vigente es de 174  assert 172 >= 174
```

La segunda mutación **es la prueba de la afirmación de los dos minutos**: no se
razona, se enseña cayendo.

## Consecuencias

**El registro deja de ser legible desde `main`.** Quien quiera ver la racha mira
la rama `estado-del-motor` o ejecuta el comando. Es el mismo coste que ya se
aceptó en ADR-083 para el diario, y por la misma razón.

**El `timeout-minutes` de cualquier job pasa a ser un parámetro de D1**, y eso
antes no era verdad de nadie. Subir el mayor tope por encima de 85 deja al
contrato §11.2 sin ninguna hora posible. Ahora sale en rojo con el motivo
escrito; antes habría sido una racha que no avanza y nadie sabe por qué.

**Lo que esto NO garantiza, y hay que decirlo:** cablear el contador no produce
días verdes. Solo empieza a medir. Un día sin línea no es un día verde
(`evaluar_racha`, condición 1), así que la racha depende de que haya trabajo
circulando **y** de que sus incidencias se puedan leer. Hoy hay seis trabajos en
el diario, así que habrá qué medir; pero el primer CUMPLE está a siete días
naturales como mínimo, y solo si esos siete salen limpios.

**Y un modo de fallo silencioso que queda vivo**: si `SIRIUS_BOT_TOKEN` faltara,
todas las lecturas caerían, la pasada no registraría nada y **saldría en verde**
—ADR-084 decidió que una lectura caída no interrumpe el contador—. El workflow lo
dice en un comentario, pero no hay guardián que lo atrape. Se deja anotado como
lo que es: un hueco conocido, no uno descubierto después.

## Alternativas descartadas y por qué

- **Empujar el registro a `main`.** Criterio (a) y, antes que eso, imposible: el
  ruleset lo rechaza.
- **Que el registro viaje por pull request.** Criterio (c). La pasada siguiente
  contaría sobre un historial rezagado, y contar mal es peor que no contar.
- **Dejar el fichero vacío en `main` «por si acaso».** Es un documento de estado
  caducado por construcción, que es la trampa que `AGENTS.md` nombra desde hoy.
