"""¿Puede esta rama entrar a revisión, o le toca esperar? (#608, la cola).

EL COSTE QUE ESTO QUITA, dicho por el propietario: «en el momento que haya tres
trabajos al mismo tiempo va a salir en rojo, aunque tú tengas el poder de
fusionar». Tenía razón, y está medido: de las 14 últimas fusiones de `main`, una
—#611, trece minutos después de #602— aterrizó en un `main` que su rama no tenía
incorporado, y es exactamente la que dejó `main` en rojo con dos `H-39`. Ninguna
de las dos pull requests pudo verlo: cada una estaba verde y cada una tenía
razón. El fallo no vive dentro de ninguna rama, vive ENTRE dos.

QUÉ DECIDE ESTE MÓDULO, Y NADA MÁS. Una sola pregunta: **¿es la punta de `main`
ancestro del head de esta rama?** Si lo es, lo que se revise es lo que
aterrizará. Si no lo es, la combinación que aterrizaría no la ha probado nadie y
la rama espera.

DE ESA SOLA CONDICIÓN SALE LA COLA, sin añadir nada. Si A y B están las dos al
día y A se fusiona, B deja de estarlo **sola**: tiene que ponerse al día para
seguir. Una a una, que es lo que el propietario pidió.

POR QUÉ UNA CONDICIÓN Y NO UN CERROJO. Un cerrojo hay que acordarse de soltarlo,
y aquí los procesos mueren: un runner se cae, una sesión se corta. Entonces el
turno se queda cogido y hace falta que alguien lo libere a mano —la familia
`regla-que-depende-de-que-alguien-se-acuerde`, que este repositorio lleva
cerrando desde ADR-174—. Esto no guarda nada: se leen dos datos y se comparan, y
si el proceso muere a mitad no queda nada pillado.

ESPERAR NO ES PARARSE, Y ESA DISTINCIÓN ES LA CLAVE. `stop_gate` en
`review-sirius-work.yml` aplica `sirius:failed-safely`, que es TERMINAL. Si la
cola dijera «todavía no» por ahí, mataría a toda rama que hiciera cola: cuanto
mejor funcionara, más trabajo muerto dejaría, que es la forma del defecto que la
#613 acaba de cerrar. Por eso esperar es una NO-transición: la etiqueta de
revisión no se aplica todavía y la incidencia se queda donde estaba, en un
estado del que el motor sale solo cuando la condición se cumple.

FAIL-CLOSED, Y AQUÍ SE PUEDE. Cualquier cosa que impida AFIRMAR que la rama está
al día responde que espere. Se puede ser estricto precisamente porque esperar es
recuperable: la condición se vuelve a evaluar y la rama sigue viva. Dejar pasar
de más, en cambio, mete en `main` una combinación que nadie probó, y eso se paga
en rojo.

PERO ESPERAR EN SILENCIO SÍ ES UN DEFECTO. ADR-183 lo dejó escrito para la rama
sin run de Quality: una espera que no se cuenta es indistinguible de un atasco.
Quien llame a esto tiene que dejar dicho en la incidencia que está esperando y
por qué; este módulo devuelve el motivo para que se pueda escribir.

POR QUÉ RECIBE UN FICHERO Y NO LLAMA A NADIE. La lectura la hace el workflow con
su `sirius_retry` y su token, que es donde vive la disciplina de reintento; aquí
solo se decide. Así la decisión se prueba de verdad en
`tests/automation/test_cola.py` en vez de quedarse como texto pegado en un YAML
que nadie ejecuta (la lección de H-14, incidencia #282).

Corre con el `python3` a secas del runner: solo biblioteca estándar
(`tests/automation/test_sirius_runner_python_compat.py` lo vigila).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import NamedTuple

#: Los dos únicos estados de `compare` que significan «la punta de `main` ya
#: está dentro de esta rama». `identical` es la rama que no ha divergido nada;
#: `ahead` es la que tiene trabajo propio ENCIMA de esa punta. Los otros dos que
#: GitHub puede devolver -`behind` y `diverged`- significan justo lo contrario:
#: hay commits en `main` que esta rama no tiene.
ESTADOS_AL_DIA = frozenset({"identical", "ahead"})


class Veredicto(NamedTuple):
    """La respuesta y por qué, porque la espera hay que poder contarla.

    `motivo` no gobierna nada -quien se ramifica lo hace por `al_dia`- pero sin
    él la espera sería silenciosa, y una espera que no se cuenta no se distingue
    de un atasco (ADR-183).
    """

    al_dia: bool
    motivo: str


def _leer(comparacion: Path) -> dict[str, object] | None:
    """El JSON de `compare`, o ``None`` si no hay forma de leerlo."""
    try:
        datos = json.loads(comparacion.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return datos if isinstance(datos, dict) else None


def puede_entrar_a_revision(comparacion: Path | str) -> Veredicto:
    """¿Está la rama al día con `main`?

    `comparacion` es el JSON de ``gh api repos/OWNER/REPO/compare/MAIN...HEAD``.
    Se mira `status`, que es exactamente la pregunta ya contestada por GitHub, y
    no se recalcula nada: reconstruir la ancestría a mano sería otra copia del
    mismo hecho, que es la familia que ADR-178 cerró.
    """
    datos = _leer(Path(comparacion))
    if datos is None:
        return Veredicto(False, "no se pudo leer la comparación con `main`")

    estado = datos.get("status")
    if not isinstance(estado, str):
        return Veredicto(False, "la comparación con `main` no trae `status`")

    if estado in ESTADOS_AL_DIA:
        return Veredicto(True, f"la punta de `main` ya está en la rama (`{estado}`)")

    detras = datos.get("behind_by")
    if isinstance(detras, int) and detras > 0:
        commits = "commit" if detras == 1 else "commits"
        return Veredicto(False, f"la rama va {detras} {commits} por detrás de `main`")
    return Veredicto(False, f"la rama no tiene la punta de `main` (`{estado}`)")


def main(argv: list[str] | None = None) -> int:
    """Sale 0 si puede entrar a revisión; distinto de 0 si le toca esperar.

    El código de salida ES la respuesta, para que el workflow se ramifique por
    él y no por un texto: un mensaje que cambie de redacción no puede convertir
    un «espera» en un «pasa». El motivo va por la salida estándar para que quien
    llame pueda escribirlo en la incidencia.
    """
    parser = argparse.ArgumentParser(description="¿Puede la rama entrar a revisión?")
    parser.add_argument("comparacion", help="JSON de compare MAIN...HEAD")
    args = parser.parse_args(argv)

    veredicto = puede_entrar_a_revision(args.comparacion)
    print(veredicto.motivo)
    return 0 if veredicto.al_dia else 1


if __name__ == "__main__":
    sys.exit(main())
