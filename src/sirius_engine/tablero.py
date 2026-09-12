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

import re
from collections.abc import Sequence

from sirius_engine.domain.mirror import MirroredWorkItem
from sirius_engine.domain.work_item import WorkItemPhase, WorkItemState
from sirius_engine.issue_body_parsing import CuerpoDeclarado
from sirius_engine.mirror_projection import _PR_ABIERTA_RE, _SHA_MARKER_RE

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


#: Lo que se neutraliza SIN que el espejo tenga nada que decir: la apertura de
#: comentario HTML y la valla de código. Son la forma de TODOS los marcadores
#: `sirius-*` -quality, verdict, round, notification, resume, stop- de una vez,
#: así que el marcador que alguien invente mañana también cae aquí.
_NEUTRALIZACIONES: tuple[tuple[str, str], ...] = (
    ("<!--", "&lt;!--"),
    ("```", "'''"),
)

#: Y lo que el espejo lee SIN comentario HTML, tomado de **sus propias
#: expresiones**, no de una copia.
#:
#: La copia es exactamente lo que falló en la tercera ronda de revisión: este
#: módulo tenía su propio patrón para `Head/Merge SHA:`, con un `\b` delante
#: que el del espejo no tiene. Resultado: `xHead SHA: deadbeef1234` pasaba el
#: neutralizador intacto y el lector sacaba de ahí un SHA, sustituyendo al de
#: verdad. Dos expresiones para la misma cosa acaban divergiendo siempre; la
#: única forma de que no diverjan es que sea **una**.
#:
#: Importarlas de `mirror_projection` ata las dos puntas: si mañana el espejo
#: aprende a leer otra forma, el neutralizador la neutraliza el mismo día, sin
#: que nadie tenga que acordarse.
_LEIDAS_POR_EL_ESPEJO: tuple[re.Pattern[str], ...] = (
    _SHA_MARKER_RE,
    _PR_ABIERTA_RE,
)


#: El blanco que separa la palabra clave del resto -`Head SHA:`, `PR abierta:`-
#: es el MISMO `\s` del lector, del mismo motor de expresiones; no el espacio
#: ASCII. La cuarta ronda de revisión encontró que aquí se sustituía el espacio
#: a secas: un tabulador real entre `Head` y `SHA:` lo acepta `\s+` y pasaba de
#: largo en los campos que no se recortan. Es la misma familia que la tercera
#: ronda -el neutralizador con una idea PROPIA de lo que el lector reconoce-,
#: y por eso :func:`_neutralizar` ya no se fía de su sustitución: termina
#: preguntándole al propio lector.
_BLANCO = re.compile(r"\s+")


class NeutralizacionIncompletaError(ValueError):
    """Quedó una forma que el espejo aún lee. Ese tablero NO se publica.

    Con los lectores de hoy no puede ocurrir -las dos formas textuales llevan
    un blanco antes de los dos puntos y ese blanco es lo que se rompe-, y la
    prueba que lo fija recorre la clase entera de blancos del lector. Existe
    para el lector que alguien añada mañana con una forma que romper el primer
    blanco no toque: ese día el tablero de esa incidencia se queda como estaba,
    con un aviso en el registro, en vez de publicar algo de lo que el motor
    sacaría un hecho.
    """


def _romper_el_primer_blanco(coincidencia: re.Match[str]) -> str:
    """`Head SHA: abc` -> `Head-SHA: abc`. Se lee igual y ya no coincide.

    Un guion en el primer blanco basta para que ninguna de las expresiones del
    espejo vuelva a encontrar la forma -las dos exigen blanco ahí- y deja el
    texto perfectamente legible para la persona que abra la incidencia. No se
    borra nada: lo que ponía se sigue viendo.
    """
    return _BLANCO.sub("-", coincidencia.group(0), count=1)


def _neutralizar(texto: str) -> str:
    """Le quita el poder de marcador a un texto, sin quitarle el sentido.

    Y lo COMPRUEBA antes de devolverlo, con los ojos del espejo: que no quede
    apertura de comentario HTML ni coincidencia de ninguna de sus expresiones.
    Si queda, se niega. Es lo que hace imposible -no improbable- que este
    módulo vuelva a divergir del lector sin que se note: las dos rondas
    anteriores fueron exactamente eso, y una divergencia que se ve en el
    registro se arregla; una que publica en silencio se cree.
    """
    for viejo, nuevo in _NEUTRALIZACIONES:
        texto = texto.replace(viejo, nuevo)
    for patron in _LEIDAS_POR_EL_ESPEJO:
        texto = patron.sub(_romper_el_primer_blanco, texto)
    if "<!--" in texto:
        raise NeutralizacionIncompletaError("queda una apertura de comentario HTML")
    for patron in _LEIDAS_POR_EL_ESPEJO:
        resto = patron.search(texto)
        if resto is not None:
            raise NeutralizacionIncompletaError(
                f"el espejo aún leería {resto.group(0)!r} (patrón {patron.pattern!r})"
            )
    return texto


def _fila(clave: str, valor: str | None) -> str | None:
    return f"| {clave} | {valor} |" if valor else None


def _ajeno(texto: str, limite: int = 400) -> str:
    """Recorta por palabras: un objetivo entero puede ocupar veinte líneas.

    **Ya no neutraliza nada**, y eso es el arreglo de la segunda ronda de
    revisión. La primera versión neutralizaba aquí, en el punto de uso, y con
    eso tres campos -``work_id``, ``bloque`` y ``rama_base``- se quedaron
    fuera por no pasar por esta función: reproducido, el tablero republicaba
    tres marcadores y el espejo sacaba de él tres ejecuciones de Quality que
    nunca ocurrieron.

    Escapar en cada sitio exige acordarse en cada sitio, y ese es el mismo
    fallo que este repositorio lleva todo el día encontrando. Ahora se
    neutraliza **una vez, sobre el texto entero**, al final de
    :func:`generar_tablero`: ningún campo puede quedarse fuera, ni los de hoy
    ni los que alguien añada mañana.

    **El agujero, medido el 12-09-2026 antes de cerrarlo.** El tablero lo
    publica ``github-actions[bot]``, que es un autor DE CONFIANZA, y el espejo
    reconstruye el estado del encargo leyendo los comentarios de confianza
    (``_texto_cronologico_de_confianza``). Copiar el objetivo tal cual bastaba
    para que un ``sirius-quality`` escrito en el cuerpo de la incidencia
    acabara republicado por el bot y releído como una ejecución de Quality que
    nunca ocurrió: reproducido, ``_interpretar_eventos_quality`` devolvía
    ``EventoQuality(head=..., conclusion='success')`` a partir del tablero. Lo
    mismo valía para ``sirius-verdict``, ``sirius-round`` y
    ``sirius-notification``, que acreditan transiciones de estado.

    """
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
            f"la última, `{ultimo.conclusion}` sobre "
            f"`{ultimo.head[:7] or 'sin head'}`{racha}."
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
            "> **Por qué se detuvo:** " + _ajeno(espejo.diagnostico_fallo, 600),
            "",
        ]

    filas = [
        f
        for f in (
            _fila("Encargo", f"`{declarado.work_id}`" if declarado.work_id else None),
            _fila("Bloque", declarado.bloque),
            _fila("Objetivo", _ajeno(declarado.objetivo) if declarado.objetivo else None),
            _fila("Entregable", _ajeno(declarado.entregable) if declarado.entregable else None),
            _fila(
                "Fuera de alcance",
                _ajeno(declarado.fuera_de_alcance) if declarado.fuera_de_alcance else None,
            ),
            _fila(
                "Criterio de terminado",
                _ajeno(declarado.criterio_terminado) if declarado.criterio_terminado else None,
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
        lineas += [f"{i}. {_ajeno(paso, 200)}" for i, paso in enumerate(declarado.plan, start=1)]
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
    # AQUÍ, y en ningún otro sitio, se neutraliza. El marcador se añade
    # DESPUÉS: es lo único del tablero que el motor sí quiere que se
    # interprete, y pasarlo por el neutralizador lo convertiría en `&lt;!--`,
    # dejando al publicador sin nada que reconocer.
    return MARCADOR + "\n\n" + _neutralizar("\n".join(lineas)) + "\n"


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
