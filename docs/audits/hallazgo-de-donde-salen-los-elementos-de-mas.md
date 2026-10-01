# De dónde salen los elementos de más — 20-09-2026

Responde a `arranque-de-donde-salen-los-elementos-de-mas.md`, escrita antes de
medir. Medición determinista, sin Ollama, sobre `main` en `66f11424`,
instrumentando `_intercalar_por_categoria`
(`rank_relevant_knowledge.py:680`), que es donde se juntan las cuatro fuentes.
47 llamadas para 47 casos: la atribución por caso es fiable.

## Las dos mediciones

### Con petición FIJA (la política de hoy)

```
0/47 exactos; 487 de mas; 72/81 hallados; omisiones criticas=0

  motor ................. 255  (52.4%)
  siembra ............... 197  (40.5%)
  categoria/criticidad ... 35  ( 7.2%)

  sembrados en total: 201 · en lo esperado: 4 (2.0%) · de mas: 197
  casos con de-mas TODOS de siembra: 9/47 · serían exactos sin ella: 7/47
```

### Con petición DECLARADA (la que produciría un intérprete que funcionara)

```
17/47 exactos; 162 de mas; 78/81 hallados; omisiones criticas=0

  motor ................. 110  (67.9%)
  categoria/criticidad ... 44  (27.2%)
  siembra ................. 8  ( 4.9%)

  sembrados en total: 12 · en lo esperado: 4 (33.3%) · de mas: 8
  casos con de-mas TODOS de siembra: 0/47 · serían exactos sin ella: 0/47
```

## El hallazgo

**La siembra no es el problema. Solo lo parece cuando la petición está mal.**

De 201 elementos sembrados con petición fija se pasa a **12** con la declarada,
y su precisión sube del 2% al 33%. La causa está en el código:
`rank_relevant_knowledge.py:611` activa la siembra con
`peticion.amplia_por_categoria`. Con la petición fija ese interruptor se
enciende a lo ancho; con la declarada solo se enciende donde el caso lo pide,
que es exactamente lo que ADR-177 decidió.

**Consecuencia sobre ADR-129.** El «precio aceptado por escrito antes de
medirlo» —la siembra mete de más y los exactos bajan— es, en buena parte, **un
artefacto de medir con petición fija**. Con la petición correcta ese precio
cuesta 8 elementos de más, no 197. Esto no contradice ADR-129: lo acota. La
decisión sigue siendo buena y las 0 omisiones críticas siguen en pie.

**Y el verdadero generador de ruido es el motor, en las dos configuraciones**:
52.4% con petición fija, **67.9%** con la declarada. Es el ranking ordinario, no
la siembra ni la ampliación.

## Contraste con la predicción

| predicción (escrita antes de medir) | resultado |
|---|---|
| la siembra explica entre el 55% y el 80% de los de más | **FALLADA** — 40.5% con petición fija, **4.9%** con la declarada |
| menos del 15% de lo sembrado estará en lo esperado | **ACERTADA** — 2.0% con petición fija (33% con la declarada) |

La fallada es la que enseña, otra vez: si la siembra hubiera dominado, la
palanca habría sido podarla, y podar la siembra pone en riesgo las 0 omisiones
críticas. Al fallar, aparece que la palanca está en otro sitio y es más segura.

## Qué dice el criterio de parada, que estaba escrito antes

El criterio decía: **menos de un tercio → la siembra no es el problema, se
registra así y NO se toca**. Con la petición declarada la siembra aporta un
**4.9%**. Así que la respuesta es la del criterio: **no se toca la siembra.**

Y se cumple también la regla dura que se escribió de antemano: no se propone
podar nada que ponga en riesgo una omisión crítica. No hace falta.

## Dónde queda el trabajo, entonces

Las dos mediciones juntas dicen lo mismo, y enlaza con la investigación de la
cardinalidad del mismo día:

1. **Arreglar el intérprete vale mucho más de lo que parecía.** No solo mejora
   los campos de la petición: **colapsa la siembra de 201 elementos a 12**,
   baja los de más de 487 a 162 y sube los exactos de 0 a 17. Es la misma
   palanca 1 cuyo defecto concreto quedó identificado hoy: la instrucción
   define la cardinalidad por la gramática de la pregunta y el canon la define
   por la forma del conjunto de respuesta.
2. **Después, el ranking del motor**: 110 de los 162 de más con petición
   declarada. Es la siguiente palanca, y es independiente de la siembra.
3. **La siembra, quieta.**

## Limitación que hay que decir

Esto descompone lo que la **etapa de búsqueda entrega** (487 y 162), no lo que
**sobrevive al filtro real** (los 218 del banco completo con Ollama). El filtro
podría podar unas fuentes más que otras y cambiar el reparto. Descomponer los
218 de verdad exige el filtro real, o sea Ollama, o sea la máquina del
propietario.

Lo que aquí se mide es sólido y es el pre-filtro. No se presenta como otra cosa.
