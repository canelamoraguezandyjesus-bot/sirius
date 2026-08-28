"""La puerta y el corrector no pueden discrepar sobre el mismo elemento.

`G4` admite un elemento de ámbito global en cualquier ámbito, sin condición y
por escrito: «un item global es visible desde cualquier ámbito: no pertenece a
uno». El corrector lo contaba como fuga de ámbito, que es fallo duro del §6.1.

Los dos no pueden tener razón. Aquí se fija cuál la tiene, y se fija sobre el
corpus real —no sobre un caso inventado— porque el desacuerdo venía de cómo el
corpus declara `PRJ-GLOBAL`: lo lista entre sus proyectos como cualquier otro,
de modo que numerarlo por posición le daba un proyecto donde no lo hay.

POR QUE ESTO NO ES AJUSTAR LA MEDIDA AL RESULTADO
=================================================

El §8.1 prohíbe cambiar la medición después de ver resultados, y con razón.
Esto no es eso: no se afloja un umbral ni se redefine un acierto, se corrige
una **contradicción interna** entre dos partes del arnés que decían cosas
opuestas del mismo elemento.

QUE SE MUEVE DE LO YA PUBLICADO, DICHO ENTERO
=============================================

Los cuatro candidatos no se mueven: su fuga era cero antes y es cero después, y
su puerta de fuga cero sigue en verdadero. El **control** sí se mueve: `T0` no
tiene etapas y recorre el canon entero para responder, así que entrega el
elemento global en todos los casos acotados. En una repetición de los 50 casos
deja de contársele 34 fugas, y **todas son la misma identidad**, `MEMORIA:1`;
no aparece ni una fuga nueva.

Su veredicto no cambia: la puerta de fuga cero seguía y sigue en falso, porque
le quedan más de mil fugas reales. De modo que la corrección no salva a nadie
ni hunde a nadie; solo deja de cobrar un fallo que no existía.

La ronda publicada no se reescribe. Queda registrada la diferencia, y quien
compare cifras antiguas con nuevas encuentra aquí por qué difieren.
"""

from __future__ import annotations

from typing import Final

from experiments.adr002.projection import build
from experiments.adr002.round import cases as cs
from experiments.adr002.round import metrics as mt
from experiments.adr002.round import participants as pt

#: El único elemento del canon cuyo eje de ámbito es global.
GLOBAL: Final = "MEMORIA:1"


def _corpus() -> dict[str, object]:
    return dict(build.cargar_familia()[cs.CORPUS])


def test_el_canon_tiene_exactamente_un_elemento_global() -> None:
    """Si dejara de haberlo, o hubiera más, estas pruebas medirían otra cosa."""
    items = _corpus()["items"]
    assert isinstance(items, list)
    globales = [i["id"] for i in items if i.get("ambito") == pt.AMBITO_SIN_PROYECTO]
    assert globales == ["MEM-001"], f"el canon ya no tiene un solo elemento global: {globales}"


def test_el_elemento_global_no_declara_proyecto() -> None:
    """El mapa del corrector codifica «global» igual que la proyección: nulo."""
    proyectos = pt.proyectos_del_canon(_corpus())
    assert proyectos[GLOBAL] is None
    #: Y el resto sí lo declaran: la corrección alcanza solo a lo global.
    con_proyecto = [k for k, v in proyectos.items() if v is not None]
    assert len(con_proyecto) == len(proyectos) - 1


def test_el_elemento_global_no_es_fuga_en_un_ambito_acotado() -> None:
    """Lo que la puerta admite, el corrector no puede contarlo como fallo duro."""
    proyectos = pt.proyectos_del_canon(_corpus())
    casos = cs.casos_ejecutables(cs.cargar_artefactos())
    acotados = [c for c in casos if not c.peticion.ambito.global_ and c.peticion.ambito.proyectos]
    assert acotados, "sin un caso acotado a proyecto esta prueba no comprueba nada"
    for caso in acotados:
        assert mt.fuga_de_ambito((GLOBAL,), caso, proyectos) == ()


def test_un_elemento_de_otro_proyecto_si_es_fuga() -> None:
    """El control negativo: la corrección no ha abierto la puerta de par en par."""
    proyectos = pt.proyectos_del_canon(_corpus())
    casos = cs.casos_ejecutables(cs.cargar_artefactos())
    for caso in casos:
        ambito = caso.peticion.ambito
        if ambito.global_ or not ambito.proyectos:
            continue
        ajeno = next(
            (i for i, p in proyectos.items() if p is not None and not ambito.autoriza(p)), None
        )
        assert ajeno is not None, "el canon deberia tener algo fuera de un ambito acotado"
        assert mt.fuga_de_ambito((ajeno,), caso, proyectos) == (ajeno,)
        return


def test_una_identidad_que_el_canon_no_conoce_sigue_siendo_fuga() -> None:
    """Ausente del mapa no es lo mismo que sin proyecto, y no puede colarse.

    Sin esta distincion, la correccion habria convertido «no se quien es» en
    «es global», que es justo lo contrario de fallar cerrado.
    """
    proyectos = pt.proyectos_del_canon(_corpus())
    casos = cs.casos_ejecutables(cs.cargar_artefactos())
    acotado = next(
        c for c in casos if not c.peticion.ambito.global_ and c.peticion.ambito.proyectos
    )
    inventada = "MEMORIA:999999"
    assert inventada not in proyectos
    assert mt.fuga_de_ambito((inventada,), acotado, proyectos) == (inventada,)
