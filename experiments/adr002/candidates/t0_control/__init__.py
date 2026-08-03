"""Arnes de conformidad de ``T0-control``.

``T0`` es la linea base congelada de Sirius 0.1 y **control de falsacion**, no
un candidato. Este paquete existe para que pueda responder a los **mismos casos
funcionales** que ``ADR002-A``, ``B``, ``C`` y ``D`` sin adoptar el motor comun
ni ninguna senal de los candidatos: traduce la peticion a lo unico que el caso
de uso productivo acepta —el texto de la consulta—, lo ejecuta **tal cual**, y
declara como resultado todo lo que T0 descarta por el camino.

**No modifica Sirius 0.1.** No importa nada de ``candidates/common`` salvo el
contrato de entrada, no implementa ``SenalesDeCandidato``, y no se pasa nunca
al motor comun. El arbol ``src/sirius`` permanece byte a byte.
"""
