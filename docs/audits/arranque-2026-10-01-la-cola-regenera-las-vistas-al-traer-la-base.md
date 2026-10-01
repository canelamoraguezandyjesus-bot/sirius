# Nota de arranque — la cola trae `main` a la rama que espera y deja las vistas generadas rotas

Rama `claude/la-cola-regenera-la-memoria`, fecha 01-10-2026 (la hora es la del
commit que la publica, y la lleva el ADR). Publicada **antes del primer commit
de arreglo**, como exige ADR-001.

## El suceso

Desde ADR-200 la cola trae `main` a la rama que espera revisión
(`advance-sirius-after-quality.yml`, paso «Fusionar la base y empujar»). La
fusión es correcta; lo que no hace es **regenerar `MEMORIA.md`** —y desde
ADR-218, `docs/audits/INDICE.md`— después de traerla. Son vistas generadas del
árbol: si `main` trajo un ADR o un documento, la combinación tiene una vista
desactualizada y Quality cae en `test_la_memoria_confirmada_en_este_arbol_esta_al_dia`.
Peor: si las dos partes tocaron la vista —lo normal, porque casi toda PR la
regenera—, `git merge` da conflicto en un fichero que nadie debería resolver a
mano, y el paso lo deshace y pide una persona.

Medido en la bitácora del ciclo (entrada 146; deuda 48): en #653 costó una
vuelta del corrector, 25 minutos. Es un caso: demasiado pequeño para una tasa.
Pero el mecanismo es determinista: toda rama que espere en la cola mientras
`main` avanza con un ADR tiene la vista vieja al salir, sin excepción.

## Las cuatro preguntas y la predicción

1. ¿Cuántas de las PR de septiembre regeneran `MEMORIA.md`? Predicción: la
   mayoría de las fusionadas desde ADR-171 (11-09), porque casi todas traen
   ADR o documento; se mide con el volcado de PR de la mina.
2. ¿Qué hace el paso cuando el conflicto está SOLO en las vistas generadas?
   Hoy: lo deshace y pide una persona. Predicción tras el arreglo: regenera,
   termina la fusión y empuja; la persona solo hace falta cuando el conflicto
   está en un fichero que no se genera.
3. ¿Qué hace cuando la fusión es limpia pero la vista queda desactualizada?
   Hoy: empuja la combinación con la vista vieja y Quality cae. Predicción:
   regenera y, si cambió, confirma un commit más antes de empujar.
4. ¿Cuánto cuesta? Predicción: dos pasos de preparación (uv) que solo corren
   cuando hay puesta al día, y unos 20 renglones de bash en el paso; ningún
   permiso nuevo (el PAT que ya usa), ninguna reescritura de historia.

## Criterio de parada (antes de medir)

- Si para regenerar hiciera falta ampliar `permissions:` o un secreto nuevo,
  parar: ADR-002, puramente aditivo o nada.
- Si el conflicto alcanza un fichero que NO es una vista generada, el paso se
  comporta exactamente como hoy: deshace y avisa. Nunca resuelve a mano nada
  que no se genere.
- La prueba ejecuta el bash del paso de verdad, sobre un repositorio de
  prueba con un remoto, con dobles de `uv` y `gh`: los tres caminos (limpia
  con vista vieja; conflicto solo en vistas; conflicto en otro fichero). Una
  prueba que solo mirara que el texto del workflow «menciona» el comando
  certificaría documentación (lección de `test_cola.py`).
- Tres mutaciones tienen que caer: M1 quitar la regeneración tras la fusión
  limpia; M2 resolver regenerando aunque el conflicto esté fuera de las
  vistas; M3 empujar sin confirmar la vista regenerada.
