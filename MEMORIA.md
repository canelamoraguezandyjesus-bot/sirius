# Memoria común del proyecto Sirius

> **Generado por `uv run sirius-memoria conocimiento` a partir del árbol del repositorio.**
> No se edita a mano: `tests/engine/test_memoria.py` falla si este fichero no
> coincide con lo que el generador produce. Si cambias un ADR, un documento de
> `docs/` o un registro, vuelve a ejecutar el comando y confirma el resultado en
> la misma PR (ADR-171).

## Cómo se usa

- **Léela entera antes de abrir nada más.** Es la memoria del trabajo: qué se
  decidió, qué registros hay y en qué estado, qué documentos existen y de
  cuándo. Desde aquí, abre solo lo que la tarea necesite.
- **Los desenlaces del motor** —qué se encargó, qué salió, dónde está la
  evidencia— están en la rama `estado-del-motor`, fichero `DESENLACES.md`
  (https://github.com/canelamoraguezandyjesus-bot/sirius/blob/estado-del-motor/DESENLACES.md), que el motor escribe solo tras cada reflejo. Se leen con
  `git fetch origin estado-del-motor && git show origin/estado-del-motor:DESENLACES.md`.
- **Regla de conflicto (ADR-171).** Si el diario del motor y un documento
  discrepan sobre un trabajo, manda el diario. Si dos documentos discrepan
  entre sí, manda el más reciente fusionado en `main`.
- **Qué no se puede hacer** está en `AGENTS.md` («Reglas obligatorias» y
  «Criterio de parada») y en el contrato operativo de automatización. Aquí no
  se copian: un dato, un dueño.
- **Todo lo que hay aquí es público**: el repositorio lo es a propósito
  (ADR-171). Quien escribe en él lo sabe.

## Qué hay, en números

- Decisiones (ADR): **191**.
- Bloques del motor: 17 cerrado, 1 fuera_de_alcance, 2 pendiente.
- Defectos registrados: 2 abierto, 48 cerrado.
- Investigaciones: **9** (fotos con fecha; caducan).
- Documentos: **142**, de los que **96** no declaran fecha.

## Qué se decidió: los ADR, del más reciente al más antiguo

**Están todos**: el índice completo -número, fecha, estado, título y enlace-
se queda entero aquí, porque saber QUÉ se decidió es la orientación que esta
vista existe para dar.

El resumen -el primer párrafo de la sección «Decisión»- solo lo llevan los ADR
desde el 174. De los anteriores está en el ADR que la fila
enlaza, a un clic, sin copiarlo aquí. No es una poda: el texto no se ha ido a
ninguna parte -aquí no se borra nada-. Es que llevar el párrafo de las ciento
y pico decisiones viejas convertía esta vista en el corpus del que venía
huyendo, y la dejó a 630 bytes de no caber en una sola lectura (ADR-196).

| ADR | Fecha | Estado | Decisión | Resumen |
|---|---|---|---|---|
| [197](docs/decisions/ADR-197-el-detector-de-familia-repetida-agrupa-por-la-ruta-que-el-revisor-escribe-no-por-el-recorte-anclado.md) | 2026-09-14 | PROPUESTO | El detector de familia repetida agrupa por la ruta que el revisor escribe, no por el recorte anclado | El detector agrupa por la ruta que encabeza la cita, extraída con `parse_archivo_location`, y normalizada con `_normalize_text` para que la comparación siga siendo insensible a mayúsculas y espacios. |
| [196](docs/decisions/ADR-196-la-vista-de-memoria-lleva-el-indice-completo-de-decisiones-y-el-resumen-solo-de-las-vigentes-como-metodo.md) | 2026-09-14 | PROPUESTO | La vista de memoria lleva el índice completo de decisiones, y el resumen solo de las que siguen vigentes como método | El índice se queda entero; la copia del resumen, no. |
| [195](docs/decisions/ADR-195-podar-significa-archivar-en-este-repositorio-no-se-borra-nada.md) | 2026-09-14 | PROPUESTO | «Podar» significa archivar: en este repositorio no se borra nada | (sin sección Decisión) |
| [194](docs/decisions/ADR-194-ci-pending-distingue-quality-todavia-no-ha-contestado-de-quality-no-va-a-contestar-nunca.md) | 2026-09-14 | PROPUESTO | `ci-pending` distingue «Quality todavía no ha contestado» de «Quality no va a contestar nunca» | El caso «sin resultado» se parte en dos, y solo lo parte un hecho explícito. |
| [193](docs/decisions/ADR-193-el-doble-de-gh-rechaza-lo-que-el-gh-real-rechaza-y-la-red-de-seguridad-vuelve-a-poder-fechar.md) | 2026-09-14 | PROPUESTO | El doble de `gh` rechaza lo que el `gh` real rechaza, y la red de seguridad vuelve a poder fechar | Dos mitades, y ninguna vale sola. |
| [192](docs/decisions/ADR-192-el-numero-de-un-defecto-es-el-numero-de-su-adr-no-un-contador-aparte.md) | 2026-09-14 | PROPUESTO | El numero de un defecto es el numero de su ADR, no un contador aparte | Uno. El número de un defecto nuevo es el número de su ADR. `H-192` para el defecto que declara ADR-192. Nadie elige nada: se copia un dato que la entrada ya está obligada a declarar desde ADR-182. |
| [191](docs/decisions/ADR-191-la-revision-es-una-cola-una-rama-entra-a-revision-solo-si-main-ya-esta-dentro-de-ella.md) | 2026-09-14 | PROPUESTO | La revision es una cola: una rama entra a revision solo si main ya esta dentro de ella | Uno. La condición es una sola pregunta: ¿es la punta de `main` ancestro del head de la rama? Si lo es, lo que se revise es lo que aterrizará. Si no, la combinación que aterrizaría no la ha probado nadie y la rama espera. |
| [190](docs/decisions/ADR-190-la-guarda-de-citas-no-sale-de-docs-decisions-medidos-590-citas-y-23-rotas-fuera-del-registro-cero-son-defectos-de-este-arbol.md) | 2026-09-14 | PROPUESTO | La guarda de citas no sale de docs/decisions/: medidas 590 citas y 23 rotas fuera del registro, cero son defectos de este árbol | La guarda de citas no sale de `docs/decisions/`. Con 0 defectos reales y 23 falsos positivos, el criterio de la incidencia #267 no se salva cambiándole la forma a la comprobación: se pueden escribir las reglas que callan cada familia —la… |
| [189](docs/decisions/ADR-189-la-salida-de-una-parada-sin-incidencia-es-una-orden-del-propietario-y-reanudar-es-despachar-en-el-mismo-gesto.md) | 2026-09-13 | PROPUESTO | La salida de una parada sin incidencia es una orden del propietario, y reanudar es despachar en el mismo gesto | Se elige la opción 1: un comando del propietario, `sirius-decidir`. Y la respuesta a «qué pasa al reanudar» es que reanudar es despachar en el mismo gesto: si el despacho no puede ocurrir, la reanudación no ocurre. |
| [188](docs/decisions/ADR-188-el-alcance-que-el-motor-no-puede-escribir-para-la-puerta-antes-de-crear-la-incidencia-y-remite-a-la-sesion-interactiva.md) | 2026-09-13 | PROPUESTO | Parar antes de crear la incidencia cuando la orden pide tocar lo que el motor no puede escribir | Opción 1 (variante B), como QUINTA causa de sensibilidad del intérprete, con la causa `permisos_o_credenciales_sensibles`. |
| [187](docs/decisions/ADR-187-una-revision-sobrevive-a-ponerse-al-dia-con-main-si-el-trabajo-propio-de-la-rama-no-cambia.md) | 2026-09-13 | APROBADO | Una revision sobrevive a ponerse al dia con main si el trabajo propio de la rama no cambia | La guarda de ADR-142 pasa de «mismo head» a «mismo trabajo»: la aprobación registrada sigue valiendo si el trabajo PROPIO de la rama es el mismo en el head aprobado y en el vigente. |
| [185](docs/decisions/ADR-185-la-puerta-de-la-memoria-se-parte-en-tres-interruptores-antes-de-abrirla.md) | 2026-09-13 | PROPUESTO | la puerta de la memoria se parte en tres interruptores antes de abrirla | Se añade `src/sirius/config/memory_gates.py` con una función pura, `puertas_de_memoria(settings) -> PuertasDeMemoria`, y un `dataclass(frozen=True)` de tres booleanos. `composition_root` la llama una vez y cablea según esta tabla: |
| [184](docs/decisions/ADR-184-la-prohibicion-no-es-una-peticion-el-detector-de-sensibilidad-exige-que-el-marcador-no-vaya-negado.md) | 2026-09-13 | PROPUESTO | La prohibicion no es una peticion: el detector de sensibilidad exige que el marcador no vaya negado | `_detectar_sensibilidad` deja de preguntar ¿aparece el marcador? y pregunta ¿la orden lo PIDE?. Una aparición cuenta solo si no va negada, y basta una aparición sin negar —de cualquier marcador— para que la puerta pare. |
| [183](docs/decisions/ADR-183-la-ausencia-de-run-de-quality-para-el-head-se-encamina-no-se-espera-en-silencio.md) | 2026-09-13 | PROPUESTO | La ausencia de run de Quality para el head se encamina, no se espera en silencio | Opción 3. En `relanzar_quality_si_ya_termino`, la rama que hoy sale con `return 0` cuando no hay ningún run relanzable pasa a llamar a `avisar_quality_sin_encaminar` y a terminar en rojo, exactamente como `consulta-runs-fallida`… |
| [182](docs/decisions/ADR-182-la-guarda-del-registro-de-defectos-deriva-de-los-adr-que-declaran-leccion.md) | 2026-09-13 | PROPUESTO | La guarda del registro de defectos deriva de los ADR que declaran leccion | La guarda del registro de defectos gana una segunda mitad, y esa mitad deriva su inventario de `docs/decisions/`: un ADR que declara una lección con `familia:` declara, por la definición que ADR-174 ya fijó —una lección se escribe *solo si… |
| [181](docs/decisions/ADR-181-la-contradiccion-de-etiquetas-se-decide-por-lo-que-proyectan-no-por-cuantas-son.md) | 2026-09-12 | PROPUESTO | La contradicción de etiquetas se decide por lo que proyectan, no por cuántas son | Opción 2. `_estado_y_fase` calcula el conjunto de destinos de las etiquetas presentes y marca contradicción si y solo si hay más de uno: |
| [180](docs/decisions/ADR-180-el-numero-del-siguiente-adr-se-calcula-contra-las-ramas-del-remoto-no-contra-las-que-el-clon-tenga-traidas.md) | 2026-09-12 | PROPUESTO | El numero del siguiente ADR se calcula contra las ramas del remoto, no contra las que el clon tenga traidas | `scripts/siguiente_adr.py` trae las cabezas del remoto antes de calcular el número, con el refspec explícito `+refs/heads/*:refs/remotes/origin/*` para que un clon estrecho -el de una sesión remota, que clona una sola rama- también las… |
| [179](docs/decisions/ADR-179-la-guarda-de-piezas-sin-llamante-deriva-su-inventario-del-codigo-del-motor.md) | 2026-09-12 | PROPUESTO | La guarda de piezas sin llamante deriva su inventario del codigo del motor | El inventario de `tests/automation/test_piezas_con_llamante.py` se deriva de `src/sirius_engine` con `ast`, en tres formas de pieza: `modulo:`, `definicion:` y `campo:`. Lo escrito a mano pasa a ser `SIN_LLAMANTE_CONOCIDO`, lo que se resta. |
| [178](docs/decisions/ADR-178-la-autoridad-por-clase-se-deriva-de-la-via-github-que-el-despachador-declara-no-de-una-segunda-tabla-a-mano.md) | 2026-09-12 | PROPUESTO | La autoridad por clase se deriva de la vía GitHub que el despachador declara, no de una segunda tabla a mano | La autoridad por clase se deriva de una sola definición en el dominio de qué clases existen en la vía GitHub (`CLASES_CON_VIA_GITHUB`, en `src/sirius_engine/domain/authority.py`), con su complemento `CLASES_SIN_VIA_GITHUB` declarado… |
| [177](docs/decisions/ADR-177-la-ampliacion-por-categoria-entra-por-una-senal-explicita-de-la-peticion-no-por-la-subcadena-contexto.md) | 2026-09-12 | PROPUESTO | La ampliación por categoría entra por una señal explícita de la petición, no por la subcadena «contexto» | `Peticion` gana un campo booleano propio, `amplia_por_categoria`, apagado por defecto, y el consumidor lee ese campo y nada más. `pide_contexto` y `PROPOSITO_DE_CONTEXTO` se retiran del dominio: ningún consumidor decide ya por subcadena… |
| [176](docs/decisions/ADR-176-el-cierre-de-una-incidencia-se-retoma-desde-donde-se-quedo.md) | 2026-09-12 | PROPUESTO | El cierre de una incidencia se retoma desde donde se quedó | El cierre de una parada sin salida se comprueba DESPUÉS de todo lo demás, y se retoma desde el estado en que el motor está. Primero se calcula el plan por etiquetas y, si hace falta, el recorrido acreditado, exactamente como siempre. Solo… |
| [175](docs/decisions/ADR-175-un-tablero-por-incidencia-un-solo-comentario-que-el-motor-mantiene-al-dia.md) | 2026-09-12 | PROPUESTO | Un tablero por incidencia: un solo comentario que el motor mantiene al día | Uno. Un solo comentario por incidencia, reescrito en cada cambio de estado. Lleva: qué se pidió (del cuerpo declarado), por dónde va el ciclo, qué se ha comprobado (Quality y rondas, con sus números), dónde está la evidencia (PR, head… |
| [174](docs/decisions/ADR-174-la-mina-en-dos-pasadas-la-leccion-se-declara-en-el-adr-que-la-produce-y-las-familias-se-cuentan-solas.md) | 2026-09-12 | PROPUESTO | La mina en dos pasadas: la lección se declara en el ADR que la produce y las familias se cuentan solas | Uno. La lección se declara en el ADR que la produce, en un bloque `## La lección` con tres líneas —`familia`, `sin esto se repetiría`, `lo hace cumplir`— o con `ninguna: <razón>`, que es una respuesta legítima y frecuente. El criterio de… |
| [173](docs/decisions/ADR-173-el-cierre-de-la-incidencia-es-un-desenlace-y-el-reflector-mira-todas-las-clases-que-el-despachador-despacha.md) | 2026-09-12 | PROPUESTO | El cierre de la incidencia es un desenlace, y el reflector mira todas las clases que el despachador despacha | — |
| [172](docs/decisions/ADR-172-la-memoria-de-sesion-vive-en-supermemory-y-el-conocimiento-en-el-repositorio-con-una-regla-de-reparto-que-toda-ia-lee.md) | 2026-09-12 | PROPUESTO | La memoria de sesión vive en Supermemory y el conocimiento en el repositorio, con una regla de reparto que toda IA lee | — |
| [171](docs/decisions/ADR-171-la-memoria-comun-arranca-sobre-lo-que-ya-existe-evaluacion-funcional-de-las-tres-piezas-y-lo-que-el-motor-tiene-que-publicar.md) | 2026-09-11 | PROPUESTO | La memoria común arranca sobre lo que ya existe: evaluación funcional de las tres piezas (T-5) y lo que el motor tiene que publicar | — |
| [170](docs/decisions/ADR-170-dec-001-entra-por-pertenencia-a-su-lista-cerrada-portar-los-miembros-del-origen-y-que-g4-decida-por-pertenencia.md) | 2026-09-11 | PROPUESTO | DEC-001 entra por pertenencia a su lista cerrada: portar los miembros del origen y que G4 decida por pertenencia | — |
| [169](docs/decisions/ADR-169-el-filtro-recorta-por-la-cardinalidad-que-la-peticion-declara.md) | 2026-09-08 | PROPUESTO | El filtro recorta por la cardinalidad que la peticion declara | — |
| [168](docs/decisions/ADR-168-listar-por-vigencia-cuando-la-pregunta-declara-un-intervalo-y-la-busqueda-lexica-no-tiene-de-donde-partir.md) | 2026-09-08 | PROPUESTO | Listar por vigencia cuando la pregunta declara un intervalo y la busqueda lexica no tiene de donde partir | — |
| [167](docs/decisions/ADR-167-las-dos-puertas-de-carril-retirado-comprueban-el-estado-real-no-declaran-exito-sin-confirmarlo-y-se-cierran-ante-cualquier-fallo-del-lector.md) | 2026-09-08 | PROPUESTO | Las dos puertas de carril retirado comprueban el estado real, no declaran éxito sin confirmarlo y se cierran ante cualquier fallo del lector | — |
| [166](docs/decisions/ADR-166-el-cargador-del-banco-da-a-cada-item-la-fecha-de-registro-que-el-corpus-declara.md) | 2026-09-08 | PROPUESTO | El cargador del banco da a cada ítem la fecha de registro que el corpus declara | — |
| [164](docs/decisions/ADR-164-la-pregunta-se-convierte-en-una-peticion-propia-interpretada-no-en-la-politica-uniforme-de-hoy.md) | 2026-09-08 | PROPUESTO | La pregunta se convierte en una petición propia interpretada, no en la política uniforme de hoy | — |
| [163](docs/decisions/ADR-163-desactivar-de-forma-reversible-los-carriles-de-investigacion-y-auditoria-el-registro-de-carriles-retirados-cierra-sus-entradas-y-explica-en-vez-de-esperar.md) | 2026-09-08 | PROPUESTO | Desactivar de forma reversible los carriles de investigación y auditoría: el registro de carriles retirados cierra sus entradas y explica en vez de esperar | — |
| [162](docs/decisions/ADR-162-la-altura-de-una-fila-del-chat-se-mide-sobre-un-layout-asentado-no-en-cuanto-aparece-el-texto.md) | 2026-09-08 | PROPUESTO | La altura de una fila del chat se mide sobre un layout asentado, no en cuanto aparece el texto | — |
| [161](docs/decisions/ADR-161-retirar-los-carriles-dedicados-de-investigacion-y-auditoria-conservando-los-revisores-del-ciclo-decision-tomada-ejecucion-pendiente.md) | 2026-09-08 | PROPUESTO | Retirar los carriles dedicados de investigación y auditoría, conservando los revisores del ciclo: decisión tomada, ejecución pendiente | — |
| [160](docs/decisions/ADR-160-formalizar-la-separacion-entre-sirius-y-su-motor-sirius-es-el-companero-el-motor-ejecuta-y-las-ias-externas-son-el-lugar-de-trabajo.md) | 2026-09-08 | PROPUESTO | Formalizar la separación entre Sirius y su motor: Sirius es el compañero, el motor ejecuta y las IAs externas son el lugar de trabajo | — |
| [159](docs/decisions/ADR-159-el-recibo-de-una-reanudacion-distingue-cada-permiso-escrito-no-solo-su-head.md) | 2026-09-08 | PROPUESTO | El recibo de una reanudación distingue cada permiso escrito, no solo su head | — |
| [158](docs/decisions/ADR-158-cada-evento-de-etiqueta-tiene-su-propia-ranura-de-notificacion.md) | 2026-09-07 | PROPUESTO | Cada evento de etiqueta tiene su propia ranura de notificación | — |
| [157](docs/decisions/ADR-157-cada-parada-deja-su-propio-marcador-de-notificacion.md) | 2026-09-07 | ACEPTADO | Cada parada deja su propio marcador de notificación | — |
| [156](docs/decisions/ADR-156-el-recolector-lee-los-hallazgos-que-codex-publica-en-el-cuerpo-de-la-revision.md) | 2026-09-07 | PROPUESTO | El recolector lee los hallazgos que Codex publica en el cuerpo de la revisión | — |
| [155](docs/decisions/ADR-155-el-corrector-entrega-por-hallazgo-con-el-plazo-a-la-vista.md) | 2026-09-06 | PROPUESTO | El corrector entrega por hallazgo, con el plazo a la vista | — |
| [154](docs/decisions/ADR-154-las-cifras-de-la-validacion-se-citan-ancladas-al-arbol-que-las-produjo.md) | 2026-09-06 | PROPUESTO | Las cifras de la validación se citan ancladas al árbol que las produjo | — |
| [153](docs/decisions/ADR-153-check.ps1-se-detiene-en-el-primer-paso-rojo-y-propaga-su-codigo-de-salida.md) | 2026-09-06 | PROPUESTO | check.ps1 se detiene en el primer paso rojo y propaga su código de salida | — |
| [152](docs/decisions/ADR-152-los-pasos-posteriores-al-agente-ejecutan-la-automatizacion-de-main-no-la-del-arbol-que-el-agente-dejo.md) | 2026-09-06 | PROPUESTO | Los pasos posteriores al agente ejecutan la automatización de `main`, no la del árbol que el agente dejó | — |
| [151](docs/decisions/ADR-151-la-pasada-del-contador-mide-y-declara-su-entrega.md) | 2026-09-06 | PROPUESTO | La pasada del contador mide y declara su entrega: retraso e higiene de su ventana previa | — |
| [150](docs/decisions/ADR-150-dar-al-corrector-tiempo-para-corregir-y-validar-con-la-cadena-completa-dentro-de-su-paso.md) | 2026-09-06 | PROPUESTO | Dar al corrector tiempo para corregir y validar con la cadena completa dentro de su paso | — |
| [149](docs/decisions/ADR-149-relanzar-quality-al-entrar-en-ci-pending-cuando-su-cierre-ya-se-consumio-con-la-incidencia-en-otro-estado.md) | 2026-09-06 | PROPUESTO | Relanzar Quality al entrar en `ci-pending` cuando su cierre ya se consumió con la incidencia en otro estado | — |
| [148](docs/decisions/ADR-148-dar-la-memoria-por-bien-hecha-solo-con-todos-los-numeros-del-banco-bien-y-llegar-por-palancas-medidas.md) | 2026-09-05 | PROPUESTO | Dar la memoria por bien hecha solo con todos los números del banco bien, y llegar por palancas medidas | — |
| [147](docs/decisions/ADR-147-la-salida-de-una-parada-la-acredita-el-permiso-escrito-del-propietario.md) | 2026-09-05 | PROPUESTO | La salida de una parada la acredita el permiso escrito del propietario | — |
| [146](docs/decisions/ADR-146-el-fallo-transitorio-que-codex-declara-se-reintenta-con-el-candado-existente.md) | 2026-09-05 | PROPUESTO | El fallo transitorio que Codex declara se reintenta con el candado existente | — |
| [145](docs/decisions/ADR-145-la-validacion-obligatoria-es-una-sola-invocacion-del-script-de-comprobacion.md) | 2026-09-05 | PROPUESTO | La validación obligatoria es una sola invocación del script de comprobación | — |
| [144](docs/decisions/ADR-144-el-derivador-de-la-hora-del-contador-no-se-cuenta-a-si-mismo.md) | 2026-09-05 | PROPUESTO | El derivador de la hora del contador no se cuenta a sí mismo | — |
| [143](docs/decisions/ADR-143-los-dos-lectores-de-cron-del-repositorio-hablan-un-unico-dialecto.md) | 2026-09-05 | PROPUESTO | Los dos lectores de cron del repositorio hablan un único dialecto | — |
| [142](docs/decisions/ADR-142-la-ruta-de-avance-repone-la-revision-cuando-la-aprobacion-caduco.md) | 2026-09-05 | PROPUESTO | La ruta de avance repone la revisión cuando la aprobación caducó | — |
| [141](docs/decisions/ADR-141-una-parada-de-infraestructura-del-revisor-rearma-una-ronda-una-sola-vez.md) | 2026-09-05 | PROPUESTO | Una parada de infraestructura del revisor rearma una ronda, una sola vez | — |
| [140](docs/decisions/ADR-140-el-corrector-firma-su-run-y-demuestra-cada-mutacion.md) | 2026-09-05 | PROPUESTO | El corrector firma su run y demuestra cada mutación | — |
| [139](docs/decisions/ADR-139-la-reconciliacion-pasa-cada-hora-activa-en-vez-de-cada-seis.md) | 2026-09-05 | RECHAZADO | La reconciliación pasa cada hora activa en vez de cada seis | — |
| [138](docs/decisions/ADR-138-los-tres-agentes-del-ciclo-corren-con-el-modelo-opus.md) | 2026-09-04 | PROPUESTO | Los tres agentes del ciclo corren con el modelo opus | — |
| [137](docs/decisions/ADR-137-el-enganche-de-sirius-reflejar-corre-en-un-workflow-propio-tras-cada-cambio-de-etiqueta.md) | 2026-09-04 | PROPUESTO | El enganche de sirius-reflejar corre en un workflow propio tras cada cambio de etiqueta | — |
| [136](docs/decisions/ADR-136-el-reflejo-del-desenlace-de-github-vuelve-al-almacen-del-motor.md) | 2026-09-04 | PROPUESTO | El reflejo del desenlace de GitHub vuelve al almacén del motor | — |
| [135](docs/decisions/ADR-135-el-corrector-actualiza-en-el-mismo-commit-el-papel-que-depende-de-su-correccion.md) | 2026-09-04 | PROPUESTO | El corrector actualiza en el mismo commit el papel que depende de su corrección | — |
| [134](docs/decisions/ADR-134-el-guardian-del-suelo-de-prueba-muerto-retira-las-dos-cotas-tautologicas-del-banco-de-evidencia.md) | 2026-09-04 | PROPUESTO | El guardián del suelo de prueba muerto retira las dos cotas tautológicas del banco de evidencia | — |
| [133](docs/decisions/ADR-133-g3-el-guardian-de-goteo-entiende-las-citas-tal-como-los-revisores-las-escriben-de-verdad.md) | 2026-09-04 | PROPUESTO | G3: el guardian de goteo entiende las citas tal como los revisores las escriben de verdad | — |
| [132](docs/decisions/ADR-132-el-guardian-del-contrato-local-de-ollama-convierte-adr-125-en-prueba-y-corrige-ollama-category-classifier.md) | 2026-09-04 | PROPUESTO | El guardián del contrato local de Ollama convierte ADR-125 en prueba y corrige ollama_category_classifier | — |
| [131](docs/decisions/ADR-131-m21b-la-interfaz-de-la-criticidad-sirius-propone-y-el-usuario-confirma-o-rechaza.md) | 2026-09-03 | PROPUESTO | M21b: la interfaz de la criticidad, Sirius propone y el usuario confirma o rechaza | — |
| [130](docs/decisions/ADR-130-m21a-sirius-propone-la-criticidad-sin-escribirla.md) | 2026-09-03 | PROPUESTO | M21a: Sirius propone la criticidad sin escribirla | — |
| [129](docs/decisions/ADR-129-m20-la-siembra-en-contexto-por-criticidad.md) | 2026-09-03 | PROPUESTO | M20: la siembra en contexto por criticidad | — |
| [128](docs/decisions/ADR-128-m19b-el-rescate-rf-25-rf-26-y-la-prioridad-de-g12-por-criticidad.md) | 2026-09-03 | PROPUESTO | M19b: el rescate RF-25/RF-26 y la prioridad de G12 por criticidad | — |
| [127](docs/decisions/ADR-127-m19a-el-indice-de-criticidad-en-la-busqueda.md) | 2026-09-03 | PROPUESTO | M19a: el índice de criticidad en la búsqueda | — |
| [126](docs/decisions/ADR-126-m18b-la-senal-de-criticidad-como-dato-propio-de-cada-recuerdo-y-decision.md) | 2026-09-02 | PROPUESTO | M18b: la señal de criticidad como dato propio de cada recuerdo y decisión | — |
| [125](docs/decisions/ADR-125-suspender-el-limite-de-300-ms-de-rnf-003-en-el-camino-del-filtro-de-relevancia-mientras-se-mide-su-coste-real.md) | 2026-09-02 | APROBADO | Suspender el limite de 300 ms de RNF-003 en el camino del filtro de relevancia mientras se mide su coste real | — |
| [124](docs/decisions/ADR-124-cablear-la-peticion-de-produccion-en-rankrelevantknowledgeusecase-con-ambito-real-derivado-del-proyecto-activo-y-proposito-honesto-que-activa-pide-contexto-m16.md) | 2026-09-01 | APROBADO | Cablear la petición de producción en RankRelevantKnowledgeUseCase con ámbito real derivado del proyecto activo y propósito honesto que activa pide_contexto (M16) | — |
| [123](docs/decisions/ADR-123-guardian-de-goteo-en-vivo-integrado-con-el-aviso-de-familia-repetida.md) | 2026-08-31 | APROBADO | Guardián de goteo en vivo, integrado con el aviso de familia repetida | — |
| [122](docs/decisions/ADR-122-consulta-por-lote-en-stagedengineport-y-ampliacion-por-categoria-filtrada-en-sql.md) | 2026-08-31 | APROBADO | Consulta por lote en StagedEnginePort y ampliación por categoría filtrada en SQL (M13, incidencia #489, integrado sobre M14) | — |
| [121](docs/decisions/ADR-121-cablear-el-detector-de-familia-repetida-al-ciclo-real-como-aviso-informativo.md) | 2026-08-31 | APROBADO | Cablear el detector de familia repetida al ciclo real como aviso informativo | — |
| [120](docs/decisions/ADR-120-m15-rf-25-rf-26-sustituye-el-candado-de-m10-y-g8-g12-se-aplican-sobre-el-conjunto-combinado-ambos-tras-la-puerta.md) | 2026-08-31 | PROPUESTO | M15: RF-25/RF-26 sustituye el candado de M10 y G8/G12 se aplican sobre el conjunto combinado, ambos tras la puerta | — |
| [119](docs/decisions/ADR-119-disenar-la-ola-de-paridad-en-produccion-portar-la-semantica-del-arnes-tras-la-puerta-category-matching-enabled-la-peticion-de-contexto-real-y-el-plan-de-optimizacion-de-rnf-003-incidencia-478.md) | 2026-08-31 | PROPUESTO | Diseñar la ola de paridad en producción: portar la semántica del arnés tras la puerta category_matching_enabled, la petición de contexto real y el plan de optimización de RNF-003 (incidencia #478) | — |
| [118](docs/decisions/ADR-118-cuatro-huecos-operativos-del-motor-verdes-sin-registrar-reparaciones-tras-mover-el-head-bloqueos-mal-enrutados-y-decisiones-invisibles-al-corrector-incidencias-435-442-453-469-471.md) | 2026-08-31 | PROPUESTO | Cuatro huecos operativos del motor: verdes sin registrar, reparaciones tras mover el head, bloqueos mal enrutados y decisiones invisibles al corrector (incidencias #435, #442, #453, #469, #471) | — |
| [117](docs/decisions/ADR-117-m11-mide-rnf-003-con-el-paquete-completo-activo-y-publica-la-coincidencia-del-etiquetado-sin-abrir-la-puerta-de-d7-punto-6.md) | 2026-08-31 | PROPUESTO | M11 mide RNF-003 con el paquete completo activo y publica la coincidencia del etiquetado, sin abrir la puerta de D7 punto 6 | — |
| [116](docs/decisions/ADR-116-categoria-de-maxima-criticidad-y-etiquetas-canonicas-provisionales-del-banco-de-47-casos-para-m11.md) | 2026-08-31 | PROPUESTO | Categoría de máxima criticidad y etiquetas canónicas provisionales del banco de 47 casos para M11 | — |
| [115](docs/decisions/ADR-115-las-dos-puertas-que-la-ampliacion-del-arnes-no-heredaba-bajan-los-aciertos-exactos-a-29-47-y-elementos-de-mas-alcanza-d1-bajo-la-poblacion-del-umbral-publicado-incidencia-469.md) | 2026-08-31 | PROPUESTO | Las dos puertas que la ampliación del arnés no heredaba bajan los aciertos exactos a 29/47 y elementos de más alcanza D1 bajo la población del umbral publicado (incidencia #469) | — |
| [114](docs/decisions/ADR-114-la-restriccion-por-ambito-del-indice-de-categoria-baja-los-elementos-de-mas-de-110-a-62-pero-no-alcanza-d1-incidencia-467.md) | 2026-08-30 | PROPUESTO | La restricción por ámbito del índice de categoría baja los elementos de más de 110 a 62 pero no alcanza D1 (incidencia #467) | — |
| [113](docs/decisions/ADR-113-el-indice-de-categoria-buscable-la-regla-de-las-criticas-original-y-la-siembra-en-contexto-cierran-las-dos-causas-de-adr-112-pero-no-alcanzan-d1-incidencia-465.md) | 2026-08-30 | PROPUESTO | El índice de categoría buscable, la regla de las críticas original y la siembra en contexto cierran las dos causas de ADR-112 pero no alcanzan D1 (incidencia #465) | — |
| [112](docs/decisions/ADR-112-el-indice-de-categoria-y-el-filtro-de-relevancia-conectados-al-arnes-del-banco-incidencia-463-mejoran-cobertura-y-omisiones-criticas-pero-empeoran-los-elementos-de-mas-y-no-alcanzan-d1.md) | 2026-08-30 | PROPUESTO | El índice de categoría y el filtro de relevancia, conectados al arnés del banco (incidencia #463), mejoran cobertura y omisiones críticas pero empeoran los elementos de más y no alcanzan D1 | — |
| [111](docs/decisions/ADR-111-la-peticion-por-caso-portada-mejora-el-banco-a-23-47-pero-d1-exige-ademas-el-indice-de-categoria-y-el-filtro-de-relevancia-ollama.md) | 2026-08-30 | PROPUESTO | La petición por caso portada mejora el banco a 23/47 pero D1 exige además el índice de categoría y el filtro de relevancia Ollama | — |
| [110](docs/decisions/ADR-110-el-motor-por-etapas-portado-mejora-el-banco-a-11-47-pero-no-alcanza-el-suelo-d1-porque-la-peticion-por-caso-del-laboratorio-no-esta-autorizada-a-portarse.md) | 2026-08-30 | PROPUESTO | El motor por etapas portado mejora el banco a 11/47 pero no alcanza el suelo D1 porque la petición por caso del laboratorio no está autorizada a portarse | — |
| [109](docs/decisions/ADR-109-el-tratamiento-lexico-portado-mejora-el-banco-de-1-47-a-10-47-pero-no-alcanza-el-suelo-d1-porque-la-precision-restante-vive-en-las-puertas-del-motor-por-etapas.md) | 2026-08-30 | PROPUESTO | El tratamiento léxico portado mejora el banco de 1/47 a 10/47, pero no alcanza el suelo D1 porque la precisión restante vive en las puertas del motor por etapas | — |
| [106](docs/decisions/ADR-106-vocabulario-y-modelo-provisionales-del-clasificador-de-categoria-en-composition-root.md) | 2026-08-29 | PROPUESTO | Vocabulario y modelo provisionales del clasificador de categoría en composition_root | — |
| [105](docs/decisions/ADR-105-anadir-rama-de-origen-no-fusionada-al-guardian-de-citas-de-los-adr.md) | 2026-08-29 | PROPUESTO | Añadir RAMA_DE_ORIGEN_NO_FUSIONADA al guardián de citas de los ADR | — |
| [104](docs/decisions/ADR-104-portar-el-banco-de-47-casos-de-evidence-adr001-spikes-al-modelo-real-de-sirius.md) | 2026-08-29 | PROPUESTO | Portar el banco de 47 casos de evidence/adr001-spikes al modelo real de Sirius | — |
| [103](docs/decisions/ADR-103-via-automatica-de-sugerencias-de-memoria-delimitador-compartido-divisor-incremental-y-superficie-de-disparo-sin-qt.md) | 2026-08-29 | PROPUESTO | Vía automática de sugerencias de memoria: delimitador compartido, divisor incremental y superficie de disparo sin Qt | — |
| [102](docs/decisions/ADR-102-las-pruebas-de-aceptacion-de-sirius-0.2-no-resuelven-las-decisiones-que-la-definicion-deja-abiertas.md) | 2026-08-29 | PROPUESTO | Las pruebas de aceptación de Sirius 0.2 no resuelven las decisiones que la Definición deja abiertas | — |
| [101](docs/decisions/ADR-101-declarar-la-precondicion-del-contador-de-siete-dias-en-vez-de-inferirla-por-caso.md) | 2026-08-28 | APROBADO | Declarar la precondicion del contador de siete dias en vez de inferirla por caso | — |
| [100](docs/decisions/ADR-100-el-manifiesto-versionado-decide-que-texto-es-cada-perfil.md) | 2026-08-28 | APROBADO | Fijar cada `rol@N` a un texto exacto con un manifiesto verificado por sha256 | — |
| [099](docs/decisions/ADR-099-la-clase-investigacion-entra-en-la-tabla-de-activacion-y-su-ejecutor-es-el-investigador-medido.md) | 2026-08-28 | PROPUESTO | La clase investigacion entra en la tabla de activación, y su ejecutor es el investigador medido | — |
| [098](docs/decisions/ADR-098-el-investigador-se-queda-con-nvidia-porque-fue-el-unico-que-pudo-correr-la-prueba.md) | 2026-08-27 | PROPUESTO | El investigador se queda con NVIDIA, porque fue el único que pudo correr la prueba | — |
| [097](docs/decisions/ADR-097-un-tres-no-es-un-fallo-sino-un-veredicto-con-motivo-y-el-plazo-se-reparte-por-pregunta.md) | 2026-08-27 | PROPUESTO | Un tres no es un fallo sino un veredicto con motivo, y el plazo se reparte por pregunta | — |
| [096](docs/decisions/ADR-096-una-contradiccion-de-etiquetas-no-es-una-divergencia-y-confundirlas-gasta-la-salida-de-emergencia.md) | 2026-08-27 | PROPUESTO | Una contradicción de etiquetas no es una divergencia, y confundirlas gasta la salida de emergencia | — |
| [095](docs/decisions/ADR-095-la-escalera-de-cuatro-preguntas-y-el-atestado-que-impide-medir-un-modelo-muerto.md) | 2026-08-27 | PROPUESTO | La escalera de cuatro preguntas, y el atestado que impide medir un modelo muerto | — |
| [094](docs/decisions/ADR-094-una-parada-anterior-a-la-primera-pr-se-reanuda-repitiendo-la-fase-no-continuando-sobre-un-head.md) | 2026-08-25 | PROPUESTO | Una parada anterior a la primera PR se reanuda repitiendo la fase, no continuando sobre un head | — |
| [093](docs/decisions/ADR-093-el-registro-de-la-racha-vive-en-la-rama-de-memoria-no-en-main.md) | 2026-08-25 | PROPUESTO | El registro de la racha vive en la rama de memoria, no en `main` | — |
| [092](docs/decisions/ADR-092-cerrar-el-marcador-de-corte-por-presupuesto-abandonandolo-cuando-el-workitem-sale-de-curso.md) | 2026-08-25 | APROBADO | Cerrar el marcador de corte por presupuesto abandonándolo cuando el WorkItem sale de curso | — |
| [091](docs/decisions/ADR-091-la-disciplina-de-evidencia-alcanza-tambien-a-responder-no-solo-a-modificar-codigo.md) | 2026-08-25 | PROPUESTO | La disciplina de evidencia alcanza también a responder, no solo a modificar código | — |
| [090](docs/decisions/ADR-090-darle-horario-al-motor-treinta-minutos-despues-del-reconciliador.md) | 2026-08-25 | PROPUESTO | Darle horario al motor, dentro de la ventana que dejan el reconciliador y el contador | — |
| [089](docs/decisions/ADR-089-partir-un-objetivo-grande-lo-hace-la-sesion-interactiva-y-el-descomponedor-automatico-queda-aplazado.md) | 2026-08-25 | PROPUESTO | Partir un objetivo grande lo hace la sesión interactiva, y el descomponedor automático queda aplazado | — |
| [088](docs/decisions/ADR-088-elegir-el-prompt-por-el-perfil-del-encargo-y-morir-en-rojo-si-no-se-reconoce.md) | 2026-08-25 | PROPUESTO | Elegir el prompt por el perfil del encargo, y morir en rojo si no se reconoce | — |
| [087](docs/decisions/ADR-087-dar-nombre-propio-a-los-bloques-del-motor-y-exigir-evidencia-para-cerrar-uno.md) | 2026-08-25 | PROPUESTO | Dar nombre propio a los bloques del motor y exigir evidencia para cerrar uno | — |
| [086](docs/decisions/ADR-086-dar-manos-al-despachador-dentro-de-actions-para-que-el-encargo-llegue-al-diario-del-motor.md) | 2026-08-25 | PROPUESTO | Dar manos al despachador dentro de Actions, para que el encargo llegue al diario del motor | — |
| [085](docs/decisions/ADR-085-el-interprete-de-intencion-comprueba-sensibilidad-y-verbo-reconocido-antes-que-marcadores-de-pasado.md) | 2026-08-25 | PROPUESTO | El intérprete de intención comprueba sensibilidad y verbo reconocido antes que marcadores de pasado | — |
| [084](docs/decisions/ADR-084-el-aviso-de-lecturas-caidas-hoy-no-interrumpe-el-contador-de-la-racha.md) | 2026-08-25 | PROPUESTO | El aviso de lecturas caidas hoy no interrumpe el contador de la racha | — |
| [083](docs/decisions/ADR-083-la-memoria-del-motor-vive-en-su-propia-rama-no-en-main.md) | 2026-08-24 | PROPUESTO | La memoria del motor vive en su propia rama, no en `main` | — |
| [082](docs/decisions/ADR-082-el-motor-corre-dentro-de-github-actions-y-su-memoria-vive-en-el-repositorio.md) | 2026-08-24 | PROPUESTO | El motor corre dentro de GitHub Actions y su memoria vive en el repositorio | — |
| [081](docs/decisions/ADR-081-un-doble-de-pruebas-que-se-calla-esconde-el-defecto-que-deberia-delatar.md) | 2026-08-23 | APROBADO | Un doble de pruebas que se calla esconde el defecto que debería delatar | — |
| [080](docs/decisions/ADR-080-un-arreglo-fusionado-se-reconoce-por-el-asunto-del-commit.md) | 2026-08-23 | APROBADO | Un arreglo fusionado se reconoce por el asunto del commit, y por eso la guarda ve poco pero no se equivoca | — |
| [079](docs/decisions/ADR-079-una-tabla-indexada-por-un-enum-cubre-el-enum-entero-o-lo-declara.md) | 2026-08-23 | APROBADO | Una tabla indexada por un enum cubre el enum entero, o lo declara | — |
| [078](docs/decisions/ADR-078-tres-rondas-consecutivas-sobre-el-mismo-archivo-son-la-familia-repetida-medido-antes-de-fijarlo.md) | 2026-08-23 | APROBADO | Tres rondas consecutivas sobre el mismo archivo son la familia repetida, medido antes de fijarlo | — |
| [077](docs/decisions/ADR-077-la-autoridad-de-una-clase-es-la-tabla-estatica-mas-un-registro-fechado-y-su-reversion-no-espera-a-la-segunda-divergencia.md) | 2026-08-23 | APROBADO | La autoridad de una clase es la tabla estática más un registro fechado, y su reversión no espera a la segunda divergencia | — |
| [076](docs/decisions/ADR-076-el-motor-deja-de-necesitar-el-arbol-de-codigo-para-ejecutar-la-proyeccion.md) | 2026-08-23 | PROPUESTO | El motor deja de necesitar el árbol de código para ejecutar la proyección | — |
| [075](docs/decisions/ADR-075-el-estado-de-un-defecto-lo-dice-el-registro-versionado-y-la-incidencia-se-cierra-con-el.md) | 2026-08-22 | PROPUESTO | El estado de un defecto lo dice el registro versionado y la incidencia se cierra con el | — |
| [074](docs/decisions/ADR-074-el-contador-de-los-siete-dias-deriva-la-correccion-manual-del-diario-de-eventos-del-motor.md) | 2026-08-22 | APROBADO | El contador de los siete días deriva la corrección manual del diario de eventos del motor | — |
| [073](docs/decisions/ADR-073-el-verificador-de-proyeccion-se-ve-fallar-antes-de-fiarse-de-que-de-verde.md) | 2026-08-22 | APROBADO | El verificador de proyección se ve fallar antes de fiarse de que dé verde | — |
| [072](docs/decisions/ADR-072-reparar-tiene-dos-entradas-porque-el-ciclo-real-tiene-dos.md) | 2026-08-22 | PROPUESTO | REPARAR tiene dos entradas, porque el ciclo real tiene dos | — |
| [071](docs/decisions/ADR-071-la-inversa-de-la-proyeccion-del-cuerpo-para-que-haya-algo-que-verificar.md) | 2026-08-22 | PROPUESTO | La inversa de la proyección del cuerpo, para que haya algo que verificar | — |
| [070](docs/decisions/ADR-070-las-defensas-de-workflow-reconocen-accion-clasificada-no-un-nombre.md) | 2026-08-22 | PROPUESTO | Las defensas de workflow reconocen «acción clasificada», no un nombre | — |
| [069](docs/decisions/ADR-069-fusionar-exige-que-la-rama-este-al-dia-con-su-base.md) | 2026-08-22 | PROPUESTO | Fusionar exige que la rama esté al día con su base | — |
| [068](docs/decisions/ADR-068-la-etiqueta-que-el-motor-aplica-depende-de-la-clase-que-despacha.md) | 2026-08-22 | PROPUESTO | La etiqueta que el motor aplica depende de la clase que despacha | — |
| [067](docs/decisions/ADR-067-las-ordenes-del-propietario-toleran-la-firma-que-anade-la-herramienta.md) | 2026-08-22 | APROBADO | Las órdenes del propietario toleran la firma que añade la herramienta | — |
| [066](docs/decisions/ADR-066-perfiles-documentales-documentalista-y-revisor-documental-coherentes-con-la-maquinaria-existente.md) | 2026-08-22 | PROPUESTO | Perfiles documentales: documentalista y revisor documental, coherentes con la maquinaria existente | — |
| [065](docs/decisions/ADR-065-el-despachador-usa-el-diario-durable-ahora-y-no-en-d2.md) | 2026-08-22 | APROBADO | El despachador usa el diario durable ahora y no en D2 | — |
| [064](docs/decisions/ADR-064-diario-del-despachador-durable-reutiliza-adr-061.md) | 2026-08-22 | APROBADO | Diario del despachador durable reutiliza ADR-061 | — |
| [063](docs/decisions/ADR-063-sirius-despachar-la-costura-entre-una-orden-y-la-via-github-con-ensayo-por-defecto.md) | 2026-08-21 | APROBADO | `sirius-despachar`: la costura entre una orden y la vía GitHub, con ensayo por defecto | — |
| [062](docs/decisions/ADR-062-c2-despacho-end-to-end-de-programacion-escritura-minima-enumerada-y-orden-enlazada-en-la-evidencia.md) | 2026-08-21 | APROBADO | C2 — despacho end-to-end de programación: escritura mínima enumerada y orden enlazada en la evidencia | — |
| [061](docs/decisions/ADR-061-diario-del-supervisor-durable-como-outbox-propio-no-acoplado-al-almacen.md) | 2026-08-21 | APROBADO | Diario del supervisor durable como outbox propio, no acoplado al almacen | — |
| [060](docs/decisions/ADR-060-un-error-del-conector-no-es-silencio-y-no-debe-costar-el-plazo-entero.md) | 2026-08-21 | APROBADO | Un error del conector no es silencio, y no debe costar el plazo entero | — |
| [059](docs/decisions/ADR-059-la-sesion-dice-no-pude-mirar-en-vez-de-no-hay-nada-y-lo-dice-tambien-cuando-encontro-algo.md) | 2026-08-21 | APROBADO | La sesión dice «no pude mirar» en vez de «no hay nada», y lo dice también cuando sí encontró algo | — |
| [058](docs/decisions/ADR-058-la-fase-entra-en-la-tabla-de-estados-como-coordenada-dependiente-y-el-eje-fase-gana-su-propia-guarda.md) | 2026-08-21 | APROBADO | La fase entra en la tabla de estados como coordenada dependiente, y el eje fase gana su propia guarda | — |
| [057](docs/decisions/ADR-057-supervisor-de-la-via-github-detectar-runs-perdidos-y-actuar.md) | 2026-08-21 | PROPUESTO | Supervisor de la vía GitHub: detectar Runs perdidos y actuar | — |
| [056](docs/decisions/ADR-056-el-motor-puede-transportar-una-orden-ya-dada-y-reparar-sus-propios-runs.md) | 2026-08-21 | APROBADO | El motor puede transportar una orden ya dada y reparar sus propios Runs | — |
| [055](docs/decisions/ADR-055-un-comando-de-consola-que-el-propietario-pueda-teclear-para-hablar-con-el-motor.md) | 2026-08-21 | PROPUESTO | Dar al motor un comando de consola que conversa y consulta, y que no puede crear trabajo | — |
| [054](docs/decisions/ADR-054-un-run-tiene-que-poder-decir-con-que-modelo-se-ejecuto.md) | 2026-08-21 | APROBADO | Un Run tiene que poder decir con qué modelo se ejecutó | — |
| [053](docs/decisions/ADR-053-no-pude-observar-es-un-valor-del-puerto-y-el-barrido-no-lo-convierte-en-exito.md) | 2026-08-21 | APROBADO | «No pude observar» es un valor del puerto, y el barrido no lo convierte en éxito | — |
| [052](docs/decisions/ADR-052-una-ruta-citada-por-un-adr-existe-o-esta-fijada-como-historia.md) | 2026-08-21 | APROBADO | Una ruta citada por un ADR existe, o está fijada como historia | — |
| [051](docs/decisions/ADR-051-el-cuerpo-de-una-incidencia-pasa-por-el-mismo-filtro-de-confianza-que-sus-comentarios.md) | 2026-08-21 | PROPUESTO | El cuerpo de una incidencia pasa por el mismo filtro de confianza que sus comentarios | — |
| [050](docs/decisions/ADR-050-los-tres-proveedores-de-contexto-tienen-la-misma-firma-y-reportan-su-fallo.md) | 2026-08-21 | APROBADO | Los tres proveedores de `contexto.recuperar` tienen la misma firma y reportan su fallo | — |
| [048](docs/decisions/ADR-048-la-capa-que-llama-a-las-reglas-tambien-necesita-su-tabla-exhaustiva-de-estados.md) | 2026-08-21 | APROBADO | La capa que llama a las reglas también necesita su tabla exhaustiva de estados | — |
| [047](docs/decisions/ADR-047-un-defecto-encontrado-se-registra-con-incidencia-y-no-se-borra-nunca.md) | 2026-08-21 | APROBADO | Un defecto encontrado se registra con incidencia y no se borra nunca | — |
| [046](docs/decisions/ADR-046-spike-i1-bordes-de-status-sobre-runs-de-actions.md) | 2026-08-21 | PROPUESTO | Spike I1: bordes de STATUS sobre runs de Actions | — |
| [045](docs/decisions/ADR-045-el-corte-por-presupuesto-tiene-que-salir-tambien-de-waiting-que-es-donde-se-gasta-el-dinero.md) | 2026-08-21 | APROBADO | El corte por presupuesto tiene que salir también de WAITING, que es donde se gasta el dinero | — |
| [044](docs/decisions/ADR-044-abrir-el-repositorio-al-publico-sin-que-el-propio-repositorio-lo-desmienta.md) | 2026-08-20 | PROPUESTO | Abrir el repositorio al público sin que el propio repositorio lo desmienta | — |
| [043](docs/decisions/ADR-043-gobierno-previo-al-primer-worker-externo-puerta-determinista-presupuesto-con-corte-y-siete-causas-cerradas-de-escalado.md) | 2026-08-19 | APROBADO | Gobierno previo al primer Worker externo: puerta determinista, presupuesto con corte y siete causas cerradas de escalado | — |
| [042](docs/decisions/ADR-042-un-paso-de-preparacion-sin-plazo-propio-puede-costar-el-trabajo-entero.md) | 2026-08-19 | APROBADO | Un paso de preparación sin plazo propio puede costar el trabajo entero | — |
| [041](docs/decisions/ADR-041-la-autoridad-de-cada-clase-de-trabajo-se-fija-antes-de-que-exista-el-primer-workitem.md) | 2026-08-19 | APROBADO | La autoridad de cada clase de trabajo se fija antes de que exista el primer WorkItem | — |
| [040](docs/decisions/ADR-040-convertir-una-intencion-en-encargo-preguntando-una-cosa-cada-vez.md) | 2026-08-19 | APROBADO | Convertir una intención en encargo preguntando una cosa cada vez | — |
| [039](docs/decisions/ADR-039-perfiles-versionados-gobiernan-a-los-workers-sin-acoplarse-a-runtimes-y-el-egress-es-imposible-de-saltar.md) | 2026-08-19 | APROBADO | Perfiles versionados gobiernan a los Workers sin acoplarse a runtimes, y el egress es imposible de saltar | — |
| [038](docs/decisions/ADR-038-una-prueba-que-mutila-datos-debe-alterar-siempre-lo-que-comprueba.md) | 2026-08-19 | APROBADO | Una prueba que mutila datos debe alterar siempre lo que comprueba | — |
| [037](docs/decisions/ADR-037-reanudar-y-fusionar-son-gestos-humanos-y-la-automatizacion-no-los-rodea.md) | 2026-08-18 | APROBADO | Reanudar y fusionar son gestos humanos, y la automatización no los rodea | — |
| [036](docs/decisions/ADR-036-una-lectura-caida-no-es-una-ausencia-y-el-llamador-tiene-que-poder-distinguirlas.md) | 2026-08-18 | APROBADO | Una lectura caída no es una ausencia, y el llamador tiene que poder distinguirlas | — |
| [035](docs/decisions/ADR-035-el-revisor-no-juzga-con-el-interprete-del-runner-y-toda-parada-tiene-vuelta.md) | 2026-08-18 | APROBADO | El revisor no juzga con el intérprete del runner, y toda parada tiene vuelta | — |
| [034](docs/decisions/ADR-034-espejo-de-solo-lectura-marca-cada-proyeccion-y-nunca-confunde-fallo-con-ausencia.md) | 2026-08-18 | PROPUESTO | El espejo de solo lectura de la vía GitHub marca cada proyección como no autoritativa y nunca confunde un fallo de lectura con una ausencia | — |
| [033](docs/decisions/ADR-033-una-regla-que-enumera-vehiculos-siempre-tiene-un-hueco-mas.md) | 2026-08-18 | PROPUESTO | Una regla que enumera vehículos siempre tiene un hueco más: enunciar la propiedad | — |
| [032](docs/decisions/ADR-032-el-numero-de-un-adr-es-el-maximo-existente-mas-uno.md) | 2026-08-17 | PROPUESTO | Calcular el número de un ADR como el máximo existente más uno | — |
| [031](docs/decisions/ADR-031-el-corrector-puede-declarar-que-el-fallo-de-ci-no-es-suyo.md) | 2026-08-18 | PROPUESTO | Un rol necesita un veredicto para cada desenlace real, incluido «esto no lo he roto yo» | — |
| [030](docs/decisions/ADR-030-una-parada-se-levanta-con-una-orden-no-con-cirugia.md) | 2026-08-18 | PROPUESTO | Todo estado de parada declara la orden que lo levanta | — |
| [029](docs/decisions/ADR-029-almacen-durable-de-referencia-y-barrido-de-recuperacion-a2.md) | 2026-08-18 | PROPUESTO | Promocionar el patrón de escritura de S1 a almacén de referencia del Work Engine, más el barrido de recuperación (A2) | — |
| [028](docs/decisions/ADR-028-una-averia-transitoria-no-justifica-una-invariante-permanente.md) | 2026-08-17 | PROPUESTO | Una avería transitoria de un tercero no justifica una invariante permanente en la suite | — |
| [027](docs/decisions/ADR-027-las-etiquetas-se-leen-del-objeto-de-la-incidencia.md) | 2026-08-17 | PROPUESTO | Las etiquetas se leen del objeto de la incidencia, nunca del endpoint `/issues/{n}/labels` | — |
| [026](docs/decisions/ADR-026-spike-i3-diario-append-only-con-checksum-e-idempotencia.md) | 2026-08-17 | PROPUESTO | Adoptar diario append-only con `fsync`, checksum por registro e idempotencia por clave como patrón de escritura seguro del spike I3 | — |
| [025](docs/decisions/ADR-025-una-afirmacion-del-prompt-sobre-el-entorno-debe-ser-verificable.md) | 2026-08-17 | PROPUESTO | Ninguna afirmación de un prompt sobre su entorno vale sin una prueba que la ate al workflow que lo ejecuta | — |
| [024](docs/decisions/ADR-024-ninguna-regla-de-rol-puede-faltar-en-un-prompt.md) | 2026-08-17 | PROPUESTO | Extender al implementador las tres reglas de rol y vigilarlas con una prueba que recorre el directorio de prompts | — |
| [023](docs/decisions/ADR-023-admitir-el-canal-por-el-que-codex-declara-que-no-encontro-hallazgos.md) | 2026-08-16 | PROPUESTO | Admitir como aprobación de Codex el comentario en el que declara no haber encontrado hallazgos | — |
| [022](docs/decisions/ADR-022-el-revisor-escribe-antes-de-revisar-no-espera-y-usa-el-entorno-que-hay.md) | 2026-08-16 | PROPUESTO | Endurecer el prompt del revisor: veredicto provisional, prohibición de esperar nada (subagentes incluidos) y revisión con el entorno acotado que hay | — |
| [021](docs/decisions/ADR-021-el-corrector-no-espera-nada-en-segundo-plano.md) | 2026-08-16 | PROPUESTO | Prohibir en el prompt que el corrector cierre el turno esperando trabajo en segundo plano | — |
| [020](docs/decisions/ADR-020-construir-el-work-engine-por-verticales-delgadas-sobre-la-via-github.md) | 2026-08-15 | APROBADO | Construir el Work Engine por verticales delgadas, reutilizando la vía GitHub y aplazando cada decisión a su punto exacto de consumo | — |
| [019](docs/decisions/ADR-019-el-motor-de-trabajo-posee-el-estado-y-los-workers-son-sustituibles.md) | 2026-08-15 | APROBADO | Diseñar el Motor de Trabajo como software determinista que posee el estado, con Workers sustituibles detrás de Adapters | — |
| [016](docs/decisions/ADR-016-el-auditor-se-lanza-por-etiqueta-y-no-escribe-nunca.md) | 2026-08-14 | PROPUESTO | El Auditor se lanza con una etiqueta, y el trabajo que puede escribir no ejecuta modelos | — |
| [016](docs/decisions/ADR-016-el-estado-se-lee-de-main-no-de-la-rama.md) | 2026-08-14 | PROPUESTO | El estado del proyecto se lee de `main`, nunca de la rama de trabajo | — |
| [015](docs/decisions/ADR-015-toda-escritura-de-etiqueta-pasa-por-una-envoltura.md) | 2026-08-14 | PROPUESTO | Toda escritura de etiqueta pasa por una envoltura con el PAT, y la prueba busca lo malo en vez de lo bueno | — |
| [014](docs/decisions/ADR-014-la-identidad-que-escribe-una-etiqueta-decide-si-avisa.md) | 2026-08-14 | PROPUESTO | Quien escribe una etiqueta notificable usa la identidad real, y el recolector de Codex no aprueba por comentario | — |
| [013](docs/decisions/ADR-013-la-contrasena-de-obs-vive-en-el-almacen-del-sistema.md) | 2026-08-14 | PROPUESTO | La contraseña de OBS vive en el almacén del sistema, y sin él no se guarda | — |
| [012](docs/decisions/ADR-012-frontera-de-confianza-de-sirius-0.1.md) | 2026-08-14 | PROPUESTO | Un proceso local que corre como el usuario está dentro de la frontera de confianza | — |
| [011](docs/decisions/ADR-011-la-respuesta-de-obs-se-correlaciona-con-su-peticion.md) | 2026-08-14 | PROPUESTO | Correlacionar cada respuesta de OBS con su petición, en vez de desconectar ante un plazo agotado | — |
| [010](docs/decisions/ADR-010-auditor-agent-v0-como-primer-piloto.md) | 2026-08-12 | PROPUESTO | Adoptar Auditor Agent v0 (solo lectura) como primer piloto de agentes | — |
| [009](docs/decisions/ADR-009-la-voz-de-model-studio-suena-por-el-sistema-y-empieza-antes.md) | 2026-08-12 | PROPUESTO | Sacar la voz de Model Studio por el reproductor del sistema y empezar a hablar antes de terminar | — |
| [008](docs/decisions/ADR-008-cargar-en-lote-las-revisiones-vigentes-al-listar.md) | 2026-08-11 | PROPUESTO | Cargar en lote las revisiones vigentes al listar recuerdos y decisiones | — |
| [007](docs/decisions/ADR-007-el-limite-de-rendimiento-solo-se-afirma-con-holgura.md) | 2026-08-10 | PROPUESTO | Afirmar el límite de rendimiento en CI solo si hay un orden de magnitud de holgura | — |
| [006](docs/decisions/ADR-006-la-trazabilidad-se-declara-y-se-comprueba.md) | 2026-08-10 | PROPUESTO | Declarar la trazabilidad PA/SP y comprobarla por máquina, en vez de derivarla por búsqueda | — |
| [005](docs/decisions/ADR-005-un-solo-registro-de-estado-para-v8.md) | 2026-08-10 | PROPUESTO | Mantener el estado de V8 en un único registro que la automatización pueda escribir | — |
| [004](docs/decisions/ADR-004-red-de-seguridad-periodica-para-estados-que-no-avanzan.md) | 2026-08-10 | PROPUESTO | Una red de seguridad periódica, porque un run muerto no puede avisar | — |
| [003](docs/decisions/ADR-003-los-plazos-son-minimos-contra-una-cota-absoluta.md) | 2026-08-10 | PROPUESTO | Un plazo es un mínimo contra una cota absoluta, nunca una ventana propia | — |
| [002](docs/decisions/ADR-002-permisos-de-la-automatizacion-sobre-workflows.md) | 2026-08-09 | PROPUESTO | No conceder a la automatización permiso sobre sus propios workflows | — |
| [001](docs/decisions/ADR-001-disciplina-de-evidencia.md) | 2026-08-08 | PROPUESTO | Instrumentar la disciplina de evidencia con una skill y este registro | — |

## Las lecciones, por familia (ADR-174)

Lo que alguien repetiría sin cada ADR, agrupado por familia de fallo y
contado por la máquina. **La cuenta no la lleva nadie**: un número escrito a
mano caduca en silencio -`AGENTS.md` decía «seis veces» cuando ya iban ocho-.
Declararla es obligatorio desde ADR-174; los anteriores
quedan exentos, así que esta vista crece desde cero en vez de nacer rellenada
de memoria.

| Familia | Veces | Hay prueba que la haga cumplir | ADR |
|---|---|---|---|
| `regla-que-depende-de-que-alguien-se-acuerde` | 6 | sí | [192](docs/decisions/ADR-192-el-numero-de-un-defecto-es-el-numero-de-su-adr-no-un-contador-aparte.md), [191](docs/decisions/ADR-191-la-revision-es-una-cola-una-rama-entra-a-revision-solo-si-main-ya-esta-dentro-de-ella.md), [188](docs/decisions/ADR-188-el-alcance-que-el-motor-no-puede-escribir-para-la-puerta-antes-de-crear-la-incidencia-y-remite-a-la-sesion-interactiva.md), [182](docs/decisions/ADR-182-la-guarda-del-registro-de-defectos-deriva-de-los-adr-que-declaran-leccion.md), [179](docs/decisions/ADR-179-la-guarda-de-piezas-sin-llamante-deriva-su-inventario-del-codigo-del-motor.md), [174](docs/decisions/ADR-174-la-mina-en-dos-pasadas-la-leccion-se-declara-en-el-adr-que-la-produce-y-las-familias-se-cuentan-solas.md) |
| `lista-a-mano` | 2 | sí | [181](docs/decisions/ADR-181-la-contradiccion-de-etiquetas-se-decide-por-lo-que-proyectan-no-por-cuantas-son.md), [178](docs/decisions/ADR-178-la-autoridad-por-clase-se-deriva-de-la-via-github-que-el-despachador-declara-no-de-una-segunda-tabla-a-mano.md) |
| `medir-lo-que-se-tiene-en-vez-de-lo-que-hay` | 2 | sí | [184](docs/decisions/ADR-184-la-prohibicion-no-es-una-peticion-el-detector-de-sensibilidad-exige-que-el-marcador-no-vaya-negado.md), [180](docs/decisions/ADR-180-el-numero-del-siguiente-adr-se-calcula-contra-las-ramas-del-remoto-no-contra-las-que-el-clon-tenga-traidas.md) |
| `pieza-sin-lector` | 2 | sí | [183](docs/decisions/ADR-183-la-ausencia-de-run-de-quality-para-el-head-se-encamina-no-se-espera-en-silencio.md), [175](docs/decisions/ADR-175-un-tablero-por-incidencia-un-solo-comentario-que-el-motor-mantiene-al-dia.md) |
| `doble-mas-permisivo-que-la-herramienta-que-dobla` | 1 | sí | [193](docs/decisions/ADR-193-el-doble-de-gh-rechaza-lo-que-el-gh-real-rechaza-y-la-red-de-seguridad-vuelve-a-poder-fechar.md) |
| `espera-sin-fin-por-un-suceso-que-nadie-va-a-emitir` | 1 | sí | [194](docs/decisions/ADR-194-ci-pending-distingue-quality-todavia-no-ha-contestado-de-quality-no-va-a-contestar-nunca.md) |
| `estado-en-el-que-se-entra-y-del-que-no-se-sale` | 1 | sí | [189](docs/decisions/ADR-189-la-salida-de-una-parada-sin-incidencia-es-una-orden-del-propietario-y-reanudar-es-despachar-en-el-mismo-gesto.md) |
| `guarda-ampliada-a-un-corpus-que-no-es-el-suyo` | 1 | sí | [190](docs/decisions/ADR-190-la-guarda-de-citas-no-sale-de-docs-decisions-medidos-590-citas-y-23-rotas-fuera-del-registro-cero-son-defectos-de-este-arbol.md) |
| `guardian-que-mide-posicion-en-vez-de-estructura` | 1 | sí | [187](docs/decisions/ADR-187-una-revision-sobrevive-a-ponerse-al-dia-con-main-si-el-trabajo-propio-de-la-rama-no-cambia.md) |
| `interruptor-que-enciende-mas-de-lo-que-se-puede-medir` | 1 | sí | [185](docs/decisions/ADR-185-la-puerta-de-la-memoria-se-parte-en-tres-interruptores-antes-de-abrirla.md) |
| `pieza-correcta-a-la-que-no-llama-quien-la-necesita` | 1 | sí | [197](docs/decisions/ADR-197-el-detector-de-familia-repetida-agrupa-por-la-ruta-que-el-revisor-escribe-no-por-el-recorte-anclado.md) |
| `plan-que-hay-que-terminar-de-una-sentada` | 1 | sí | [176](docs/decisions/ADR-176-el-cierre-de-una-incidencia-se-retoma-desde-donde-se-quedo.md) |
| `prosa-que-el-cambio-deja-falsa` | 1 | no en todas | [177](docs/decisions/ADR-177-la-ampliacion-por-categoria-entra-por-una-senal-explicita-de-la-peticion-no-por-la-subcadena-contexto.md) |
| `regla-del-propietario-que-solo-vive-en-una-conversacion` | 1 | sí | [195](docs/decisions/ADR-195-podar-significa-archivar-en-este-repositorio-no-se-borra-nada.md) |
| `vista-que-copia-el-corpus-del-que-venia-huyendo` | 1 | sí | [196](docs/decisions/ADR-196-la-vista-de-memoria-lleva-el-indice-completo-de-decisiones-y-el-resumen-solo-de-las-vigentes-como-metodo.md) |

### `regla-que-depende-de-que-alguien-se-acuerde`

- **[ADR-192](docs/decisions/ADR-192-el-numero-de-un-defecto-es-el-numero-de-su-adr-no-un-contador-aparte.md)** — elegir a mano un identificador leyendo el máximo del (lo hace cumplir `tests/automation/test_registro_de_defectos.py`).
- **[ADR-191](docs/decisions/ADR-191-la-revision-es-una-cola-una-rama-entra-a-revision-solo-si-main-ya-esta-dentro-de-ella.md)** — fusionar una rama cuya combinación con `main` no ha (lo hace cumplir `tests/automation/test_cola.py`).
- **[ADR-188](docs/decisions/ADR-188-el-alcance-que-el-motor-no-puede-escribir-para-la-puerta-antes-de-crear-la-incidencia-y-remite-a-la-sesion-interactiva.md)** — despachar al ciclo automático un encargo cuyo alcance cae donde la credencial del motor no llega, hacer el trabajo entero y perderlo en el push, porque la única regla que lo evitaba vivía en la cabeza de quien despacha. (lo hace cumplir `tests/engine/test_intent_interpreter.py`).
- **[ADR-182](docs/decisions/ADR-182-la-guarda-del-registro-de-defectos-deriva-de-los-adr-que-declaran-leccion.md)** — poner a vigilar un registro con comprobaciones que solo miran la coherencia de lo ya escrito; el registro deja de recibir lo que pasa, ninguna de ellas puede notarlo y el verde lo confirma —aquí fueron doce días sin una sola entrada, con todos los ADR de ese intervalo entrando entretanto. (lo hace cumplir `tests/automation/test_registro_de_defectos.py`).
- **[ADR-179](docs/decisions/ADR-179-la-guarda-de-piezas-sin-llamante-deriva-su-inventario-del-codigo-del-motor.md)** — escribir un guardián sobre una lista de inclusión (lo hace cumplir `tests/automation/test_piezas_con_llamante.py`).
- **[ADR-174](docs/decisions/ADR-174-la-mina-en-dos-pasadas-la-leccion-se-declara-en-el-adr-que-la-produce-y-las-familias-se-cuentan-solas.md)** — escribir la regla de captura en un catálogo y dar por hecho que alguien la aplicará; los dos sitios de lecciones de este repositorio llevaban 48 ADR sin una sola entrada, con sus reglas escritas dentro. (lo hace cumplir `tests/automation/test_mina_de_lecciones.py`).

### `lista-a-mano`

- **[ADR-181](docs/decisions/ADR-181-la-contradiccion-de-etiquetas-se-decide-por-lo-que-proyectan-no-por-cuantas-son.md)** — escribir como lista de excepciones un criterio que el dato de al lado ya define —aquí «qué etiquetas pueden convivir», enumerado a mano habiendo una tabla que dice a dónde apunta cada una—, de modo que la lista solo contiene lo que alguien recordó el día que la escribió y acusa de avería a todo lo demás. (lo hace cumplir `tests/engine/test_mirror_projection.py`).
- **[ADR-178](docs/decisions/ADR-178-la-autoridad-por-clase-se-deriva-de-la-via-github-que-el-despachador-declara-no-de-una-segunda-tabla-a-mano.md)** — escribir dos veces «qué clases existen en la vía GitHub» -una tabla que decide y una copia que se queda vieja- y comprobar la copia en vez de la relación; es la familia que ADR-033 nombró, y aquí dejó quince encargos sin medir durante dos semanas. (lo hace cumplir `tests/engine/test_authority.py`).

### `medir-lo-que-se-tiene-en-vez-de-lo-que-hay`

- **[ADR-184](docs/decisions/ADR-184-la-prohibicion-no-es-una-peticion-el-detector-de-sensibilidad-exige-que-el-marcador-no-vaya-negado.md)** — poner una guarda a responder la pregunta que sabe contestar barata —«¿aparece la palabra?»— en lugar de la que tiene que contestar —«¿la orden lo pide?»—, y no notarlo porque el sustituto acierta casi siempre: aquí acertó en 1 de 3 paradas reales y paró sobre las salvaguardas que prohibían justo la operación. (lo hace cumplir `tests/engine/test_intent_interpreter.py`).
- **[ADR-180](docs/decisions/ADR-180-el-numero-del-siguiente-adr-se-calcula-contra-las-ramas-del-remoto-no-contra-las-que-el-clon-tenga-traidas.md)** — preguntarle a la copia local por un hecho que vive fuera -las ramas traídas en vez de las que existen- y creer que la respuesta cubre el caso; aquí el guion veía el 3,4% de las ramas y repartió el mismo número tres veces en un día. (lo hace cumplir `tests/automation/test_registro_de_decisiones.py`).

### `pieza-sin-lector`

- **[ADR-183](docs/decisions/ADR-183-la-ausencia-de-run-de-quality-para-el-head-se-encamina-no-se-espera-en-silencio.md)** — escribir la rama «no hay nada que hacer» de un encaminador como un `return 0` con un `echo`, de modo que la única prueba de que el ciclo se ha parado viva en un log que nadie lee. (lo hace cumplir `tests/automation/test_sirius_apply_verdict.py`).
- **[ADR-175](docs/decisions/ADR-175-un-tablero-por-incidencia-un-solo-comentario-que-el-motor-mantiene-al-dia.md)** — proyectar en cada pasada el estado entero de una incidencia -fase, rondas, Quality, PR, diagnóstico- y no enseñárselo nunca a quien tiene que decidir; es la novena vez que un dato correcto de esta casa no tiene lector, tres días después de la octava. (lo hace cumplir `tests/engine/test_tablero.py`).

### `doble-mas-permisivo-que-la-herramienta-que-dobla`

- **[ADR-193](docs/decisions/ADR-193-el-doble-de-gh-rechaza-lo-que-el-gh-real-rechaza-y-la-red-de-seguridad-vuelve-a-poder-fechar.md)** — una prueba en verde sobre una invocación que la (lo hace cumplir `tests/automation/test_sirius_reconcile.py`).

### `espera-sin-fin-por-un-suceso-que-nadie-va-a-emitir`

- **[ADR-194](docs/decisions/ADR-194-ci-pending-distingue-quality-todavia-no-ha-contestado-de-quality-no-va-a-contestar-nunca.md)** — una incidencia en un estado que solo mueve la máquina, (lo hace cumplir `tests/automation/test_sirius_reconcile.py`).

### `estado-en-el-que-se-entra-y-del-que-no-se-sale`

- **[ADR-189](docs/decisions/ADR-189-la-salida-de-una-parada-sin-incidencia-es-una-orden-del-propietario-y-reanudar-es-despachar-en-el-mismo-gesto.md)** — dar por buena una arista del dominio que en producción no llama nadie, y dejar así un estado en el que el motor entra solo y del que solo puede salir un mecanismo que necesita un dato que ese estado, por definición, no tiene. (lo hace cumplir `tests/engine/test_decision_cli.py`).

### `guarda-ampliada-a-un-corpus-que-no-es-el-suyo`

- **[ADR-190](docs/decisions/ADR-190-la-guarda-de-citas-no-sale-de-docs-decisions-medidos-590-citas-y-23-rotas-fuera-del-registro-cero-son-defectos-de-este-arbol.md)** — llevar una comprobación al sitio donde el hueco está declarado sin medir antes qué cosecharía allí, y pagar la ampliación con excepciones escritas a mano; aquí el criterio calibrado sobre `docs/decisions/` —un corpus homogéneo, donde un ADR cita este árbol— habría gritado 17 veces en falso y cazado cero defectos al salir a `docs/`, donde una investigación cita los árboles de otros repositorios. (lo hace cumplir `tests/automation/test_citas_de_los_adr.py`).

### `guardian-que-mide-posicion-en-vez-de-estructura`

- **[ADR-187](docs/decisions/ADR-187-una-revision-sobrevive-a-ponerse-al-dia-con-main-si-el-trabajo-propio-de-la-rama-no-cambia.md)** — escribir un guardián que comprueba que algo aparece (lo hace cumplir `tests/automation/test_misma_obra.py`).

### `interruptor-que-enciende-mas-de-lo-que-se-puede-medir`

- **[ADR-185](docs/decisions/ADR-185-la-puerta-de-la-memoria-se-parte-en-tres-interruptores-antes-de-abrirla.md)** — poner una sola puerta delante de varias piezas (lo hace cumplir `tests/unit/test_composition_root_relevance_gate.py`).

### `pieza-correcta-a-la-que-no-llama-quien-la-necesita`

- **[ADR-197](docs/decisions/ADR-197-el-detector-de-familia-repetida-agrupa-por-la-ruta-que-el-revisor-escribe-no-por-el-recorte-anclado.md)** — dos piezas del mismo árbol leen la misma clase de dato (lo hace cumplir `tests/engine/test_round_family_detector.py`).

### `plan-que-hay-que-terminar-de-una-sentada`

- **[ADR-176](docs/decisions/ADR-176-el-cierre-de-una-incidencia-se-retoma-desde-donde-se-quedo.md)** — escribir un plan de varios pasos contra un almacén que los aplica uno a uno, y comprobar la precondición del primero en vez del estado real en que el motor está, de modo que una interrupción a la mitad deja el trabajo atascado para siempre. (lo hace cumplir `tests/engine/test_reflect.py`).

### `prosa-que-el-cambio-deja-falsa`

- **[ADR-177](docs/decisions/ADR-177-la-ampliacion-por-categoria-entra-por-una-senal-explicita-de-la-peticion-no-por-la-subcadena-contexto.md)** — retirar un símbolo de producción y dejar vivas las frases que lo daban por cierto; al quitar `pide_contexto` quedaron falsos los once pasajes de prosa que la sección 6 de esta ficha enumera, 22 referencias del literal en las pruebas más otros cuatro pasajes de pruebas que describían el mecanismo sin nombrarlo, y el criterio de aceptación de M16 de la Arquitectura Técnica; y el barrido que las buscó en `scripts/` y `tests/` no miró en `docs/evolution/` ni podía ver lo que no escribe el literal, así que una lista solo se declara completa sobre el alcance del barrido que la produjo y el resto se dice cubierto por lectura. (sin prueba que lo haga cumplir: ninguna prueba: nada en este repositorio vigila la coherencia de la prosa de `docs/` con el árbol, y la ocurrencia que queda viva está en la Arquitectura Técnica, que la salvaguarda de #581 prohíbe tocar sin decisión del propietario.).

### `regla-del-propietario-que-solo-vive-en-una-conversacion`

- **[ADR-195](docs/decisions/ADR-195-podar-significa-archivar-en-este-repositorio-no-se-borra-nada.md)** — una regla dada de viva voz —«no se elimina nada»— que no (lo hace cumplir `tests/automation/test_registro_de_defectos.py`).

### `vista-que-copia-el-corpus-del-que-venia-huyendo`

- **[ADR-196](docs/decisions/ADR-196-la-vista-de-memoria-lleva-el-indice-completo-de-decisiones-y-el-resumen-solo-de-las-vigentes-como-metodo.md)** — una vista que existe para caber en una sola lectura (lo hace cumplir `tests/engine/test_memoria.py`).

## Los bloques del motor

Registro: `docs/implementation/bloques_del_motor.yml`. No confundir con los 16 bloques del
producto Sirius 0.1, cerrados el 10-08-2026.

| Bloque | Estado | Título |
|---|---|---|
| E0 | cerrado | El permiso escrito para construir el motor |
| A1 | cerrado | Las reglas del juego, qué es un trabajo y qué saltos están prohibidos |
| S1 | cerrado | Experimento desechable, cómo guardar en disco sin perder ni duplicar |
| A2 | cerrado | El motor ya no olvida al reiniciarse |
| A3 | cerrado | El motor ya puede mirar GitHub, sin tocar nada |
| A4 | cerrado | Qué puede y qué no puede hacer cada rol, y la barrera de salida de datos |
| E1a | cerrado | Quién manda sobre cada tipo de trabajo, contrato v1.7 |
| A5 | cerrado | Distinguir charla de orden, presupuesto con corte, escalado al propietario |
| S2 | cerrado | Probar si el investigador externo funciona y qué cuesta |
| B1 | cerrado | Que Sirius investigue de verdad desde una orden |
| E1b | cerrado | Contrato v1.8, permitir al motor activar y vigilar |
| S3 | cerrado | Medir cuándo GitHub dice que algo terminó |
| C1 | cerrado | Que el motor desatasque solo lo que se cuelga |
| C2 | cerrado | Una orden tuya y no tocas GitHub hasta «fusiona» |
| C3 | cerrado | El mismo ciclo para documentos |
| C4 | cerrado | La auditoría dentro del motor |
| D1 | pendiente | Pasar el mando de GitHub al motor, clase por clase |
| D2 | cerrado | Que el motor corra solo, siempre |
| D3 | fuera_de_alcance | Hablar con Sirius por Telegram |
| D4 | pendiente | Partir un objetivo grande en bloques |

## Los defectos registrados

Registro: `docs/audits/registro_defectos.yml`. Solo se listan los que no están
cerrados; el recuento completo está arriba.

| Defecto | Estado | Título |
|---|---|---|
| H-43 | abierto | Una rama se fusionaba sin que nadie probara su combinacion con main |
| H-197 | abierto | El detector de familia repetida agrupaba por el recorte anclado y no veia 6 familias reales de cada 14 |

## Las investigaciones: fotos con fecha, que caducan

Una investigación sirve para decidir qué preguntar, nunca para responder sobre
algo vivo (`AGENTS.md`). Cada una declara de qué depende para caducar.

| Fecha | Estado | Investigación | Caduca con |
|---|---|---|---|
| 2026-08-27 | PARCIALMENTE CADUCADA | [La medición real de NVIDIA contra Google, con las claves puestas](docs/investigaciones/2026-08-27-medicion-real-nvidia-contra-google.md) | las cuotas y límites de la capa gratuita de Google AI (si suben, Google merece la revancha; la condición está en el ADR-098); las cuotas de build.nvidia.com; el comportamiento de DuckDuckGo con las IP de los runners de GitHub; los nombres de modelo (gemini-3.5-flash, nemotron-3-nano-30b-a3b) |
| 2026-08-27 | PARCIALMENTE CADUCADA | [NVIDIA vs Google para el Investigador de Sirius](docs/investigaciones/2026-08-27-nvidia-vs-google-para-el-investigador.md) | nombres de modelo de cualquier proveedor; precios publicados; condiciones de uso de las capas gratuitas; qué modelos incluye la cuota de una cuenta concreta |
| 2026-08-28 | VIGENTE | [Examen lado a lado, Sirius contra la investigación profunda de ChatGPT](docs/investigaciones/2026-08-28-examen-lado-a-lado-sirius-contra-chatgpt.md) | la configuración del investigador (modelo, buscador, modo, idioma); la herramienta de investigación profunda de ChatGPT, que también cambia; los tres informes comparados, cada uno con su propia caducidad |
| 2026-08-28 | VIGENTE | [Investigación de la orden](docs/investigaciones/2026-08-28-orden-386-investiga-cuales-son-los-limites-actuales-de-la-capa-gratuit.md) | los datos y las fuentes que cita el informe; la fecha de esta ejecución: es UNA pasada del investigador, no un hecho estable |
| 2026-08-28 | VIGENTE | [Investigación de la orden](docs/investigaciones/2026-08-28-orden-392-investiga-y-compara-los-proveedores-de-api-de-modelos-nvidia.md) | los datos y las fuentes que cita el informe; la fecha de esta ejecución: es UNA pasada del investigador, no un hecho estable |
| 2026-08-31 | VIGENTE | [Investigación de la orden](docs/investigaciones/2026-08-31-orden-483-investiga-una-sola-pregunta-acotada-el-marco-de-agentes-herm.md) | los datos y las fuentes que cita el informe; la fecha de esta ejecución: es UNA pasada del investigador, no un hecho estable |
| 2026-09-11 | VIGENTE | [Flujos reales de agentes de código, comparados con el motor de Sirius](docs/investigaciones/2026-09-11-flujos-reales-de-agentes-comparados-con-el-motor.md) | el contenido de los trece repositorios citados, verificado el 11-09-2026 en su último commit; la documentación de Supermemory y Mem0 sobre Claude Code, Codex y ChatGPT, que cambia cada pocas semanas; los artículos, vídeos y fechas de publicación, que esta sesión no pudo abrir |
| 2026-09-11 | VIGENTE | [Qué memoria compartida para IAs existe ya hecha y probada, y si supera a la generada en el repositorio](docs/investigaciones/2026-09-11-que-memoria-compartida-para-ias-existe-ya-hecha-y-probada.md) | los precios y límites gratuitos de los servicios alojados (Mem0, Supermemory, Basic Memory Cloud, Letta Cloud, Zep); qué clientes admiten MCP y cómo (Claude Code, Codex, ChatGPT), que cambia cada pocos meses; las versiones y la actividad de cada proyecto, medidas el día de la clonación; la lista de herramientas que leen AGENTS.md |
| sin fecha declarada | — | [Investigaciones](docs/investigaciones/README.md) | — |

## Los documentos, carpeta a carpeta

La fecha es la que cada documento **declara** en su cabecera; la vista no data
nada por su cuenta. «Sin fecha declarada» es un aviso, no un dato.

### `docs/audits`

| Fecha | Documento |
|---|---|
| sin fecha declarada | [Auditoría integral de incorporación de Claude — Proyecto Sirius (julio 2026)](docs/audits/AUDITORIA_INTEGRAL_INCORPORACION_CLAUDE_2026-07.md) |
| sin fecha declarada | [Defectos encontrados en el Work Engine — parte para actuar](docs/audits/DEFECTOS_ENCONTRADOS_2026-08-20.md) |
| sin fecha declarada | [SIRIUS — Auditoría de la cadena de activación y estados (20-jul-2026, 2ª pasada)](docs/audits/SIRIUS_AUDITORIA_ACTIVACION_2026-07.md) |
| sin fecha declarada | [SIRIUS — Auditoría de robustez de la automatización de roles (Claude Code)](docs/audits/SIRIUS_AUDITORIA_AUTOMATIZACION_ROLES_2026-07.md) |
| 2026-07-20 | [SIRIUS — Auditoría integral del repositorio (julio de 2026)](docs/audits/SIRIUS_AUDITORIA_INTEGRAL_REPOSITORIO_2026-07.md) |
| sin fecha declarada | [SIRIUS — Auditoría de Model Studio (7 de agosto de 2026)](docs/audits/SIRIUS_AUDITORIA_MODEL_STUDIO_2026-08.md) |
| 2026-08-31 | [La mina: primer informe de aprendizaje sobre nuestros propios datos operativos](docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-08.md) |
| 2026-09-14 | [La mina, segunda edición: cuánta razón tiene el detector de familia repetida](docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-09-14.md) |
| 2026-08-28 | [Nota de arranque — atestar al buscador antes de gastar en medirlo](docs/audits/arranque-atestar-al-buscador.md) |
| 2026-08-28 | [Nota de arranque — B1: que una orden de investigación produzca un informe](docs/audits/arranque-b1-investigar-desde-una-orden.md) |
| 2026-08-27 | [Nota de arranque — un buscador que devuelva fuentes](docs/audits/arranque-buscador-con-fuentes.md) |
| sin fecha declarada | [Nota de arranque — `ci-pending` no distingue «todavía no» de «nunca»](docs/audits/arranque-ci-pending-no-espera-un-suceso-que-no-va-a-llegar.md) |
| 2026-08-28 | [Nota de arranque — el medidor cuenta un registro que Tavily no alimenta](docs/audits/arranque-contar-las-dos-fuentes.md) |
| 2026-08-27 | [Nota de arranque — una contradicción de etiquetas no es una divergencia](docs/audits/arranque-contradiccion-no-es-divergencia.md) |
| 2026-08-27 | [Nota de arranque — que el banco diga por qué no midió](docs/audits/arranque-el-banco-dice-por-que.md) |
| sin fecha declarada | [Nota de arranque — el detector de familia agrupa por la ruta, no por el recorte final](docs/audits/arranque-el-detector-de-familia-agrupa-por-la-ruta.md) |
| sin fecha declarada | [Nota de arranque — el doble de `gh` acepta lo que el `gh` real rechaza](docs/audits/arranque-el-doble-de-gh-rechaza-lo-que-el-real-rechaza.md) |
| sin fecha declarada | [Nota de arranque — el identificador de un defecto deja de escribirse a mano](docs/audits/arranque-el-identificador-de-defecto-no-se-escribe-a-mano.md) |
| 2026-08-28 | [Nota de arranque — ¿Está el motor preparado para recibir órdenes reales?](docs/audits/arranque-el-motor-esta-preparado.md) |
| 2026-08-28 | [Nota de arranque — H-25: el contador declara su precondición (§11.2)](docs/audits/arranque-h25-el-contador-declara-su-precondicion.md) |
| 2026-08-28 | [Nota de arranque — H-26: LOST no libera la cancelación sin confirmar](docs/audits/arranque-h26-lost-no-libera.md) |
| 2026-08-28 | [Nota de arranque — H-27: la frontera WorkItem–Run](docs/audits/arranque-h27-frontera-workitem-run.md) |
| 2026-08-28 | [Nota de arranque — H-28: la versión del perfil gobierna el prompt](docs/audits/arranque-h28-el-perfil-versionado-gobierna-el-prompt.md) |
| 2026-08-28 | [Nota de arranque — H-29: la intención durable antes del efecto externo](docs/audits/arranque-h29-intencion-antes-del-efecto.md) |
| 2026-08-28 | [Nota de arranque — H-30: comprobar y gastar en una sola operación](docs/audits/arranque-h30-presupuesto-atomico.md) |
| 2026-08-28 | [Nota de arranque — H-31: behind_by ilegible pasa a bloquear](docs/audits/arranque-h31-fail-closed.md) |
| 2026-08-28 | [Nota de arranque — H-32: STATUS.md contradice a PLAN.md](docs/audits/arranque-h32-status-contradice-a-plan.md) |
| 2026-08-28 | [Nota de arranque — implementar el descarte de ADR-098](docs/audits/arranque-implementar-el-descarte.md) |
| 2026-08-28 | [Nota de arranque — el interruptor de profundidad](docs/audits/arranque-interruptor-de-profundidad.md) |
| sin fecha declarada | [Nota de arranque — la memoria cabe en una sola lectura, y dejó de caber](docs/audits/arranque-la-memoria-cabe-en-una-sola-lectura.md) |
| sin fecha declarada | [Nota de arranque — la revisión es una cola](docs/audits/arranque-la-revision-es-una-cola.md) |
| 2026-09-13 | [Nota de arranque — Que una revisión sobreviva a ponerse al día con `main`](docs/audits/arranque-mejora-la-revision-sobrevive-a-ponerse-al-dia.md) |
| 2026-08-28 | [Nota de arranque — las tres palancas del examen](docs/audits/arranque-tres-palancas.md) |
| sin fecha declarada | [Evidencia — H-17](docs/audits/evidencia-H-17.md) |
| sin fecha declarada | [Evidencia — H-18: el recordatorio de evidencia pedía un sitio imposible](docs/audits/evidencia-H-18.md) |
| sin fecha declarada | [Evidencia — H-19](docs/audits/evidencia-H-19.md) |
| sin fecha declarada | [Evidencia — H-20, H-21 y H-22](docs/audits/evidencia-H-20-H-22.md) |
| sin fecha declarada | [Evidencia — H-23](docs/audits/evidencia-H-23.md) |
| sin fecha declarada | [Evidencia — La raíz de las cuatro rondas, y el arreglo que la hace imposible](docs/audits/evidencia-atestado-de-modelos.md) |
| 2026-08-28 | [Evidencia — atestar al buscador antes de gastar en medirlo](docs/audits/evidencia-atestar-al-buscador.md) |
| sin fecha declarada | [Evidencia — La quinta pieza sin llamante era la salida de emergencia](docs/audits/evidencia-autoridad-sin-llamante.md) |
| 2026-08-28 | [Evidencia — B1: investigar desde una orden](docs/audits/evidencia-b1-investigar-desde-una-orden.md) |
| sin fecha declarada | [Evidencia — El lazo que faltaba entre atestiguar y medir](docs/audits/evidencia-banco-atestigua-en-su-pasada.md) |
| sin fecha declarada | [Evidencia — El banco vuelve a tener botón, y ya no puede medir un cadáver](docs/audits/evidencia-banco-con-atestado.md) |
| 2026-08-27 | [Evidencia — un buscador que devuelva fuentes](docs/audits/evidencia-buscador-con-fuentes.md) |
| 2026-08-28 | [Evidencia — cerrar B1](docs/audits/evidencia-cerrar-b1.md) |
| 2026-08-28 | [Evidencia — cerrar S2](docs/audits/evidencia-cerrar-s2.md) |
| sin fecha declarada | [Evidencia — `ci-pending` no espera un suceso que no va a llegar](docs/audits/evidencia-ci-pending-no-espera-un-suceso-que-no-va-a-llegar.md) |
| sin fecha declarada | [Evidencia — siete defectos decían `abierto` con su arreglo ya fusionado](docs/audits/evidencia-cierra-los-defectos-ya-arreglados.md) |
| 2026-09-08 | [Evidencia — Propuesta de separación entre Sirius y su motor](docs/audits/evidencia-claude-sirius-motor-separation-proposal-svoy0a.md) |
| 2026-08-28 | [Evidencia — contar las dos fuentes](docs/audits/evidencia-contar-las-dos-fuentes.md) |
| sin fecha declarada | [Evidencia — D1, anotado sin exagerar](docs/audits/evidencia-d1-anotado.md) |
| 2026-08-27 | [Evidencia — que el banco diga por qué no midió](docs/audits/evidencia-el-banco-dice-por-que.md) |
| sin fecha declarada | [Evidencia — el doble de `gh` rechaza lo que el `gh` real rechaza](docs/audits/evidencia-el-doble-de-gh-rechaza-lo-que-el-real-rechaza.md) |
| sin fecha declarada | [Evidencia — el identificador de un defecto no puede seguir eligiéndose](docs/audits/evidencia-el-identificador-de-defecto-no-se-escribe-a-mano.md) |
| 2026-08-28 | [Evidencia — El motor está preparado para recibir órdenes reales](docs/audits/evidencia-el-motor-esta-preparado.md) |
| 2026-08-28 | [Evidencia — el examen lado a lado](docs/audits/evidencia-examen-lado-a-lado.md) |
| 2026-09-01 | [Evidencia — Experimento: el filtro de relevancia, fiel a la corrida del laboratorio](docs/audits/evidencia-experimento-filtro-fiel-al-laboratorio.md) |
| sin fecha declarada | [Evidencia — seis defectos decían `abierto` con su arreglo ya fusionado (14-09-2026)](docs/audits/evidencia-fix-cierra-los-defectos-de-la-noche.md) |
| 2026-08-28 | [Evidencia — H-25: el contador declara su precondición (§11.2)](docs/audits/evidencia-h25-el-contador-declara-su-precondicion.md) |
| sin fecha declarada | [Evidencia — H-26: LOST no libera la cancelación sin confirmar](docs/audits/evidencia-h26-lost-no-libera.md) |
| 2026-08-28 | [Evidencia — H-27: la frontera WorkItem–Run](docs/audits/evidencia-h27-frontera-workitem-run.md) |
| 2026-08-28 | [Evidencia — H-28: la versión del perfil gobierna el prompt](docs/audits/evidencia-h28-el-perfil-versionado-gobierna-el-prompt.md) |
| sin fecha declarada | [Evidencia — H-29: la intención durable antes del efecto externo](docs/audits/evidencia-h29-intencion-antes-del-efecto.md) |
| sin fecha declarada | [Evidencia — H-30: la admisión es una reserva atómica](docs/audits/evidencia-h30-presupuesto-atomico.md) |
| sin fecha declarada | [Evidencia — H-31: behind_by ilegible bloquea](docs/audits/evidencia-h31-fail-closed.md) |
| 2026-08-28 | [Evidencia — H-32: STATUS.md contradice a PLAN.md](docs/audits/evidencia-h32-status-contradice-a-plan.md) |
| 2026-08-28 | [Evidencia — implementar el descarte de ADR-098](docs/audits/evidencia-implementar-el-descarte.md) |
| 2026-08-28 | [Evidencia — el interruptor de profundidad](docs/audits/evidencia-interruptor-de-profundidad.md) |
| sin fecha declarada | [Evidencia — Probar seis al azar no es probar](docs/audits/evidencia-mas-candidatos.md) |
| sin fecha declarada | [Evidencia — cerrar S2: medir de verdad la calidad del investigador](docs/audits/evidencia-medir-investigador.md) |
| sin fecha declarada | [Evidencia — la revisión es una cola](docs/audits/evidencia-mejora-la-revision-es-una-cola.md) |
| 2026-09-13 | [Evidencia — Que una revisión sobreviva a ponerse al día con `main`](docs/audits/evidencia-mejora-la-revision-sobrevive-a-ponerse-al-dia.md) |
| sin fecha declarada | [Evidencia — Los cuatro que responden, encontrados probándolos](docs/audits/evidencia-modelos-que-responden.md) |
| sin fecha declarada | [Evidencia — Los modelos, sacados del servidor y no de un papel](docs/audits/evidencia-modelos-vivos.md) |
| sin fecha declarada | [Evidencia — «Ocupado» no es «muerto», y confundirlos cuesta lo mismo](docs/audits/evidencia-ocupado-no-es-muerto.md) |
| sin fecha declarada | [Evidencia — Preflight: preguntarle al servidor en vez de creerle a un informe](docs/audits/evidencia-preflight-investigador.md) |
| sin fecha declarada | [Evidencia — El preflight contesta la pregunta directa](docs/audits/evidencia-preflight-veredicto.md) |
| sin fecha declarada | [Evidencia — El catálogo tampoco basta](docs/audits/evidencia-probar-catalogo.md) |
| sin fecha declarada | [Evidencia — Existir no es poder usarse](docs/audits/evidencia-prueba-de-vida.md) |
| 2026-08-28 | [Evidencia — registro-cierre-h25: el apunte contable de H-25](docs/audits/evidencia-registro-cierre-h25.md) |
| 2026-08-28 | [Evidencia — registro-cierre-h32: el apunte contable final de la fase de corrección](docs/audits/evidencia-registro-cierre-h32.md) |
| 2026-08-28 | [Evidencia — las tres palancas](docs/audits/evidencia-tres-palancas.md) |
| sin fecha declarada | [Evidencia — verificar la auditoría externa (puntero)](docs/audits/evidencia-verificar-auditoria-externa.md) |
| sin fecha declarada | [Verificación de la auditoría externa del 28-08-2026](docs/audits/verificacion-auditoria-externa-20260828.md) |

### `docs/canonical`

| Fecha | Documento |
|---|---|
| sin fecha declarada | [Estado canónico](docs/canonical/STATUS.md) |

### `docs/evolution`

| Fecha | Documento |
|---|---|
| sin fecha declarada | [Artefactos aprobados - Evolución post-0.1 de Sirius](docs/evolution/ARTIFACTS.md) |
| sin fecha declarada | [Auditoría cerrada - Plan de evolución de Sirius después de 0.1](docs/evolution/AUDIT.md) |
| sin fecha declarada | [Decisiones canónicas - Evolución post-0.1 de Sirius](docs/evolution/DECISIONS.md) |
| sin fecha declarada | [Propuesta de separación entre Sirius y su motor de trabajo](docs/evolution/PROPUESTA_SEPARACION_SIRIUS_MOTOR.md) |
| sin fecha declarada | [Evolución de Sirius después de 0.1](docs/evolution/README.md) |
| sin fecha declarada | [Documento Rector - Evolución de Sirius después de 0.1](docs/evolution/RECTOR.md) |
| sin fecha declarada | [Sirius AI Core y estrategia de modelos — recolección de ideas](docs/evolution/SIRIUS_AI_CORE_AND_MODEL_STRATEGY.md) |
| sin fecha declarada | [Arquitectura Técnica — Sirius 0.2 «Memoria útil»](docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md) |
| sin fecha declarada | [Plan de Pruebas de Aceptación — Sirius 0.2 «Memoria útil»](docs/evolution/SIRIUS_PLAN_PRUEBAS_0.2_v0.1_PROPUESTO.md) |
| sin fecha declarada | [Definición de Producto — Sirius 0.2 «Memoria útil»](docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md) |
| sin fecha declarada | [Estado - Evolución post-0.1 de Sirius](docs/evolution/STATUS.md) |

### `docs/evolution/history`

| Fecha | Documento |
|---|---|
| sin fecha declarada | [Sirius — Tarjeta de referencia](docs/evolution/history/PROPUESTA_ALCANCE_POST_0_1_v2.md) |

### `docs/implementation`

| Fecha | Documento |
|---|---|
| sin fecha declarada | [Agentes de Sirius — desde dónde se invocan](docs/implementation/AGENTES_SUPERFICIE_DE_INVOCACION.md) |
| sin fecha declarada | [SIRIUS — Matriz de oportunidades de agentes (Fase 0)](docs/implementation/AGENT_OPPORTUNITY_MATRIX.md) |
| sin fecha declarada | [AUDITOR AGENT v0 — Especificación reproducible del agente](docs/implementation/AUDITOR_AGENT_V0.md) |
| sin fecha declarada | [SIRIUS - Plan del flujo general de automatización](docs/implementation/AUTOMATION_FLOW_PLAN_SIRIUS_0.1.md) |
| sin fecha declarada | [SIRIUS - Contrato operativo de automatización](docs/implementation/AUTOMATION_OPERATING_CONTRACT.md) |
| sin fecha declarada | [SIRIUS — Evidencia de prueba de humo de automatización](docs/implementation/AUTOMATION_SMOKE_EVIDENCE_20260719.md) |
| sin fecha declarada | [SIRIUS - Máquina de estados del flujo automático](docs/implementation/AUTOMATION_STATE_MACHINE_SIRIUS_0.1.md) |
| sin fecha declarada | [B13 — Empaquetado reproducible de Sirius 0.1 para Windows 11 x64](docs/implementation/B13_PACKAGING.md) |
| sin fecha declarada | [B14 — Windows sin clave](docs/implementation/B14_WINDOWS_SIN_CLAVE.md) |
| sin fecha declarada | [B4 — Plan de ejecución operativo](docs/implementation/B4_EXECUTION.md) |
| sin fecha declarada | [Banco de evaluación de agentes — diseño v0](docs/implementation/BANCO_DE_EVALUACION_DISENO.md) |
| sin fecha declarada | [Bloque B — ¿Sirven las suscripciones para un runner multimodelo, o hacen falta claves de API?](docs/implementation/BLOQUE_B_SUSCRIPCIONES_O_CLAVES.md) |
| sin fecha declarada | [Cloud Smoke Test Evidence — 2026-07-18](docs/implementation/CLOUD_SMOKE_EVIDENCE_20260718.md) |
| sin fecha declarada | [Prueba de humo de Claude Code cloud](docs/implementation/CLOUD_SMOKE_TEST.md) |
| sin fecha declarada | [Dónde estamos](docs/implementation/DONDE_ESTAMOS_2026-08-21.md) |
| sin fecha declarada | [Método de interrogatorio](docs/implementation/METODO_INTERROGATORIO.md) |
| sin fecha declarada | [Plan de implementación por verticales](docs/implementation/PLAN.md) |
| sin fecha declarada | [SIRIUS 0.2 — Paquete operativo de spikes de ADR-001](docs/implementation/SIRIUS_0.2_ADR001_PAQUETE_OPERATIVO_SPIKES_v1.0.md) |
| sin fecha declarada | [SIRIUS — Routines genéricas de automatización 0.1](docs/implementation/SIRIUS_GENERIC_ROUTINES_0.1.md) |
| 2026-08-15 | [Sirius Work Engine — Arquitectura mínima implementable](docs/implementation/SIRIUS_WORK_ENGINE_ARQUITECTURA_MINIMA.md) |
| 2026-08-15 | [Sirius Work Engine — Inventario y reconciliación del estado real](docs/implementation/SIRIUS_WORK_ENGINE_INVENTARIO.md) |
| 2026-08-15 | [Sirius Work Engine — Plan mínimo de implementación](docs/implementation/SIRIUS_WORK_ENGINE_PLAN_IMPLEMENTACION.md) |
| sin fecha declarada | [Trazabilidad de las pruebas de aceptación, personalidad y seguridad](docs/implementation/TRAZABILIDAD_PA_SP.md) |
| sin fecha declarada | [V8 — Ejecución, puertas y evidencia](docs/implementation/V8_EXECUTION.md) |
| sin fecha declarada | [SIRIUS — Auditoría de procesos de trabajo (Fase 0)](docs/implementation/WORK_PROCESS_AUDIT.md) |

### `docs/implementation/model_studio`

| Fecha | Documento |
|---|---|
| sin fecha declarada | [SIRIUS · MODEL STUDIO · MÓDULO CAPTURA](docs/implementation/model_studio/SIRIUS_MODEL_STUDIO_CAPTURA_INVESTIGACION.md) |
| sin fecha declarada | [SIRIUS · MODEL STUDIO · MÓDULO CAPTURA](docs/implementation/model_studio/SIRIUS_MODEL_STUDIO_PRIMERA_PRUEBA_CAPTURA.md) |
| sin fecha declarada | [SIRIUS · MODEL STUDIO](docs/implementation/model_studio/SIRIUS_MODEL_STUDIO_RECONCILIACION_v1.0_PROPUESTA.md) |
| sin fecha declarada | [SIRIUS · MODEL STUDIO](docs/implementation/model_studio/SIRIUS_MODEL_STUDIO_UI_001_INTERFAZ_v1.0_APROBADA.md) |

### `docs/operations`

| Fecha | Documento |
|---|---|
| sin fecha declarada | [Incorporación de Claude al Proyecto Sirius](docs/operations/CLAUDE_PROJECT_ONBOARDING.md) |
| sin fecha declarada | [Base de conocimiento de Claude sobre el Proyecto Sirius](docs/operations/CLAUDE_SIRIUS_KNOWLEDGE_BASE.md) |
| sin fecha declarada | [Cómo se usa el motor de Sirius](docs/operations/MOTOR_DE_SIRIUS.md) |

### `docs/robotics/head`

| Fecha | Documento |
|---|---|
| sin fecha declarada | [Artefactos aprobados - Sirius HEAD-R1](docs/robotics/head/ARTIFACTS.md) |
| sin fecha declarada | [Auditoría y cierre documental - Sirius HEAD-R1](docs/robotics/head/AUDIT.md) |
| sin fecha declarada | [Decisiones canónicas - Sirius HEAD-R1](docs/robotics/head/DECISIONS.md) |
| sin fecha declarada | [Sirius HEAD-R1](docs/robotics/head/README.md) |
| sin fecha declarada | [Documento Rector — Cabeza Robótica Sirius HEAD-R1](docs/robotics/head/RECTOR.md) |
| sin fecha declarada | [Estado - Sirius HEAD-R1](docs/robotics/head/STATUS.md) |

### `(raíz)`

| Fecha | Documento |
|---|---|
| sin fecha declarada | [Instrucciones para agentes de programación](AGENTS.md) |
| sin fecha declarada | [Registro de cambios](CHANGELOG.md) |
| sin fecha declarada | [Claude Code](CLAUDE.md) |
| sin fecha declarada | [Forma de trabajo](CONTRIBUTING.md) |
| sin fecha declarada | [Sirius 0.1](README.md) |
| sin fecha declarada | [Estado actual del repositorio](REPOSITORY_STATUS.md) |
