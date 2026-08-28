# Nota de arranque — H-31: behind_by ilegible pasa a bloquear

Fecha: 2026-08-28. ANTES del primer cambio (ADR-001). Autorización del
propietario: «dale a la fase de corrección entera».

## Afirmación a corregir

`sirius_merge_on_command.sh` §4b sigue adelante cuando `behind_by` no se puede
leer (fail-open), y `test_sirius_merge.py` FIJA ese comportamiento. Era una
decisión documentada; la auditoría la impugna y el argumento gana: las demás
lecturas materiales del mismo guion fallan cerradas, y el coste de un verde
calculado contra una base vieja (main rota tras fusionar) ya se pagó una vez.

## Las preguntas

1. ¿La prueba invertida se ve FALLAR contra la implementación actual?
2. ¿`behind_by=0` sigue pasando y `>0` sigue bloqueando? (no romper lo sano)
3. ¿Vacío, null, no numérico y fallo de API bloquean CON mensaje reintentable?

## Criterio de parada

- (a) El bloqueo por ilegible tiene que decir «reintenta»: cambiar un merge
  colado por una orden tirada en silencio sería cambiar un defecto por otro.
- (b) Dos rondas (ADR-001).
