# Notas de arranque por rama

Aquí viven las notas de arranque de la disciplina de evidencia (ADR-001):
un archivo `<rama-saneada>.md` por rama de trabajo, con el criterio de
parada, la afirmación y la comprobación que la sostiene.

La puerta del push (`.claude/hooks/exigir_evidencia_push.py`) acepta como
evidencia un ADR tocado en el diff de la rama o una nota aquí. Confírmala en
la rama: así sobrevive a los contenedores efímeros y queda visible en la PR,
que es donde la visibilidad ata.

Los marcadores `.empujon-*` son estado local del hook de cierre y no se
versionan.
