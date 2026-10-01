# Nota de arranque — Los dos que la mejor búsqueda no trae

Escrita **antes de mirar**, 20-09-2026, 20:00 UTC. ADR-001.

## Por qué, y por qué es lo último que queda aquí

La entrada 136 dejó la lista corta de lo que falta:

- **2 casos** donde la mejor búsqueda (`--ejes --peticion`) no trae lo esperado:
  `CA-29` (falta `MEM-020`) y `CA-30` (falta `MEM-001`).
- **4 casos** donde el filtro tira esperado — exigen Ollama, no se pueden tocar
  desde aquí.
- **2 casos** de exceso indecidido — también del filtro.

O sea: **estos dos son lo único que queda que se pueda estudiar y arreglar sin
modelo**. Si son defecto, hay encargo; si no, la línea de la búsqueda se cierra
del todo y lo que quede es todo del filtro o del propietario.

Y son raros los dos, que es la razón de mirarlos:

- `CA-29` «¿Cuál es el plazo legal de entrega?» no recupera `MEM-020` «La fuente
  externa afirma que el plazo legal de entrega es de 30 días». **Las palabras
  coinciden casi literales.** Que no entre no puede ser un problema de texto.
- `CA-30` no recupera `MEM-001`, y `MEM-001` **sí entra** en `CA-01`, `CA-02`,
  `CA-26` y `CA-31`. Entra en cuatro y en éste no.

## Las cuatro preguntas

1. ¿Por qué no entra `MEM-020` en `CA-29`, con las palabras coincidiendo?
2. ¿Por qué no entra `MEM-001` en `CA-30`, si entra en otros cuatro?
3. ¿Es la misma causa en los dos, o dos causas distintas?
4. En cada uno: ¿la causa es **una guarda declarada** —ámbito, vigencia,
   confirmación, disponibilidad, autoridad, cupo— haciendo lo que le mandaron, o
   es un **fallo de recuperación** de una candidata que era elegible?

## Criterio de parada

- Si la causa es **una guarda declarada haciendo su trabajo**: no es defecto, es
  el caso probando la guarda. Se registra el negativo y **estos casos no son
  ganables sin cambiar una regla**, lo cual es del propietario, no mío.
- Si la causa es un **fallo de recuperación** de algo elegible: **es defecto por
  cualquier regla**, y se escribe como encargo con su alcance recortado.
- Si son causas distintas, se tratan por separado y se dice cuál es cuál.
- Si la causa de alguno resulta ser **el cupo por cardinalidad**: entonces
  depende de `limite.n`, que ya es la deuda 38, y se remite allí en vez de
  abrir una línea nueva.

**Regla dura**: se lee el motor y se instrumenta la medición; **no se cambia una
línea de producción**. No se toca el corpus, ni `resultado_esperado`, ni el
fixture, ni las adjudicaciones. No se lee `criticidad.razon_segura`.

## Predicción, escrita antes de mirar

1. **`CA-29` es una guarda declarada.** «La fuente externa afirma» huele a
   ítem no confirmado o de autoridad externa, y alguna guarda lo excluye. Le doy
   un **70%**.
2. **`CA-30` NO es una guarda: es ámbito o multiobjetivo.** La consulta pide tres
   cosas a la vez («preferencia de redacción, el presupuesto vigente…») y
   `MEM-001` es `GLOBAL`; sospecho que el caso deriva un proyecto activo y
   `MEM-001` se queda fuera por ahí, o que el cupo se agota antes de llegar a
   ella. Le doy un **60%**.
3. **Al menos uno de los dos es una guarda haciendo su trabajo**, así que como
   mucho **uno** es atacable. Le doy un **75%**.

**Si acierto la 3**, la línea de la búsqueda se cierra esta noche con un encargo
o con ninguno, y todo lo que quede en Sirius es del filtro (Ollama, máquina del
propietario) o decisión suya. Sería la primera vez en esta auditoría que **no
queda nada que yo pueda hacer solo**, y conviene saberlo antes que tarde.
