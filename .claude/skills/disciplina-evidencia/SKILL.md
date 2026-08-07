---
name: disciplina-evidencia
description: >-
  Método obligatorio de evidencia para CUALQUIER trabajo de este repositorio:
  implementar, corregir, diagnosticar un fallo, decidir entre opciones, auditar,
  investigar, comparar, revisar hallazgos de un revisor, cerrar una incidencia o
  registrar una decisión (ADR). Cárgala siempre que vayas a afirmar algo sobre
  el comportamiento del sistema, a arreglar un defecto o a producir un
  documento con conclusiones. Enseña la nota de arranque, el criterio de parada
  escrito antes de ver resultados, la regla de las dos rondas y la prueba por
  mutación.
---

# Disciplina de evidencia

**Regla única: nada se afirma sin la comprobación que lo sostiene, y la
comprobación se enseña.**

Nació de la PR #136: 19 defectos en 8 rondas, todos de dos familias —
*afirmar más de lo que el dato sostiene* y *garantías puestas donde no pueden
cumplirse*— y una raíz que era detectable en el minuto uno y tardó un día en
mirarse.

## 1. Nota de arranque (antes del primer commit)

Antes de tocar nada, escribe y PUBLICA donde el humano pueda verla (la
incidencia si existe; si no, el ADR de la rama) la respuesta a cuatro
preguntas:

1. **¿Dónde vive el fallo y dónde voy a poner el arreglo?** Si el arreglo vive
   dentro de lo que falla, explica por qué puede funcionar. La pregunta que
   caza la raíz: *¿puede el sitio del arreglo OBSERVAR el fallo que arregla?*
   Un proceso que muere no puede informar de su propia muerte.
2. **¿Qué NO va a garantizar esto?** Escrito antes, no como excusa después.
3. **Criterio de parada**, decidido ANTES de la primera revisión o resultado.
   Lo que ata no es tenerlo: es haberlo publicado.
4. **¿Qué haría el fallo IMPOSIBLE en vez de improbable?** Si no lo haces,
   di por qué no.

## 2. Regla de las dos rondas

Dos rondas de revisión seguidas con defectos de la misma familia →
**prohibido seguir parcheando**. Se escribe el patrón, se busca la raíz y se
decide: seguir, retirar lo construido, o escalar al propietario. En la #136
esta regla habría ahorrado cinco rondas.

Desde la ronda 2, cambia también la pregunta al revisor: no «revisa este
diff», sino «aquí están los hallazgos anteriores; ¿está mal el enfoque?». Un
revisor de diffs no puede decirte que el enfoque entero está mal si no se lo
preguntas.

## 3. Prueba por mutación (obligatoria)

Ninguna prueba que fije una propiedad («esto no puede volver a pasar») se da
por buena sin haberla visto FALLAR. Al corregir un hallazgo, verifica en las
dos direcciones: la versión vieja pasa con la mutación, la nueva falla. En la
#136 la mutación cazó cuatro pruebas vacuas; una era invisible para el
revisor externo.

## 4. Hallazgos de revisores

Cada hallazgo se verifica contra el código ANTES de aceptarlo, y se dice
explícitamente qué se comprobó. En la #136 dos hallazgos válidos traían el
mecanismo equivocado; aceptarlos tal cual habría empeorado las cosas.

## 5. Al terminar

Todo trabajo que produjo una decisión deja un **ADR** en `docs/decisions/`
(plantilla en `docs/decisions/PLANTILLA.md`). Las decisiones enterradas en
comentarios de PR no se encuentran después. Si el trabajo no produjo ninguna
decisión, dilo explícitamente.

Consulta y AMPLÍA [patrones.md](patrones.md): entra un patrón cuando ha
mordido dos veces; se poda lo que lleve un trimestre sin usarse.
