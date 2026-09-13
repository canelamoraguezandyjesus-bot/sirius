# ADR-187 — Una revision sobrevive a ponerse al dia con main si el trabajo propio de la rama no cambia

- Estado: APROBADO
- Fecha: 2026-09-13
- Aprobación: el propietario ordenó terminar las mejoras del motor antes de
  volver a la línea de memoria; la parte 2 de la incidencia #608 es la única de
  las tres que su propio análisis declara despachable «sin preguntar nada». La
  fusión de la PR lo confirma.

## Contexto y problema

En palabras del propietario: «cada vez que fusiono, se mueve `main`, y entonces
tengo que actualizar la otra, que pase por Quality y que tenga que revisar otra
vez. O sea, otra ronda más solo por fusionar una cosa».

Con N pull requests abiertas, fusionar una obliga a reconciliar N-1, y cada
reconciliación cuesta tres cosas: traer `main`, otra vuelta de Quality (~10
minutos) y **otra ronda de revisión**. La tercera es la cara, y es la que esta
decisión quita.

`advance-sirius-after-quality.yml` ya sabía desde ADR-142 que un re-run de
Quality sobre el head **ya aprobado** no debe reponer `sirius:review-requested`:
reponerla destruiría una aprobación válida. Pero esa guarda exigía que el head
fuera EXACTAMENTE el aprobado, así que en cuanto `update-branch` movía el head
para traer `main`, la aprobación dejaba de cubrirlo y el verde del head nuevo
abría ronda de revisión aunque el trabajo de la rama no hubiera cambiado ni una
línea.

## Criterio de parada (escrito ANTES de decidir)

Publicado en `docs/audits/arranque-mejora-la-revision-sobrevive-a-ponerse-al-dia.md`
antes del primer cambio:

- (a) Si para saber cuál fue el head aprobado hiciera falta un dato que la
  incidencia no guarda, parar en vez de inventar un registro nuevo.
- (b) Si el arreglo exigiera tocar también la puerta del revisor
  (`review-sirius-work.yml`), parar y traer las dos guardas delante.
- (c) Nada de ampliar el alcance de la credencial del motor (ADR-002): este
  cambio lo hace la sesión interactiva, que es lo que ese ADR prescribe.
- (d) Dos rondas con defectos de la misma familia → parar y nombrar la raíz.

Ninguno se activó: el head aprobado ya viaja en el marcador
`sirius-verdict:reviewer:approved:<sha>`, y la puerta del revisor no se toca.

## Opciones consideradas

1. **Comparar los dos heads por su diff propio** (la elegida).
2. **Cola de fusión nativa de GitHub** (parte 3 de #608): quita el trabajo
   manual de actualizar ramas, pero no evita la ronda de revisión ni sabe
   resolver el conflicto de un fichero generado. Se deja para después, si tras
   esta decisión y la de `MEMORIA.md` sigue doliendo.
3. **Ampliar la ventana de la puerta del revisor** (que acepte revisar un head
   distinto del que pasó Quality): descartada sin medir. Esa puerta existe para
   que nadie revise una versión sin Quality en verde; relajarla cambia una
   garantía por una comodidad.

## Decisión

La guarda de ADR-142 pasa de **«mismo head»** a **«mismo trabajo»**: la
aprobación registrada sigue valiendo si el trabajo PROPIO de la rama es el mismo
en el head aprobado y en el vigente.

«Trabajo propio» es el diff de la rama contra su **base de mezcla**, que es lo
que devuelve `gh api repos/OWNER/REPO/compare/BASE...SHA`. Por construcción, lo
que entra por `main` no cuenta como trabajo de la rama, que es exactamente la
distinción que hacía falta.

Quien decide es `scripts/automation/sirius_misma_obra.py`, **no el YAML**: es la
lección de H-14 (incidencia #282), donde una puerta escrita como texto dentro de
un workflow no la ejecutaba ninguna prueba. El workflow hace las dos lecturas con
su `sirius_retry` de siempre y se ramifica por el **código de salida**, no por un
texto que pueda cambiar de redacción.

**Las vistas generadas no cuentan como trabajo.** `VISTAS_GENERADAS` declara
hoy un solo fichero, `MEMORIA.md`, y la huella lo descarta. Sin esto la mejora
no serviría para el caso que de verdad ocurre: ponerse al día con `main` obliga
a regenerar esa vista -toda rama con un ADR la toca, y por eso todas chocan
entre sí (#608)-, así que la aprobación caducaría igual. Ignorarla es seguro
porque su corrección la garantiza OTRA guarda, no un revisor:
`test_la_memoria_confirmada_en_este_arbol_esta_al_dia` falla en Quality si el
fichero confirmado no es exactamente lo que el generador produce (ADR-171). Un
humano releyendo una vista generada no añade nada que esa prueba no diga ya. Y
si, quitadas las vistas, no queda nada que comparar, se responde que no.

Esto es lo que hace innecesario tocar cómo se mantiene `MEMORIA.md`: ADR-171
decidió que viviera versionado en `main` porque «es lo primero que tiene que
leer una IA al entrar, y una IA entra por `main`». Esa decisión se respeta
entera; lo que cambia es que regenerarla deje de costar una ronda de revisión.

**Fail-closed sin excepciones.** Cualquier cosa que impida afirmar que el trabajo
es el mismo —un fichero que no está, un JSON roto, una comparación sin la clave
`files`, un binario sin `sha`, una lectura caída— responde que NO y se repone la
revisión, que es lo que pasa hoy. La respuesta negativa cuesta una ronda; la
positiva equivocada aprobaría trabajo que nadie revisó, y eso no se recupera.

## Comprobación que la sostiene

Doce pruebas en `tests/automation/test_misma_obra.py`, **vistas FALLAR antes**
(9 errores por módulo inexistente; 3 fallos de cableado contra el workflow real).
Cuatro mutaciones sembradas y vistas caer:

| Mutación | Resultado |
| --- | --- |
| M1: la huella deja de ordenar los ficheros | CAE |
| M2: una comparación sin ficheros afirma igualdad | CAE |
| M3: un fichero ilegible afirma igualdad | CAE |
| M4: la decisión queda FUERA de la guarda de ADR-142 | CAE |
| M5: la vista generada vuelve a contar como trabajo | CAE |
| M6': la lista de vistas crece con un fichero de código | CAE |
| M7: sin vistas queda huella vacía y afirma igualdad | CAE |

Una mutación **no cayó, y queda escrita porque enseña algo**: ignorar
*cualquier* fichero (`if nombre: continue`) deja las dos huellas vacías, y la
guarda de huella vacía convierte eso en «no es la misma obra». Es decir, la
degradación de esa lista es fail-closed por construcción: una lista demasiado
ancha desactiva el atajo en vez de regalar aprobaciones. La mutación peligrosa
de verdad -meter un fichero de código en la lista- sí cae (M6').

M4 **no cayó a la primera**, y eso queda escrito porque es el hallazgo del día:
la primera versión de su guardián comprobaba que la invocación apareciera
*después* de la guarda en el fichero, no que estuviera *dentro* de ella. Una
mutación que la sacaba del bloque pasaba en verde. El guardián se reescribió para
medir anidamiento —abertura, `fi` a la sangría de la guarda, invocación en
medio—, y solo entonces cayó.

De paso, `test_sirius_runner_python_compat.py` cazó un defecto propio antes de
que saliera de la rama: `ruff format` reescribió `except (OSError, ValueError):`
a la sintaxis de PEP 758, que el `python3` 3.12 del runner no entiende. Es
exactamente la clase de fallo para la que esa prueba existe. Partido en dos
`except`, con el porqué escrito en el código.

Validaciones: `ruff format --check`, `ruff check`, `mypy src tests` y la suite
completa, en verde (transcritas en el cuerpo de la PR).

## Consecuencias

- Fusionar una PR deja de costar una ronda de revisión en las demás **siempre
  que la reconciliación no toque el trabajo**. Mientras `MEMORIA.md` siga
  viajando en las ramas, la reconciliación sí lo toca; por eso esta decisión va
  emparejada con la parte 1 de #608, que el propietario ya autorizó por la vía
  que no abre permisos nuevos: que las ramas dejen de tocar ese fichero y se
  regenere al fusionar.
- La puerta del revisor (`review-sirius-work.yml`) no cambia: sigue negándose a
  revisar un head que no pasó Quality.
- Aparece una dependencia nueva del ciclo sobre un script del repositorio, con
  su entrada en `SCRIPTS_RUN_ON_THE_RUNNER`.

## La lección

- familia: `guardian-que-mide-posicion-en-vez-de-estructura`
- sin esto se repetiría: escribir un guardián que comprueba que algo aparece
  «después de» otra cosa en el fichero creyendo que comprueba que está «dentro
  de» ella. Pasó aquí mismo: la primera versión de
  `test_la_decision_se_consulta_dentro_de_la_guarda_de_adr_142` medía posición,
  y la mutación M4 —que saca la decisión del bloque de ADR-142, es decir, que
  consultaría la aprobación donde nada la protege— pasó en VERDE. Es la quinta
  vez que la familia vacua muerde en este repositorio y la primera con esta
  forma: las anteriores medían comentarios en vez de código; esta medía orden en
  vez de anidamiento. La receta se amplía: cuando lo que se protege es una
  condición, el guardián mide el BLOQUE —apertura, cierre a su sangría,
  invocación en medio—, y se siembra la mutación que saca el código del bloque
  para saber si el guardián sirve.
- lo hace cumplir: `tests/automation/test_misma_obra.py`

## Alternativas descartadas y por qué

Ver «Opciones consideradas»: la cola de fusión no evita la ronda de revisión y no
resuelve el conflicto del fichero generado; relajar la puerta del revisor cambia
una garantía por una comodidad.
