# ADR-190 — La guarda de citas no sale de docs/decisions/: medidas 590 citas y 23 rotas fuera del registro, cero son defectos de este árbol

- Estado: PROPUESTO
- Fecha: 2026-09-14
- Aprobación: la fusión de la PR por el propietario
- Contexto: incidencia #619 (WI-20260914-010842), criterio de medir antes de
  fijar de la incidencia #267 tal como lo escribió ADR-078
- Relacionadas: ADR-052 (la guarda de citas y su diseño conservador), ADR-001
  (la disciplina de evidencia), ADR-078 (medir un criterio antes de fijarlo),
  ADR-177 (el hueco declarado: «lo hace cumplir: ninguna prueba»),
  `tests/automation/test_citas_de_los_adr.py`

## Nota de arranque (ADR-001, escrita ANTES de clasificar y de decidir)

Esta sección es la nota de arranque de la rama. El contrato del implementador
solo autoriza un comentario en la incidencia (`PR abierta: <URL>`), así que se
publica aquí, que es la otra sede que la skill `disciplina-evidencia` admite.

Lo que ya estaba visto al escribirla: **la medición en bruto y nada más**. La
incidencia ordena reproducirla antes de tocar nada, así que al redactar estas
cuatro respuestas ya se conocían el recuento (132 ficheros, 590 citas, 23 rotas
en 17 ficheros) y la lista de pares `documento → cita`. **Ningún veredicto
estaba escrito todavía**: la clasificación de las 23 se hizo después de
publicar el criterio de parada, que es lo que el método exige.

1. **¿Dónde vive el fallo y dónde va el arreglo?** El hueco vive en la prosa de
   `docs/`: ADR-177 lo declara en su bloque de lección («lo hace cumplir:
   ninguna prueba … nada en este repositorio vigila la coherencia de la prosa
   de `docs/` con el árbol»). El sitio candidato del arreglo es
   `tests/automation/test_citas_de_los_adr.py`, que hoy barre solo
   `docs/decisions/`. ¿Puede el sitio del arreglo **observar** el fallo que
   arregla? Sí, y sin rodeos: la guarda lee ficheros del árbol y comprueba si
   una ruta se puede abrir; ampliar el barrido es hacerle mirar donde hoy no
   mira. No es el caso del proceso que no puede informar de su propia muerte.
2. **¿Qué NO va a garantizar esto?** No garantiza que la prosa de `docs/` sea
   cierta: solo que las rutas que cita se puedan abrir. Sigue sin mirar dentro
   de los bloques de código ni las citas sin una raíz del repositorio delante
   —ADR-052 midió esa renuncia en 18 de 156—. No dice nada de `docs/canonical/`
   ni de la Arquitectura Técnica, que esta incidencia deja fuera de alcance. Y
   sobre una cita a otro repositorio no puede afirmar nada: como mucho, callar.
3. **Criterio de parada.** Publicado aquí antes del primer veredicto:
   - (a) Las 23 se clasifican una a una. **Defecto real** = la prosa afirma
     algo falso sobre ESTE árbol en este commit (el fichero se movió o se borró
     y la frase se quedó atrás). **Falso positivo** = la prosa es correcta y lo
     que falla es la guarda (rama de origen sin fusionar, repositorio ajeno,
     ruta elidida con `…`, ruta propuesta, nombre de rama, artefacto efímero).
   - (b) Si los falsos superan a los ciertos, la guarda **no entra tal cual**:
     se cambia su forma y se vuelve a medir. Es literalmente el criterio (a) de
     la nota de arranque de la incidencia #277, que ADR-078 dejó escrito.
   - (c) Si después de cambiarle la forma los defectos reales cazados siguen
     siendo **cero**, no se amplía. Una guarda cuya única cosecha medida son
     excepciones escritas a mano no caza nada, y sí deja permisos permanentes
     que hay que vigilar con más pruebas.
   - (d) Si ampliar exigiera tocar `docs/canonical/`, la Arquitectura Técnica,
     el contrato operativo o `.github/**`, se para.
   - (e) Si ampliar exigiera **debilitar** el barrido de `docs/decisions/`
     —renunciar a algo que hoy sí mira—, se para.
4. **¿Qué haría el fallo imposible en vez de improbable?** Que una cita no
   fuera texto: un enlace resuelto al construir el documento, que no compila si
   el destino no existe. Eso cambia el formato de toda la documentación del
   repositorio y ni esta incidencia lo autoriza ni el alcance permitido lo
   cubre. Se hace, por tanto, lo improbable-pero-medible: mirar, o decidir con
   la medida delante que mirar no sale a cuenta.

## Contexto y problema

## Decisión

## Comprobación que la sostiene

## Consecuencias

## Alternativas descartadas y por qué

## La lección
