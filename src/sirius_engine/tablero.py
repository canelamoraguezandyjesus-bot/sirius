"""El tablero de una incidencia: un solo comentario con la foto de AHORA (ADR-175).

Por qué existe, medido el 12-09-2026: las 40 incidencias más recientes del
ciclo acumulan **1.019 comentarios** —mediana 21, máximo 157 (#545)— y ninguno
dice el estado. Cada uno es un HECHO con su marcador, publicado una vez y nunca
vuelto a tocar: el motor publica historial, no publica estado. Para saber qué
pasa en una incidencia hay que leerse veintiún comentarios.

Y el motor lo sabe: el espejo ya proyecta fase, rondas, veredictos, eventos de
Quality, PR, head y diagnóstico, y ``leer_cuerpo_declarado`` ya parte el cuerpo
en objetivo, entregable, criterio y plan. Es la misma forma que ADR-173 encontró
con el campo ``cerrada``: el dato está, la máquina lo lee para lo suyo, y a un
humano no se le enseña nunca.

Este módulo es **puro**: no habla con GitHub, ni con el disco, ni con el reloj.
Recibe lo que el espejo proyectó y devuelve el texto del comentario. Quien lo
publica es ``notify-sirius-state.yml``, en el mismo paso en el que ya publica
el aviso de estado -mismo disparador, mismo permiso, ningún nivel nuevo de
automatización-.

**El tablero no sustituye al historial.** Los avisos, veredictos y registros de
ronda siguen exactamente igual: son la película. Esto es la foto.
"""

from __future__ import annotations

from collections.abc import Sequence

from sirius_engine.domain.mirror import MirroredWorkItem
from sirius_engine.domain.work_item import WorkItemPhase, WorkItemState
from sirius_engine.issue_body_parsing import CuerpoDeclarado

#: Lo que identifica al tablero entre los comentarios de la incidencia. Es lo
#: ÚNICO que el publicador busca para decidir si edita o crea, así que no
#: cambia nunca: un marcador distinto deja huérfano al tablero anterior y
#: publica un segundo, que es justo lo que este comentario existe para evitar.
MARCADOR = "<!-- sirius-tablero -->"

#: El ciclo de fases de la arquitectura §3.4, en el orden en que se recorre.
#: `REPARAR` no está en la línea porque no es un paso adelante sino la vuelta
#: de `REVISAR` a `COMPROBAR`; cuando el encargo está ahí se dice aparte.
_RECORRIDO = (
    WorkItemPhase.PREPARAR,
    WorkItemPhase.EJECUTAR,
    WorkItemPhase.COMPROBAR,
    WorkItemPhase.REVISAR,
    WorkItemPhase.ENTREGAR,
)

#: Qué significa cada estado para quien lee, y qué se espera de él. El texto es
#: corto a propósito: el aviso de estado ya da el mensaje largo, y repetirlo
#: aquí sería tener el mismo dato en dos sitios.
_LECTURA: dict[WorkItemState, tuple[str, str]] = {
    WorkItemState.PLANNED: ("🟦 preparado, sin empezar", "nada por ahora"),
    WorkItemState.ACTIVE: ("🟦 trabajando", "nada por ahora"),
    WorkItemState.WAITING: ("⏳ esperando algo de fuera", "nada por ahora"),
    WorkItemState.NEEDS_DECISION: (
        "🟡 detenido: necesita una decisión tuya",
        "**decide aquí**, en un comentario de esta incidencia",
    ),
    WorkItemState.PAUSED: ("⏸️ en pausa", "nada por ahora"),
    WorkItemState.FAILED_SAFELY: (
        "🔴 detenido de forma segura",
        "lee el diagnóstico y decide si se reanuda",
    ),
    WorkItemState.CANCELLED: ("⬛ cancelado", "nada: esto está cerrado"),
    WorkItemState.DELIVERED: ("✅ entregado", "nada: esto está cerrado"),
}

#: El único estado en que la pelota está en el tejado del propietario sin que
#: el motor esté detenido: el trabajo está hecho y falta su autorización.
_ESPERA_FUSION = "**fusiona** en un comentario, si lo apruebas"


def _fila(clave: str, valor: str | None) -> str | None:
    return f"| {clave} | {valor} |" if valor else None


def _recorte(texto: str, limite: int = 400) -> str:
    """Recorta por palabras: un objetivo entero puede ocupar veinte líneas."""
    limpio = " ".join(texto.split())
    if len(limpio) <= limite:
        return limpio
    return limpio[:limite].rsplit(" ", 1)[0] + "…"


def _linea_del_ciclo(espejo: MirroredWorkItem) -> str:
    """El recorrido de fases con la actual en negrita, en una línea."""
    if espejo.fase is None:
        return "_El ciclo no ha empezado, o sus etiquetas no dicen en qué fase está._"
    if espejo.fase is WorkItemPhase.REPARAR:
        pasos = [f"`{fase.value}`" for fase in _RECORRIDO]
        return (
            " → ".join(pasos)
            + "  \n**Ahora mismo está en `reparar`**, que es la vuelta de `revisar` a "
            "`comprobar`: se corrige lo señalado y se vuelve a comprobar."
        )
    return " → ".join(
        f"**`{fase.value}`**" if fase is espejo.fase else f"`{fase.value}`" for fase in _RECORRIDO
    )


def _comprobado(espejo: MirroredWorkItem) -> list[str]:
    """Qué se ha comprobado ya, con el dato que lo sostiene."""
    lineas: list[str] = []
    if espejo.eventos_quality:
        ultimo = espejo.eventos_quality[-1]
        racha = (
            f", racha de fallos consecutivos: **{espejo.fallos_quality_consecutivos}**"
            if espejo.fallos_quality_consecutivos
            else ""
        )
        lineas.append(
            f"- **Quality**: {len(espejo.eventos_quality)} ejecución(es) observada(s); "
            f"la última, `{ultimo.conclusion}` sobre `{ultimo.head[:7] or 'sin head'}`{racha}."
        )
    else:
        lineas.append("- **Quality**: ninguna ejecución observada todavía.")
    if espejo.rondas:
        ronda = espejo.rondas[-1]
        lineas.append(
            f"- **Revisión**: ronda **{ronda.numero}**, con **{ronda.pendientes}** "
            f"hallazgo(s) pendiente(s) (gravedad total {ronda.gravedad_total}) sobre "
            f"`{ronda.head[:7] or 'sin head'}`."
        )
    else:
        lineas.append("- **Revisión**: ninguna ronda registrada todavía.")
    return lineas


def generar_tablero(declarado: CuerpoDeclarado, espejo: MirroredWorkItem, *, numero: int) -> str:
    """El texto del comentario-tablero. Puro: solo depende de lo que recibe.

    ``declarado`` sale de ``leer_cuerpo_declarado`` sobre el cuerpo de la
    incidencia; ``espejo``, de ``leer_y_proyectar_work_item``. Los dos se
    calculan ya en cada pasada y ninguno se lee para enseñárselo a nadie.
    """
    if espejo.etiquetas_contradictorias:
        estado_texto = "⚠️ **sus etiquetas de estado se contradicen**"
        espera = "míralo: el motor no puede decidir qué estado tiene"
    elif espejo.estado is None:
        estado_texto = "sin etiqueta de estado reconocida"
        espera = "nada por ahora"
    else:
        estado_texto, espera = _LECTURA[espejo.estado]
        if "sirius:ready-for-merge" in espejo.etiquetas:
            estado_texto = "🟢 listo para fusionar"
            espera = _ESPERA_FUSION
    if espejo.cerrada:
        estado_texto += " · incidencia **cerrada**"

    lineas = [
        MARCADOR,
        "",
        f"## 🗒️ Tablero de la incidencia #{numero}",
        "",
        "> Un solo comentario, que el motor reescribe en cada cambio de estado",
        "> (ADR-175). Es la foto de **ahora**; la película entera son los demás",
        "> comentarios, que no se tocan. Todo lo de aquí sale del cuerpo de la",
        "> incidencia y de sus etiquetas y comentarios de confianza: el motor no",
        "> añade nada que no se pueda comprobar más abajo.",
        "",
        f"**Ahora mismo:** {estado_texto}",
        "",
        f"**Lo que se espera de ti:** {espera}.",
        "",
    ]
    if espejo.diagnostico_fallo:
        lineas += [
            "> **Por qué se detuvo:** " + _recorte(espejo.diagnostico_fallo, 600),
            "",
        ]

    filas = [
        f
        for f in (
            _fila("Encargo", f"`{declarado.work_id}`" if declarado.work_id else None),
            _fila("Bloque", declarado.bloque),
            _fila("Objetivo", _recorte(declarado.objetivo) if declarado.objetivo else None),
            _fila("Entregable", _recorte(declarado.entregable) if declarado.entregable else None),
            _fila(
                "Fuera de alcance",
                _recorte(declarado.fuera_de_alcance) if declarado.fuera_de_alcance else None,
            ),
            _fila(
                "Criterio de terminado",
                _recorte(declarado.criterio_terminado) if declarado.criterio_terminado else None,
            ),
            _fila("Rama base", f"`{declarado.rama_base}`" if declarado.rama_base else None),
        )
        if f is not None
    ]
    if filas:
        lineas += ["| Qué se pidió | |", "|---|---|", *filas, ""]
    else:
        lineas += [
            "_El cuerpo de esta incidencia no declara ninguna de las secciones que el",
            "motor escribe al despachar._",
            "",
        ]

    if declarado.plan:
        lineas += ["**El plan declarado:**", ""]
        lineas += [f"{i}. {_recorte(paso, 200)}" for i, paso in enumerate(declarado.plan, start=1)]
        lineas.append("")

    lineas += [
        "**Por dónde va el ciclo:**",
        "",
        _linea_del_ciclo(espejo),
        "",
        "**Qué se ha comprobado:**",
        "",
        *_comprobado(espejo),
        "",
        "**Dónde está la evidencia:**",
        "",
        *_evidencia(espejo),
    ]
    return "\n".join(lineas) + "\n"


def _evidencia(espejo: MirroredWorkItem) -> Sequence[str]:
    lineas = []
    if espejo.pr_url:
        lineas.append(f"- Pull Request: {espejo.pr_url}")
    else:
        lineas.append("- Pull Request: todavía no hay ninguna enlazada.")
    lineas.append(
        f"- Último head observado: `{espejo.head_sha}`."
        if espejo.head_sha
        else "- Último head observado: ninguno."
    )
    etiquetas = ", ".join(f"`{e}`" for e in sorted(espejo.etiquetas)) or "ninguna"
    lineas.append(f"- Etiquetas vigentes: {etiquetas}.")
    lineas.append(f"- Leído de: {espejo.origen.fuente}.")
    return lineas
