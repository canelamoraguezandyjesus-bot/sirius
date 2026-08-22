"""Leer de vuelta lo que ``issue_body_projection`` escribió: la mitad que faltaba.

La proyección motor -> incidencia existe desde C2 y escribe once secciones. **No
existía la inversa**, y esa ausencia es la que deja a D1 sin nada que verificar:
medido sobre el diseño del verificador, la superficie comparable hoy es **un solo
campo** (``estado``), y encima colapsado — de las trece etiquetas del vocabulario,
ocho significan ``ACTIVE``. Siete días en verde de eso no dirían nada, y
autorizarían la conmutación de canonicidad igual (incidencia #250, hallazgo H-C).

Este módulo lee las secciones que la proyección escribe y devuelve los campos que
contienen. Con él, la comparación pasa de un campo colapsado a los que el cuerpo
declara de verdad.

**No reconstruye un WorkItem.** Devuelve lo declarado en el cuerpo, que es otra
cosa: el cuerpo no lleva ``peticion_original``, ``prioridad``, ``clase``,
``version``, ``created_at``, ``updated_at``, ``evidencia``, ``resultado``,
``diagnostico`` ni ``paused_from``. Confundir «lo que el cuerpo declara» con «el
WorkItem» sería inventar los diez campos que faltan.

Determinista y sin red: recibe texto y devuelve datos.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Encabezado de sección y el texto que le sigue hasta el siguiente encabezado.
#: Se ancla a `^## ` en modo MULTILINE: un `## ` dentro de un bloque de código
#: partiría la sección, y por eso el cuerpo proyectado no los lleva.
_SECCION = re.compile(
    r"^## (?P<titulo>.+?)\s*\n(?P<cuerpo>.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL
)

_PREFIJO_REFERENCIAS = "Referencias autorizadas:"
_PLAN = re.compile(r"\n\nPlan:\n(?P<pasos>(?:- .*(?:\n|$))+)", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class CuerpoDeclarado:
    """Lo que el cuerpo de una incidencia DECLARA, no un WorkItem.

    Cada campo es ``None`` cuando su sección no está o está vacía. Distinguir
    «ausente» de «vacío» importa: un cuerpo truncado y uno que declara una lista
    vacía no son lo mismo, y tratarlos igual haría que el verificador diera por
    comparable algo que no pudo leer.
    """

    work_id: str | None = None
    bloque: str | None = None
    objetivo: str | None = None
    contexto_origen: tuple[str, ...] | None = None
    entregable: str | None = None
    fuera_de_alcance: str | None = None
    criterio_terminado: str | None = None
    plan: tuple[str, ...] | None = None
    rama_base: str | None = None


def _secciones(cuerpo: str) -> dict[str, str]:
    return {m.group("titulo").strip(): m.group("cuerpo").strip() for m in _SECCION.finditer(cuerpo)}


def _o_none(texto: str | None) -> str | None:
    if texto is None:
        return None
    limpio = texto.strip()
    return limpio or None


def _referencias(texto: str | None) -> tuple[str, ...] | None:
    """Las referencias de «Base y dependencias», o ``()`` si declara que no hay.

    La proyección escribe una frase fija cuando ``contexto_origen`` está vacío;
    leerla como «ninguna» y no como «no se pudo leer» es lo que permite comparar
    ese caso en vez de excluirlo.
    """
    limpio = _o_none(texto)
    if limpio is None:
        return None
    if not limpio.startswith(_PREFIJO_REFERENCIAS):
        return ()
    resto = limpio[len(_PREFIJO_REFERENCIAS) :].strip().rstrip(".")
    return tuple(parte.strip() for parte in resto.split(",") if parte.strip())


def _criterio_y_plan(texto: str | None) -> tuple[str | None, tuple[str, ...] | None]:
    """Separar el criterio de terminado del plan, que la proyección concatena."""
    limpio = _o_none(texto)
    if limpio is None:
        return None, None
    encontrado = _PLAN.search("\n\n" + limpio if not limpio.startswith("\n") else limpio)
    if encontrado is None:
        return limpio, None
    pasos = tuple(
        linea[2:].strip()
        for linea in encontrado.group("pasos").splitlines()
        if linea.startswith("- ")
    )
    criterio = limpio[: encontrado.start()].strip() if encontrado.start() > 0 else limpio
    criterio = criterio.split("\n\nPlan:")[0].strip()
    return (criterio or None), pasos


def leer_cuerpo_declarado(cuerpo: str) -> CuerpoDeclarado:
    """Los campos que declara un cuerpo proyectado por ``generar_cuerpo_incidencia``."""
    secciones = _secciones(cuerpo)
    criterio, plan = _criterio_y_plan(secciones.get("Requisitos y pruebas de aceptación"))
    return CuerpoDeclarado(
        work_id=_o_none(secciones.get("Work ID")),
        bloque=_o_none((secciones.get("Bloque") or "").split("\n")[0]),
        objetivo=_o_none(secciones.get("Objetivo")),
        contexto_origen=_referencias(secciones.get("Base y dependencias")),
        entregable=_o_none(secciones.get("Alcance permitido")),
        fuera_de_alcance=_o_none(secciones.get("Fuera de alcance")),
        criterio_terminado=criterio,
        plan=plan,
        rama_base=_o_none(secciones.get("Rama base")),
    )
