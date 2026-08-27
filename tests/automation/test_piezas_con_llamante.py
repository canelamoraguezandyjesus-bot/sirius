"""La enfermedad de esta casa: una pieza correcta a la que no llama nadie.

Este repositorio lleva **cinco** casos contados, y los cinco tenían pruebas en
verde vigilando código que no se ejecutaba nunca:

| pieza | cuánto estuvo muerta |
|---|---|
| el despachador (C2) | semanas |
| H-13 | días |
| el supervisor (`supervise_runs`, C1) | desde C1 hasta D2 |
| el contador de los siete días (`sirius-racha`) | desde el 23-08 |
| **`authority_reversion` (D1c)** | desde que se escribió, hasta hoy |

El quinto era el peor: es la **salida de emergencia del §11.4**, lo único que
devolvería el mando a la vía GitHub si el motor se porta mal con una clase ya
conmutada. Una salvaguarda que nadie invoca no es una salvaguarda; es un adorno
que se cita en un contrato.

Esta batería no comprueba que las piezas estén bien hechas —eso lo hacen sus
propias pruebas—. Comprueba que **alguien las llame**, que es la mitad que
faltaba las cinco veces.
"""

from __future__ import annotations

from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]

#: Módulo -> por qué importa que tenga llamante, en una frase que se lee en el
#: fallo. Sin el motivo, un rojo aquí parece burocracia y se silencia.
PIEZAS = {
    "authority_reversion": (
        "es la salida de emergencia del §11.4: lo único que devuelve el mando a "
        "GitHub si el motor se porta mal con una clase ya conmutada"
    ),
    "seven_day_streak": (
        "es el contador de los siete días del §11.2: sin llamante, D1 no puede "
        "completarse nunca y nadie sabría por qué"
    ),
    "projection_verifier": (
        "es quien compara el motor con su incidencia: sin él no hay días verdes que contar"
    ),
    "supervisor": ("es el turno del motor: reconcilia el mundo y rescata lo que se atascó"),
}


def _sin_comentarios(texto: str, fichero: str) -> str:
    """El fichero sin sus comentarios, que es lo único donde vale buscar.

    ESTA FUNCIÓN NACIÓ DE LA CUARTA MUTACIÓN QUE NO FALLÓ EN LA MISMA NOCHE.
    La primera versión de esta batería buscaba el nombre del módulo con `grep -rl`
    y daba por bueno un fichero que solo lo **mencionaba en un comentario** — y el
    comentario era el mío, el que explica que la pieza estaba sin llamante. Quitar
    el `import` real dejaba la prueba impasible.

    Los otros tres fueron el guardián de H-14, el de `ddgs` y el de la memoria del
    preflight. Los cuatro son el mismo defecto y merece la pena nombrarlo de una
    vez: **un guardián que se conforma con que algo esté NOMBRADO no comprueba que
    esté LLAMADO.** Es la raíz que ADR-095 describe, aplicada a las pruebas.
    """
    marca = "#"
    lineas = []
    for linea in texto.splitlines():
        limpia = linea.split(marca, 1)[0] if fichero.endswith((".py", ".yml", ".sh")) else linea
        lineas.append(limpia)
    return "\n".join(lineas)


def _llamantes(modulo: str) -> list[str]:
    """Ficheros de PRODUCCIÓN cuyo CÓDIGO nombra este módulo.

    Se excluyen las pruebas a propósito: una pieza llamada solo por sus pruebas es
    exactamente el caso que esta batería existe para cazar. Y se excluyen los
    comentarios, por el motivo que explica `_sin_comentarios`.
    """
    encontrados: list[str] = []
    for carpeta in ("src", "scripts", ".github/workflows"):
        raiz = RAIZ / carpeta
        if not raiz.is_dir():
            continue
        for ruta in raiz.rglob("*"):
            if ruta.suffix not in (".py", ".yml", ".sh") or "__pycache__" in ruta.parts:
                continue
            if ruta.stem == modulo:
                continue
            try:
                texto = ruta.read_text(encoding="utf-8")
            except OSError, UnicodeDecodeError:
                continue
            if modulo in _sin_comentarios(texto, ruta.name):
                encontrados.append(str(ruta.relative_to(RAIZ)))
    return sorted(encontrados)


@pytest.mark.parametrize(("modulo", "motivo"), sorted(PIEZAS.items()))
def test_cada_pieza_tiene_quien_la_llame(modulo: str, motivo: str) -> None:
    """Una pieza sin llamante está muerta aunque sus pruebas estén en verde."""
    llamantes = _llamantes(modulo)
    assert llamantes, (
        f"`{modulo}` no lo llama nadie en producción, y {motivo}.\n"
        "Está construido, probado y muerto: es el sexto caso de esta casa. "
        "O se cablea, o se retira y se dice por qué."
    )


def test_la_lista_no_esta_vacia() -> None:
    """Anti-vacua: una lista vacía haría pasar esta batería sin comprobar nada."""
    assert PIEZAS, "no hay ninguna pieza vigilada: esta batería no mediría nada"
