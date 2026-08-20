# ADR-044 — Abrir el repositorio al público sin que el propio repositorio lo desmienta

- Estado: PROPUESTO
- Fecha: 2026-08-20
- Aprobación: decisión del propietario (20-08-2026, «Vale, pues lo hacemos público. Ya está, decidido»); la fusión de la PR lo pasa a APROBADO
- Relacionadas: ADR-002 (la automatización no edita `.github/**`; una sesión interactiva sí), ADR-042 (un paso sin plazo propio puede costar el trabajo entero)
- Este documento ES la nota de arranque de la rama (skill `disciplina-evidencia`)

## Contexto y problema

Se agotaron los minutos de GitHub Actions con 10 € de exceso. Desde las 17:00
del 19-08 toda ejecución muere en dos segundos sin llegar a asignarse un runner
—`runner_id: 0`, sin pasos, registros con HTTP 404—, así que el ciclo de trabajo
está parado por dinero, no por defectos.

Un repositorio **público** tiene minutos ilimitados y gratuitos en los runners
estándar. Eso resuelve el problema entero y de paso hace innecesaria la otra
salida que se estaba costeando: montar un runner autoalojado en un portátil de
repuesto. Las dos, además, **no se combinan**: en un repositorio público la PR de
un desconocido ejecutaría código en la máquina del propietario. Es lo uno o lo
otro, y el propietario eligió lo uno («¿qué carajos voy a poner el runner en el
ordenador cuando ya tengo minutos gratis? Es una estupidez»).

El problema real no es decidir: es que **cambiar la visibilidad no tiene vuelta
atrás limpia**. Lo que se copie, se bifurque o se indexe mientras esté público
sigue fuera aunque después se cierre. Y había una puerta escrita por el propio
repositorio, en `PRIVATE_PROJECT.md`:

> Antes de cualquier publicación o distribución se revisarán licencias, avisos,
> dependencias y estrategia legal.

Este ADR es la ejecución de esa puerta.

## Criterio de parada (escrito ANTES de decidir)

Publicado al propietario antes de ejecutar una sola comprobación:

> - ¿Hay en el historial completo algo que no deba ser público: credenciales,
>   datos personales de terceros, información financiera?
> - Con el repositorio público, ¿puede un desconocido hacer actuar a la
>   automatización o llegar a los secretos por algún camino que no he mirado?
> - ¿Qué afirmaciones del repositorio dejan de ser ciertas al publicarlo?
> - ¿Qué queda desprotegido legalmente (licencia, atribución de terceros)?
>
> **Paro** cuando las cuatro tengan respuesta con su comprobación, y una ronda de
> crítica no encuentre familia sin cubrir. **Dos hallazgos de la misma familia →
> busco la raíz, no parcheo uno a uno.**

Las dos cláusulas se ejercieron, y no de adorno: la segunda disparó el arreglo de
`scripts/siguiente_adr.py` que se describe más abajo.

## Opciones consideradas

1. Subir el límite de gasto y seguir en privado.
2. Runner autoalojado en el portátil de repuesto (HP 255 G6, AMD E2-9000e, 4 GB).
3. Repositorio público con los runners de GitHub.

## Decisión

**La tercera, y expresamente no la segunda.** El árbol pasa a ser de lectura
pública; el uso queda reservado (ver `LICENSE`). No se instala ningún runner
autoalojado mientras el repositorio sea público.

Antes de tocar el interruptor se corrige lo que la revisión encontró (sección
siguiente). El interruptor lo pulsa el propietario: cambiar la visibilidad no
está en la API de la que dispone la sesión.

## Comprobación que la sostiene

### Primero, una corrección del propio método

El primer barrido se hizo sobre el clon local: **154 commits**. El servidor tiene
**157 ramas** y `git fetch` completo deja **889 commits** alcanzables. La primera
versión de esta auditoría cubría el **17 %** de lo que se iba a publicar, y lo
habría presentado como si fuera todo. Es exactamente la familia de error de
ADR-042 —medir una cosa y afirmar otra— repitiéndose en la revisión que debía
evitarla. Todo lo que sigue está medido después del `fetch` completo.

### Credenciales: nada, sobre el 100 % del contenido

```
=== 6 coincidencias | 2727/2727 blobs leidos | 51.3 MB escaneados ===
```

Doce familias de patrón (tokens de GitHub, Anthropic, OpenAI, AWS, Slack, Google,
GitLab, claves privadas, URLs con credencial, tokens de Telegram, JWT) contra
**todos** los blobs del historial, no solo los del árbol. Las seis coincidencias
son claves falsas de las propias pruebas antifiltración:

```
_FAKE_KEY = "sk-super-secret-value-should-never-leak-0000000000"
"Bearer sk-live-super-secret-token-should-never-appear"
```

Y ningún fichero portador de secretos ha existido nunca en las 157 ramas:

```
git log --all --name-only | grep -iE '\.env|\.pem$|\.key$|credentials?\.json|id_rsa'
  ninguno
```

El escáner tuvo que escribirse dos veces, y la primera versión merece constar:
mandaba los 2727 SHAs a `git cat-file --batch` sin leer su salida, la tubería se
llenó a los 64 KB y los dos procesos se quedaron esperándose. Estuvo **diez
minutos** aparentando trabajar con la CPU al 0 %. Un proceso vivo no es un proceso
que avanza.

Los metadatos de los diez `.docx` versionados (`docProps/core.xml`) tampoco llevan
nombre personal: `dc:creator` es `Proyecto Sirius` o `python-docx`.

### Lo que un desconocido puede hacer: un hallazgo, y bloquea

Los dos únicos workflows que un extraño puede intentar disparar con un comentario
—`merge-sirius-work.yml` y `resume-sirius-on-command.yml`— exigen
`github.event.comment.author_association == 'OWNER'`. Nunca ha existido
`pull_request_target`. No hay una sola interpolación de `${{ github.event.* }}`
dentro de un `run:`: el texto de terceros viaja por `env:` y se consume
entrecomillado.

**El hallazgo que sí bloquea** lo encontraron dos frentes por separado y dos
refutadores independientes no consiguieron tumbarlo. Cuatro workflows volcaban la
transcripción íntegra del agente al registro de la ejecución, con la premisa
escrita en el propio fichero:

```yaml
# Salida completa en el log del runner (repo privado, log solo visible
# para el propietario): ... Revertir a false cuando el ciclo esté estabilizado.
show_full_output: true
```

Los registros de Actions de un repositorio público los lee cualquiera, sin cuenta,
durante 90 días. La premisa muere al pulsar el interruptor y el propio comentario
ya preveía revertirlo. Se pone a `false` en `implement-sirius-work.yml`,
`repair-sirius-work.yml`, `review-sirius-work.yml` y `audit-sirius-repository.yml`.
Para auditar una ejecución quedan el veredicto en `SIRIUS_VERDICT_FILE` y el
resumen del paso.

Se añade además una guarda que hoy no hacía falta:
`advance-sirius-after-quality.yml` es el único workflow alcanzable desde fuera que
porta el PAT, y la PR de un desconocido contra `main` dispara Quality **en este**
repositorio, cuyo `workflow_run` llegaba hasta él. Ahora exige
`head_repository.full_name == github.repository`.

### Afirmaciones que dejaban de ser ciertas

- `README.md:3` decía «Repositorio privado…». Es la primera frase que lee un
  visitante y era falsa desde el segundo del cambio.
- `PRIVATE_PROJECT.md` prohibía expresamente la redistribución pública. Se
  sustituye por `LICENSE`, y las dos listas de protección que lo nombraban
  (`.claude/settings.json`, `.claude/commands/work.md`) pasan a nombrar `LICENSE`.
- El contrato operativo y `reconcile-sirius-states.yml` justificaban la cadencia
  de seis horas del reconciliador con «los 2000 minutos gratuitos del repositorio
  privado». Ese argumento desaparece. La cadencia **se mantiene**, pero por la
  razón que sí queda en pie: el reconciliador es una excepción declarada a «los
  eventos mandan», y una excepción horaria se parece demasiado a un motor.
- `scripts/verify_windows_no_network.ps1:115` traía la ruta real del equipo del
  propietario (cuenta de Windows y carpeta de OneDrive) dentro de un comentario
  cuya lección técnica no depende de ella. Se sustituye por una genérica.

### Licencia

No hay ni ha habido nunca `LICENSE` en 889 commits, y `pyproject.toml` declara
`license = { text = "Proprietary" }` sin nada que lo respalde. Publicar así no
expone nada, pero deja el régimen sin escribir. Se añade `LICENSE`: lectura
pública, uso reservado, con el aviso de que un artefacto distribuible enlaza
PySide6/Qt bajo LGPL-3.0 y debe acompañarse de sus avisos.

No hay código de terceros copiado en el árbol: el barrido de cabeceras de
copyright ajenas sobre los blobs de los 889 commits no devuelve ninguna.

### La regla de las dos rondas, ejercida

Al ir a registrar esta decisión, `scripts/siguiente_adr.py` propuso **43** — y el
43 ya estaba cogido en la rama de A5. Era la segunda colisión del mismo día: por la
mañana, el ADR del arreglo de Qt y el de A5 se llevaron **ambos el 042**, y eso
dejó Quality en rojo y la incidencia #206 atascada. El criterio de parada obligaba
a buscar la raíz en vez de elegir un número a mano.

La raíz estaba escrita en el propio guion como limitación aceptada: «solo ve el
árbol de trabajo local». Ahora calcula el máximo contra el árbol **y** contra los
ADR de cualquier rama que el clon conozca:

```
consultadas 55 ramas del clon con ADR
aviso: ADR-043 ya esta cogido en una rama sin fusionar
       (sirius-learning-audit-ixtr0g, a5-interaccion-intencion-v0); no se reutiliza
44
```

Con el comportamiento anterior (`--solo-local`) sigue diciendo `43`, que es la
colisión. Tres pruebas nuevas lo fijan, y las dos mutaciones exigidas caen:

| Mutación sembrada | Resultado |
| --- | --- |
| Ignorar los números que usan otras ramas | 1 prueba falla |
| No consultar las ramas del clon | 2 pruebas fallan |

Queda un límite dicho en voz alta en vez de disimulado: el guion solo ve las ramas
**traídas**, así que imprime cuántas consultó.

### La crítica de completitud, y un fallo del propio arreglo

Una última pasada preguntó qué familia había quedado fuera de los seis frentes.
Encontró dos cosas, y la primera es un defecto **de la corrección de este ADR**.

**El arreglo de `show_full_output` es de rama, no de repositorio.** Comprobarlo con
un `grep` del árbol local decía «verde». Comprobarlo donde importa dice otra cosa:

```
$ git grep -n show_full_output origin/main -- '.github/workflows/'
origin/main:.github/workflows/audit-sirius-repository.yml:154:  show_full_output: true
origin/main:.github/workflows/implement-sirius-work.yml:251:  show_full_output: true
origin/main:.github/workflows/repair-sirius-work.yml:449:  show_full_output: true
origin/main:.github/workflows/review-sirius-work.yml:277:  show_full_output: true
```

Los workflows disparados por `issues: labeled` se ejecutan desde la **rama por
defecto**. Mientras esta rama no esté fusionada, la corrección no existe para
GitHub. De ahí la única condición de orden de esta decisión, que no es una
recomendación sino parte de ella:

> **Primero se fusiona esta rama. Después se cambia la visibilidad.** Al revés,
> el arreglo no está puesto en el sitio donde corre.

Es —por tercera vez en el mismo día— la familia «medir en un sitio y afirmar de
otro»: el contenedor en vez del runner (ADR-042), 154 commits en vez de 889 al
empezar esta auditoría, y ahora el árbol de trabajo en vez de la rama por defecto.
Contra eso se añade la única guarda que no depende de acordarse:
`tests/automation/test_registros_publicos.py` falla si **cualquier** workflow
declara `show_full_output` distinto de `false`, y corre en Quality sobre el árbol
fusionado. Las dos mutaciones caen, incluida la forma que un `grep` no ve:

| Mutación sembrada sobre una copia | ¿La caza? |
| --- | --- |
| `show_full_output: true` (booleano) | sí |
| `show_full_output: "true"` (cadena) | sí |

**Lo que se publica y no está en git.** 58 incidencias con ~500 comentarios, unas
208 PRs, y los registros de las ejecuciones de Actions. Ninguna comprobación sobre
ficheros los alcanza y ninguna edición previa los limpia. Sobre los registros hay
un dato que sí importa: poner `show_full_output: false` arregla las ejecuciones
**futuras**; las que ya existen conservan la transcripción y GitHub las guarda 90
días. Solo el implementador lleva **362 ejecuciones**.

El purgado no necesita borrarlas una a una: **Settings → Actions → General →
Artifact and log retention**, bajarlo a 1 día, esperar a que se aplique y luego
cambiar la visibilidad. Cuesta un ajuste y un día. Se deja como decisión del
propietario, con el dato encima de la mesa en vez de descubierto después: lo que
esas transcripciones contienen es sobre todo el código que va a ser público de
todas formas, y los informes del Auditor ya están publicados como comentarios de
incidencia, así que la exposición incremental es acotada — pero es irreversible.

### Lo que se buscó y se descartó

Cuatro hallazgos no sobrevivieron a la refutación, y constan para que no se
vuelvan a levantar:

- **Las URLs de sesión en 391 mensajes de commit.** Son identificadores opacos
  ligados a una cuenta; no son credenciales y no abren nada sin autenticarse.
- **`claude-code-action@v1` anclada por etiqueta móvil.** El refutador demostró
  que la premisa del hallazgo («los cuatro jobs con más privilegio») era falsa.
- **`persist-credentials: true` en dos checkouts.** El camino de exposición que
  reclamaba pasaba por la transcripción pública; apagada esa, se cierra.
- **La obligación LGPL de PySide6.** Se dispara al distribuir el binario, no al
  publicar el código. Queda como nota en `LICENSE`, no como bloqueo.

## Consecuencias

- **El orden es parte de la decisión**: fusionar esta rama primero, cambiar la
  visibilidad después. Antes de la fusión, la corrección no está donde corre.
- Minutos de Actions ilimitados y gratuitos. Desaparece el gasto que paró el ciclo.
- **No se instala ningún runner autoalojado** mientras el repositorio sea público.
  Si algún día se cerrara, esta decisión se revisa entera.
- El árbol, el historial completo, las 58 incidencias y sus ~500 comentarios pasan
  a ser legibles por cualquiera. El nombre y el correo del propietario quedan en la
  autoría de sus commits, como en cualquier repositorio público.
- Tres documentos citan frases textuales del propietario
  (`METODO_INTERROGATORIO.md`, ADR-040, ADR-041). Se dejan porque son parte del
  razonamiento que sostiene esas decisiones, y se señalan aquí para que la
  permanencia sea una elección y no un descuido.
- Se pierde la capacidad de auditar una ejecución leyendo la transcripción íntegra
  en el log. Es el precio directo de la apertura y estaba previsto revertirlo.
- El guion de ADR deja de proponer números ya cogidos en ramas vivas. La prueba
  del registro sigue siendo la garantía; el guion, la fricción que se quita.

## Alternativas descartadas y por qué

**Subir el límite de gasto y seguir en privado.** Resuelve hoy y vuelve el mes que
viene. La automatización consume más desde que se le quitó el tope de dos ciclos
(v1.5) y se le añadió la revisión dual (v1.4): el gasto crece con el uso, y el uso
es el objetivo.

**Runner autoalojado en el HP de repuesto.** Descartada por dos razones
independientes, y basta cualquiera de ellas. La primera es de seguridad: no se
combina con un repositorio público. La segunda es de capacidad: un AMD E2-9000e
con 4 GB es más flojo que el runner estándar de GitHub, y 4 GB quedan por debajo
del mínimo que las pruebas gráficas necesitan.

**Publicar sin revisar, aprovechando que «no hay secretos».** Era cierto, y no
habría bastado: el hallazgo que bloqueaba no era un secreto en el árbol, sino una
opción de un workflow cuya justificación escrita era la privacidad del
repositorio. Lo encontró la revisión, no la intuición.
