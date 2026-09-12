"""La memoria común, generada y nunca curada (ADR-171).

Dos vistas, dos funciones puras:

- :func:`generar_memoria` lee el árbol del repositorio —los ADR, los registros
  YAML con estado, las investigaciones y los documentos de `docs/` y de la
  raíz— y devuelve el texto de ``MEMORIA.md``. **No lee el reloj, ni la red,
  ni git**: dos llamadas sobre el mismo árbol devuelven el mismo texto, y eso
  es lo que permite que una prueba falle cuando el fichero confirmado se queda
  viejo (criterio de parada (a) de ADR-171).
- :func:`generar_desenlaces` lee el diario del motor y el de despacho y
  devuelve el texto de ``DESENLACES.md``: qué se encargó, qué salió y dónde
  está la evidencia (propuesta §6.2). Lo escribe el motor en su rama.

Ninguna de las dos resume con criterio ni data nada por su cuenta: el resumen
de un ADR es el primer párrafo de su ``## Decisión`` tal cual está escrito, y un
documento que no declara fecha sale como «sin fecha declarada». Lo que la
vista enseña pobre se arregla en la fuente, no en la vista.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

COMANDO = "sirius-memoria"
FICHERO_MEMORIA = "MEMORIA.md"
FICHERO_DESENLACES = "DESENLACES.md"
RAMA_MEMORIA = "estado-del-motor"
REPOSITORIO = "canelamoraguezandyjesus-bot/sirius"
URL_DESENLACES = f"https://github.com/{REPOSITORIO}/blob/{RAMA_MEMORIA}/{FICHERO_DESENLACES}"

CARPETA_DECISIONES = Path("docs/decisions")
CARPETA_INVESTIGACIONES = Path("docs/investigaciones")
REGISTRO_BLOQUES = Path("docs/implementation/bloques_del_motor.yml")
REGISTRO_DEFECTOS = Path("docs/audits/registro_defectos.yml")

LONGITUD_RESUMEN = 240
LONGITUD_OBJETIVO = 110
LINEAS_DE_CABECERA = 20
SIN_FECHA = "sin fecha declarada"

_NOMBRE_ADR = re.compile(r"^ADR-(\d{3})-.*\.md$")
_TITULO = re.compile(r"^#\s+(.+?)\s*$")
# Guion largo, guion corto (por sus códigos: RUF001 los confunde con `-`) o guion.
_PREFIJO_ADR_EN_TITULO = re.compile("^ADR-\\d+\\s*[\u2014\u2013-]\\s*")
_ESTADO_ADR = re.compile(r"^-\s*Estado:\s*(.+?)\s*$")
_ESTADO_NORMAL = re.compile(r"[A-ZÁÉÍÓÚÑ]+(?:\s+por\s+ADR-\d+)?")
_FECHA_ADR = re.compile(r"^-\s*Fecha:\s*(\d{4}-\d{2}-\d{2})")
_FECHA_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_FECHA_DMA = re.compile(r"\b(\d{2})-(\d{2})-(\d{4})\b")
_LINEA_CON_FECHA = re.compile(r"fecha|actualiz", re.IGNORECASE)
_MARCADOR_DE_LISTA = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_ENFASIS = re.compile(r"\*\*|__")
_ESPACIOS = re.compile(r"\s+")
_URL_DE_RUN = re.compile(r"https://github\.com/\S+/actions/runs/\d+\S*")

#: Desde este ADR, declarar la lección es obligatorio (ADR-174). Los anteriores
#: quedan exentos a propósito: rellenarlos hoy sería escribir de memoria lo que
#: en su día no se capturó, que es justo lo que este mecanismo existe para no
#: volver a hacer.
PRIMER_ADR_CON_LECCION = 174

#: El encabezado del bloque, EXACTO: `_seccion` compara la línea entera, y un
#: encabezado aproximado deja la lección invisible sin que nadie se entere.
TITULO_LECCION = "## La lección"

#: Las tres claves de una lección, y la cuarta que declara que no hay ninguna.
CLAVE_FAMILIA = "familia"
CLAVE_REPETIRIA = "sin esto se repetiría"
CLAVE_GUARDIAN = "lo hace cumplir"
CLAVE_SIN_LECCION = "ninguna"

#: Lo que vale como «todavía no hay prueba que lo haga cumplir»: la razón va
#: detrás, y sin razón no cuenta.
SIN_GUARDIAN = "ninguna prueba"

_ITEM_DE_LECCION = re.compile(r"^\s*-\s*([^:]+?)\s*:\s*(.*?)\s*$")
_FAMILIA_VALIDA = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


# --- Lo que se lee del árbol ------------------------------------------------


@dataclass(frozen=True, slots=True)
class Decision:
    """Una fila de la tabla de decisiones: lo que un ADR dice de sí mismo."""

    numero: int
    ruta: str
    titulo: str
    fecha: str
    estado: str
    resumen: str
    leccion: Leccion | None = None


@dataclass(frozen=True, slots=True)
class Leccion:
    """Lo que un ADR declara que alguien repetiría sin él (ADR-174).

    ``familia`` vacía con ``sin_leccion`` escrito es la forma «este ADR no dejó
    ninguna lección, y esta es la razón»: una declaración explícita, que no es
    lo mismo que no haber escrito nada.
    """

    familia: str
    repetiria: str
    guardian: str
    sin_leccion: str = ""

    @property
    def tiene_guardian(self) -> bool:
        """Si una prueba la hace cumplir, o solo es prosa que alguien debe recordar."""
        return bool(self.familia) and not self.guardian.startswith(SIN_GUARDIAN)


@dataclass(frozen=True, slots=True)
class Documento:
    """Un documento de `docs/` o de la raíz, con la fecha que DECLARA."""

    ruta: str
    titulo: str
    fecha: str | None
    estado: str | None = None
    caduca_con: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Entrada:
    """Una entrada de un registro YAML con estado (bloques, defectos)."""

    identificador: str
    titulo: str
    estado: str


@dataclass(frozen=True, slots=True)
class Encargo:
    """Un WorkItem del diario, reducido a lo que la memoria necesita."""

    work_id: str
    clase: str
    estado: str
    fase: str
    creado: str
    ultimo_suceso: str
    objetivo: str
    incidencia: int | None
    merge_sha: str | None
    run: str | None
    sucesos: int


@dataclass(frozen=True, slots=True)
class Arbol:
    """Todo lo que la vista de conocimiento lee, ya interpretado."""

    decisiones: tuple[Decision, ...]
    bloques: tuple[Entrada, ...]
    defectos: tuple[Entrada, ...]
    investigaciones: tuple[Documento, ...]
    documentos: tuple[Documento, ...]
    avisos: tuple[str, ...] = field(default_factory=tuple)


# --- Leer ADR ----------------------------------------------------------------


def _seccion(lineas: Sequence[str], encabezado: str) -> list[str]:
    """Las líneas entre `## encabezado` y el siguiente `## `."""
    dentro = False
    cuerpo: list[str] = []
    for linea in lineas:
        if linea.startswith("## "):
            if dentro:
                break
            dentro = linea.strip() == encabezado
            continue
        if dentro:
            cuerpo.append(linea)
    return cuerpo


def _primer_parrafo(lineas: Iterable[str]) -> str:
    """El primer párrafo de prosa: se saltan citas, títulos, comentarios y tablas.

    Si el párrafo termina en dos puntos, lo que anuncia es la lista que le
    sigue, y se incluye: «Tres piezas, y ninguna más:» a secas no resume nada.
    """
    parrafo: list[str] = []
    en_lista_anunciada = False
    for linea in lineas:
        texto = linea.strip()
        if not texto:
            if parrafo and parrafo[-1].endswith(":") and not en_lista_anunciada:
                en_lista_anunciada = True
                continue
            if parrafo:
                break
            continue
        if texto.startswith(("#", ">", "<!--", "|", "```")):
            if parrafo:
                break
            continue
        if en_lista_anunciada and not _MARCADOR_DE_LISTA.match(texto):
            break
        parrafo.append(_MARCADOR_DE_LISTA.sub("", texto))
    return " ".join(parrafo)


def _limpiar(texto: str) -> str:
    return _ESPACIOS.sub(" ", _ENFASIS.sub("", texto)).strip()


def _recortar(texto: str, longitud: int) -> str:
    if len(texto) <= longitud:
        return texto
    corte = texto.rfind(" ", 0, longitud)
    if corte <= 0:
        corte = longitud
    return texto[:corte].rstrip(" ,;:") + "…"


def _titulo_de(lineas: Sequence[str]) -> str | None:
    for linea in lineas:
        coincidencia = _TITULO.match(linea)
        if coincidencia:
            return coincidencia.group(1)
    return None


def _estado_normalizado(texto: str) -> str:
    coincidencia = _ESTADO_NORMAL.match(texto)
    return coincidencia.group(0) if coincidencia else _recortar(texto, 40)


def leer_leccion(lineas: Sequence[str]) -> Leccion | None:
    """La lección que un ADR declara, o ``None`` si no declara ninguna.

    ``None`` es «no hay bloque», que no es lo mismo que «no hay lección»: eso
    último se dice con ``- ninguna: <razón>`` y produce una ``Leccion`` con
    ``familia`` vacía.
    """
    seccion = _seccion(lineas, TITULO_LECCION)
    if not seccion:
        return None
    campos: dict[str, str] = {}
    for linea in seccion:
        if (m := _ITEM_DE_LECCION.match(linea)) is not None:
            campos.setdefault(m.group(1).strip().lower(), _limpiar(m.group(2)).strip("`"))
    if (sin_leccion := campos.get(CLAVE_SIN_LECCION)) and not campos.get(CLAVE_FAMILIA):
        return Leccion(familia="", repetiria="", guardian="", sin_leccion=sin_leccion)
    return Leccion(
        familia=campos.get(CLAVE_FAMILIA, ""),
        repetiria=campos.get(CLAVE_REPETIRIA, ""),
        guardian=campos.get(CLAVE_GUARDIAN, ""),
        sin_leccion=campos.get(CLAVE_SIN_LECCION, ""),
    )


def problemas_de_la_leccion(texto: str, *, raiz: Path | None = None) -> tuple[str, ...]:
    """Qué le falta al bloque de lección de un ADR; vacío si está bien (ADR-174).

    Es EL detector: lo ejecutan la vista generada y la batería que obliga a
    declarar, y es lo que las pruebas de mutación rompen a propósito. Vive aquí
    y no en la batería por la lección de ADR-172: una guardia que no ejecuta el
    detector que dice probar no prueba nada.

    Con ``raiz`` comprueba además que la prueba citada exista de verdad; sin
    ella se queda en lo que el texto dice, que es lo que necesita cualquiera que
    quiera comprobar el formato sin árbol delante.
    """
    lineas = texto.splitlines()
    leccion = leer_leccion(lineas)
    if leccion is None:
        return (
            f"no trae el bloque «{TITULO_LECCION}»: sin él nadie sabrá qué se "
            "repetiría sin este ADR",
        )
    if leccion.sin_leccion and leccion.familia:
        return (
            f"declara «{CLAVE_SIN_LECCION}» y «{CLAVE_FAMILIA}» a la vez: o hay "
            "lección o no la hay",
        )
    if leccion.sin_leccion:
        return ()
    problemas: list[str] = []
    if not leccion.familia:
        problemas.append(
            f"no declara «{CLAVE_FAMILIA}»: sin familia nadie puede contar cuántas "
            f"veces ha mordido (o declara «{CLAVE_SIN_LECCION}: <razón>»)"
        )
    elif not _FAMILIA_VALIDA.match(leccion.familia):
        problemas.append(
            f"la familia «{leccion.familia}» no es un identificador estable: en "
            "minúsculas y con guiones, para que dos ADR de la misma familia se "
            "cuenten juntos"
        )
    if not leccion.repetiria:
        problemas.append(
            f"no declara «{CLAVE_REPETIRIA}»: el criterio de captura es que sin "
            "esto alguien repetiría el error, y hay que decir cuál"
        )
    if not leccion.guardian:
        problemas.append(
            f"no declara «{CLAVE_GUARDIAN}»: o la prueba que la hace imposible, o "
            f"«{SIN_GUARDIAN}: <razón>»"
        )
    elif leccion.tiene_guardian and raiz is not None and not (raiz / leccion.guardian).exists():
        problemas.append(
            f"dice que la hace cumplir «{leccion.guardian}», y ese fichero no existe en el árbol"
        )
    return tuple(problemas)


def leer_decision(ruta: Path, raiz: Path) -> Decision | None:
    """Interpretar un ADR; `None` si el nombre no es el de un ADR."""
    coincidencia = _NOMBRE_ADR.match(ruta.name)
    if not coincidencia:
        return None
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    titulo = _titulo_de(lineas) or ruta.stem
    titulo = _PREFIJO_ADR_EN_TITULO.sub("", titulo)
    estado = "sin estado declarado"
    fecha = SIN_FECHA
    for linea in lineas[:LINEAS_DE_CABECERA]:
        if (m := _ESTADO_ADR.match(linea)) and estado == "sin estado declarado":
            estado = _estado_normalizado(m.group(1))
        if (m := _FECHA_ADR.match(linea)) and fecha == SIN_FECHA:
            fecha = m.group(1)
    resumen = _limpiar(_primer_parrafo(_seccion(lineas, "## Decisión")))
    return Decision(
        numero=int(coincidencia.group(1)),
        ruta=ruta.relative_to(raiz).as_posix(),
        titulo=_limpiar(titulo),
        fecha=fecha,
        estado=estado,
        resumen=_recortar(resumen, LONGITUD_RESUMEN) if resumen else "(sin sección Decisión)",
        leccion=leer_leccion(lineas),
    )


def leer_decisiones(raiz: Path) -> tuple[Decision, ...]:
    """Todos los ADR, de la más reciente a la más antigua; los números repetidos se listan."""
    carpeta = raiz / CARPETA_DECISIONES
    decisiones = [d for d in (leer_decision(r, raiz) for r in carpeta.glob("ADR-*.md")) if d]
    return tuple(sorted(decisiones, key=lambda d: (-d.numero, d.ruta)))


# --- Leer documentos ---------------------------------------------------------


def _fecha_declarada(lineas: Sequence[str]) -> str | None:
    """La primera fecha en una línea de cabecera que hable de fecha; ISO o DD-MM-AAAA."""
    for linea in lineas[:LINEAS_DE_CABECERA]:
        if not _LINEA_CON_FECHA.search(linea):
            continue
        if m := _FECHA_ISO.search(linea):
            return m.group(0)
        if m := _FECHA_DMA.search(linea):
            return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return None


def _portada(texto: str) -> Mapping[str, Any] | None:
    """El front matter YAML de una investigación, si lo hay."""
    if not texto.startswith("---\n"):
        return None
    _, _, resto = texto.partition("---\n")
    cuerpo, separador, _ = resto.partition("\n---")
    if not separador:
        return None
    try:
        datos = yaml.safe_load(cuerpo)
    except yaml.YAMLError:
        return None
    return datos if isinstance(datos, Mapping) else None


def _texto_de_item(item: object) -> str:
    """Un elemento de `caduca_con` como texto.

    YAML lee «los clientes MCP: cambian» como un mapa de una clave; se devuelve
    «los clientes MCP: cambian», no la repr del diccionario.
    """
    if isinstance(item, Mapping):
        return "; ".join(f"{_limpiar(str(k))}: {_limpiar(str(v))}" for k, v in item.items())
    return _limpiar(str(item))


def leer_documento(ruta: Path, raiz: Path) -> Documento:
    texto = ruta.read_text(encoding="utf-8")
    lineas = texto.splitlines()
    portada = _portada(texto)
    if portada is not None:
        caduca = portada.get("caduca_con")
        return Documento(
            ruta=ruta.relative_to(raiz).as_posix(),
            titulo=_limpiar(str(portada.get("titulo") or _titulo_de(lineas) or ruta.stem)),
            fecha=str(portada["fecha"]) if portada.get("fecha") else _fecha_declarada(lineas),
            estado=str(portada["estado"]) if portada.get("estado") else None,
            caduca_con=tuple(_texto_de_item(c) for c in caduca) if isinstance(caduca, list) else (),
        )
    return Documento(
        ruta=ruta.relative_to(raiz).as_posix(),
        titulo=_limpiar(_titulo_de(lineas) or ruta.stem),
        fecha=_fecha_declarada(lineas),
    )


def leer_documentos(raiz: Path) -> tuple[tuple[Documento, ...], tuple[Documento, ...]]:
    """(investigaciones, documentos): todo `docs/**/*.md` menos los ADR, más la raíz."""
    rutas = sorted(
        r
        for r in (raiz / "docs").rglob("*.md")
        if CARPETA_DECISIONES not in r.relative_to(raiz).parents
    )
    rutas += sorted(r for r in raiz.glob("*.md") if r.name != FICHERO_MEMORIA)
    investigaciones: list[Documento] = []
    documentos: list[Documento] = []
    for ruta in rutas:
        documento = leer_documento(ruta, raiz)
        relativa = ruta.relative_to(raiz)
        if CARPETA_INVESTIGACIONES in relativa.parents:
            investigaciones.append(documento)
        else:
            documentos.append(documento)
    return tuple(investigaciones), tuple(documentos)


# --- Leer registros YAML ------------------------------------------------------


def leer_registro(ruta: Path, clave: str) -> tuple[Entrada, ...]:
    """Las entradas de un registro YAML `clave: [ {id, titulo, estado}, ... ]`."""
    if not ruta.is_file():
        return ()
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, Mapping) or not isinstance(datos.get(clave), list):
        return ()
    entradas: list[Entrada] = []
    for elemento in datos[clave]:
        if not isinstance(elemento, Mapping):
            continue
        entradas.append(
            Entrada(
                identificador=str(elemento.get("id", "?")),
                titulo=_limpiar(str(elemento.get("titulo", ""))),
                estado=str(elemento.get("estado", "sin estado")),
            )
        )
    return tuple(entradas)


# --- El árbol entero ----------------------------------------------------------


def leer_arbol(raiz: Path) -> Arbol:
    investigaciones, documentos = leer_documentos(raiz)
    avisos: list[str] = []
    if not (raiz / REGISTRO_BLOQUES).is_file():
        avisos.append(f"no existe `{REGISTRO_BLOQUES.as_posix()}`")
    if not (raiz / REGISTRO_DEFECTOS).is_file():
        avisos.append(f"no existe `{REGISTRO_DEFECTOS.as_posix()}`")
    return Arbol(
        decisiones=leer_decisiones(raiz),
        bloques=leer_registro(raiz / REGISTRO_BLOQUES, "bloques"),
        defectos=leer_registro(raiz / REGISTRO_DEFECTOS, "defectos"),
        investigaciones=investigaciones,
        documentos=documentos,
        avisos=tuple(avisos),
    )


# --- Escribir la vista de conocimiento ---------------------------------------


def _celda(texto: str) -> str:
    return texto.replace("|", "\\|").replace("\n", " ")


def _tabla(cabeceras: Sequence[str], filas: Iterable[Sequence[str]]) -> list[str]:
    lineas = [
        "| " + " | ".join(cabeceras) + " |",
        "|" + "|".join("---" for _ in cabeceras) + "|",
    ]
    lineas.extend("| " + " | ".join(_celda(c) for c in fila) + " |" for fila in filas)
    return lineas


def _recuento(entradas: Iterable[Entrada]) -> str:
    cuenta: dict[str, int] = {}
    for entrada in entradas:
        cuenta[entrada.estado] = cuenta.get(entrada.estado, 0) + 1
    return ", ".join(f"{n} {estado}" for estado, n in sorted(cuenta.items())) or "ninguna entrada"


def _carpeta_de(ruta: str) -> str:
    return ruta.rpartition("/")[0] or "(raíz)"


def _lineas_de_lecciones(decisiones: Sequence[Decision]) -> list[str]:
    """La tabla de familias, y debajo las lecciones de cada una (ADR-174).

    Determinista y sin más fuente que los propios ADR: una familia existe
    porque un ADR la declara, y muerde tantas veces como ADR la declaren.
    """
    con_leccion = [
        (d, d.leccion) for d in decisiones if d.leccion is not None and d.leccion.familia
    ]
    if not con_leccion:
        return [
            "*Todavía no hay ninguna lección declarada.* La primera la traerá el primer",
            f"ADR desde el {PRIMER_ADR_CON_LECCION} que encuentre un fallo repetible.",
        ]
    familias: dict[str, list[tuple[Decision, Leccion]]] = {}
    for decision, leccion in con_leccion:
        familias.setdefault(leccion.familia, []).append((decision, leccion))
    orden = sorted(familias.items(), key=lambda par: (-len(par[1]), par[0]))
    lineas = list(
        _tabla(
            ("Familia", "Veces", "Hay prueba que la haga cumplir", "ADR"),
            (
                (
                    f"`{familia}`",
                    str(len(entradas)),
                    ("sí" if all(le.tiene_guardian for _, le in entradas) else "no en todas"),
                    ", ".join(f"[{d.numero:03d}]({d.ruta})" for d, _ in entradas),
                )
                for familia, entradas in orden
            ),
        )
    )
    for familia, entradas in orden:
        lineas += ["", f"### `{familia}`", ""]
        for decision, leccion in sorted(entradas, key=lambda par: -par[0].numero):
            guardian = (
                f"lo hace cumplir `{leccion.guardian}`"
                if leccion.tiene_guardian
                else f"sin prueba que lo haga cumplir: {leccion.guardian}"
            )
            lineas.append(
                f"- **[ADR-{decision.numero:03d}]({decision.ruta})** — "
                f"{leccion.repetiria} ({guardian})."
            )
    sin_leccion = [d for d in decisiones if d.leccion is not None and d.leccion.sin_leccion]
    if sin_leccion:
        lineas += [
            "",
            f"Y **{len(sin_leccion)}** ADR declaran expresamente que no dejaron lección: "
            + ", ".join(f"[{d.numero:03d}]({d.ruta})" for d in sin_leccion[:12])
            + ("…" if len(sin_leccion) > 12 else "")
            + ".",
        ]
    return lineas


def generar_memoria(raiz: Path) -> str:
    """El texto de `MEMORIA.md` para este árbol. Determinista: solo depende del árbol."""
    arbol = leer_arbol(raiz)
    sin_fecha = sum(1 for d in arbol.documentos if d.fecha is None)
    lineas: list[str] = [
        "# Memoria común del proyecto Sirius",
        "",
        f"> **Generado por `uv run {COMANDO} conocimiento` a partir del árbol del repositorio.**",
        "> No se edita a mano: `tests/engine/test_memoria.py` falla si este fichero no",
        "> coincide con lo que el generador produce. Si cambias un ADR, un documento de",
        "> `docs/` o un registro, vuelve a ejecutar el comando y confirma el resultado en",
        "> la misma PR (ADR-171).",
        "",
        "## Cómo se usa",
        "",
        "- **Léela entera antes de abrir nada más.** Es la memoria del trabajo: qué se",
        "  decidió, qué registros hay y en qué estado, qué documentos existen y de",
        "  cuándo. Desde aquí, abre solo lo que la tarea necesite.",
        "- **Los desenlaces del motor** —qué se encargó, qué salió, dónde está la",
        f"  evidencia— están en la rama `{RAMA_MEMORIA}`, fichero `{FICHERO_DESENLACES}`",
        f"  ({URL_DESENLACES}), que el motor escribe solo tras cada reflejo. Se leen con",
        f"  `git fetch origin {RAMA_MEMORIA} && "
        f"git show origin/{RAMA_MEMORIA}:{FICHERO_DESENLACES}`.",
        "- **Regla de conflicto (ADR-171).** Si el diario del motor y un documento",
        "  discrepan sobre un trabajo, manda el diario. Si dos documentos discrepan",
        "  entre sí, manda el más reciente fusionado en `main`.",
        "- **Qué no se puede hacer** está en `AGENTS.md` («Reglas obligatorias» y",
        "  «Criterio de parada») y en el contrato operativo de automatización. Aquí no",
        "  se copian: un dato, un dueño.",
        "- **Todo lo que hay aquí es público**: el repositorio lo es a propósito",
        "  (ADR-171). Quien escribe en él lo sabe.",
        "",
        "## Qué hay, en números",
        "",
        f"- Decisiones (ADR): **{len(arbol.decisiones)}**.",
        f"- Bloques del motor: {_recuento(arbol.bloques)}.",
        f"- Defectos registrados: {_recuento(arbol.defectos)}.",
        f"- Investigaciones: **{len(arbol.investigaciones)}** (fotos con fecha; caducan).",
        f"- Documentos: **{len(arbol.documentos)}**, de los que **{sin_fecha}** no declaran fecha.",
    ]
    for aviso in arbol.avisos:
        lineas.append(f"- ⚠ {aviso}.")
    lineas += [
        "",
        "## Qué se decidió: los ADR, del más reciente al más antiguo",
        "",
        "El resumen es el primer párrafo de la sección «Decisión» de cada ADR, tal cual",
        "está escrito. Si sale pobre, se arregla en el ADR.",
        "",
        *_tabla(
            ("ADR", "Fecha", "Estado", "Decisión", "Resumen"),
            (
                (
                    f"[{d.numero:03d}]({d.ruta})",
                    d.fecha,
                    d.estado,
                    d.titulo,
                    d.resumen,
                )
                for d in arbol.decisiones
            ),
        ),
        "",
        "## Las lecciones, por familia (ADR-174)",
        "",
        "Lo que alguien repetiría sin cada ADR, agrupado por familia de fallo y",
        "contado por la máquina. **La cuenta no la lleva nadie**: un número escrito a",
        "mano caduca en silencio -`AGENTS.md` decía «seis veces» cuando ya iban ocho-.",
        f"Declararla es obligatorio desde ADR-{PRIMER_ADR_CON_LECCION}; los anteriores",
        "quedan exentos, así que esta vista crece desde cero en vez de nacer rellenada",
        "de memoria.",
        "",
        *_lineas_de_lecciones(arbol.decisiones),
        "",
        "## Los bloques del motor",
        "",
        f"Registro: `{REGISTRO_BLOQUES.as_posix()}`. No confundir con los 16 bloques del",
        "producto Sirius 0.1, cerrados el 10-08-2026.",
        "",
        *_tabla(
            ("Bloque", "Estado", "Título"),
            ((b.identificador, b.estado, b.titulo) for b in arbol.bloques),
        ),
        "",
        "## Los defectos registrados",
        "",
        f"Registro: `{REGISTRO_DEFECTOS.as_posix()}`. Solo se listan los que no están",
        "cerrados; el recuento completo está arriba.",
        "",
    ]
    abiertos = [d for d in arbol.defectos if d.estado != "cerrado"]
    if abiertos:
        lineas += _tabla(
            ("Defecto", "Estado", "Título"),
            ((d.identificador, d.estado, d.titulo) for d in abiertos),
        )
    else:
        lineas.append("Ningún defecto sin cerrar.")
    lineas += [
        "",
        "## Las investigaciones: fotos con fecha, que caducan",
        "",
        "Una investigación sirve para decidir qué preguntar, nunca para responder sobre",
        "algo vivo (`AGENTS.md`). Cada una declara de qué depende para caducar.",
        "",
        *_tabla(
            ("Fecha", "Estado", "Investigación", "Caduca con"),
            (
                (
                    i.fecha or SIN_FECHA,
                    i.estado or "—",
                    f"[{i.titulo}]({i.ruta})",
                    "; ".join(i.caduca_con) or "—",
                )
                for i in arbol.investigaciones
            ),
        ),
        "",
        "## Los documentos, carpeta a carpeta",
        "",
        "La fecha es la que cada documento **declara** en su cabecera; la vista no data",
        "nada por su cuenta. «Sin fecha declarada» es un aviso, no un dato.",
    ]
    carpeta_actual = None
    for documento in arbol.documentos:
        carpeta = _carpeta_de(documento.ruta)
        if carpeta != carpeta_actual:
            carpeta_actual = carpeta
            lineas += ["", f"### `{carpeta}`", ""]
            lineas += _tabla(("Fecha", "Documento"), ())
        lineas.append(
            f"| {documento.fecha or SIN_FECHA} | [{_celda(documento.titulo)}]({documento.ruta}) |"
        )
    lineas.append("")
    return "\n".join(lineas)


def comprobar_memoria(raiz: Path) -> str | None:
    """`None` si `MEMORIA.md` coincide con lo generado; si no, qué hacer."""
    fichero = raiz / FICHERO_MEMORIA
    if not fichero.is_file():
        return f"no existe `{FICHERO_MEMORIA}`; genéralo con `uv run {COMANDO} conocimiento`."
    if fichero.read_text(encoding="utf-8") == generar_memoria(raiz):
        return None
    return (
        f"`{FICHERO_MEMORIA}` no coincide con lo que produce el generador a partir del "
        f"árbol: hay un ADR, un documento o un registro que cambió sin regenerarla, o "
        f"alguien la editó a mano. Ejecuta `uv run {COMANDO} conocimiento` y confirma el "
        f"resultado."
    )


def escribir_memoria(raiz: Path) -> Path:
    fichero = raiz / FICHERO_MEMORIA
    fichero.write_text(generar_memoria(raiz), encoding="utf-8", newline="\n")
    return fichero


# --- La vista de desenlaces ---------------------------------------------------


def _lineas_json(ruta: Path) -> list[Mapping[str, Any]]:
    entradas: list[Mapping[str, Any]] = []
    for numero, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), start=1):
        if not linea.strip():
            continue
        try:
            dato = json.loads(linea)
        except json.JSONDecodeError as error:
            raise ValueError(f"{ruta}:{numero}: no es JSON ({error.msg})") from error
        if isinstance(dato, Mapping):
            entradas.append(dato)
    return entradas


def _texto(valor: object) -> str:
    return valor if isinstance(valor, str) else ""


def _incidencias_despachadas(despacho: Path | None) -> dict[str, int]:
    if despacho is None or not despacho.is_file():
        return {}
    incidencias: dict[str, int] = {}
    for entrada in _lineas_json(despacho):
        work_id = entrada.get("work_id")
        numero = entrada.get("numero_incidencia")
        if isinstance(work_id, str) and isinstance(numero, int):
            incidencias[work_id] = numero
    return incidencias


def leer_encargos(
    diario: Path, despacho: Path | None = None
) -> tuple[tuple[Encargo, ...], int, str]:
    """(encargos del más reciente al más antiguo, sucesos leídos, último `occurred_at`)."""
    incidencias = _incidencias_despachadas(despacho)
    ultimo_por_encargo: dict[str, Mapping[str, Any]] = {}
    sucesos_por_encargo: dict[str, int] = {}
    total = 0
    ultimo_instante = ""
    for suceso in _lineas_json(diario):
        total += 1
        ultimo_instante = max(ultimo_instante, _texto(suceso.get("occurred_at")))
        if suceso.get("aggregate_type") != "work_item":
            continue
        work_id = _texto(suceso.get("aggregate_id"))
        if not work_id:
            continue
        sucesos_por_encargo[work_id] = sucesos_por_encargo.get(work_id, 0) + 1
        anterior = ultimo_por_encargo.get(work_id)
        if anterior is None or _texto(suceso.get("occurred_at")) >= _texto(
            anterior.get("occurred_at")
        ):
            ultimo_por_encargo[work_id] = suceso
    encargos: list[Encargo] = []
    for work_id, suceso in ultimo_por_encargo.items():
        entidad = suceso.get("entity")
        if not isinstance(entidad, Mapping):
            entidad = {}
        resultado = entidad.get("resultado")
        if not isinstance(resultado, Mapping):
            resultado = {}
        numero = resultado.get("numero_incidencia")
        incidencia = numero if isinstance(numero, int) else incidencias.get(work_id)
        run = _URL_DE_RUN.search(_texto(entidad.get("diagnostico")))
        objetivo = _texto(entidad.get("objetivo")).strip().splitlines()
        encargos.append(
            Encargo(
                work_id=work_id,
                clase=_texto(entidad.get("clase")) or "?",
                estado=_texto(entidad.get("estado")) or "?",
                fase=_texto(entidad.get("fase")) or "?",
                creado=_texto(entidad.get("created_at")),
                ultimo_suceso=_texto(suceso.get("occurred_at")),
                objetivo=_recortar(_limpiar(objetivo[0]) if objetivo else "", LONGITUD_OBJETIVO),
                incidencia=incidencia,
                merge_sha=_texto(resultado.get("merge_sha")) or None,
                run=run.group(0).rstrip(".,)") if run else None,
                sucesos=sucesos_por_encargo[work_id],
            )
        )
    encargos.sort(key=lambda e: (e.ultimo_suceso, e.work_id), reverse=True)
    return tuple(encargos), total, ultimo_instante


def _instante(iso: str) -> str:
    return iso[:16].replace("T", " ") + " UTC" if len(iso) >= 16 else (iso or "—")


def _evidencia(encargo: Encargo) -> str:
    partes: list[str] = []
    if encargo.incidencia is not None:
        partes.append(
            f"[#{encargo.incidencia}](https://github.com/{REPOSITORIO}/issues/{encargo.incidencia})"
        )
    if encargo.merge_sha:
        partes.append(f"fusión `{encargo.merge_sha[:7]}`")
    if encargo.run:
        partes.append(f"[run]({encargo.run})")
    return ", ".join(partes) or "—"


def generar_desenlaces(diario: Path, despacho: Path | None = None) -> str:
    """El texto de `DESENLACES.md` para este diario. Determinista: solo depende de los ficheros."""
    encargos, total, ultimo = leer_encargos(diario, despacho)
    cuenta: dict[str, int] = {}
    for encargo in encargos:
        cuenta[encargo.estado] = cuenta.get(encargo.estado, 0) + 1
    lineas = [
        "# Desenlaces del motor de Sirius",
        "",
        f"> **Generado por `uv run {COMANDO} desenlaces`** a partir de `{diario.name}`"
        + (f" y `{despacho.name}`" if despacho is not None and despacho.is_file() else "")
        + f": {total} sucesos, el último el {_instante(ultimo)}. Lo escribe el motor en la rama",
        f"> `{RAMA_MEMORIA}` tras cada reflejo (ADR-171). **El diario manda**: si un documento",
        "> dice otra cosa sobre un encargo, vale esto.",
        "",
        "## Recuento por estado",
        "",
        *_tabla(("Estado", "Encargos"), ((estado, str(n)) for estado, n in sorted(cuenta.items()))),
        "",
        "## Los encargos, del más reciente al más antiguo",
        "",
        *_tabla(
            (
                "Encargo",
                "Clase",
                "Estado / fase",
                "Creado",
                "Último suceso",
                "Objetivo",
                "Evidencia",
            ),
            (
                (
                    encargo.work_id,
                    encargo.clase,
                    f"{encargo.estado} / {encargo.fase}",
                    _instante(encargo.creado),
                    _instante(encargo.ultimo_suceso),
                    encargo.objetivo or "—",
                    _evidencia(encargo),
                )
                for encargo in encargos
            ),
        ),
        "",
    ]
    return "\n".join(lineas)


def escribir_desenlaces(diario: Path, salida: Path, despacho: Path | None = None) -> Path:
    salida.write_text(generar_desenlaces(diario, despacho), encoding="utf-8", newline="\n")
    return salida
