# ADR-210 — Archivar las incidencias que ya no describen nada, y decir dónde vive la bitácora del ciclo

- Estado: APROBADO
- Fecha: 2026-09-20
- Aprobación: la fusión de la PR por el propietario. La decisión 2 la dio él
  —«archívalas si no dañan ni pasa nada»—, con esa condición, que es la que
  este ADR comprueba; las decisiones 4 y 9 las delegó en la sesión.
- Nota de arranque: la de ADR-204, que cubre esta tanda entera.

## Contexto y problema

Tres de las diez decisiones de la auditoría, todas sobre lo mismo: registros
abiertos que ya no describen nada, y trabajo que nadie puede encontrar.

## Criterio de parada (escrito ANTES de decidir)

La condición la puso el propietario: **se archiva lo que no daña**. Antes de
cerrar cada incidencia se comprueba si su contenido vive en algún otro sitio; si
no vive en ninguno, no se cierra hasta que lo tenga. Y nada de la línea física
—cabeza, mano, laboratorio— se toca: es suya y la sacó del alcance el 19-09.

## Decisión

### 1. Se archivan cinco incidencias; tres no se tocan; dos se cierran porque su contenido ya tiene casa

De las nueve abiertas que la decisión 2 nombraba:

| Incidencia | Qué se hace | Por qué |
|---|---|---|
| #8 Panel Maestro | archivar | Su trabajo lo hacen `MEMORIA.md` y `V8_EXECUTION.md`, que se generan o se prueban |
| #9 Cierre de Sirius 0.1 | archivar | Cerrado y aceptado el 17-08-2026 |
| #10 Programación supervisada | archivar | Es lo que acabó siendo el motor: 24 workflows y un contrato en v1.11 |
| #25 Patrón operativo con ChatGPT | archivar | Describe un flujo que ya no existe: el usuario empujando y ChatGPT abriendo la PR |
| #137 Prueba intermitente | archivar | **Arreglada**: ADR-162 encontró la raíz y la corrigió |
| #14 Reglas operativas | archivar | Sus reglas viven ahora en `AGENTS.md` (ADR-204 y ADR-208) y en el contrato |
| #15 Bandeja de ideas | archivar | Sus ideas viven ahora en `docs/ideas/registro_de_ideas.yml` (ADR-208) |
| #11, #12, #13 robótica y laboratorio | **no se tocan** | Son del propietario y quedan fuera del alcance por su decisión del 19-09 |

Archivar una incidencia es **cerrarla con la razón escrita en un comentario**
(ADR-195). Ninguna se borra.

### 2. La bitácora del ciclo: su sitio es `main`, pero no la trae esta sesión

`docs/audits/DONDE_VIVE_LA_BITACORA_DEL_CICLO.md` dice dónde está, cómo leerla
sin cambiar de rama, y qué falta para que entre.

## Comprobación que la sostiene

**La condición del propietario, comprobada incidencia por incidencia**, que es
justo lo que el criterio de parada exigía:

- #14 y #15 **no se podían cerrar cuando él lo dijo**: eran el único sitio donde
  vivían sus reglas de trabajo y sus ideas aparcadas. Se cierran ahora, y solo
  ahora, porque ADR-208 les dio casa el mismo día. Cerrarlas antes habría
  perdido lo único que había.
- #137: se midió antes de darla por muerta. La prueba
  `test_streaming_message_grows_without_overlapping_neighbours` se corrió **20
  veces seguidas: 20 en verde, 0 en rojo**. Y la causa consta: ADR-162 encontró
  que la medición leía el alto de una fila antes de que Qt asentara el layout
  —«24 px vs 54 px»— y lo corrigió. La incidencia no describe nada que siga
  pasando.
- #8, #9, #10, #25: su contenido está en `main`, en documentos que se generan o
  se prueban.

**La bitácora, comprobado antes de traerla:**

| Qué se comprobó | Resultado |
|---|---|
| ¿Viene sola? | No: cita **7 documentos** hermanos que solo viven en esa rama; el comprobador documental encuentra **10 referencias rotas** al traerla suelta |
| ¿Está viva su rama? | Sí: último commit **ocho minutos antes** de la comprobación |
| ¿Se pierde algo si no se trae? | No: la rama está empujada, que es lo que ADR-195 llama archivar una rama |

La segunda fila es la que decidió. **Es la primera vez que la comprobación de
ADR-206 se ejecuta de verdad, y ha parado una colisión real**: copiar a `main`
el trabajo en vuelo de otra sesión es exactamente lo que produjo la #165 el
14-08.

## Consecuencias

- De 15 incidencias abiertas quedan 8, y las que quedan describen algo que pasa.
- El propietario deja de ver un tablero cuyo 60 % es historia.
- La bitácora se puede encontrar desde `main` sin saber que existe.
- **Lo que no mejora:** las 128 entradas y sus 32 deudas siguen sin estar en
  `main`, así que la mina mensual no las ve. Queda nombrado en la nota y es
  trabajo de la sesión que las escribe.

## Alternativas descartadas y por qué

- **Cerrar también #11, #12 y #13.** Están igual de paradas y son de la línea
  física, que el propietario reservó para sí el 19-09: «ese trabajo es mío, ahí
  no hay que revisar nada».
- **Traer la bitácora igualmente y arreglar las referencias.** Serían diez
  ediciones sobre el trabajo en vuelo de otra sesión, y el resultado sería dos
  copias divergiendo desde el primer minuto.
- **Dejar la bitácora sin nota.** Es lo que llevaba pasando: 128 entradas que
  nadie fuera de esa sesión sabía que existían.

## La lección

- familia: `pieza-sin-lector`
- sin esto se repetiría: el tablero de incidencias seguiría llenándose de cosas
  cerradas hace meses, y un registro de 128 entradas seguiría siendo invisible
  desde `main`.
- lo hace cumplir: `ninguna prueba: cerrar una incidencia ocurre en GitHub, no
  en el árbol, y ninguna guarda de este repositorio puede leerlo sin red. La
  parte que sí vive en el árbol —que la bitácora se pueda encontrar— la sostiene
  el comprobador documental sobre `docs/audits/DONDE_VIVE_LA_BITACORA_DEL_CICLO.md`.
