## Work ID

`WI-20260920-MODO-Y-CORTE`

## Bloque

B04 — Búsqueda y recuperación. Palanca 1 de ADR-148 (ADR-164). Continuación de `WI-20260920-CARDINALIDAD` (#653), sobre el mismo fichero y el mismo defecto de fondo.

Perfil: implementer@4

## Objetivo

Alinear con **B04 §5** los bloques `modo` y `corte_de_registro` de la instrucción del intérprete, por la misma razón que #653 alineó `cardinalidad`: **la instrucción parafrasea el canon de memoria y cada paráfrasis pierde el matiz que el banco puntúa**.

Medido con Ollama real, 20-09-2026: `modo 40/47`, `corte_de_registro 42/47`.

## Base y dependencias

- Rama base: `main`, con **#653 ya fusionado**. Si #653 no está en `main`, **parar**: los dos encargos tocan la misma constante y hay que evitar el conflicto.
- **B04 §5**, «Modos de recuperación y elegibilidad» (`SIRIUS_0.2_BLOQUE_04_BUSQUEDA_Y_RECUPERACION_v1.0_APROBADO.docx`, en `docs/architecture/canonical_sources/` de la rama `evidence/adr001-spikes`), literal:

  | modo | canon | qué dice hoy nuestra instrucción | qué pierde |
  |---|---|---|---|
  | `M1` | «Responder o continuar trabajo **en el tiempo objetivo solicitado**»; «"Ahora" es el valor por defecto» | «responder **ahora** con lo que está vigente» | convierte el valor por defecto en la definición |
  | `M2` | «Consultar qué era válido, qué se decidió o qué se sabía antes»; «**separa tiempo válido de corte de registro**» | «revisar el historial… lo ya sustituido o archivado» | la separación de los dos tiempos |
  | `M3` | «Comprobar origen, **literalidad, matiz** o contradicción» | «verificar de dónde viene algo, quién lo dijo o en qué se apoya» | **literalidad** y **matiz** |
  | `M4` | «Inspeccionar candidatas, rechazadas, suprimidas, restringidas o sin soporte» | «administrar la propia memoria» | los estados concretos |
  | `M5` | «Examinar **afirmaciones incompatibles y soportes**» | «contradicción entre **dos cosas recordadas**» | el conflicto documento-contra-memoria |

- **Definición del corte**, del mismo documento: «Fecha hasta la que se considera lo que Sirius había registrado; permite "qué sabía Sirius el día T"».
- Evidencia: `docs/audits/hallazgo-los-otros-campos-tambien-reducen-el-canon.md`, en la rama `claude/adr002-tol209-forensic-audit-i0ui8k`.

**Los tres casos que lo demuestran**, del fallo medido:

- `B04-CA-18` «¿Qué **dice** el anexo técnico requerido?» → canon `M3`, el modelo dijo `M1`. Es **literalidad**, palabra que nuestra instrucción no usa.
- `B04-CA-28` «¿Qué se **dijo** en la sesión no guardada?» → canon `M3`, el modelo dijo `M2`. Lo mismo.
- `B04-CA-27` «¿Qué presupuesto aplico en Beta **según el documento**?» → canon `M5`, el modelo dijo `M1`. Es documento-contra-memoria, que «dos cosas recordadas» excluye.

**Y el del corte**: `B04-CA-32` «¿Qué sabía Sirius sobre el aforo el 1 de marzo?» espera `2026-03-01T00:00:00` y el modelo devuelve `...T23:59:59.999999`. **No es semántica: es que la instrucción nunca dice si «el día T» es el principio o el final del día.**

## Alcance permitido

1. **`src/sirius/adapters/ollama_query_intent_classifier.py`**: los bloques `modo` y `corte_de_registro` de `_INSTRUCCION`, y **solo ésos**. Los cinco modos enuncian la finalidad del canon sin reducirla; el corte enuncia además **la convención horaria** que el banco usa.
2. **Las pruebas de ese adaptador**: una prueba que fije los cinco criterios de modo y la convención del corte, para que no vuelvan a derivar en silencio.
3. **El ADR**, con `scripts/siguiente_adr.py`.

## Fuera de alcance

- **El bloque `cardinalidad`**: es de #653 y ya está hecho. No se toca.
- **El bloque `limite`** y el bloque `tiempo_objetivo`. El segundo tiene una traducción **registrada en ADR-111** (intervalo → extremo final) y un caso sin explicar (`CA-22` espera `2026-03-20`, que no es el extremo final): **cambiarlo sin entender ese caso es sustituir una decisión registrada por una corazonada.**
- **`src/sirius/adapters/ollama_relevance_filter.py`.** Su instrucción tiene el mismo defecto de tiempo, pero está **portada literal** del laboratorio que midió 29/47 (M18a), y tocarla rompe esa procedencia, que es la referencia de todo el proyecto. **Es decisión del propietario, no de un encargo.**
- El corpus, `resultado_esperado`, adjudicaciones, `memory_gates.py`, `settings.json`, `STATUS.md`, `.github/**`, `docs/canonical/**`.
- **No se abre ningún interruptor.**

## Requisitos y pruebas de aceptación

1. Los cinco modos enuncian la finalidad de §5 sin reducirla. En particular: `M3` dice **literalidad** y **matiz**; `M5` habla de **afirmaciones incompatibles y sus soportes**, no solo de dos recuerdos; `M1` dice **el tiempo objetivo solicitado** y que «ahora» es solo el valor por defecto; `M2` **separa el tiempo válido del corte de registro**.
2. El bloque `corte_de_registro` enuncia **la convención horaria**: «el día T» se traduce al **instante inicial** de ese día.
3. Un comentario junto a la constante cita documento y sección de cada definición.
4. **Una prueba vista fallar antes del cambio** (ADR-001) que fije esos criterios. Primera línea del fallo, transcrita en el ADR.
5. **Una mutación vista fallar**: devolver los bloques a su redacción de hoy hace fallar esa prueba. Transcrita.
6. Las pruebas deterministas existentes siguen verdes, **ninguna cambia de intención**.
7. El ADR recoge la predicción de abajo tal cual.

**La predicción, publicada aquí antes de medir nada:**

> `modo` pasa de `40/47` a **`>= 44/47`** y `corte_de_registro` de `42/47` a **`>= 45/47`**. Si `modo` sale **por debajo de 40/47**, es regresión y se revierte.

## Validaciones obligatorias

- **Una sola invocación** de `scripts/check.ps1`, salida 0, con la terna de `pytest` **anclada al árbol** que la produjo.
- `git diff --check` contra `main` limpio.
- El diff no toca ninguna ruta de «Fuera de alcance».

## Rama base

`main`, con #653 ya dentro. Rama de trabajo nueva.

## Condiciones de parada

- **NO se mide con Ollama**: CI no lo tiene, y una cifra simulada es peor que ninguna (ADR-117). La medición la corre el propietario.
- Si #653 **no** está en `main`, **parar** antes de tocar nada.
- Si cumplir el objetivo exigiera tocar algo de «Fuera de alcance» —y en particular la instrucción del **filtro**—, **parar con `BLOCKED_BY_DECISION`**.
- **Dos rondas con hallazgos de la misma familia: parar** (regla de #581).

## Salvaguardas

- No se fusiona nada: la fusión es gesto del propietario.
- No se toca el corpus, `resultado_esperado` ni ninguna adjudicación.
- **No se lee ni se indexa `criticidad.razon_segura`.**
- Nada de rebase, squash, amend, force-push ni reset destructivo.
- Los adaptadores siguen siendo solo-localhost y fallando abiertos.
- Nota de arranque publicada antes del primer commit de código.
