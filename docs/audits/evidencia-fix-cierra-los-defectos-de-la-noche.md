# Evidencia — seis defectos decían `abierto` con su arreglo ya fusionado (14-09-2026)

Rama `fix/cierra-los-defectos-de-la-noche`, 14-09-2026, fusionada en la PR #636.

**No hay decisión nueva que registrar y por eso no lleva ADR**, igual que su
hermana de la misma noche, `docs/audits/evidencia-cierra-los-defectos-ya-arreglados.md`:
cerrar una entrada cuando su arreglo está en `main` es lo que el registro ya
prescribe, y el criterio para elegir el commit de cierre lo fijó ADR-080. Esto es
el hecho medido y la lista verificada.

## Lo primero, porque es un defecto de esta misma rama

**Esta evidencia se escribe DESPUÉS de fusionar la #636, no antes del primer
commit.** ADR-001 pide lo segundo, y la guarda de parada del repositorio lo cazó
al terminar. Se dice aquí en vez de disimularlo con una fecha.

Lo que sí se sostiene: el criterio de abajo **no se inventó al escribir este
documento**. Es literalmente el de la #618, citado por su nombre en el mensaje
del commit de cierre y en el cuerpo de la PR antes de tocar el registro, y las
seis comprobaciones se ejecutaron antes de marcar ninguna entrada como cerrada.
Lo que faltó fue **publicarlo**, que es justamente la mitad que ADR-001 exige y
la que hace que un criterio se pueda comprobar en vez de creer.

## Criterio (el de la #618, reutilizado sin cambios)

- Una entrada solo se cierra si su commit de cierre **existe** (`git log -1`) y
  está **contenido en `origin/main`** (`git branch -r --contains`). Si alguno de
  los dos falla, esa entrada se queda abierta y se dice por qué.
- El commit de cierre es el de **la fusión** de la PR que trajo el arreglo, no el
  número de la PR ni una inferencia a partir del ADR.
- Si al terminar queda cualquier identificador repetido, o `MEMORIA.md` deja de
  coincidir con lo que genera `sirius-memoria conocimiento`, el trabajo no vale.

## Las seis, comprobadas una a una

```
$ for c in 2fd882df c3f2884e 345dc854 8324a65a 0bc8ed14 ab801b85; do
    git rev-parse $c; git branch -r --contains $c | grep -c 'origin/main'
  done
```

| Defecto | Commit de cierre | `git log -1` | en `origin/main` |
|---|---|---|---|
| `H-190` | `2fd882dfadef4d92cc9ae0a63003ce72b0de17d2` | sí | sí |
| `H-192` | `c3f2884eb00264943fac0833ce813bf0d2456b7d` | sí | sí |
| `H-193` | `345dc8542885aa5a118ddde7927f7d77fb0d4f54` | sí | sí |
| `H-194` | `8324a65a07e55bb0223a714f578b62f1109c2d64` | sí | sí |
| `H-195` | `ab801b856725f69a573fe850d5da6c6679e7314d` | sí | sí |
| `H-196` | `0bc8ed1466d7b891b23189debd71746425c7460b` | sí | sí |

Las seis pasan las dos comprobaciones. El registro queda en **48 cerrado, 1
abierto**.

## La séptima, que NO se cerró

`H-43` —«una rama se fusionaba sin que nadie probara su combinación con `main`»—
cumple el criterio mecánico: ADR-191 está fusionado. **Y aun así se deja
abierta**, con la razón escrita junto a la entrada en el propio registro.

Motivo: ADR-191 trajo la *condición* (`scripts/automation/sirius_cola.py`) pero
**dejó escrito que no cablea la puerta**, porque
`.github/workflows/advance-sirius-after-quality.yml` declara `contents: read` y
no puede poner al día la rama que espera. Mientras nadie la cablee, la frase del
título sigue siendo verdad, así que cerrarla sería el «cerrado» falso que este
barrido viene a quitar.

**Esto es una lectura, no una medición**, y conviene decirlo: el criterio
mecánico decía «ciérrala» y se decidió en contra leyendo lo que el ADR declara
de sí mismo. Si alguien discrepa, el sitio donde discutirlo es la #608, donde
está puesta la decisión que lo desbloquea.

## Qué NO garantiza esto

- **No impide que vuelva a pasar.** Cerrar una entrada sigue siendo un gesto que
  alguien tiene que acordarse de hacer al fusionar; nada lo deriva. Lo que
  cerraría la familia —derivar `cerrado` de si el commit está en `main`— sigue
  sin hacerse, igual que lo declaró la #618.
- **No comprueba que el defecto esté arreglado**, solo que el commit que dice
  arreglarlo está en `main`. Es el mismo límite que declaró la #618 y se repite
  aquí en vez de darlo por sabido.
- **No comprueba que estos seis sean todos.** Son los que el registro tenía
  abiertos el 14-09-2026 a las 10:20 UTC; `grep -c "estado: abierto"` sobre el
  fichero da el resto de la respuesta en cualquier momento.

## Comprobación de la rama

```
uv run ruff format --check .   636 files already formatted
uv run ruff check .            All checks passed!
uv run mypy src tests          Success: no issues found in 599 source files
uv run pytest -q               6665 passed, 17 skipped, 2 xfailed in 744.49s
git diff --check               (sin salida)
```

`MEMORIA.md` se regeneró **después** de tocar el registro, nunca antes: el
generador también lo lee, e invertir el orden fue lo que puso la #598 en rojo.
