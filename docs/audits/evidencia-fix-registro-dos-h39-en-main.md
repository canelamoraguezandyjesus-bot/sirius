# Evidencia — `main` tenía dos H-39 y la guarda del registro estaba en rojo

Rama `fix/registro-dos-h39-en-main`, 13-09-2026. **No hay decisión nueva que
registrar y por eso no lleva ADR**: el criterio que resuelve la colisión —manda
el identificador que entró antes en `main`— ya se sentó ese mismo día, cuando
`main` (ADR-185, #604) y la rama de ADR-184 (#602) se disputaron el H-38 y
ganó `main`. Aquí se aplica ese mismo criterio a un caso idéntico un nivel más
arriba. Esto es el hecho medido que lo sostiene.

## Aviso de método: la nota de arranque NO se publicó antes

ADR-001 exige la nota de arranque antes del primer commit. **No se hizo.** El
arreglo salió de encontrar `main` en rojo mientras se revisaba otra cosa, y se
escribió y empujó antes de escribir esta nota. Se declara en vez de disimularlo,
porque una disciplina que se cuenta a posteriori como si se hubiera cumplido
vale menos que no tenerla.

Lo que sí se hizo en su sitio: el criterio de parada de abajo se fijó antes de
tocar el fichero, y la afirmación se midió antes de escribir el arreglo —el
rojo de `main` es la primera comprobación de esta nota, tomada sobre
`origin/main`, no sobre la rama.

## Afirmación

`origin/main` en `b8ecb2d6` tiene **dos** entradas `H-39` en
`docs/audits/registro_defectos.yml`, y `test_ningun_identificador_repetido`
falla sobre él.

Ninguna de las dos PR que las trajeron pudo verlo venir: #602 (ADR-184) dio de
alta H-39 en su rama y #611 (ADR-187) dio de alta H-39 en la suya, y **cada una
estaba verde por separado**, porque dentro de su propio árbol el identificador
era único. La colisión solo existe después de fusionar las dos, y la fusión no
vuelve a correr la guarda. Es el problema medido en la incidencia #608 —fusionar
una PR obliga a reconciliar las demás— mordiendo esta vez en `main`.

## Criterio de parada (fijado antes de tocar el fichero)

1. Si las dos entradas resultaran ser la misma repetida por error de copia, se
   borra la sobrante en vez de renumerar. Medido: son defectos distintos, con
   título, bloque, ADR e incidencia distintos. Se renumera.
2. Renumera **la que entró después en `main`**, no la que a uno le convenga.
   Medido con `git log`: #602 se fusionó a las 16:15:16 y #611 a las 16:28:41.
   Conserva el número ADR-184; ADR-187 pasa a H-40.
3. El arreglo no vale si deja cualquier otro identificador repetido, ni si
   `MEMORIA.md` deja de coincidir con lo que genera `sirius-memoria
   conocimiento`. Las dos cosas se comprueban abajo.
4. Cerrar una entrada exige su commit de cierre **verificado y contenido en
   `origin/main`**, no inferido del número de PR.

## Comprobación

La afirmación, sobre `origin/main` sin tocar nada:

```
$ git checkout -B main origin/main && uv run pytest tests/automation/test_registro_de_defectos.py -q
tests/automation/test_registro_de_defectos.py:69: AssertionError
FAILED tests/automation/test_registro_de_defectos.py::test_ningun_identificador_repetido
1 failed, 67 passed, 1 skipped in 0.82s
```

Las dos entradas, en `main`:

```
508:  - id: H-39
509:    titulo: El detector de sensibilidad confundia una prohibicion con una peticion
513:    adr: 184
--
545:  - id: H-39
546:    titulo: Ponerse al dia con main tiraba la aprobacion de revision aunque el trabajo no cambiara
550:    adr: 187
```

Los cinco commits de cierre, verificados uno a uno con `git log -1` y
comprobados contenidos en `origin/main`:

| Defecto | ADR | Incidencia | Cerrado por |
|---|---|---|---|
| H-33 | 182 | #597 | `f4a201f` |
| H-37 | 183 | #599 | `8912e1d` |
| H-38 | 185 | #603 | `e36fc55` |
| H-39 | 184 | #601 | `1b8dd40` |
| H-40 | 187 | #608 | `b8ecb2d` |

Con el arreglo, la cadena completa (no hay `pwsh` en esta sesión, así que el
equivalente a `scripts/check.ps1` va a mano):

```
uv run ruff format --check .  -> 632 files already formatted
uv run ruff check .           -> All checks passed!
uv run mypy src tests         -> Success: no issues found in 596 source files
uv run pytest tests/engine/ tests/automation/ -q
                              -> 3805 passed, 13 skipped in 361.62s
git diff --check              -> sin salida
```

`tests/engine/` va incluido a propósito: la guarda de coherencia de `MEMORIA.md`
vive en `tests/engine/test_memoria.py` y `tests/automation/` sola no la corre —
la lección que puso la #598 en rojo.

## Un segundo hallazgo, del mismo origen

Al regenerar `MEMORIA.md` **después** del registro (nunca antes: el generador
también lo lee) aparece que la `MEMORIA.md` de `main` iba además una decisión
por detrás: el recuento de ADR pasa de 180 a 181, porque ADR-187 no estaba
contado. Mismo mecanismo que la colisión: dos fusiones seguidas sobre un fichero
generado que ninguna de las dos pudo reconciliar contra la otra.

El registro queda en **40 cerrado, 0 abierto**.

## Lo que NO queda demostrado

- **No se ha comprobado cuántas veces ha ocurrido esto antes.** Esta nota mide
  un caso, el de hoy. Cuántas veces `main` ha estado en rojo por una colisión
  entre dos fusiones verdes es una medida que no se ha tomado y que la
  incidencia #608 necesitaría para priorizar su arreglo grande.
- **Este arreglo no impide que vuelva a pasar.** Renumera y cierra; no añade
  ninguna guarda que impida que dos ramas tomen el mismo identificador. Lo que
  lo impediría —derivar el identificador en vez de escribirlo a mano, o
  comprobar el registro después de fusionar y no solo antes— no se decide aquí.
  Mientras tanto, el siguiente par de PR que den de alta un defecto a la vez
  volverá a dejar `main` en rojo.
- **Los cierres de H-38 y H-40 no son de trabajo propio de esta rama.** Se
  cierran porque su arreglo está fusionado y dejarlos en `abierto` es una
  afirmación falsa; la decisión de cerrarlos es de quien escribe esta nota y
  queda declarada aquí para que se pueda revertir si el propietario no la
  comparte.
