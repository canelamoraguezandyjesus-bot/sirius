"""Código experimental aislado para los spikes decisivos de ADR-001.

NO es código productivo de Sirius 0.1 ni de Sirius 0.2. Existe solo para
falsar la alternativa A del ADR-001 mediante evidencia ejecutable, según
`docs/implementation/SIRIUS_0.2_ADR001_PAQUETE_OPERATIVO_SPIKES_v1.0.md`.

Reglas que este paquete respeta por construcción:

- nunca importa ni modifica código productivo salvo para leer el esquema
  canónico de 0.1 a través de ``upgrade_to_head`` (solo lectura de esquema);
- nunca hace ALTER ni DROP sobre una tabla de Sirius 0.1;
- todas las tablas experimentales llevan el prefijo ``x_``;
- todas las bases de datos son temporales y sintéticas.
"""
