# La memoria del motor no está aquí

Está en la rama **`estado-del-motor`**, no en `main`. Este fichero es el cartel
que lo dice, porque buscarla aquí es lo primero que hace cualquiera.

Para verla:

    git fetch origin estado-del-motor
    git show origin/estado-del-motor:diario.jsonl

## Por qué en otra rama

**`main` está protegido.** Exige pull request, así que un `git push` directo
desde el workflow del motor se rechaza. El primer turno en el servidor tapó ese
rechazo: salió antes de empujar —no había nada que anotar— y la ejecución dio
verde sin llegar a intentarlo. El fallo estaba esperando al primer turno con
trabajo dentro.

**La alternativa era abrir un agujero.** Meter al motor en la lista de
excepciones del ruleset le daría permiso permanente para empujar a `main`, para
esto y para cualquier otra cosa. Su propia rama no abre ninguno: el ruleset
apunta a la rama por defecto, y esta no lo es.

**Y el historial se queda limpio.** El motor anota en cada turno. Eso es
estado, no código, y no tiene por qué llenar el historial de `main` de apuntes
de contabilidad.

## Qué hay en esa rama

- `diario.jsonl` — el diario del motor: WorkItems, Runs y sus transiciones.
- `diario-supervision.jsonl` — los episodios del supervisor, para que una
  invocación no repita lo que ya hizo la anterior.

Los dos son append-only, con checksum por registro (ADR-026). La rama es
huérfana a propósito: no comparte historia con `main` y no la arrastra.

## Lo que esto NO resuelve

Que dos invocaciones simultáneas se pisen. Eso lo impide el grupo de
concurrencia del workflow, y está medido en
`tests/engine/test_exclusion_entre_invocaciones.py`: dos lecturas independientes
del diario despachan el mismo trabajo dos veces. Cambiar de rama no cambia eso.
