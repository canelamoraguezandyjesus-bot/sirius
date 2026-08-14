# ADR-015 — Toda escritura de etiqueta pasa por una envoltura con el PAT, y la prueba busca lo malo en vez de lo bueno

- Estado: PROPUESTO
- Fecha: 2026-08-14
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario
- Numeración: comprobada contra **todas** las ramas remotas antes de asignar,
  no solo contra `main`. En la PR #153 se crearon dos `ADR-008` por no hacerlo.
- Extiende, no sustituye, a [ADR-014](ADR-014-la-identidad-que-escribe-una-etiqueta-decide-si-avisa.md).

## Contexto y problema

ADR-014 decidió que las etiquetas notificables se escriben con el PAT. **La
implementación quedó incompleta y nadie lo notó**, porque la prueba que debía
protegerla no podía verlo.

Al refutar los hallazgos de AUDITOR-V0-RUN-001 (#154), un verificador
independiente encontró que `sirius:failed-safely` seguía escribiéndose con el
`GITHUB_TOKEN` en tres sitios:

| Fichero | Qué parada |
|---|---|
| `advance-sirius-after-quality.yml:134` | ambigüedad: varias incidencias candidatas |
| `advance-sirius-after-quality.yml:186` | Quality termina en un estado que no es éxito ni fallo |
| `review-sirius-work.yml:107` | parada segura del gate de revisión |

De los seis estados notificables, es el peor que se puede perder: `failed-safely`
existe precisamente para decir que la automatización se ha parado y necesita a
una persona. La propia auditoría había medido el coste de no enterarse — **14 h
50 m** para rescatar un `failed-safely` falso.

Los comentarios del workflow enunciaban el defecto sin verlo: «el resto del paso
(lecturas y **paradas seguras**) sigue con el GITHUB_TOKEN».

### La raíz, que es lo que hace falta decidir

`tests/automation/test_sirius_notifications.py` ha fallado **dos veces por la
misma causa**:

1. Comprobaba que el PAT aparecía en algún sitio **del fichero**. Se satisfacía
   con cualquier otra aparición —el `checkout`, la acción de Claude—.
2. Se estrechó a algún sitio **del paso**. Un paso con cuatro llamadas seguía
   pasando si UNA usaba el PAT. Por ahí se coló este defecto.

Dos rondas, misma familia. Por la regla de las dos rondas (ADR-001) no toca
estrechar el ámbito una tercera vez: toca ver la raíz.

**La raíz no es el ámbito.** Es que preguntar *«¿está presente lo bueno?»* se
satisface con una sola aparición y no dice nada de las demás. Es una pregunta
existencial usada para defender una propiedad universal. Ningún ámbito arregla
eso: en cuanto un ámbito contiene dos llamadas, vuelve el agujero.

## Criterio de parada (escrito ANTES de decidir)

Si formular la comprobación correcta exige decidir, desde el **texto** de un
guion de shell, si una llamada está dentro de una subshell que exportó el PAT,
se para y se cambia el código en vez de la prueba. Esa deducción exige un
intérprete de shell, y es exactamente la puerta del push de ADR-001: quince
defectos, ninguno repetido, hasta entender que **un texto de shell no dice qué
va a ejecutar sin un shell que lo interprete**.

**Se disparó.** La comprobación por llamada, con las subshells multilínea que
había, era indecidible sin parsear. De ahí la convención de la decisión.

## Decisión

**Uno. La pregunta se invierte.** La prueba ya no busca que el PAT esté
presente; busca que no haya ninguna escritura sin él. Absence-of-bad en vez de
presence-of-good.

**Dos. Una convención hace la respuesta textual.** Ninguna función cruda de
escritura de etiquetas se invoca directamente en un workflow: solo desde una
envoltura de **una línea** que exporta el PAT. Con eso, la comprobación no
necesita saber qué es una subshell — le basta con que todo nombre crudo aparezca
en una línea que también exporte el PAT.

Es cambiar el código para que la propiedad sea barata de comprobar, en vez de
construir un analizador para un código que no lo era.

**Tres. La regla es ancha: TODA escritura de etiqueta usa la identidad real**,
sea notificable o no. Por eso `sirius:reviewing` también pasa por envoltura
aunque hoy no notifique. La regla estrecha obliga a decidir en cada llamada si
la etiqueta que escribe es notificable; equivocarse ahí cuesta un aviso perdido,
y pasarse cuesta un evento que nadie consume. Ya lo defendía el comentario de la
versión anterior de la prueba; ahora es la regla y no una nota al pie.

**Cuatro. La prueba barre todos los workflows** con `glob`, sin lista fija. La
lista fija era el otro agujero: `review-sirius-work.yml` escribía
`sirius:failed-safely` y no estaba en ella, así que nadie lo miraba.

**Cinco. Se añade un guardián de la guardiana.** Si el barrido dejara de
encontrar llamadas —por un cambio de nombres, un `glob` que no encuentra nada, un
YAML que deja de parsear— la prueba principal pasaría trivialmente y afirmaría
que todo va bien. Una prueba que no puede fallar es peor que ninguna.

## Comprobación que la sostiene

Verificado por mutación, en las dos direcciones:

| Mutación | Resultado |
|---|---|
| `advance-*.yml` a su versión anterior | **falla**, y nombra los dos sitios |
| `review-*.yml` a su versión anterior | **falla** |
| Todos los workflows a `cdd103d` (el defecto original de ADR-014) | **falla** — no hay regresión |
| Sin mutar | 3 passed |

377 pruebas de `tests/automation/` en verde. Ruff format, lint y mypy correctos.
Los 13 workflows siguen parseando como YAML.

## Consecuencias

**Lo que esto NO garantiza.** Que la notificación llegue. La prueba comprueba la
**precondición** —qué token escribe— no la **consecuencia**. Que GitHub suprima
los eventos del `GITHUB_TOKEN` es comportamiento documentado de la plataforma,
externo, y ninguna prueba de este repositorio puede exhibirlo. Confirmarlo exige
un `failed-safely` real en GitHub, y sigue dependiendo de la máquina del
propietario.

**La convención tiene coste, y ya se cobró uno.** `test_sirius_reconcile.py`
fijaba el **nombre** de la función en su expresión regular y se rompió al
aparecer la envoltura, sin que hubiera cambiado nada de lo que esa prueba
comprueba. Se corrigió anclando en la **firma** de la llamada en vez del nombre,
y se verificó por mutación que sigue detectando lo suyo. Es la advertencia de que
una convención de nombres crea acoplamientos donde antes no los había.

**El PAT se usa en dos sitios más** (el gate de revisión y el consumo de
revisión). No amplía ningún permiso: es el mismo secreto ya configurado, en dos
pasos más, y siempre acotado a la subshell de la escritura — las lecturas siguen
con el `GITHUB_TOKEN`.

**Queda un límite conocido.** Si un paso corre entero con el PAT
(`env.GH_TOKEN` es el secreto), la prueba admite llamadas crudas dentro. Es
correcto —todo el paso escribe con la identidad real— pero significa que la
convención no es uniforme: hay dos formas legítimas, no una.

## Alternativas descartadas y por qué

- **Estrechar el ámbito a la llamada, dejando el código como estaba.** Es el
  tercer parche de la misma familia, y exige decidir si una llamada está dentro
  de una subshell con el PAT: el intérprete de shell que ADR-001 prohíbe.
- **Regla estrecha, solo etiquetas notificables.** Obliga a leer los argumentos
  de cada llamada para saber qué etiqueta escribe. Más fiel y más frágil, y el
  error se paga en avisos perdidos.
- **Que cada workflow publique su propio comentario de notificación.** Ya se
  descartó en ADR-014 (opción B): duplica el mecanismo de avisos y deja dos
  sitios que se desincronizan.
