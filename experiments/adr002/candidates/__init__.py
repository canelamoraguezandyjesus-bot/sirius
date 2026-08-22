"""Candidatos de ADR-002 y su infraestructura comun neutral.

``common/`` posee el bucle de recuperacion —etapas, puertas, paradas, trazas—
y no conoce a ningun candidato. Cada paquete de candidato aporta unicamente
sus senales por etapa. La separacion es la garantia de neutralidad: si la capa
comun conociera a quien la usa, cualquier ventaja concedida a uno seria
invisible para el benchmark.
"""
