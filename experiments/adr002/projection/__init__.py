"""Proyeccion experimental ejecutable de la familia de conformidad v0.6.

La familia v0.6 esta **congelada como datos**: cuatro JSON y un canal lateral
heredado por blob. Nada de eso se puede ejecutar. Este paquete la convierte en
**tres planos materializados**, uno por capacidad de la clasificacion aprobada,
de modo que quien puede leer que no dependa de una convencion sino de **que
fichero recibe**.

Los tres planos y su regla de acceso:

===========================  =================================================
``entrada.sqlite3``          Esquema canonico de Sirius 0.1, sin DDL adicional.
                             Lo abre el puerto. Capacidad ``ENTRADA_DE_CANDIDATO``.
``ejes_p2.sqlite3``          Los ejes que el esquema de Sirius 0.1 **no puede
                             sostener**. Misma capacidad; fichero aparte porque
                             anadir tablas al primero romperia la garantia de
                             que el puerto lee el esquema canonico intacto.
``reservado.sqlite3``        ``property_key`` y criticidad aplicada. Capacidades
                             ``SOLO_CAPA_COMUN`` y ``HANDOFF_A_B05``. **Ningun
                             candidato recibe su ruta.**
===========================  =================================================

**El oraculo no se proyecta.** El constructor recibe por firma el corpus y los
tres canales laterales, y nada mas: no puede leer casos, referencias,
adjudicaciones ni resultados esperados porque no los tiene.
"""
