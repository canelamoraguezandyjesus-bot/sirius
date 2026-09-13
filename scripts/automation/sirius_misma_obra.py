"""¿El trabajo propio de una rama es el mismo en dos heads distintos? (#608, parte 2).

EL COSTE QUE ESTO QUITA, dicho por el propietario: «cada vez que fusiono, se
mueve `main`, y entonces tengo que actualizar la otra, que pase por Quality y
que tenga que revisar otra vez. O sea, otra ronda más solo por fusionar una
cosa». Con N pull requests abiertas, fusionar una obliga a reconciliar N-1, y
de las tres cosas que cuesta cada reconciliación -traer `main`, otra vuelta de
Quality, otra ronda de revisión- la cara es la tercera.

QUÉ DECIDE ESTE MÓDULO, Y NADA MÁS. `advance-sirius-after-quality.yml` ya sabe
desde ADR-142 que un re-run de Quality sobre el head YA APROBADO no debe reponer
`sirius:review-requested`: reponerla destruiría una aprobación válida. Pero esa
guarda exige que el head sea EXACTAMENTE el aprobado, así que ponerse al día con
`main` -que mueve el head sin tocar una sola línea del trabajo- tira la
aprobación y cuesta la ronda entera. Aquí se decide lo único que falta para
distinguir los dos casos: si el trabajo PROPIO de la rama es el mismo.

QUÉ ES «EL TRABAJO PROPIO». Lo que `gh api repos/OWNER/REPO/compare/BASE...SHA`
devuelve: el diff de la rama contra la BASE DE MEZCLA, no contra la punta de
`main`. Por eso lo que entra por `main` no cuenta como trabajo de la rama, que
es justo la distinción que hace falta.

POR QUÉ RECIBE FICHEROS Y NO LLAMA A NADIE. Las dos lecturas las hace el
workflow con su `sirius_retry` y su token, que es donde vive la disciplina de
reintento; aquí solo se compara. Así esta decisión -la que puede ahorrar o
regalar una revisión- se prueba de verdad en `tests/automation/test_misma_obra.py`
en vez de quedarse como texto pegado en un YAML que nadie ejecuta (la lección de
H-14, incidencia #282).

FAIL-CLOSED, SIN EXCEPCIONES. Cualquier cosa que impida AFIRMAR que el trabajo
es el mismo -un fichero que no está, un JSON roto, una comparación sin la clave
`files`, un fichero del que no se puede caracterizar el contenido- responde que
NO. La respuesta negativa solo cuesta lo que cuesta hoy: una ronda de revisión.
La positiva equivocada aprobaría trabajo que nadie revisó, y eso no se recupera.

Corre con el `python3` a secas del runner: solo biblioteca estándar
(`tests/automation/test_sirius_runner_python_compat.py` lo vigila).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

#: Vistas que el repositorio GENERA y vigila, y que por tanto no son trabajo que
#: nadie tenga que revisar dos veces. Ponerse al día con `main` obliga a
#: regenerar `MEMORIA.md` -toda rama con un ADR lo toca, y por eso todas chocan
#: entre sí (#608)-, así que sin esta lista esta mejora no ahorraría ninguna
#: ronda en el caso que de verdad ocurre.
#:
#: Ignorarlas es seguro porque su corrección la garantiza OTRA guarda, no un
#: revisor: `tests/engine/test_memoria.py::test_la_memoria_confirmada_en_este_arbol_esta_al_dia`
#: falla en Quality si el fichero confirmado no es exactamente lo que
#: `uv run sirius-memoria conocimiento` produce a partir del árbol (ADR-171). Un
#: humano releyendo una vista generada no añade nada que esa prueba no diga ya.
#:
#: Entrar en esta lista exige ser eso: una vista con generador y con prueba que
#: la vigile. `tests/automation/test_misma_obra.py` lo comprueba.
VISTAS_GENERADAS: tuple[str, ...] = ("MEMORIA.md",)


def _huella(ruta: Path) -> str | None:
    """Huella del trabajo propio descrito por una comparación, o ``None``.

    ``None`` significa «no se puede afirmar nada», y el llamador lo trata como
    «no es la misma obra». Nunca se devuelve una huella a partir de datos
    incompletos: dos huecos idénticos parecerían trabajo idéntico.
    """
    # Dos `except` y no uno con tupla: `ruff format` reescribe la tupla a la
    # sintaxis de PEP 758 (Python 3.14) y el runner corre 3.12, que no la
    # entiende. Lo cazó `test_sirius_runner_python_compat.py`, que existe por
    # exactamente este fallo (se coló una vez en `sirius_convergence.py`).
    try:
        datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    except OSError:
        return None
    except ValueError:
        return None
    if not isinstance(datos, dict):
        return None
    ficheros = datos.get("files")
    # Una comparación sin ficheros no es un caso que este atajo deba cubrir: una
    # rama sin trabajo propio no tiene aprobación que conservar.
    if not isinstance(ficheros, list) or not ficheros:
        return None

    entradas: list[tuple[str, str, str]] = []
    for fichero in ficheros:
        if not isinstance(fichero, dict):
            return None
        nombre = fichero.get("filename")
        if not isinstance(nombre, str) or not nombre:
            return None
        if nombre in VISTAS_GENERADAS:
            continue
        parche = fichero.get("patch")
        # Un binario no trae `patch`; su `sha` de blob sí lo caracteriza. Si no
        # hay ninguno de los dos, no se puede decir qué contiene ese fichero.
        blob = fichero.get("sha")
        texto = parche if isinstance(parche, str) else ""
        identidad = blob if isinstance(blob, str) else ""
        if not texto and not identidad:
            return None
        entradas.append((nombre, texto, identidad))

    # Si quitadas las vistas generadas no queda nada, no hay trabajo propio que
    # comparar: se responde que no, igual que ante una comparación vacía.
    if not entradas:
        return None

    # GitHub no promete orden estable en `files`, y un orden distinto no es
    # trabajo distinto: sin ordenar, esto cobraría rondas de revisión por nada.
    entradas.sort()
    canonico = json.dumps(entradas, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def es_la_misma_obra(comparacion_aprobada: Path | str, comparacion_vigente: Path | str) -> bool:
    """``True`` solo si las dos comparaciones describen el MISMO trabajo propio."""
    huella_aprobada = _huella(Path(comparacion_aprobada))
    if huella_aprobada is None:
        return False
    return huella_aprobada == _huella(Path(comparacion_vigente))


def main(argv: list[str] | None = None) -> int:
    """Sale 0 si es la misma obra; distinto de 0 en cualquier otro caso.

    El código de salida ES la respuesta, para que el workflow se ramifique por
    él y no por un texto: un mensaje que cambie de redacción no puede convertir
    un «no» en un «sí».
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("comparacion_aprobada", help="JSON de compare BASE...head aprobado")
    parser.add_argument("comparacion_vigente", help="JSON de compare BASE...head vigente")
    args = parser.parse_args(argv)

    if es_la_misma_obra(args.comparacion_aprobada, args.comparacion_vigente):
        print("El trabajo propio de la rama es el mismo que el aprobado.")
        return 0
    print("El trabajo propio de la rama no es el aprobado, o no se pudo afirmar que lo sea.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
