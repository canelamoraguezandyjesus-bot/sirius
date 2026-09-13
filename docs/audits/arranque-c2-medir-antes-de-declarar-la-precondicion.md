# Nota de arranque — C2: medir ANTES de declarar la precondición (§11.2)

Fecha: 2026-09-13. ANTES del primer commit (ADR-001). Encargo
`WI-20260913-072231`, incidencia #605: declarar `programacion` y
`documentacion` en `CLASES_CON_ESTADO_PROPIO`
(`src/sirius_engine/projection_verifier.py:86`) si —y solo si— la medida lo
sostiene.

## De quién es el criterio de parada, y por qué importa aquí

El criterio no lo elijo yo: viene escrito en el cuerpo de la incidencia, por el
propietario, antes de que nadie midiera nada. Literal:

> Si lo que sale es DIVERGENCIA SISTEMATICA -no una ventana ni un caso
> suelto-, PARA con BLOCKED_BY_DECISION, explica que diverge y por que, y NO
> declares: declarar para que el contador acuse al motor de un defecto que es
> del reflejo seria peor que el silencio de hoy.

Digo en voz alta lo que hice y en qué orden, porque la disciplina exige el
criterio publicado antes del resultado y este archivo se escribe después de
correr la medida: **ejecuté las lecturas (paso (a)) antes de redactar esta
nota**. Lo que impide que eso contamine la decisión no es mi palabra: es que el
criterio con el que se juzga la medida estaba publicado en la incidencia —donde
el propietario puede releerlo— desde antes de la primera lectura, y no lo he
tocado. Si hubiera redactado el criterio después de ver los números, la nota
serviría de coartada en vez de de ata.

## Las cuatro preguntas

1. **¿Dónde vive el fallo y dónde iría el arreglo?** El fallo vive en que
   `racha_siete_dias.jsonl` lleva 356 líneas y ninguna cuenta: todas salen
   `no_comparable` por la precondición del §11.2, que declara que el contador
   no puede empezar antes de que el motor lleve el estado por sí mismo. El
   arreglo propuesto —declarar dos clases en `CLASES_CON_ESTADO_PROPIO`— vive
   en el mismo módulo que emite esas líneas, así que **sí puede observar lo que
   arregla**: basta ejecutar `verificar_dia` con el conjunto lleno sobre los
   datos reales y leer lo que sale. Por eso el paso (a) del encargo es medir, y
   por eso se puede medir sin escribir nada.
2. **¿Qué NO va a garantizar esto?** Declarar la precondición no pone ningún
   día en verde por sí mismo: solo retira el `no_comparable` y deja que los dos
   ejes se comparen de verdad. Tampoco conmuta nada (§11.3, fuera de alcance
   duro), ni arregla el reflejo, ni toca `authority_reversion`, ni escribe en
   la rama `estado-del-motor`.
3. **Criterio de parada.** El del propietario, citado arriba: divergencia
   sistemática ⇒ `BLOCKED_BY_DECISION` y no se declara; medida que lo sostiene
   ⇒ se declara `programacion` y `documentacion`, se reescribe
   `test_h25_el_conjunto_declarado_esta_vacio_hoy` y se añade una prueba nueva
   vista fallar. Añado un único criterio propio, subordinado y más estricto, no
   más laxo: **una clase sin ninguna línea comparable hoy tampoco se declara**,
   porque declarar sin medida es exactamente lo que ADR-136 aplazó «hasta
   observar al menos una pasada real».
4. **¿Qué haría el fallo IMPOSIBLE en vez de improbable?** Que el conjunto no
   se pudiera escribir a mano nunca: que se derivara de una medida ejecutable
   en vez de de una constante. No se hace hoy, y digo por qué: el §11.2 pide un
   hecho declarado y auditable, no una heurística que pudiera declararse sola
   el día que los datos vengan sucios; ADR-101 eligió esa forma a propósito. Lo
   que sí queda imposible de hacer de pasada es cambiar el conjunto sin tocar
   `test_h25_el_conjunto_declarado_esta_vacio_hoy`, que existe justo para eso.

## Qué se mide, exactamente

Con copias en `/tmp` de `diario.jsonl` y `diario-despacho.jsonl` de la rama
`estado-del-motor` (nunca escribir en esa rama) y lecturas `gh` de solo lectura
del espejo, se ejecuta la MISMA `verificar_dia` de producción dos veces por
WorkItem —con el conjunto vacío (hoy) y con `{programacion, documentacion}`
declaradas (C2)— y se compara qué sale por eje: `coincide`, `divergencia` o
ventana.

## Dónde queda el resultado

En el ADR de esta rama, con los números y los `work_id` concretos, tal y como
pide el paso (a) del encargo.
