"""Un workflow sin disparador activo es una pieza a la que no puede llamar nadie.

Es la enfermedad de esta casa —«una pieza correcta a la que no llama nadie»,
`test_piezas_con_llamante.py`— aplicada al único sitio donde no se vigilaba.

EL CASO QUE LA TRAJO. `medir-investigador.yml` estuvo del 26 al 27-08-2026 con
su bloque `on:` entero comentado. Fue una decisión deliberada y buena: el arnés
estaba refutado y no debía gastar cuota de las dos APIs del propietario. El
problema no fue apagarlo, fue que **nada recordaba que estaba apagado**. El
fichero seguía en su sitio, con sus 900 líneas medidas y sus pruebas en verde, y
lo único que decía la verdad era un cartel de texto en la cabecera —que además
se quedó obsoleto cuando el disparador se repuso, afirmando durante horas que el
workflow no se podía correr mientras sí se podía—.

POR QUÉ NO BASTA CON LEER LA CABECERA, y por qué esta batería no lo intenta: un
comentario no es un estado. Para saber si un workflow puede dispararse hay que
mirar su `on:`, que es lo que mira GitHub. Cualquier guardián que buscase la
frase «desactivado» en la prosa se aprobaría a sí mismo en cuanto alguien la
citara —este mismo párrafo la contiene— y ése es exactamente el defecto de
guardián vacuo que este repositorio lleva cuatro veces corrigiendo.

QUÉ NO COMPRUEBA. No dice si el disparador es el correcto, ni si el workflow
hace algo útil, ni si alguien lo llama de verdad. Solo que **existe una puerta**.
Apagar un workflow sigue siendo legítimo: lo que exige esta batería es que
apagarlo se declare aquí, con su motivo y su fecha, en vez de dejarlo mudo.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[2]
WORKFLOWS = RAIZ / ".github" / "workflows"

#: Workflows apagados A PROPÓSITO -> motivo y condición para volver a encenderlo.
#: Vacío hoy, y ésa es la situación sana. Añadir una entrada aquí es la forma
#: correcta de apagar un workflow; dejarlo mudo sin entrada es la incorrecta.
APAGADOS_A_PROPOSITO: dict[str, str] = {}


def _ficheros() -> list[Path]:
    return sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))


def _disparadores(ruta: Path) -> object:
    """Lo que GitHub leería como `on:`, no lo que la prosa diga que hay.

    YAML 1.1 convierte la clave desnuda `on` en el booleano `True` —la misma
    trampa que hace que `no` sea `False`—, así que hay que mirar las dos.
    """
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, dict):
        return None
    for clave in (True, "on"):
        if clave in datos:
            return datos[clave]
    return None


@pytest.mark.parametrize("ruta", _ficheros(), ids=lambda r: r.name)
def test_cada_workflow_tiene_una_puerta_por_donde_entrar(ruta: Path) -> None:
    """Sin `on:` con contenido, GitHub no puede lanzarlo nunca."""
    nombre = ruta.name
    disparadores = _disparadores(ruta)
    if nombre in APAGADOS_A_PROPOSITO:
        assert not disparadores, (
            f"`{nombre}` está en la lista de apagados a propósito pero SÍ tiene "
            f"disparador ({disparadores!r}). O se quita de la lista, o se apaga "
            "de verdad: una lista que miente es peor que no tenerla."
        )
        return
    assert disparadores, (
        f"`{nombre}` no tiene ningún disparador activo: su bloque `on:` está "
        "vacío o entero comentado, así que GitHub no puede lanzarlo nunca y el "
        "fichero es una pieza muerta con las pruebas en verde.\n"
        "Si está apagado a propósito, decláralo en `APAGADOS_A_PROPOSITO` con el "
        "motivo y la condición para reponerlo. Apagar es legítimo; quedarse mudo, no."
    )


def test_hay_workflows_que_vigilar() -> None:
    """Anti-vacua: sin ficheros, la batería entera pasaría sin comprobar nada."""
    assert len(_ficheros()) >= 10, (
        "se esperaban al menos diez workflows y hay "
        f"{len(_ficheros())}: si el directorio se mueve, esta batería dejaría de "
        "vigilar sin ponerse roja ni una vez."
    )


def test_lo_declarado_apagado_existe() -> None:
    """Una entrada para un fichero borrado protege a un fantasma."""
    nombres = {r.name for r in _ficheros()}
    huerfanos = sorted(set(APAGADOS_A_PROPOSITO) - nombres)
    assert not huerfanos, (
        f"declarados apagados pero no existen: {huerfanos}. "
        "La lista quedó vieja y ya no describe el repositorio."
    )
