# ADR-071 — La inversa de la proyección del cuerpo, para que haya algo que verificar

- Estado: PROPUESTO
- Fecha: 2026-08-22
- Aprobación: la fusión de la PR de esta rama por el propietario
- Nota de arranque de esta rama: este ADR. Publicado antes del primer commit.

## Contexto y problema

D1 conmuta la canonicidad de una clase —de «la incidencia manda» a «el motor
manda con proyección obligatoria»— cuando un **verificador de proyección** pasa
siete días en verde (contrato §11.2). Al diseñarlo apareció que **no hay casi
nada que verificar**, y el número es peor de lo que suena.

Medido sobre el código, no razonado (incidencia #250, hallazgo H-C):

| | |
|---|---|
| Campos de `WorkItem` | 19 |
| Campos que el cuerpo de la incidencia proyecta | 9 |
| **Campos con contenido informativo comparable hoy** | **2** — `estado` y `fase` |

Y el único obligatorio de esos dos está colapsado: `_LABEL_STATE` tiene trece
etiquetas y **ocho de ellas significan `ACTIVE`** (`implementing`,
`audit-requested`, `ci-pending`, `review-requested`, `reviewing`,
`repair-requested`, `repairing`, `ready-for-merge`). Un motor en `ACTIVE`
coincide con el 62 % del vocabulario de etiquetas.

**Siete días en verde de eso no dirían nada — y autorizarían la conmutación
igual.** Un verificador que no puede ponerse rojo es peor que no tener
verificador: no es que no ayude, es que da permiso.

### Por qué no había más que comparar

`issue_body_projection.py` escribe **once secciones** desde C2. La inversa **no
existía**: el espejo (`mirror_projection.py`) solo corre dos expresiones
regulares sobre el cuerpo —el SHA y la URL de la PR— e identifica el trabajo
como `repo#numero`, no por su `work_id`. La proyección era de ida y no de
vuelta, y por eso todo lo que el cuerpo declara quedaba fuera de cualquier
comparación posible.

## Criterio de parada (escrito ANTES de decidir)

Si leer el cuerpo de vuelta exigiera **cambiar la proyección** —tocar lo que C2
escribe para que sea más fácil de parsear— se para: eso cambiaría el cuerpo de
incidencias reales que el motor ya publica, y es una decisión con consecuencias
en el ciclo, no una comodidad del parser. No se activó: la proyección queda
intacta y la inversa se ajusta a lo que ya escribe.

Y si la inversa necesitara **inventar** algún campo que el cuerpo no lleva, se
para: un verificador que compara un valor inventado con otro real da rojo
siempre o verde siempre, y las dos cosas son inútiles. Tampoco se activó — de
ahí la decisión de abajo.

## Decisión

Un módulo nuevo, `issue_body_parsing.py`, que lee las secciones que la
proyección escribe y devuelve **`CuerpoDeclarado`**: nueve campos, cada uno
`None` cuando su sección falta o está vacía.

**No reconstruye un `WorkItem`, y el nombre lo dice.** El cuerpo no lleva
`peticion_original`, `prioridad`, `clase`, `version`, `created_at`,
`updated_at`, `evidencia`, `resultado`, `diagnostico` ni `paused_from`.
Devolver un `WorkItem` obligaría a inventar esos diez campos, y un verificador
que compara campos inventados es exactamente el «verde vacío» que este trabajo
viene a impedir. Se devuelve lo que el cuerpo **declara**, que es otra cosa y se
llama distinto.

### Ausente y vacío no son lo mismo

Cada campo distingue «la sección no está» (`None`) de «la sección declara que no
hay nada» (`()` en las listas). Importa para el verificador: un cuerpo truncado
y uno que declara una lista vacía no son el mismo hecho, y tratarlos igual haría
que diera por comparable algo que no pudo leer — otra receta de verde vacío.

## Consecuencias

- La superficie comparable de un futuro verificador pasa de **un campo
  colapsado** a los que el cuerpo declara de verdad: `work_id`, `objetivo`,
  `entregable`, `criterio_terminado`, `contexto_origen`, `plan`,
  `fuera_de_alcance`, `bloque` y `rama_base`.
- **`work_id` deja de faltar como clave de unión.** El espejo identificaba el
  trabajo como `repo#numero` y el cuerpo lleva el `work_id` real; ahora se puede
  leer.

## Lo que esto NO hace

- **No construye el verificador**, ni desbloquea D1 por sí solo. Quedan los
  falsos rojos estructurales del hallazgo H-D de #250 —el instante del despacho,
  la ventana de tolerancia y las dos máquinas de estados que no son el mismo
  grafo—, y siguen sin resolverse.
- **No compara nada todavía.** Es la mitad que faltaba, no la comparación.
- **No garantiza que los nueve campos sean informativos.** Tres de ellos
  (`bloque`, `rama_base` y `fuera_de_alcance`) son casi siempre constantes en la
  práctica; cuánto discriminan de verdad es una medición que el verificador
  tendrá que hacer antes de contarlos como cobertura.

## Comprobación que la sostiene

- **Ida y vuelta como propiedad**, no como ejemplo pegado a mano: se proyecta un
  `WorkItem` y se lee de vuelta, y los campos coinciden. Un cuerpo literal en la
  prueba envejecería en cuanto la proyección cambiara una palabra, y entonces la
  prueba mediría el pegado.
- Cinco formas de objetivo —dos líneas, acentos, dos puntos, `código en línea`,
  negrita— sobreviven a la vuelta.
- **Dos mutaciones vistas fallar**: desactivada la separación del plan, cae la
  prueba que la fija; convertido el «sin referencias» en `None`, cae la que
  distingue ausente de vacío.
