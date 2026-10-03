# Nota de arranque — la puerta de activación resuelve el `Perfil: rol@N` antes de arrancar el ciclo

Rama `claude/la-puerta-resuelve-el-perfil`, fecha 01-10-2026 (la hora es la del
commit que la publica, y la lleva el ADR). Publicada **antes del primer commit
de arreglo**, como exige ADR-001.

## El suceso

El 20-09 la incidencia #653 arrancó el ciclo y murió a los seis segundos: el
cuerpo declaraba `Perfil: implementer@2` y el paso del implementador que
resuelve el prompt (`resolver_prompt.py --carril ejecucion`, H-28) paró en rojo
antes de ejecutar nada. La puerta de activación
(`sirius_validate_activation.sh`) había dado la activación por válida: comprueba
que la incidencia está abierta, que lleva `sirius:planned`, que no hay estados
incompatibles y que el cuerpo tiene todas las secciones; **no mira el
`Perfil:`**. Hoy el guion de la puerta no contiene la palabra «Perfil»
(bitácora del ciclo, entradas 123, 124 y 138; deudas 34 y 35; mina del 30-09,
§6.4).

Lo que cuesta: un run del implementador que no implementa nada, la incidencia
en `failed-safely` y una persona leyendo el log del run para saber por qué.

## Las cuatro preguntas y la predicción

1. ¿Cuántas activaciones de septiembre murieron en la resolución del prompt?
   Se mide en el volcado como «`implementing` seguido de `failed-safely` en
   menos de dos minutos y sin ninguna ronda». Predicción: menos de cinco, #653
   entre ellas; demasiado pequeño para una tasa, y se dirá así.
2. ¿Puede la puerta rechazar antes, con el mismo resolutor que usa el
   implementador? Predicción: sí, llamando a `resolver_prompt.py` sobre el
   cuerpo ya leído, sin red y sin `uv`; el motivo de rechazo será
   `perfil-sin-resolver` y el comentario llevará el texto del resolutor.
3. ¿Qué pasa con un `rol@N` válido pero no vigente (#653 llevaba `@2` y la
   versión vigente era la 4)? Predicción: no se rechaza —el manifiesto fija
   que `rol@N` sigue significando un texto— y se avisa una vez, con marcador,
   diciendo cuál es la vigente.
4. ¿Cuánto cuesta? Predicción: un paso más en la puerta, dos funciones de
   lectura en `resolver_prompt.py` sin dependencias nuevas, y cuatro pruebas
   que ejecutan la puerta de verdad con el doble de `gh`.

## Criterio de parada (antes de medir)

- La puerta **no corrige** el cuerpo ni elige un perfil por su cuenta: rechaza
  y dice qué poner (misma política que el resto de la puerta).
- El resolutor que usa la puerta es **el mismo fichero** que usa el
  implementador: dos resolutores serían dos verdades.
- Si para leer la versión vigente hiciera falta una dependencia que el
  `python3` del runner no tiene (PyYAML), se lee la línea `version:` del
  perfil con la biblioteca estándar y se dice.
- Tres mutaciones tienen que caer: M1 la puerta deja de resolver el perfil;
  M2 el `rol@N` no vigente deja de avisar; M3 el aviso de no vigente se
  convierte en rechazo.
