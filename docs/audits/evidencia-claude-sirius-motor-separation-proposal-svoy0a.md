# Evidencia — Propuesta de separación entre Sirius y su motor

Fecha: 2026-09-08. Rama `claude/sirius-motor-separation-proposal-svoy0a`.
Entregable: `docs/evolution/PROPUESTA_SEPARACION_SIRIUS_MOTOR.md`.
Árbol comprobado: `main` en `f2085db`.

**Este fichero es solo el método.** No añade ni una afirmación nueva sobre la
propuesta: registra cómo se comprobó lo que la propuesta dice. El encargo pedía
«un único documento» y ese sigue siendo el entregable; la evidencia va aparte
porque ADR-001 y `CLAUDE.md` la exigen, y porque este es el sitio donde el
repositorio la busca.

## 0. Dónde se publicó la nota de arranque, y dónde no

La nota se escribió y se enseñó al propietario **antes de leer el fondo de la
documentación**: primero en la respuesta de la sesión, y a la vez en un fichero
de trabajo fuera del árbol. Después se incorporó al entregable como su apartado
0.1, y ese apartado sí entró en el primer commit.

Lo que **no** se hizo a tiempo es este fichero, en el sitio convencional del
repositorio (`docs/audits/`). Se escribe después del primer commit, avisado por
el gancho de parada. No se disfraza de nota previa: la nota es previa, su
publicación aquí no lo es.

## 1. Nota de arranque (transcrita del fichero escrito antes de leer)

**1. ¿Dónde vive el fallo y dónde voy a poner el arreglo?**
No hay un fallo de software. Lo que hay es una DESALINEACIÓN entre lo que la
documentación aprobada dice que es Sirius y lo que el propietario acaba de
expresar como visión. El «arreglo» es un documento nuevo que NO modifica los
documentos desalineados: los señala. ¿Puede el sitio del arreglo observar el
fallo? Sí: un documento nuevo puede citar apartado por apartado los documentos
que contradicen la visión, sin tocarlos. Lo que NO puede hacer un documento es
comprobar que la desalineación se resuelve: eso lo decide el propietario.

**2. ¿Qué NO va a garantizar esto?**
No garantiza que el reparto propuesto sea el que el propietario quiere. No
garantiza inventario exhaustivo de dependencias de código: reviso las fronteras
relevantes (imports entre paquetes), no todo el árbol. No garantiza que las
enmiendas propuestas sean suficientes: son las que encuentro leyendo, y
declararé qué NO leí. No decide herramienta de memoria común, ni numeración de
versión, ni retirada de ningún componente. No verifica comportamiento en
ejecución: no ejecuto el motor ni la suite.

**3. Criterio de parada (decidido antes de ver resultados).**
Me detengo y lo declaro como pregunta abierta al propietario, en vez de
resolverlo yo, cuando: (a) dos documentos vigentes se contradicen sobre el
estado de algo y el historial no lo desempata; (b) la visión expresada choca con
una decisión ya APROBADA (no propuesta); (c) hace falta elegir herramienta,
repositorio, versión o arquitectura; (d) un componente parece candidato a
retirada pero también sostiene una función que el propietario quiere conservar
(revisión/comprobaciones); (e) no encuentro respaldo documental de una
afirmación: escribo «no lo he encontrado», no la afirmo.

**4. ¿Qué lo haría imposible en vez de improbable?**
El error más probable aquí es confundir «PROPUESTO» en la cabecera con el estado
real de aprobación (aviso explícito de AGENTS.md y del propio encargo). Lo haría
IMPOSIBLE una tabla, dentro del entregable, que para CADA documento citado
registre: cabecera literal + dónde consta su estado real (registro, ADR o
historial) + veredicto. No basta con «tener cuidado». Eso hago: el apartado 8 del
entregable lleva esa tabla y ninguna afirmación de estado va sin fila. Lo que NO
puedo hacer imposible: que un ADR aprobado haya sido superado por otro posterior
que no cite al primero. Mitigación: cruzar por tema, no por número, y declarar el
residuo.

**Producto de decisión.** Este trabajo NO produce ADR: no toma decisiones, las
propone. Lo declaro explícitamente en el entregable.

## 2. Las cuatro preguntas, contestadas con lo que pasó

**1. ¿Pudo el documento nuevo observar la desalineación sin tocar nada?** Sí, y
se comprueba solo: el apartado 4.1 del entregable cita once apartados concretos
con su línea, y `git status` de la rama enseña **un único fichero nuevo** antes
de este —cero modificaciones de documentos aprobados, código, workflows o
permisos—.

**2. ¿Se respetó lo que se declaró que no se garantizaba?** Sí, y el sitio donde
se comprueba es el apartado 5.5 del entregable: nueve cuestiones declaradas como
no verificadas, entre ellas que no se ejecutó el motor, ni un run, ni la suite, y
que el clon de esta sesión es superficial (50 commits), por lo que ninguna
aprobación por fusión se afirma desde el historial.

**3. ¿Se disparó el criterio de parada?** **Sí, en tres de sus cinco ramas**, y
en las tres se paró en vez de resolver:

| Rama | Dónde se disparó | Qué se hizo |
|---|---|---|
| (b) choque con decisión APROBADA | EV-002 y EV-004 frente a la visión | No se enmendó nada: quedó como decisiones D-A y D-D del apartado 7 |
| (c) elegir herramienta | La memoria común | No se comparó ninguna herramienta: se escribieron R1-R14 y las cinco preguntas de 6.4 |
| (d) candidato a retirada que sostiene algo que se conserva | El perfil `investigador` y la puerta del implementador | Se nombró la costura en 2.3 en vez de proponer borrarla |

La rama (a) —dos documentos vigentes que se contradicen— apareció dos veces
(`README.md` contra `docs/canonical/STATUS.md`; `docs/robotics/head/STATUS.md`
contra lo mismo) y **no** obligó a parar: el historial sí desempata, porque uno de
los dos declara la fecha y la fuente. Quedan registradas como enmiendas, no como
preguntas.

**4. ¿La tabla del apartado 8 hizo imposible el error de la cabecera?** Sí en lo
que podía: cada afirmación de estado del entregable tiene fila. Lo que no cubre
sigue declarado (5.5, punto 9): el cruce fue por tema, no por los 151 ficheros de
ADR uno a uno.

## 3. Afirmación → comprobación

Cada comprobación es un comando repetible sobre `f2085db`.

| Afirmación del entregable | Comprobación | Resultado |
|---|---|---|
| `sirius` y `sirius_engine` no se importan en ninguna dirección | `grep` de imports en ambos árboles | Cero resultados en las dos direcciones |
| Y hay una guarda que lo impide | Lectura de `tests/engine/test_boundary.py` | Dos pruebas, una por dirección |
| El motor no necesita las dependencias del producto | `grep` de todos los `import`/`from` de `src/sirius_engine/` | Solo stdlib + `platformdirs` + `yaml` |
| La automatización lee el árbol del motor por ruta | Lectura de `resolver_prompt.py`, `sirius_convergence.py`, `sirius_drip_guard_cli.py` | Cuatro rutas literales a `src/sirius_engine/` |
| Nueve workflows invocan al motor | `grep -rln` de `sirius_engine` y de los cinco comandos sobre `.github/workflows/` | Nueve ficheros |
| Revisores y comprobaciones no comparten lógica con auditor ni investigador | `grep` de `auditor\|auditoria` e `investigador` sobre los cinco workflows del ciclo | Solo comentarios, salvo **una** puerta real en el implementador: se corrigió la afirmación (ver §4) |
| El perfil `investigador` no tiene YAML de perfil | `ls docs/implementation/work_engine/perfiles/` | Siete ficheros, ninguno `investigador` |
| No existe nada de «memoria común» | `grep -rln` de Obsidian / Basic Memory / memoria compartida / memoria común sobre `docs/`, `src/`, `scripts/` | Cero resultados |
| Model Studio no aparece en ningún documento de estado | `grep -rin "studio"` sobre los seis documentos citados | Cero resultados |
| El producto no tiene herramientas ni web | Lectura de la cabecera de `src/sirius/adapters/llm/openai_responses.py` | Lo declara literalmente |
| La rama `estado-del-motor` existe | `git ls-remote --heads origin` | Presente (390 ramas en total) |
| Huecos de numeración de ADR | Cálculo sobre los nombres de `docs/decisions/` | Faltan 17, 18, 49, 107, 108, 147, 148; 151 ficheros y 150 números (dos `ADR-016`) |
| M17 no está cerrado | `grep -rn "M17" docs/decisions/*.md` | 9 apariciones, ninguna lo declara cumplido |
| `docs/evolution/STATUS.md` lleva sin tocarse desde el 31-08 | `git log -1 -- docs/evolution/STATUS.md` | 2026-08-31 |
| Las 43 citas `ruta:linea` del entregable resuelven | Guion de comprobación (§5) | 43 en rango, cero defectos |
| El documento pasa el comprobador del repositorio | `python3 scripts/automation/sirius_check_docs.py <entregable>` | «Sin defectos documentales», código 0 |
| Las guardas documentales siguen verdes | `uv run --frozen pytest tests/unit/test_documentation_single_source.py tests/automation/test_sirius_check_docs.py -q` | 40 pruebas en verde, 0,64 s |

## 4. Lo que la comprobación encontró mal, en mi propio texto

Se registra porque una tabla de comprobaciones que solo confirma no ha
comprobado nada.

| Defecto | Cómo se cazó | Corrección |
|---|---|---|
| Cita al §11.1 del contrato en una línea vacía (634) | Abrir el fichero en la línea citada | Es la 637 |
| Cita a `dispatch_cli.py` línea 70 para la fila `AUDITORIA` | Ídem | Es la 69 (la 70 es `DOCUMENTACION`) |
| Cita a `pyproject.toml` línea 6 para la versión | Ídem | La 6 es `requires-python`; la versión es la 3 |
| «los revisores no comparten **ni un fichero** con el auditor ni el investigador» | `grep` de `investigador` sobre los workflows del ciclo | **Falso**: el implementador tiene una puerta real que cede el perfil. Reescrito a «no comparten lógica», con la costura nombrada y su línea |
| Una cita sin ruta (`review-sirius-work.yml:284`) que el guion no resolvía | El guion del §5 | Cualificada con su ruta completa |
| «las siete cuestiones no verificadas» tras añadir dos | Relectura | Nueve |

Familia dominante: **citar de memoria una fuente que está en el mismo árbol** —
la misma que `AGENTES_SUPERFICIE_DE_INVOCACION.md` §8 ya registró dos veces—.
Tres defectos de esa familia en la misma pasada dispararían la regla de las dos
rondas si hubiera revisión externa; aquí se aplicó su consecuencia directamente:
en vez de parchear cita a cita, se escribió el guion del §5 y se pasó sobre
**todas** las citas del documento, no sobre las sospechosas.

## 5. Prueba por mutación

La propiedad que se quiere fijar es «ninguna cita `ruta:linea` del entregable
apunta fuera de rango». El guion que la comprueba
(`verificar_citas.py`, escrito para este trabajo y **no** incorporado al árbol:
es utillaje de una pasada, no una guarda del repositorio) se verificó en las dos
direcciones:

- **Sobre el documento real:** 43 citas en rango, código de salida **0**.
- **Con la mutación** —sustituir en una copia la cita a la línea 146 del Rector
  por una línea 9999 inexistente—: dos defectos reportados con el motivo
  («el fichero tiene 294 líneas»), código de salida **1**.

Se vio fallar antes de fiarse de su verde. Lo que esta prueba **no** cubre, y se
dice: que la línea citada diga lo que el texto afirma. Eso no lo puede
comprobar un guion, así que se hizo a mano: 24 de las citas de carga argumental
se volcaron de una pasada, línea a línea, contrastando cada una con la frase que
la usa, y el resto se comprobaron abriendo el fichero al escribirlas. Las que no
llevan línea son referencias de localización, y solo se comprobó que existen.

## 6. Producto de decisión

**Ninguno.** Este trabajo no toma decisiones: las propone y las deja
enumeradas como D-A a D-I en el apartado 7 del entregable, para el propietario.
Por eso no hay ADR, y ADR-001 pide decirlo explícitamente en vez de callarlo.

Si el propietario decide sobre cualquiera de las nueve, **esa** decisión sí
necesita su ADR, y no es este documento quien lo escribe.
