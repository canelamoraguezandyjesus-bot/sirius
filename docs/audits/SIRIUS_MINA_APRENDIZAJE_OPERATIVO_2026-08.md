# La mina: primer informe de aprendizaje sobre nuestros propios datos operativos

- Fecha: 2026-08-31
- Incidencia: #493 (Work ID WI-20260831-163257)
- Alcance: solo lectura de la API de GitHub sobre este mismo repositorio
  (`canelamoraguezandyjesus-bot/sirius`); ningún cambio de comportamiento en
  código, workflows ni prompts.
- Autor: documentalista genérico de Sirius (encargo autónomo)

## Nota de método (antes de los resultados)

Cuatro decisiones se tomaron antes de mirar las cifras finales, siguiendo la
disciplina de evidencia de ADR-001:

1. **Dónde vive el dato y dónde vive el análisis.** El dato vive en los
   comentarios de las incidencias de GitHub (bloques `RONDA_HALLAZGOS` y
   `OBSERVACIONES_ESTRUCTURADAS`, marcadores `sirius-verdict:`/`sirius-quality:`,
   comentarios `CORRECCION_APLICADA`) y en `docs/decisions/ADR-*.md`; el
   análisis vive únicamente en este documento nuevo. No se toca ningún otro
   fichero.
2. **Qué NO garantiza este informe.** No es una auditoría exhaustiva de las
   156 incidencias del repositorio: la métrica de goteo (§3) se mide sobre una
   muestra de 12 incidencias multi-ronda, no sobre las 55 que tienen registros
   de ronda parseables. Los huecos declarados en §6 son reales, no retóricos.
   Ninguna de las propuestas de §7 se implementa aquí.
3. **Criterio de parada, decidido antes de clasificar ningún hallazgo tardío
   (§3):** cuando el fichero citado por un hallazgo de ronda N>1 no cambió en
   absoluto entre el head de la ronda 1 y el head de la ronda N (comprobado
   con la API de comparación de GitHub, no por lectura), el veredicto es
   `GOTEO_REAL` sin excepción — la revisión de la ronda 1 se define como
   exhaustiva por la política vigente (`AGENTS.md:81-86`, que ya nombra este
   patrón: «un hallazgo sobre líneas ya idénticas en la ronda previa se
   reporta igualmente, declarando que llega tarde por goteo del revisor»),
   así que un fichero intacto no puede esconder un hallazgo legítimamente
   nuevo — este informe mide, con datos reales, cuánto ocurre y con qué
   frecuencia por fuente. Cuando el
   fichero sí cambió pero el hallazgo no cita una línea concreta, la
   clasificación exige lectura del `problema` contra el `patch` real; ese
   trabajo se delegó en un agente con la regla explícita de clasificar
   `GOTEO_REAL` por defecto ante la duda razonable (ver métodos en §3).
4. **Qué haría el fallo imposible, no solo improbable.** No aplica de forma
   directa: este informe no corrige nada, solo mide y propone (§7 se detiene
   explícitamente antes de implementar).

Fuentes leídas: `gh issue list`/`gh search issues --match comments` sobre
`canelamoraguezandyjesus-bot/sirius` (156 incidencias en total, 107 con
prefijo `[SIRIUS]`), los comentarios de autor de confianza (`OWNER` o
`github-actions`) de las incidencias con al menos un bloque `RONDA_HALLAZGOS`
u `OBSERVACIONES_ESTRUCTURADAS` (62 candidatas por búsqueda de texto; 59 con
al menos una observación estructurada parseable; 55 con al menos un registro
de ronda parseable con `sirius_engine.round_history.parse_round_records`, el
mismo analizador que usa la convergencia real — reutilizado, no reescrito),
`docs/audits/registro_defectos.yml`, `AGENTS.md` y los ADR citados. La
API de comparación de GitHub (`gh api repos/.../compare/{base}...{head}`) se
usó para obtener los diffs reales entre cabeceras de ronda.

## 1. Distribución de hallazgos por fuente, gravedad y tipo de fichero

Datos: los 324 hallazgos publicados en bloques `RONDA_HALLAZGOS` (el registro
ya agregado y normalizado que escribe `sirius_apply_verdict.sh`) de las 55
incidencias con registros de ronda parseables, contando **todas** las rondas
publicadas alguna vez (no solo las vigentes tras un reinicio).

Comando reproducible (con `GH_TOKEN` exportado y este repositorio como
directorio de trabajo):

```bash
gh search issues "RONDA_HALLAZGOS" --repo canelamoraguezandyjesus-bot/sirius --match comments --limit 200 --json number,title,state,url
gh search issues "OBSERVACIONES_ESTRUCTURADAS" --repo canelamoraguezandyjesus-bot/sirius --match comments --limit 200 --json number,title,state,url
# para cada número candidato N:
gh api "repos/canelamoraguezandyjesus-bot/sirius/issues/$N/comments" --paginate \
  --jq '.[] | select(.author_association=="OWNER" or (.user.login // "")=="github-actions[bot]") | .body'
# y sobre el texto concatenado en orden cronológico:
uv run python3 -c "
from sirius_engine.round_history import parse_round_records
import sys
print(parse_round_records(sys.stdin.read()))
"
```

Nota de corrección: la receta anterior usaba `((.user.login // "") | ltrimstr("app/"))=="github-actions"`,
un filtro pensado para el campo `author.login` de la API de GraphQL (donde
las apps se prefijan con `app/`), aplicado por error sobre la API REST — ahí
el login del bot ya viene como `github-actions[bot]`, sin prefijo, tal como
usan `scripts/automation/sirius_issue.sh:87` y
`tests/automation/test_sirius_issue.py:895-906`. El filtro original nunca
igualaba y descartaba en silencio cualquier comentario de `github-actions[bot]`.
Verificado sobre las 12 incidencias de la muestra de §3 (y una comprobación
adicional en las incidencias #148, #177, #193, #268): todo bloque
`RONDA_HALLAZGOS`/`OBSERVACIONES_ESTRUCTURADAS`/`CORRECCION_APLICADA` lo
publica el propio propietario (`author_association=="OWNER"`, usuario
`canelamoraguezandyjesus-bot`); los comentarios de `github-actions[bot]`
encontrados son notificaciones de estado del flujo (activación, inicio,
parada segura), no datos de ronda. La cláusula `OWNER` del filtro ya
capturaba, sola, todo el contenido que alimenta las cifras de este informe,
así que el error no afecta ninguna métrica publicada aquí; se corrige la
receta para que sea reproducible tal cual está escrita.

### 1.1 Por fuente

| Fuente | Hallazgos | % |
|---|---|---|
| CODEX | 231 | 71.3% |
| CLAUDE | 93 | 28.7% |
| **Total** | **324** | 100% |

### 1.2 Por gravedad (dentro de cada fuente, porque usan escalas distintas)

CODEX etiqueta siempre en escala P0–P4; CLAUDE mezcla esa misma escala con
palabras en español (`alta`, `media`, `baja`, `crítica`, `menor`,
`bloqueante`) según la ronda — un dato en sí mismo (ver familia F5 candidata
a guardián, §7, sobre normalizar la taxonomía no es una propuesta con
evidencia suficiente todavía y se deja fuera de la lista final).

| Fuente | Gravedad | Hallazgos |
|---|---|---|
| CODEX | p2 | 136 |
| CODEX | p1 | 91 |
| CODEX | p3 | 4 |
| CLAUDE | media | 26 |
| CLAUDE | p2 | 17 |
| CLAUDE | alta | 15 |
| CLAUDE | menor | 11 |
| CLAUDE | baja | 9 |
| CLAUDE | p1 | 5 |
| CLAUDE | p3 | 5 |
| CLAUDE | crítica/critica | 3 |
| CLAUDE | bloqueante | 2 |

### 1.3 Por tipo de fichero (extensión del fichero citado en el hallazgo)

| Extensión | Hallazgos |
|---|---|
| `.md` | 157 |
| `.py` | 156 |
| `.yml` | 4 |
| (sin extensión) | 4 |
| `.json` | 3 |

Casi la mitad de todos los hallazgos (157/324, 48.5%) caen sobre
documentación, prácticamente empatado con el código (156/324, 48.1%). Esto
importa para §7: un guardián barato sobre `.md` (citas, contradicciones)
cubre, en volumen, la misma fracción del problema que uno sobre `.py`.

## 2. Rondas por incidencia

Datos: las mismas 55 incidencias de §1, contando cada registro de ronda
publicado alguna vez (`records_all`, no solo el historial vigente tras un
reinicio — este informe mide todo lo ocurrido, no solo lo que cuenta hoy
para la convergencia).

```bash
uv run python3 -c "
from sirius_engine.round_history import parse_round_records
# uno por incidencia, sobre el texto cronológico de sus comentarios de confianza
"
```

- Media: **2.93 rondas** por incidencia con al menos una ronda.
- Mediana: **2 rondas**.
- Distribución (rondas → nº de incidencias): 1→21, 2→10, 3→6, 4→5, 5→3,
  6→5, 7→4, 9→1.

Las 5 peores, con su coste en ciclos (nº de rondas):

| Incidencia | Rondas |
|---|---|
| #459 | 9 |
| #182 | 7 |
| #186 | 7 |
| #435 | 7 |
| #469 | 7 |

## 3. Tasa de goteo por revisor

**Definición operativa** (decidida antes de clasificar, §Nota de método):
un hallazgo de la ronda N>1 es *goteo real* si el contenido al que se refiere
ya estaba presente, sin cambios, desde el head que revisó la ronda 1 de la
misma incidencia — el revisor pudo haberlo visto entonces y no lo vio.
Es *legítimo* si señala algo que la corrección introdujo o modificó después
de la ronda 1.

### 3.1 Muestra y método

Muestra: 12 incidencias multi-ronda — las 8 con más rondas del repositorio
(#459, #182, #186, #435, #469, #202, #246, #415) más 4 adicionales para
diversidad temporal (#148, #177, #193, #268). De estas 12, **8 coinciden**
con las 14 incidencias multi-ronda que enumera
`docs/decisions/ADR-078-tres-rondas-consecutivas-sobre-el-mismo-archivo-son-la-familia-repetida-medido-antes-de-fijarlo.md:98-99`
(#148, #177, #182, #186, #193, #202, #246, #268); las otras 4 de esta muestra
(#459, #435, #469, #415) son incidencias posteriores a la medición de
ADR-078 (agosto) y no aparecen en su lista, mientras que 6 incidencias de
ADR-078 (#206, #211, #232, #240, #247, #265) no entraron en esta muestra.
Es un solapamiento parcial, no una comprobación cruzada de que ambas
mediciones coincidan de forma independiente: ADR-078 no valida esta muestra
de 12, solo confirma que 8 de sus incidencias ya eran conocidas como
multi-ronda en agosto. Total: **89 hallazgos de ronda N>1** a clasificar.

Clasificación en dos niveles:

- **Mecánico (17 de 89 hallazgos, el 19.1%):** cuando el hallazgo cita un
  número de línea (o rango) **sobre una ruta real del repositorio**, se
  compara el head de la ronda 1 con el head de la ronda N vía
  `gh api repos/.../compare/{head1}...{headN}`, restringido al fichero
  citado. Si el fichero no aparece en el diff → `GOTEO_REAL` (evidencia
  binaria: el fichero no cambió, punto). Si aparece y la línea citada cae
  dentro de un `hunk` modificado **y esa línea concreta es una adición o
  modificación real (no una línea de contexto sin tocar)** → `LEGITIMO`. Si
  aparece pero la línea citada queda fuera de todo `hunk`, o es una línea de
  contexto sin cambios dentro de un `hunk` cuyo contenido relacionado no fue
  tocado por esa misma corrección → `GOTEO_REAL`. Estar dentro del rango de
  un `hunk` no basta por sí solo: un diff unificado incluye líneas de
  contexto intactas, así que cada veredicto mecánico exige además leer el
  contenido de la línea exacta (revisión que corrigió cuatro filas mal
  clasificadas y dos filas con método mal etiquetado en la ronda 2 de esta
  incidencia, ver historial de correcciones). Cuando el `archivo` citado por
  un hallazgo no es una ruta del repositorio (p. ej. el cuerpo de una Pull
  Request, un mensaje de commit, un título de ADR), el nivel mecánico no es
  aplicable — `gh api compare` nunca podrá contener ese contenido — y el
  hallazgo se reclasifica al nivel manual.
- **Manual (72 de 89, el 80.9%):** cuando el hallazgo no cita línea sobre una
  ruta real del repositorio (la mayoría — reviewers describen el documento o
  función, no el número, o citan contenido que no es un fichero del árbol),
  se comparó a mano el texto completo de `problema` contra el `patch` real
  ronda1→rondaN del fichero citado (o, si el `archivo` no es una ruta del
  repositorio, contra los comentarios de la incidencia que documentan cuándo
  cambió ese contenido), con la regla explícita de clasificar `GOTEO_REAL`
  por defecto ante la duda razonable, y `INDETERMINADO` solo cuando el patch
  se cortó (límite de 6000 caracteres por fichero) antes de alcanzar el
  contenido relevante.

Comandos reproducibles:

```bash
gh api "repos/canelamoraguezandyjesus-bot/sirius/compare/{head_ronda_1}...{head_ronda_N}" \
  --jq '[.files[] | {filename, status, patch}]'
```

### 3.2 Resultado agregado

| Fuente | LEGITIMO | GOTEO_REAL | INDETERMINADO | Total | Tasa de goteo (sobre clasificables) |
|---|---|---|---|---|---|
| CODEX | 45 | 1 | 7 | 53 | **2.2%** (1/46) |
| CLAUDE | 25 | 11 | 0 | 36 | **30.6%** (11/36) |
| **Total** | 70 | 12 | 7 | 89 | 14.6% (12/82) |

Los 11 goteos de CLAUDE se reparten en 7 incidencias distintas de las 12
muestreadas (#182, #186, #202, #246, #415, #435, #459), no en una sola — no
es un artefacto de un caso aislado (la incidencia #469, que en una versión
anterior de esta tabla aparecía con 3 goteos, quedó reclasificada: sus tres
hallazgos citaban el cuerpo de la Pull Request #470, no un fichero del
repositorio, y correspondían a correcciones reales de rondas 2 a 5 — ver
§3.1 y la fila de #469 en §3.3). De los 12 goteos reales totales, 10 (83.3%)
los detectó el nivel mecánico sin necesitar lectura del contenido más allá
de comprobar que la línea citada cae fuera de todo `hunk` modificado: el
propio mecanismo de §3.1 usado en vivo es, con dos excepciones conocidas
(#459 rondas 3 y 4, ver §5), el guardián propuesto en §7.1 — esas dos filas
son `LEGITIMO` pese a que su línea citada no cambió, porque una línea
hermana del mismo hunk sí lo hizo.

### 3.3 Lista clasificada completa (89 hallazgos)

| Incidencia | Ronda | Id | Fuente | Veredicto | Método | Motivo/evidencia |
|---|---|---|---|---|---|---|
| #148 | 2 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | La sección 'Corrección de ronda 2' con el nuevo troceo de IN(...) es contenido añadido en este diff; el hallazgo pide sincronizar V8_EXECUTION.md con esa evidencia nueva. |
| #177 | 2 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | El bucle de cancelación sobre LIVE_STATES en change_work_item_scope es código nuevo de esta ronda que omite PREPARED. |
| #177 | 3 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | invalidate_prepared() es un método nuevo de esta ronda; el hallazgo señala que retry() todavía no lo reconoce. |
| #177 | 4 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | La nueva guarda 'or previous.desenlace is RunOutcome.CANCELLED' añadida en este diff es la que se critica por sobre-alcanzar. |
| #177 | 5 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | El nuevo bloque if/elif con invalidate_prepared/request_cancel(por_cambio_de_alcance) es el criticado por omitir cancelaciones ya UNCONFIRMED. |
| #182 | 2 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | recover_invalid_tail() es función enteramente nueva en este diff, con el ftruncate que causa el bug señalado. |
| #182 | 2 | CODEX-002 | CODEX | LEGITIMO | manual (revisión de diff + texto) | run_from_dict() es función nueva de este diff que no envuelve resultado en MappingProxyType. |
| #182 | 2 | CODEX-003 | CODEX | LEGITIMO | manual (revisión de diff + texto) | El test nuevo test_matriz_punto_de_muerte_por_resultado_run es el criticado por no usar run_from_dict. |
| #182 | 3 | CLAUDE-REV-001 | CLAUDE | GOTEO_REAL | manual (revisión de diff + texto) | El diff no toca work_item_from_dict(); solo añade funciones nuevas de Run después de su cuerpo, que queda idéntico desde ronda 1. |
| #182 | 3 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | El criterio 'SOLO si no hay ningún registro completo...' es nuevo en este diff y aún no cubre la última línea terminada corrupta. |
| #182 | 4 | CLAUDE-REV182-001 | CLAUDE | LEGITIMO | manual (revisión de diff + texto) | La cifra '18 passed' cambia de '10' en este mismo diff; se le critica no reflejar los 4 tests añadidos por las correcciones de esta ronda. |
| #182 | 4 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | La rama '(b) la línea inválida no termina en su propio salto de línea' es nueva en este diff. |
| #182 | 5 | CLAUDE-REVIEWER182-001 | CLAUDE | LEGITIMO | manual (revisión de diff + texto) | La cifra de pruebas (18→22) y la matriz de RESULTADOS.md cambian en este mismo diff; se critica que otra cifra no siguió el mismo ritmo. |
| #182 | 5 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | La reescritura de RESULTADOS.md (matriz, sección 'Cobertura de Run') es nueva; se señala un vacío dentro de ese contenido nuevo. |
| #182 | 6 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | Todo el mecanismo recover_invalid_tail/InternalCorruptionError es nuevo desde ronda 1; se señala un caso de escritura corta no cubierto por esa lógica nueva. |
| #182 | 7 | CLAUDE-REVIEW-001 | CLAUDE | LEGITIMO | mecánico (diff ronda1 vs rondaN) | RESULTADOS.md y ADR-026 SÍ cambiaron entre ronda 1 y esta ronda; el hunk `@@ -185,7 +207,7 @@` de ADR-026 modifica exactamente la línea con la cifra de pytest ('2229'→'2242 passed') que el hallazgo cita como desactualizada ('debería decir 2243') — línea citada dentro de un hunk modificado, por regla propia de §3.1 |
| #186 | 2 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | _fsync_directory es código enteramente nuevo; el hallazgo es consecuencia directa de introducirlo sin manejar su fallo posterior. |
| #186 | 2 | CODEX-002 | CODEX | LEGITIMO | manual (revisión de diff + texto) | El bloque 'created = not journal_path.exists() ... _fsync_directory(...)' es nuevo en este diff. |
| #186 | 3 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | El patrón try/except DirectorySyncError con _absorb es nuevo (introducido para corregir el hallazgo de la ronda 2). |
| #186 | 4 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | La derivación de clave 'K::scope-cascade::R' por concatenación de texto es el mecanismo nuevo de la cascada que colisiona con claves públicas. |
| #186 | 5 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | _ScopeCascadeKey (tupla) y _decode_idempotency_key son mecanismo explícitamente nuevo de la ronda 5 que no migra claves heredadas. |
| #186 | 6 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | _LEGACY_SCOPE_CASCADE_MARKER/_LEGACY_SCOPE_CASCADE_KINDS son código nuevo de la ronda 6 que confunde cancelaciones públicas con heredadas. |
| #186 | 7 | CLAUDE-SIRIUS-REVIEW-A2-CANCELLED-01 | CLAUDE | GOTEO_REAL | mecánico (diff ronda1 vs rondaN) | fichero sin cambios entre ronda 1 y esta ronda |
| #193 | 2 | CLAUDE-REV-001 | CLAUDE | LEGITIMO | mecánico (diff ronda1 vs rondaN) | línea citada dentro de un hunk modificado |
| #202 | 2 | CLAUDE-REVISOR-001 | CLAUDE | LEGITIMO | manual (revisión de diff + texto) | La eliminación de 'veredicto.escribir' de reviewer.yml es el cambio de esta ronda que crea la inconsistencia con contrato_salida. |
| #202 | 2 | CLAUDE-REVISOR-002 | CLAUDE | GOTEO_REAL | mecánico (diff ronda1 vs rondaN) | fichero sin cambios entre ronda 1 y esta ronda |
| #202 | 2 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | La guarda 'definicion.escritura and envelope.escritura is None' es código nuevo de esta ronda que solo rechaza None, no cadenas vacías. |
| #202 | 3 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | 'escritura: false' para veredicto.escribir es el cambio introducido en este commit para esquivar la guarda. |
| #202 | 3 | CODEX-002 | CODEX | GOTEO_REAL | mecánico (diff ronda1 vs rondaN) | fichero sin cambios entre ronda 1 y esta ronda |
| #202 | 3 | CODEX-003 | CODEX | LEGITIMO | manual (revisión de diff + texto) | La condición nueva 'or not escritura' añadida en esta misma ronda aún no cubre cadenas de solo espacios. |
| #202 | 4 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | reviewer.yml pasa a declarar 'escritura: veredicto' en este diff, habilitando por primera vez el cruce con repo.escribir/pr.crear que se señala. |
| #202 | 5 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | ambitos_escritura y _campo_ambitos_escritura son mecanismo enteramente nuevo de esta ronda, con el hueco de cadenas de solo espacios. |
| #202 | 6 | CLAUDE-REVISOR-003 | CLAUDE | LEGITIMO | manual (revisión de diff + texto) | Toda la Adenda del ADR-039 (rondas 2-5) se añade en este mismo diff, y precisamente le falta documentar la ronda 6 que el propio commit introduce. |
| #246 | 2 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | _slugs_con_sufijos es función nueva de este diff con el bug de colisión de sufijos señalado. |
| #246 | 2 | CODEX-002 | CODEX | LEGITIMO | manual (revisión de diff + texto) | _fichero_local_de_enlace es función nueva de este diff que no decodifica el URL-encoding de la ruta. |
| #246 | 3 | CLAUDE-001 | CLAUDE | LEGITIMO | manual (revisión de diff + texto) | _anclas_rotas se elimina en este mismo diff, dejando huérfanas las funciones auxiliares (también nuevas desde ronda 2). |
| #246 | 3 | CLAUDE-002 | CLAUDE | LEGITIMO | manual (revisión de diff + texto) | El párrafo nuevo sobre la retirada de anclas y el docstring cambiado a 'tres comprobaciones' se añaden en este diff, creando la contradicción con el docstring superior no tocado. |
| #246 | 4 | CLAUDE-C3A-TRAVERSAL-01 | CLAUDE | GOTEO_REAL | mecánico (diff ronda1 vs rondaN) | línea citada fuera de todo hunk modificado (fichero cambió en otro punto) |
| #246 | 5 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | _contenida_en_raiz es función nueva de esta ronda con el orden resolve()-antes-que-validar criticado. |
| #246 | 6 | CLAUDE-REVISOR-001 | CLAUDE | GOTEO_REAL | mecánico (diff ronda1 vs rondaN) | línea citada fuera de todo hunk modificado (fichero cambió en otro punto) |
| #246 | 6 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | El nuevo bucle de normalización léxica con pop() en _contenida_en_raiz (fix de la ronda anterior) es el que no resuelve el caso de symlinks. |
| #268 | 2 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | --raiz/--hora-recomendada son funcionalidad nueva de esta ronda que queda inalcanzable por el import no relacionado. |
| #268 | 3 | CLAUDE-001 | CLAUDE | LEGITIMO | manual (revisión de diff + texto) | El diff de esta ronda modifica mirror_projection.py, justo el módulo que el propio corrector había declarado fuera de alcance poco antes. |
| #268 | 3 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | _sirius_convergence() es función nueva de esta ronda con el problema de sys.path/site-packages señalado. |
| #415 | 2 | CLAUDE-REVISOR-001 | CLAUDE | GOTEO_REAL | mecánico (diff ronda1 vs rondaN) | línea citada fuera de todo hunk modificado (fichero cambió en otro punto) |
| #415 | 2 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | El rediseño de conflicts_list con ítems seleccionables por miembro es contenido nuevo de esta ronda. |
| #415 | 2 | CODEX-002 | CODEX | LEGITIMO | manual (revisión de diff + texto) | El mismo rediseño nuevo habilita approve_decision_button para elementos ya aprobados. |
| #415 | 3 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | Toda la sección '1. Disparador automático tras la conversación' es nueva en este diff. |
| #415 | 3 | CODEX-002 | CODEX | LEGITIMO | manual (revisión de diff + texto) | El texto sobre _selected_conflict_entity, añadido en la ronda 2, sigue siendo nuevo respecto a ronda 1 y es el que se critica por pruebas insuficientes. |
| #415 | 4 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | La sección nueva del disparador automático (persistente desde ronda 3) es la que no ubica el saneamiento antes de append_message. |
| #415 | 5 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | El párrafo nuevo sobre el campo memory_suggestion y el saneamiento en el adaptador (fix de esta ronda) no cubre los terminales CANCELLED/FAILED. |
| #415 | 6 | CLAUDE-REVISOR-001 | CLAUDE | LEGITIMO | mecánico (diff ronda1 vs rondaN) | línea citada dentro de un hunk modificado |
| #415 | 6 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | La afirmación 'volverá a entrar en un contexto futuro' es texto añadido en la ronda 5 (presente en este diff acumulado) y se corrige aquí por ser incorrecta. |
| #435 | 2 | CLAUDE-REVISOR-001 | CLAUDE | GOTEO_REAL | mecánico (diff ronda1 vs rondaN) | fichero sin cambios entre ronda 1 y esta ronda |
| #435 | 2 | CLAUDE-REVISOR-002 | CLAUDE | GOTEO_REAL | manual (revisión de diff + texto) | El diff no toca §6.1 ni el criterio de aceptación de M8; el propio hallazgo dice que 'siguen redactados' sin cambio desde antes de esta ronda. |
| #435 | 3 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | El párrafo 'Pendiente de decisión del propietario, no diseñado aquí' en §6.1 es nuevo en este diff. |
| #435 | 4 | CLAUDE-REVISOR-001 | CLAUDE | LEGITIMO | manual (revisión de diff + texto) | La frase 'M1–M7 y M11 no dependen de esa decisión' en STATUS.md es nueva en este diff. |
| #435 | 4 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | El párrafo nuevo en §6.2 ('Misma premisa pendiente que §6.1') es el criticado por no bloquear también la ordenación de M8/M9. |
| #435 | 4 | CODEX-002 | CODEX | LEGITIMO | manual (revisión de diff + texto) | La misma frase nueva de STATUS.md permite ordenar M11 pese a depender de M10 bloqueado. |
| #435 | 5 | CLAUDE-A6-001 | CLAUDE | LEGITIMO | manual (revisión de diff + texto) | Las citas concretas a STATUS.md que se señalan como erróneas son ediciones nuevas de este mismo diff (desplazamiento de línea). |
| #435 | 6 | CLAUDE-DOC-436-001 | CLAUDE | LEGITIMO | manual (revisión de diff + texto) | El párrafo de 13 líneas y los cambios de citas en STATUS.md son enteramente nuevos en este diff, tocando un fichero fuera del alcance autorizado. |
| #435 | 7 | CLAUDE-SIRIUS-REV-435-001 | CLAUDE | LEGITIMO | manual (revisión de diff + texto) | Las citas concretas señaladas (p. ej. STATUS.md:145-168, :165-168) son ediciones visibles y cambiantes en este mismo diff. |
| #435 | 7 | CODEX-001 | CODEX | INDETERMINADO | manual (revisión de diff + texto) | El contenido sobre STATUS.md:108-123 y el bloqueo de M8-M11 no aparece en el diff de esta ronda, cortado a 6000 caracteres. |
| #435 | 7 | CODEX-002 | CODEX | INDETERMINADO | manual (revisión de diff + texto) | El contenido sobre la definición de M7 y el pipeline base no aparece en el diff truncado a 6000 caracteres. |
| #435 | 7 | CODEX-003 | CODEX | INDETERMINADO | manual (revisión de diff + texto) | El contenido sobre M10/timeout de Ollama no aparece en el diff truncado a 6000 caracteres. |
| #435 | 7 | CODEX-004 | CODEX | INDETERMINADO | manual (revisión de diff + texto) | El contenido sobre el 40% de ADR-008 y M8 no aparece en el diff truncado a 6000 caracteres. |
| #459 | 2 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | El propio hallazgo indica que la clasificación desglosada de projection/ es introducida por este commit, y el diff añade PENDIENTE DE CONFIRMAR como estado nuevo. |
| #459 | 3 | CLAUDE-REVISOR-001 | CLAUDE | LEGITIMO | manual (la línea 87 citada es una línea de contexto sin tocar, no una adición; el mecanismo de mera pertenencia al hunk no basta) | La fila `neutrality.py` (línea 87) en sí no cambió, pero esta misma ronda reclasificó a `PENDIENTE DE CONFIRMAR` la fila hermana `derived.py` dentro del mismo hunk, dejando visible por primera vez la inconsistencia de no aplicar el mismo criterio a `neutrality.py` — inconsistencia que la propia corrección de esta ronda introdujo |
| #459 | 3 | CLAUDE-REVISOR-002 | CLAUDE | LEGITIMO | mecánico (diff ronda1 vs rondaN) | línea citada (115) es la propia línea añadida que cambia la cita a `test_pa_0_2_rec_01_banco_evidencia.py:227` |
| #459 | 4 | CLAUDE-REVISOR-003 | CLAUDE | GOTEO_REAL | mecánico (diff ronda1 vs rondaN) | línea citada fuera de todo hunk modificado (fichero cambió en otro punto) |
| #459 | 4 | CLAUDE-REVISOR-004 | CLAUDE | LEGITIMO | manual (la línea 136 citada es una línea de contexto sin tocar, no una adición; el mecanismo de mera pertenencia al hunk no basta) | La fila `lateral/` (línea 136) en sí no cambió, pero esta misma ronda reclasificó a `PENDIENTE DE CONFIRMAR` las filas hermanas `projection/contracts.py` y `cards/`/`rederivation/`/etc. dentro del mismo hunk, dejando visible por primera vez la inconsistencia de no aplicar el mismo criterio a `lateral/` — inconsistencia que la propia corrección de esta ronda introdujo |
| #459 | 4 | CODEX-001 | CODEX | INDETERMINADO | manual (revisión de diff + texto) | El contenido sobre el arnés round/execute_round.py etc. no aparece dentro del diff truncado a 6000 caracteres. |
| #459 | 5 | CLAUDE-REVISOR-001 | CLAUDE | LEGITIMO | mecánico (diff ronda1 vs rondaN) | línea citada dentro de un hunk modificado |
| #459 | 5 | CODEX-001 | CODEX | INDETERMINADO | manual (revisión de diff + texto) | El diff se corta justo antes de alcanzar el resumen con comodines v0.6 que el hallazgo critica. |
| #459 | 6 | CLAUDE-REVISOR-INDEP-001 | CLAUDE | GOTEO_REAL | mecánico (diff ronda1 vs rondaN) | línea citada fuera de todo hunk modificado (fichero cambió en otro punto) |
| #459 | 7 | CLAUDE-REVISOR-INDEP-001 | CLAUDE | GOTEO_REAL | mecánico (diff ronda1 vs rondaN) | línea citada fuera de todo hunk modificado (fichero cambió en otro punto) |
| #459 | 8 | CLAUDE-REVISOR-INDEP-001 | CLAUDE | LEGITIMO | mecánico (diff ronda1 vs rondaN) | línea citada dentro de un hunk modificado |
| #459 | 9 | CLAUDE-REVISOR-INDEP-001 | CLAUDE | LEGITIMO | mecánico (diff ronda1 vs rondaN) | línea citada dentro de un hunk modificado |
| #459 | 9 | CODEX-001 | CODEX | INDETERMINADO | manual (revisión de diff + texto) | Los términos 'solapamiento', 'comparten_estructura' y 'grouping.py' no aparecen en el diff truncado a 6000 caracteres. |
| #459 | 9 | CODEX-002 | CODEX | LEGITIMO | manual (revisión de diff + texto) | El texto nuevo sobre 'Estado... PROPUESTO' y la nota de cita desactualizada de ADR-110 es visible y nuevo en este diff. |
| #469 | 2 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | El párrafo nuevo que suma los 16 casos de ausencia a los 21 para dar 50 es contenido añadido en este diff. |
| #469 | 3 | CLAUDE-REVISOR-469-001 | CLAUDE | LEGITIMO | manual (el 'archivo' citado es el cuerpo de la PR #470, no una ruta del repositorio: el nivel mecánico no es aplicable) | El hallazgo señala que el cuerpo de la PR #470 no se actualizó tras la corrección de la ronda 3 (commit ae435a9, que resolvió CODEX-001), que sí cambió la conclusión real del ADR-115 fusionado — discrepancia introducida por una corrección posterior a la ronda 1 |
| #469 | 3 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | La reescritura del docstring/test sobre la población de 31 vs 47 casos es nueva en este diff. |
| #469 | 4 | CLAUDE-REVISOR-469-001 | CLAUDE | LEGITIMO | manual (revisión de diff + texto) | El diff de esta ronda muestra el reverso criticado: renombrado del test y vuelta a 'el suelo D1 sigue sin alcanzarse'. |
| #469 | 5 | CLAUDE-REVISOR-469-001 | CLAUDE | LEGITIMO | manual (el 'archivo' citado es el cuerpo de la PR #470, no una ruta del repositorio: el nivel mecánico no es aplicable) | El hallazgo señala que el cuerpo de la PR #470 sigue citando el commit `a4c910a9...` que la propia ronda 1 demostró que no contiene el fichero, pese a que la corrección de ronda 2 (commit aeb42b2) ya lo sustituyó por el commit correcto en el diff fusionado — discrepancia introducida por una corrección posterior a la ronda 1 |
| #469 | 5 | CLAUDE-REVISOR-469-002 | CLAUDE | LEGITIMO | manual (el 'archivo' citado es el cuerpo de la PR #470, no una ruta del repositorio: el nivel mecánico no es aplicable) | El hallazgo señala que el cuerpo de la PR #470 sigue afirmando que 'elementos_de_mas' no alcanza D1, posición del head de ronda 4 que la propia corrección de ronda 5 (head 477c091) revirtió explícitamente por decisión del propietario del 2026-08-31T02:56:16Z — discrepancia introducida por una corrección posterior a la ronda 1 |
| #469 | 5 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | La nueva conclusión ('las cuatro quedan afirmadas') añadida en este diff contradice la sección de Opciones consideradas, no tocada. |
| #469 | 6 | CODEX-001 | CODEX | LEGITIMO | manual (revisión de diff + texto) | El propio hallazgo declara que este commit introduce la justificación de la opción 5 que se critica. |
| #469 | 7 | CLAUDE-REVISOR-469-002 | CLAUDE | LEGITIMO | manual (revisión de diff + texto) | El cambio de título (H1) que desincroniza con el nombre de archivo es una edición visible del diff de esta ronda (y rondas previas). |

## 4. Familias de defecto más repetidas entre incidencias distintas

Cada familia siguiente aparece en **3 o más incidencias distintas**, con
evidencia citada de al menos dos.

### F1 — Contenido o ficheros fuera del alcance declarado

7 hallazgos en 6 incidencias distintas: #193, #268, #392, #435, #459, #469.

- #193 `CLAUDE-REV-001` (bloqueante): «La incidencia #193, sección 'Fuera de
  alcance', dice literalmente: 'No modificar `scripts/automation/**`'» — la
  PR tocaba justo ese árbol.
- #268 `CLAUDE-001` (P1): «La incidencia #268 (D1b) declara explícitamente en
  'Fuera de alcance': 'Cambiar el verificador de D1a, la proyección...' El
  commit de la ronda 3 modifica precisamente la proyección».
- #435 `CLAUDE-DOC-436-001` (alta): edición de `docs/evolution/STATUS.md`
  fuera del alcance autorizado de la incidencia.

### F2 — Cita o cifra que deja de sostenerse tras la propia corrección

4 incidencias: #182, #211, #459, #469.

- #182 `CLAUDE-REVIEWER182-001`: el ADR afirma «2229 passed» correspondiente
  a la ronda 1, y nunca se actualizó pese a que las rondas posteriores
  añadieron pruebas.
- #459 `CLAUDE-REVISOR-INDEP-001`: cita `tests/.../test_pa_0_2_rec_01_banco_evidencia.py:227`
  como ubicación de `_ejecutar_banco`; la fusión de la PR #458 movió esa
  línea y la cita quedó apuntando a otro sitio.
- #469 `CLAUDE-REVISOR-469-001`/`-002`: el cuerpo de la PR #470 no se
  actualizó tras la corrección de la ronda 3, y el título del ADR-115
  codifica una conclusión que su propia primera línea contradice.
- #211 `CLAUDE-REVISOR-001`: la sección "Consecuencias" del ADR-046 sigue
  afirmando una cadencia de sondeo «justificada por medición real» que un
  commit posterior de la misma PR (`f2ee154`) ya había retractado en
  `RESULTADOS.md` como «NO CONCLUYENTE» — el ADR no se sincronizó con su
  propio spike.

### F3 — Pieza o dato correcto sin lector ni llamante

Familia ya reconocida y contada por el propio repositorio, no descubierta
en este informe: `AGENTS.md:17-20` documenta «seis veces una pieza correcta a
la que no llamaba nadie, y una séptima casi se construye por duplicado» —
código funcionalmente correcto que nadie invoca, redescubierto o
reconstruido por no encontrarlo. `docs/audits/registro_defectos.yml:312-334`
(H-24) registra una variante del mismo patrón con un **dato** en vez de una
función: seis líneas del registro de la racha con `incidencia=None` que el
espejo marcaba con `etiquetas_contradictorias` y ningún consumidor leía —
«séptimo caso de la enfermedad de esta casa, y el primero que es un DATO SIN
LECTOR en vez de una función sin llamante».

### F4 — Rondas consecutivas repitiendo la misma familia sobre el mismo fichero

Familia ya medida y publicada en
`docs/decisions/ADR-078-tres-rondas-consecutivas-sobre-el-mismo-archivo-son-la-familia-repetida-medido-antes-de-fijarlo.md:94-126`:
sobre las 14 incidencias con más de una ronda vigente conocidas en esa
medición, el criterio «mismo fichero en 3+ rondas consecutivas» se disparó en
4 (**#182, #186, #211, #246**), verificado a mano leyendo el texto de cada
ronda — 4 aciertos, 0 falsos. El detector ya existe
(`src/sirius_engine/round_family_detector.py`) pero no está conectado al
flujo de revisión (ADR-078, sección «Consecuencias»).

### F5 — Contradicción interna dentro del mismo documento

3 incidencias: #349, #389, #467.

- #349 `CLAUDE-SIRIUS-350-001`: «El contrato del investigador se contradice
  a sí mismo. La línea 96-98 dice explícitamente [...] mientras que [otra
  sección] permite lo contrario».
- #389 `CODEX-002`: un informe de investigación infiere una política de
  cuota a partir de comentarios de foro que su propia sección de
  referencias no sostiene.
- #467 `CLAUDE-SIRIUS-467-001`: un docstring nuevo cita una ubicación de una
  rama no fusionada de forma inconsistente con el resto del documento.

## 5. Guardián mecánico simple por familia: aciertos y falsos positivos estimados

Criterio de entrada, tal como lo fija la incidencia #267 y repite ADR-078:
**una comprobación entra solo si caza más defectos reales que falsos
positivos.** Ninguna de las siguientes se implementa aquí (alcance de esta
incidencia); son estimaciones razonadas sobre la mina, no mediciones de un
guardián en ejecución.

| Familia | Guardián candidato | Aciertos reales estimados | Falsos positivos estimados | Evidencia |
|---|---|---|---|---|
| F4 (rondas repetidas) | Conectar `round_family_detector` (ya construido) al flujo de revisión | 4 de 14 incidencias candidatas | 0 | Medición ya publicada y verificada a mano en ADR-078 — no es una estimación, es un resultado. |
| §3 (goteo) | Marcar como posible goteo un hallazgo de ronda N>1 cuyo fichero/línea citados no cambiaron desde el head de la ronda 1 (exactamente el mecanismo de §3.1) | 10 de 12 goteos reales confirmados en la muestra de este informe (83.3%) | 2 sobre los 89 hallazgos completos, no solo sobre el subconjunto mecánico: §459 ronda 3 (`CLAUDE-REVISOR-001`, línea 87) y ronda 4 (`CLAUDE-REVISOR-004`, línea 136) citan una línea de contexto sin tocar, que la condición mecánica pura marcaría como posible goteo, pero son `LEGITIMO` — una línea hermana del mismo hunk sí cambió y reveló la inconsistencia recién en esa ronda, matiz que la condición no distingue. Neto: 10−2=8. | §3.2 y §3.3 (filas #459 ronda 3 y ronda 4) de este mismo informe. |
| F1 (fuera de alcance) | Ningún fichero tocado por la PR aparece citado textualmente en la sección "Fuera de alcance" de la incidencia | 1 de 7 hallazgos de la familia (#193, que nombra `scripts/automation/**` en prosa) | Bajo si se exige coincidencia literal de ruta, pero la cobertura es baja: la mayoría de las secciones de alcance de este repositorio son prosa sin rutas literales (incluida la de esta misma incidencia #493), así que el guardián callaría casi siempre sin poder afirmar nada. | Lectura directa de los cuerpos de incidencia citados en F1. |
| F2/F5 (citas y cifras) | Ampliar el guardián de citas ya existente (`tests/automation/test_citas_de_los_adr.py`, hoy limitado a `docs/decisions/ADR-*.md` y solo a existencia de ruta — no de línea, `tests/automation/test_citas_de_los_adr.py:296-320`) a todo `docs/**.md` | 0 aciertos directos sobre los ejemplos de F2/F5 de este informe (ninguno es una ruta inexistente; todos son desplazamiento de línea o contradicción semántica, que un guardián de mera existencia no distingue) | Bajo: mismo mecanismo ya en producción sobre ADR, que midió 0 falsos y evitó 18 abstenciones deliberadas (ADR-052) | El guardián actual seguiría sin cazar los casos reales encontrados; es una mejora de higiene general, no una respuesta directa a F2/F5. |
| F3 (sin lector) | Analizador estático de referencias (tipo `vulture`) sobre `src/` | Potencialmente alto — la familia ya mordió 7 veces documentadas | Alto sin medir: la arquitectura de puertos/adaptadores invoca implementaciones por inyección de dependencias, no por llamada directa por nombre, así que un analizador ingenuo marcaría adaptadores legítimos como "sin uso". No cumple el criterio de la incidencia #267 sin antes medirse contra el árbol real. | `AGENTS.md:17-20`, `docs/audits/registro_defectos.yml:312-334` (H-24). |

## 6. Huecos declarados

- La muestra de goteo (§3) cubre 12 de las 55 incidencias con registros de
  ronda parseables (21.8%), no todas. Se eligieron las de más rondas —donde
  hay más oportunidad de goteo tardío— más 4 de diversidad temporal, no al
  azar; una muestra aleatoria podría dar una tasa distinta.
- 7 de los 89 hallazgos tardíos (7.9%) quedaron `INDETERMINADO`: el diff de
  comparación se truncó a 6000 caracteres por fichero antes de alcanzar el
  contenido citado por el hallazgo. Todos son de `CODEX` en las incidencias
  #435 y #459, sobre ficheros largos (`STATUS.md`,
  `INVENTARIO_PAQUETE_D1_LABORATORIO_A_MAIN.md`). No se relee el patch
  completo por presupuesto de esta incidencia; el sesgo que introduce es
  conocido y pequeño (7/89) pero real.
- La familia F4 (§4) reutiliza la medición ya publicada de ADR-078 en lugar
  de recalcularla sobre el conjunto completo de 55 incidencias de este
  informe (que es más amplio que las 14 que medía ADR-078 en agosto). No se
  ha comprobado si el criterio de "3+ rondas consecutivas" sigue dando 0
  falsos sobre las incidencias nuevas desde entonces.
- Los marcadores `sirius-verdict:*` y `sirius-quality:*` y los comentarios
  `CORRECCION_APLICADA` que cita el objetivo de la incidencia #493 no se
  explotan como fuente propia en este informe más allá de identificar qué
  incidencias tienen ciclo de revisión (search de `RONDA_HALLAZGOS`/
  `OBSERVACIONES_ESTRUCTURADAS`, que ya implica que hubo verdicts y
  correcciones): no se construyó una métrica separada sobre ellos porque
  las cinco métricas mínimas exigidas no lo requerían y el presupuesto de
  esta incidencia es finito. Declarado, no medido.
- No se ha medido la tasa de goteo de CODEX con la misma profundidad manual
  que la de CLAUDE: de sus 53 hallazgos tardíos en la muestra, 45 son
  `LEGITIMO` por lectura del diff (alta confianza) pero solo 1 es
  `GOTEO_REAL`, lo que podría reflejar una tasa real baja o una asimetría en
  cómo CODEX cita sus hallazgos (con más frecuencia sobre código con
  funciones/símbolos nuevos fáciles de verificar como "nuevos" a simple
  vista) más que una diferencia real de disciplina frente a CLAUDE. No se
  puede separar ambos efectos con los datos de este informe.

## 7. Propuestas

Ordenadas por (defectos reales cazados − falsos positivos estimados),
descendente. **Ninguna se implementa en esta incidencia**: son candidatas
para encargos aparte, sujetas a la aprobación del propietario, tal como
exige el objetivo de la incidencia #493.

1. **Guardián de goteo en vivo:** cuando una ronda N>1 reporta un hallazgo
   cuyo fichero y línea citados no cambiaron desde el head de la ronda 1 de
   la misma incidencia (mismo mecanismo de §3.1: `gh api .../compare/{head1}...{headN}`
   restringido al fichero), marcarlo explícitamente como «posible goteo,
   ¿por qué no se vio en la ronda 1?» antes de aceptarlo como bloqueante.
   Sobre la muestra de este informe habría señalado 10 de los 12 goteos
   reales confirmados, con 2 falsos positivos conocidos sobre el conjunto
   completo de 89 (§459 rondas 3 y 4: la línea citada es contexto sin tocar,
   pero el hallazgo es `LEGITIMO` porque una línea hermana del mismo hunk sí
   cambió — la condición mecánica pura no distingue ese caso; ver §5). Neto
   estimado: 8. Aplicaría sobre todo al revisor
   CLAUDE, cuya tasa de goteo medida (30.6%) es aproximadamente 14 veces la
   de CODEX (2.2%).
2. **Conectar `round_family_detector` (ya construido en ADR-078) al flujo de
   revisión real.** Ya mide 4 aciertos y 0 falsos sobre 14 incidencias
   candidatas, con verificación manual publicada. No hace falta diseñar ni
   medir nada nuevo: hace falta cablear un CLI ya existente
   (`sirius-familia-repetida`) a `.github/workflows/repair-sirius-work.yml`
   o equivalente, que ADR-078 dejó fuera a propósito por ser trabajo de
   `.github/**` (ADR-002).
3. **Guardián de alcance textual:** fallar si algún fichero tocado por la PR
   aparece citado literalmente dentro de la sección "Fuera de alcance" del
   cuerpo de la incidencia. Cobertura parcial y honesta: solo 1 de los 7
   casos reales de F1 tenía una ruta literal citada (#193); el resto son
   prosa sin rutas ("la proyección", "el documento fuera del objetivo
   pedido"), que un guardián simple de coincidencia de texto no puede
   interpretar. Se propone como mejora incremental de bajo riesgo, no como
   solución de la familia.
4. **Ampliar el guardián de citas de fichero** (`tests/automation/test_citas_de_los_adr.py`)
   de `docs/decisions/ADR-*.md` a todo `docs/**.md`, con la misma regla
   conservadora ya probada (solo existencia de ruta, sin razonar sobre
   contenido). No habría cazado los ejemplos concretos de F2/F5 de este
   informe (todos son desplazamiento de línea, no ruta inexistente), pero
   extiende a más documentación una comprobación que ya evitó 3 citas rotas
   reales en `bbfb625` (ADR-052) con 0 falsos conocidos hasta hoy.
5. **Medir antes de decidir: analizador de "pieza sin lector"** (F3) sobre
   `src/sirius_engine/` sin tocar `adapters/`/`ports/` (donde la invocación
   por inyección de dependencias haría que cualquier analizador ingenuo
   produjera falsos positivos). No se propone activarlo: se propone medirlo
   —contando aciertos y falsos reales sobre el árbol actual, como exige el
   criterio de la incidencia #267— en una incidencia dedicada, dado que la
   familia ya mordió 7 veces documentadas y el coste de seguir sin medir es
   seguir descubriendo el mismo patrón por accidente.
