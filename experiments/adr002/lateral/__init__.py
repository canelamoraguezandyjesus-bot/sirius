"""Indices laterales: vocabulario extra que se consulta junto al indice medido.

Un indice lateral **no toca** el indice del canon ni el texto guardado. Es una
tabla aparte, borrable y regenerable entera desde la fuente, que se consulta en
`E1` y aporta candidatos que la busqueda por palabras no habria traido.

Hay dos, y se parecen menos de lo que parece:

* el de la **ingesta**, escrito por un modelo local al guardar cada dato. Medido
  dos veces: no mejora nada y cuesta dos llamadas al modelo por elemento;
* el de **categoria**, escrito desde la criticidad que el canon ya declara. No
  cuesta ninguna llamada, no hay modelo, y es determinista.
"""
