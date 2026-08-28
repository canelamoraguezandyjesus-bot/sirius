"""Lector canónico v0.3 · selección de tablas DOCX **por identidad**.

El lector v0.2 —conservado intacto en ``canonical_source.py``— seleccionaba
cada tabla por número de columnas y forma de fila. La auditoría demostró que
eso es frágil: el Plan de Pruebas contiene **dos** tablas de seis columnas
cuya primera columna es ``RED-\\d{3}`` —el Registro RED del §4 y el Anexo B
del §23— y ambas se mezclaban en el mismo diccionario. Que el resultado
final fuese correcto dependía del orden físico de las tablas en el fichero.

Este módulo corrige B-01:

* cada tabla se localiza por **cabecera literal + contexto canónico**; si hay
  cero o más de una candidata, falla de forma explícita (`TablaCanonicaError`);
* cada identidad declara el **número exacto de filas** y, cuando procede, el
  patrón de su primera columna: una fila añadida, perdida o duplicada falla;
* el Anexo B se comprueba en **ambas direcciones** y conserva expresamente las
  métricas canónicas de otros bloques (`B05-M16`, `B08-M25`), en vez de
  filtrarlas en silencio;
* los identificadores se validan contra su universo canónico: `RED-099`,
  `B04-M99` o `F99` no se aceptan.

Determinista: bytes fijos verificados por SHA-256 contra `MANIFEST.md`. Sin
reloj, sin red, sin aleatoriedad.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
import zipfile
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
FUENTES = RAIZ / "docs" / "architecture" / "canonical_sources"
MANIFEST = FUENTES / "MANIFEST.md"

B04 = "SIRIUS_0.2_BLOQUE_04_BUSQUEDA_Y_RECUPERACION_v1.0_APROBADO.docx"
PDP = "SIRIUS_0.2_PLAN_DE_PRUEBAS_Y_REGISTRO_EXTERNO_DE_DELEGACIONES_v1.0_APROBADO.docx"
ARQ00 = "SIRIUS_0.2_ARQ_00_MARCO_RECTOR_ARQUITECTURA_Y_MAPA_DECISIONES_v1.0_APROBADO.docx"

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class FuenteCanonicaError(RuntimeError):
    """La fuente canónica no está disponible o no coincide con su huella."""


class TablaCanonicaError(FuenteCanonicaError):
    """Una identidad de tabla no resolvió a exactamente una tabla válida."""


# ---------------------------------------------------------------------------
# 1. Lectura del DOCX en tablas con contexto
# ---------------------------------------------------------------------------


def _texto_nodo(nodo: ElementTree.Element) -> str:
    partes: list[str] = []
    for hijo in nodo.iter():
        etiqueta = hijo.tag[len(_W) :] if hijo.tag.startswith(_W) else hijo.tag
        if etiqueta == "t":
            partes.append(hijo.text or "")
        elif etiqueta == "tab":
            partes.append("\t")
        elif etiqueta == "br":
            partes.append("\n")
    return "".join(partes)


@dataclass(frozen=True)
class Tabla:
    """Una tabla del DOCX con su cabecera, sus filas de datos y su contexto."""

    documento: str
    indice: int
    contexto: str
    cabecera: tuple[str, ...]
    filas: tuple[tuple[str, ...], ...]

    def columna(self, n: int) -> tuple[str, ...]:
        return tuple(f[n].strip() if n < len(f) else "" for f in self.filas)


@lru_cache(maxsize=8)
def tablas(nombre: str) -> tuple[Tabla, ...]:
    """Todas las tablas del cuerpo, con el último párrafo no vacío como contexto."""
    ruta = FUENTES / nombre
    if not ruta.is_file():
        raise FuenteCanonicaError(f"fuente canónica ausente: {ruta}")
    with zipfile.ZipFile(ruta) as zf:
        xml = zf.read("word/document.xml")
    cuerpo = ElementTree.fromstring(xml).find(f"{_W}body")
    if cuerpo is None:
        raise FuenteCanonicaError(f"{nombre}: sin cuerpo OOXML")
    salida: list[Tabla] = []
    contexto = ""
    for nodo in cuerpo:
        etiqueta = nodo.tag[len(_W) :] if nodo.tag.startswith(_W) else nodo.tag
        if etiqueta == "p":
            texto = _texto_nodo(nodo).strip()
            if texto:
                contexto = texto
        elif etiqueta == "tbl":
            filas = [
                tuple(
                    " ".join(_texto_nodo(p) for p in tc.findall(f"{_W}p")).strip()
                    for tc in tr.findall(f"{_W}tc")
                )
                for tr in nodo.findall(f"{_W}tr")
            ]
            if not filas:
                continue
            salida.append(
                Tabla(
                    documento=nombre,
                    indice=len(salida),
                    contexto=contexto,
                    cabecera=tuple(c.strip() for c in filas[0]),
                    filas=tuple(filas[1:]),
                )
            )
    return tuple(salida)


# ---------------------------------------------------------------------------
# 2. Identidades canónicas de tabla
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Identidad:
    """Cómo se reconoce una tabla canónica, sin usar su posición física."""

    documento: str
    cabecera: tuple[str, ...]
    contexto: str
    filas: int
    patron_col0: str | None = None
    descripcion: str = ""


IDENTIDADES: dict[str, Identidad] = {
    "b04_casos_17": Identidad(
        documento=B04,
        cabecera=("ID", "Riesgo", "Entrada", "Resultado esperado", "Fallo observable"),
        contexto=r"^17\. Casos de aceptación finales",
        filas=39,
        patron_col0=r"CA-\d{2}",
        descripcion="B04 §17 · casos de aceptación CA-01 a CA-39",
    ),
    "b04_casos_17_1": Identidad(
        documento=B04,
        cabecera=("ID", "Riesgo", "Entrada", "Resultado esperado", "Fallo observable"),
        contexto=r"^17\.1 Casos añadidos y corregidos",
        filas=11,
        patron_col0=r"CA-\d{2}",
        descripcion="B04 §17.1 · casos añadidos y corregidos CA-40 a CA-50",
    ),
    "b04_modos": Identidad(
        documento=B04,
        cabecera=("Modo", "Finalidad", "Elegibilidad"),
        contexto=r"^5\. Modos de recuperación",
        filas=5,
        patron_col0=r"M[1-5]\b.*",
        descripcion="B04 §5 · modos de recuperación",
    ),
    "b04_etapas": Identidad(
        documento=B04,
        cabecera=("Etapa", "Comportamiento", "Salida"),
        contexto=r"^15\.1 Etapas normativas",
        filas=6,
        patron_col0=r"E[0-5]\b.*",
        descripcion="B04 §15.1 · etapas E0-E5",
    ),
    "b04_cardinalidad": Identidad(
        documento=B04,
        cabecera=("Cardinalidad", "Definición", "Regla de parada"),
        contexto=r"^15\.2 Cardinalidad y suficiencia",
        filas=3,
        patron_col0=r"EXACTA|ACOTADA|EXHAUSTIVA",
        descripcion="B04 §15.2 · cardinalidad y regla de parada",
    ),
    "b04_paradas": Identidad(
        documento=B04,
        cabecera=("ID", "Condición"),
        contexto=r"^15\.3 Criterios de parada",
        filas=7,
        patron_col0=r"S[1-7]\b.*",
        descripcion="B04 §15.3 · criterios de parada S1-S7",
    ),
    "b04_requisitos": Identidad(
        documento=B04,
        cabecera=("ID", "Requisito"),
        contexto=r"^16\. Requisitos funcionales finales",
        filas=32,
        patron_col0=r"B04-RF-\d{2}",
        descripcion="B04 §16 · requisitos funcionales B04-RF-01 a 32",
    ),
    "b04_metricas": Identidad(
        documento=B04,
        cabecera=("ID", "Métrica", "Cálculo / qué mide", "Umbral / puerta"),
        contexto=r"^18\. Métricas y puertas finales",
        filas=21,
        patron_col0=r"B04-M\d{2}",
        descripcion="B04 §18 · métricas B04-M01 a M21",
    ),
    "pdp_ficha_7": Identidad(
        documento=PDP,
        cabecera=("Campo", "Definición", "Cuándo se congela"),
        contexto=r"^7\. Unidad de caso y ficha obligatoria",
        filas=14,
        patron_col0=None,
        descripcion="PDP §7 · ficha obligatoria de caso, catorce campos",
    ),
    "pdp_familias_8": Identidad(
        documento=PDP,
        cabecera=("ID", "Familia", "Cobertura mínima"),
        contexto=r"^8\. Corpus obligatorio",
        filas=25,
        patron_col0=r"F\d{2}",
        descripcion="PDP §8 · veinticinco familias con cobertura mínima",
    ),
    "pdp_casos_transversales": Identidad(
        documento=PDP,
        cabecera=("ID", "Entrada adversarial", "Resultado esperado"),
        contexto=r"276 casos numerados aprobados",
        filas=28,
        patron_col0=r"PDP-CA-\d{2}",
        descripcion="PDP §9 · casos transversales PDP-CA-01 a 28",
    ),
    "pdp_registro_red": Identidad(
        documento=PDP,
        cabecera=(
            "ID",
            "Fuente",
            "Localizador",
            "Delegación obligatoria",
            "Artefacto del Plan",
            "Estado",
        ),
        contexto=r"denominador final de RED-1\.0",
        filas=79,
        patron_col0=r"RED-\d{3}",
        descripcion="PDP §4 · Registro RED, expresamente distinto del Anexo B",
    ),
    "pdp_anexo_b": Identidad(
        documento=PDP,
        cabecera=(
            "RED",
            "Familia",
            "Caso(s) exactos",
            "Métrica / puerta",
            "Evidencia mínima",
            "Estado",
        ),
        contexto=r"La matriz asigna a cada fila RED",
        filas=79,
        patron_col0=r"RED-\d{3}",
        descripcion="PDP Anexo B · matriz RED -> familia / casos / métrica / evidencia",
    ),
    "arq00_destinos_20": Identidad(
        documento=ARQ00,
        cabecera=(
            "ID",
            "Familia canónica",
            "Cobertura mínima literal",
            "Área responsable",
            "Destino",
        ),
        contexto=r"El PDP conserva las preguntas y huecos",
        filas=25,
        patron_col0=r"F\d{2}",
        descripcion="ARQ-00 §20 · destino por familia del PDP",
    ),
}


def tabla(identidad: str) -> Tabla:
    """Localiza una tabla por identidad. Falla si hay cero o varias candidatas."""
    if identidad not in IDENTIDADES:
        raise TablaCanonicaError(f"identidad de tabla desconocida: {identidad}")
    ident = IDENTIDADES[identidad]
    candidatas = [
        t
        for t in tablas(ident.documento)
        if t.cabecera == ident.cabecera and re.search(ident.contexto, t.contexto)
    ]
    if len(candidatas) != 1:
        raise TablaCanonicaError(
            f"{identidad}: {len(candidatas)} tablas candidatas para la cabecera "
            f"{ident.cabecera} y el contexto {ident.contexto!r}; se exige exactamente una"
        )
    encontrada = candidatas[0]
    if len(encontrada.filas) != ident.filas:
        raise TablaCanonicaError(
            f"{identidad}: {len(encontrada.filas)} filas de datos (esperadas {ident.filas}); "
            "una fila añadida, perdida o duplicada invalida la lectura"
        )
    if ident.patron_col0 is not None:
        malas = [
            (n, f[0])
            for n, f in enumerate(encontrada.filas)
            if not re.fullmatch(ident.patron_col0, f[0].strip())
        ]
        if malas:
            raise TablaCanonicaError(f"{identidad}: filas con primera columna inesperada: {malas}")
        col0 = [f[0].strip() for f in encontrada.filas]
        duplicadas = sorted({c for c in col0 if col0.count(c) > 1})
        if duplicadas:
            raise TablaCanonicaError(f"{identidad}: identificadores duplicados: {duplicadas}")
    return encontrada


def inventario_de_tablas() -> list[dict[str, Any]]:
    """Diagnóstico: qué tabla resuelve cada identidad y con cuántas filas."""
    salida: list[dict[str, Any]] = []
    for nombre, ident in IDENTIDADES.items():
        t = tabla(nombre)
        salida.append(
            {
                "identidad": nombre,
                "documento": ident.documento,
                "indice_fisico": t.indice,
                "contexto": t.contexto[:90],
                "cabecera": list(t.cabecera),
                "filas": len(t.filas),
                "descripcion": ident.descripcion,
            }
        )
    return salida


# ---------------------------------------------------------------------------
# 3. Huellas
# ---------------------------------------------------------------------------


def sha256(nombre: str) -> str:
    ruta = FUENTES / nombre
    if not ruta.is_file():
        raise FuenteCanonicaError(f"fuente canónica ausente: {ruta}")
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def huellas_del_manifest() -> dict[str, str]:
    if not MANIFEST.is_file():
        raise FuenteCanonicaError(f"manifiesto ausente: {MANIFEST}")
    salida: dict[str, str] = {}
    for linea in MANIFEST.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([0-9a-f]{64})\s+(\S+\.docx)\s*$", linea.strip())
        if m:
            salida[m.group(2)] = m.group(1)
    return salida


def verificar_huellas() -> dict[str, dict[str, Any]]:
    esperadas = huellas_del_manifest()
    salida: dict[str, dict[str, Any]] = {}
    for nombre in (B04, PDP, ARQ00):
        real = sha256(nombre)
        salida[nombre] = {
            "sha256_real": real,
            "sha256_manifest": esperadas.get(nombre),
            "coincide": esperadas.get(nombre) == real,
            "bytes": (FUENTES / nombre).stat().st_size,
        }
    return salida


# ---------------------------------------------------------------------------
# 4. Universos canónicos de identificadores
# ---------------------------------------------------------------------------

CA_B04_VALIDOS = frozenset(f"B04-CA-{n:02d}" for n in range(1, 51))
CA_PDP_VALIDOS = frozenset(f"PDP-CA-{n:02d}" for n in range(1, 29))
RF_B04_VALIDOS = frozenset(f"B04-RF-{n:02d}" for n in range(1, 33))
M_B04_VALIDOS = frozenset(f"B04-M{n:02d}" for n in range(1, 22))
FAMILIAS_VALIDAS = frozenset(f"F{n:02d}" for n in range(1, 26))
RED_VALIDOS = frozenset(f"RED-{n:03d}" for n in range(1, 80))


def normalizar(texto: str) -> str:
    """Minúsculas sin acentos ni signos: base común de toda comparación léxica."""
    descompuesto = unicodedata.normalize("NFKD", texto)
    sin_acentos = "".join(c for c in descompuesto if not unicodedata.combining(c))
    return re.sub(r"[^0-9a-z]+", " ", sin_acentos.lower()).strip()


# ---------------------------------------------------------------------------
# 5. B04 · casos, vocabularios, requisitos y métricas
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CasoCanonico:
    identificador: str
    riesgo: str
    entrada: str
    resultado_esperado: str
    fallo_observable: str
    seccion: str


def casos_b04() -> dict[str, CasoCanonico]:
    """`B04-CA-01` … `B04-CA-50`, leídos de §17 y §17.1 por identidad de tabla."""
    salida: dict[str, CasoCanonico] = {}
    for identidad, seccion in (
        ("b04_casos_17", "B04 v1.0 APROBADO §17"),
        ("b04_casos_17_1", "B04 v1.0 APROBADO §17.1"),
    ):
        for celdas in tabla(identidad).filas:
            m = re.fullmatch(r"CA-(\d{2})", celdas[0].strip())
            if not m:  # pragma: no cover - `tabla()` ya lo garantiza
                raise TablaCanonicaError(f"{identidad}: fila sin identificador CA: {celdas[0]!r}")
            ident = f"B04-CA-{int(m.group(1)):02d}"
            if ident in salida:
                raise FuenteCanonicaError(f"{ident} aparece dos veces en B04")
            if ident not in CA_B04_VALIDOS:
                raise FuenteCanonicaError(f"{ident} está fuera del universo B04-CA-01-50")
            salida[ident] = CasoCanonico(
                identificador=ident,
                riesgo=celdas[1],
                entrada=celdas[2],
                resultado_esperado=celdas[3],
                fallo_observable=celdas[4],
                seccion=seccion,
            )
    if set(salida) != CA_B04_VALIDOS:
        faltan = sorted(CA_B04_VALIDOS - set(salida))
        raise FuenteCanonicaError(f"B04 §17/§17.1 incompletos: faltan {faltan}")
    return salida


def reglas_cardinalidad_b04() -> dict[str, str]:
    return {f[0].strip(): f[2].strip() for f in tabla("b04_cardinalidad").filas}


def paradas_b04() -> dict[str, str]:
    salida: dict[str, str] = {}
    for celdas in tabla("b04_paradas").filas:
        m = re.match(r"^(S[1-7])\s*·\s*", celdas[0].strip())
        if m:
            salida[m.group(1)] = celdas[1].strip()
    return salida


def etapas_b04() -> dict[str, str]:
    salida: dict[str, str] = {}
    for celdas in tabla("b04_etapas").filas:
        m = re.match(r"^(E[0-5])\s*·\s*", celdas[0].strip())
        if m:
            salida[m.group(1)] = celdas[1].strip()
    return salida


def modos_b04() -> dict[str, str]:
    salida: dict[str, str] = {}
    for celdas in tabla("b04_modos").filas:
        m = re.match(r"^(M[1-5])\s*·\s*", celdas[0].strip())
        if m:
            salida[m.group(1)] = celdas[2].strip()
    return salida


def s1_prohibida_en_exhaustiva() -> bool:
    return "S1 deshabilitado" in reglas_cardinalidad_b04().get("EXHAUSTIVA", "")


def requisitos_b04() -> dict[str, str]:
    salida = {f[0].strip(): f[1].strip() for f in tabla("b04_requisitos").filas}
    ajenos = sorted(set(salida) - RF_B04_VALIDOS)
    if ajenos:
        raise FuenteCanonicaError(f"requisitos fuera de B04-RF-01-32: {ajenos}")
    return salida


def metricas_b04() -> dict[str, dict[str, str]]:
    salida = {
        f[0].strip(): {"metrica": f[1].strip(), "calculo": f[2].strip(), "umbral": f[3].strip()}
        for f in tabla("b04_metricas").filas
    }
    ajenas = sorted(set(salida) - M_B04_VALIDOS)
    if ajenas:
        raise FuenteCanonicaError(f"métricas fuera de B04-M01-21: {ajenas}")
    return salida


# ---------------------------------------------------------------------------
# 6. Plan de Pruebas · Anexo B, ficha §7, familias §8, PDP-CA
# ---------------------------------------------------------------------------


def _expandir_ids(texto: str) -> list[str]:
    """``"B04-CA-39, PDP-CA-09, 22"`` -> los tres ids completos, con rangos."""
    salida: list[str] = []
    prefijo = ""
    for bruto in re.split(r",\s*", texto.strip()):
        pieza = bruto.strip()
        if not pieza:
            continue
        m = re.match(r"^([A-Z0-9]+(?:-[A-Z]+)?)-(\d+)(?:\s*[\u2013-]\s*(\d+))?$", pieza)
        if m and not m.group(1).isdigit():
            prefijo = m.group(1)
            inicio, fin = int(m.group(2)), int(m.group(3) or m.group(2))
            salida.extend(f"{prefijo}-{n:02d}" for n in range(inicio, fin + 1))
            continue
        m = re.match(r"^(\d+)(?:\s*[\u2013-]\s*(\d+))?$", pieza)
        if m and prefijo:
            inicio, fin = int(m.group(1)), int(m.group(2) or m.group(1))
            salida.extend(f"{prefijo}-{n:02d}" for n in range(inicio, fin + 1))
    return salida


def _expandir_metricas(texto: str) -> list[str]:
    """``"B08-M12/M25"`` -> ``["B08-M12", "B08-M25"]`` · ``"PDP-M01<en dash>M17"`` -> el rango.

    El v0.2 devolvía ``M25`` suelto: un identificador que no existe en ningún
    bloque. Arrastrar el prefijo conserva la métrica externa real —`B08-M25`,
    `B05-M16`— en vez de filtrarla en silencio.
    """
    salida: list[str] = []
    prefijo = ""
    for bruto in re.split(r"[/,]\s*", texto.strip()):
        pieza = bruto.strip()
        if not pieza:
            continue
        m = re.fullmatch(r"([A-Z0-9]+)-M(\d{2})(?:\s*[\u2013-]\s*M?(\d{2}))?", pieza)
        if m:
            prefijo = m.group(1)
            inicio, fin = int(m.group(2)), int(m.group(3) or m.group(2))
            salida.extend(f"{prefijo}-M{n:02d}" for n in range(inicio, fin + 1))
            continue
        m = re.fullmatch(r"M(\d{2})(?:\s*[\u2013-]\s*M?(\d{2}))?", pieza)
        if m and prefijo:
            inicio, fin = int(m.group(1)), int(m.group(2) or m.group(1))
            salida.extend(f"{prefijo}-M{n:02d}" for n in range(inicio, fin + 1))
            continue
        salida.append(pieza)
    return salida


def _expandir_familias(texto: str) -> list[str]:
    salida: list[str] = []
    for pieza in re.split(r"[/,]\s*", texto.strip()):
        limpio = pieza.strip()
        m = re.fullmatch(r"F(\d{2})\s*[\u2013-]\s*F(\d{2})", limpio)
        if m:
            salida.extend(f"F{n:02d}" for n in range(int(m.group(1)), int(m.group(2)) + 1))
            continue
        if re.fullmatch(r"F\d{2}", limpio):
            salida.append(limpio)
    return salida


@dataclass(frozen=True)
class FilaAnexoB:
    red: str
    familias_texto: str
    familias: tuple[str, ...]
    casos: tuple[str, ...]
    metricas: tuple[str, ...]
    evidencia: str
    estado: str

    def casos_b04(self) -> tuple[str, ...]:
        return tuple(c for c in self.casos if c.startswith("B04-CA-"))

    def casos_pdp(self) -> tuple[str, ...]:
        return tuple(c for c in self.casos if c.startswith("PDP-CA-"))

    def casos_externos(self) -> tuple[str, ...]:
        return tuple(c for c in self.casos if not c.startswith(("B04-CA-", "PDP-CA-")))

    def metricas_b04(self) -> tuple[str, ...]:
        return tuple(m for m in self.metricas if m.startswith("B04-M"))

    def metricas_externas(self) -> tuple[str, ...]:
        return tuple(m for m in self.metricas if not m.startswith("B04-M"))


def anexo_b() -> dict[str, FilaAnexoB]:
    """Anexo B del Plan de Pruebas, leído de **su** tabla y de ninguna otra."""
    salida: dict[str, FilaAnexoB] = {}
    for celdas in tabla("pdp_anexo_b").filas:
        red = celdas[0].strip()
        if red in salida:
            raise FuenteCanonicaError(f"{red} duplicado en el Anexo B")
        if red not in RED_VALIDOS:
            raise FuenteCanonicaError(f"{red} está fuera del denominador RED-001-079")
        casos = tuple(_expandir_ids(celdas[2]))
        for caso in casos:
            if caso.startswith("B04-CA-") and caso not in CA_B04_VALIDOS:
                raise FuenteCanonicaError(f"{red}: caso inexistente {caso}")
            if caso.startswith("PDP-CA-") and caso not in CA_PDP_VALIDOS:
                raise FuenteCanonicaError(f"{red}: caso inexistente {caso}")
        metricas = tuple(_expandir_metricas(celdas[3]))
        for metrica in metricas:
            if metrica.startswith("B04-M") and metrica not in M_B04_VALIDOS:
                raise FuenteCanonicaError(f"{red}: métrica inexistente {metrica}")
        familias = tuple(_expandir_familias(celdas[1]))
        for familia in familias:
            if familia not in FAMILIAS_VALIDAS:
                raise FuenteCanonicaError(f"{red}: familia inexistente {familia}")
        salida[red] = FilaAnexoB(
            red=red,
            familias_texto=celdas[1].strip(),
            familias=familias,
            casos=casos,
            metricas=metricas,
            evidencia=celdas[4].strip(),
            estado=celdas[5].strip(),
        )
    return salida


def registro_red() -> dict[str, dict[str, str]]:
    """Registro RED del §4 · tabla **distinta** del Anexo B, con su cabecera propia."""
    salida: dict[str, dict[str, str]] = {}
    for celdas in tabla("pdp_registro_red").filas:
        red = celdas[0].strip()
        if red not in RED_VALIDOS:
            raise FuenteCanonicaError(f"{red} está fuera del denominador RED-001-079")
        salida[red] = {
            "fuente": celdas[1].strip(),
            "localizador": celdas[2].strip(),
            "delegacion": celdas[3].strip(),
            "artefacto": celdas[4].strip(),
            "estado": celdas[5].strip(),
        }
    return salida


def asignaciones_canonicas_por_ca() -> dict[str, dict[str, list[str]]]:
    """Invierte el Anexo B: por cada `B04-CA`, qué RED, métricas y familias lo fijan."""
    salida: dict[str, dict[str, list[str]]] = {}
    for red, fila in sorted(anexo_b().items()):
        for caso in fila.casos_b04():
            entrada = salida.setdefault(
                caso, {"red": [], "metricas": [], "familias": [], "metricas_externas": []}
            )
            if red not in entrada["red"]:
                entrada["red"].append(red)
            for metrica in fila.metricas_b04():
                if metrica not in entrada["metricas"]:
                    entrada["metricas"].append(metrica)
            for metrica in fila.metricas_externas():
                if metrica not in entrada["metricas_externas"]:
                    entrada["metricas_externas"].append(metrica)
            for familia in fila.familias:
                if familia not in entrada["familias"]:
                    entrada["familias"].append(familia)
    return {k: {kk: sorted(vv) for kk, vv in v.items()} for k, v in sorted(salida.items())}


def asignaciones_canonicas_por_pdp_ca() -> dict[str, dict[str, list[str]]]:
    """Los `PDP-CA` anclados por una fila del Anexo B que cita B04 (RED-017)."""
    salida: dict[str, dict[str, list[str]]] = {}
    for red, fila in sorted(anexo_b().items()):
        if not (fila.casos_b04() or fila.metricas_b04()):
            continue
        for caso in fila.casos_pdp():
            entrada = salida.setdefault(
                caso,
                {
                    "red": [],
                    "metricas": [],
                    "metricas_externas": [],
                    "familias": [],
                    "casos_b04": [],
                },
            )
            for clave, valores in (
                ("red", [red]),
                ("metricas", list(fila.metricas_b04())),
                ("metricas_externas", list(fila.metricas_externas())),
                ("familias", list(fila.familias)),
                ("casos_b04", list(fila.casos_b04())),
            ):
                for valor in valores:
                    if valor not in entrada[clave]:
                        entrada[clave].append(valor)
    return {k: {kk: sorted(vv) for kk, vv in v.items()} for k, v in sorted(salida.items())}


def metricas_del_anexo_b() -> dict[str, list[str]]:
    """Separa lo que el Anexo B cita: métricas B04 propias y externas canónicas."""
    propias: set[str] = set()
    externas: set[str] = set()
    for fila in anexo_b().values():
        propias.update(fila.metricas_b04())
        externas.update(fila.metricas_externas())
    return {"b04_propias": sorted(propias), "externas_canonicas": sorted(externas)}


def ficha_obligatoria_pdp7() -> dict[str, dict[str, str]]:
    """PDP §7 · los catorce campos con su definición y su momento de congelación."""
    salida: dict[str, dict[str, str]] = {}
    for celdas in tabla("pdp_ficha_7").filas:
        campo = celdas[0].strip()
        if campo in salida:
            raise FuenteCanonicaError(f"campo duplicado en la ficha del PDP §7: {campo}")
        salida[campo] = {"definicion": celdas[1].strip(), "congelacion": celdas[2].strip()}
    return salida


def familias_pdp() -> dict[str, dict[str, str]]:
    """PDP §8 · familia -> nombre y texto literal de cobertura mínima."""
    salida: dict[str, dict[str, str]] = {}
    for celdas in tabla("pdp_familias_8").filas:
        familia = celdas[0].strip()
        salida[familia] = {"nombre": celdas[1].strip(), "cobertura_minima": celdas[2].strip()}
    if set(salida) != FAMILIAS_VALIDAS:
        raise FuenteCanonicaError(
            f"familias PDP incompletas: {sorted(FAMILIAS_VALIDAS - set(salida))}"
        )
    return salida


@dataclass(frozen=True)
class CasoPdp:
    identificador: str
    entrada_adversarial: str
    resultado_esperado: str


def casos_transversales_pdp() -> dict[str, CasoPdp]:
    salida: dict[str, CasoPdp] = {}
    for celdas in tabla("pdp_casos_transversales").filas:
        ident = celdas[0].strip()
        if ident not in CA_PDP_VALIDOS:
            raise FuenteCanonicaError(f"{ident} está fuera de PDP-CA-01-28")
        salida[ident] = CasoPdp(
            identificador=ident,
            entrada_adversarial=celdas[1].strip(),
            resultado_esperado=celdas[2].strip(),
        )
    return salida


# ---------------------------------------------------------------------------
# 7. ARQ-00 · §20 destinos y §23 alternativas mínimas
# ---------------------------------------------------------------------------


def destinos_pdp_arq00() -> dict[str, dict[str, str]]:
    salida: dict[str, dict[str, str]] = {}
    for celdas in tabla("arq00_destinos_20").filas:
        salida[celdas[0].strip()] = {
            "familia": celdas[1].strip(),
            "cobertura_minima": celdas[2].strip(),
            "area": celdas[3].strip(),
            "destino": celdas[4].strip(),
        }
    return salida


def expandir_destinos(texto: str) -> list[str]:
    salida: list[str] = []
    prefijo = ""
    for bruto in texto.split("/"):
        pieza = bruto.strip()
        if not pieza:
            continue
        if "-" in pieza:
            prefijo = pieza.split("-", 1)[0]
            salida.append(pieza)
        elif re.fullmatch(r"\d{3}[A-Z]?", pieza) and prefijo:
            salida.append(f"{prefijo}-{pieza}")
        else:
            salida.append(pieza)
    return salida


def familias_destino_adr002() -> list[str]:
    return sorted(
        f for f, d in destinos_pdp_arq00().items() if "ADR-002" in expandir_destinos(d["destino"])
    )


@lru_cache(maxsize=1)
def _parrafos_arq00() -> tuple[str, ...]:
    ruta = FUENTES / ARQ00
    with zipfile.ZipFile(ruta) as zf:
        xml = zf.read("word/document.xml")
    cuerpo = ElementTree.fromstring(xml).find(f"{_W}body")
    if cuerpo is None:  # pragma: no cover - documento verificado por huella
        raise FuenteCanonicaError(f"{ARQ00}: sin cuerpo OOXML")
    salida: list[str] = []
    for nodo in cuerpo:
        etiqueta = nodo.tag[len(_W) :] if nodo.tag.startswith(_W) else nodo.tag
        if etiqueta == "p":
            salida.append(_texto_nodo(nodo).strip())
    return tuple(salida)


def alternativas_minimas_arq00() -> dict[str, str]:
    """ARQ-00 §23 · alternativas mínimas de ADR-002, texto literal."""
    salida: dict[str, str] = {}
    en_seccion_23 = False
    dentro = False
    for texto in _parrafos_arq00():
        if texto.startswith("23. ADR-002"):
            en_seccion_23 = True
            continue
        if not en_seccion_23:
            continue
        if texto == "Alternativas mínimas":
            dentro = True
            continue
        if dentro:
            m = re.match(r"^([ABCD]):\s*(.+)$", texto)
            if m:
                salida[m.group(1)] = m.group(2).strip()
                continue
            if texto and len(salida) == 4:
                break
    return salida


# ---------------------------------------------------------------------------
# 8. Vista consolidada e invariantes mínimas
# ---------------------------------------------------------------------------

# §3.2 del paquete 03C: el lector no puede producir un PASS parcial.
INVARIANTES: dict[str, int] = {
    "casos_b04": 50,
    "filas_anexo_b": 79,
    "filas_registro_red": 79,
    "ca_b04_nombrados_por_anexo_b": 20,
    "familias_pdp": 25,
    "casos_pdp": 28,
    "campos_ficha_pdp7": 14,
    "requisitos_b04": 32,
    "metricas_b04": 21,
    "destinos_arq00": 25,
}

# Los catorce campos de la ficha del PDP §7, en su forma canónica literal.
CAMPOS_PDP7_CANONICOS: tuple[str, ...] = (
    "ID y familia",
    "Objetivo",
    "Entrada",
    "Unidad de trabajo",
    "Operación y modo",
    "Ámbito",
    "Tiempo y corte",
    "Referencia",
    "Criticidad",
    "Tolerancias",
    "Señales observables",
    "Fallo",
    "Evidencia",
    "Resultado",
)


@dataclass
class Canon:
    """Vista consolidada del canon para el generador y el validador v0.3."""

    # Las fábricas se resuelven por nombre de módulo en cada construcción: así una
    # sustitución del lector —o una prueba negativa— se ve reflejada de verdad.
    huellas: dict[str, dict[str, Any]] = field(default_factory=lambda: verificar_huellas())
    casos: dict[str, CasoCanonico] = field(default_factory=lambda: casos_b04())
    anexo: dict[str, FilaAnexoB] = field(default_factory=lambda: anexo_b())
    registro_red: dict[str, dict[str, str]] = field(default_factory=lambda: registro_red())
    familias: dict[str, dict[str, str]] = field(default_factory=lambda: familias_pdp())
    ficha_pdp7: dict[str, dict[str, str]] = field(default_factory=lambda: ficha_obligatoria_pdp7())
    casos_pdp: dict[str, CasoPdp] = field(default_factory=lambda: casos_transversales_pdp())
    destinos: dict[str, dict[str, str]] = field(default_factory=lambda: destinos_pdp_arq00())
    requisitos: dict[str, str] = field(default_factory=lambda: requisitos_b04())
    metricas: dict[str, dict[str, str]] = field(default_factory=lambda: metricas_b04())

    def medidas(self) -> dict[str, int]:
        return {
            "casos_b04": len(self.casos),
            "filas_anexo_b": len(self.anexo),
            "filas_registro_red": len(self.registro_red),
            "ca_b04_nombrados_por_anexo_b": len(asignaciones_canonicas_por_ca()),
            "familias_pdp": len(self.familias),
            "casos_pdp": len(self.casos_pdp),
            "campos_ficha_pdp7": len(self.ficha_pdp7),
            "requisitos_b04": len(self.requisitos),
            "metricas_b04": len(self.metricas),
            "destinos_arq00": len(self.destinos),
        }

    def comprobar_minimos(self) -> None:
        """Falla pronto y entero: una tabla vacía no puede dar un PASS parcial."""
        problemas: list[str] = []
        malas = [n for n, h in self.huellas.items() if not h["coincide"]]
        if malas:
            problemas.append(f"huellas que no coinciden con el MANIFEST: {malas}")
        for clave, esperado in INVARIANTES.items():
            real = self.medidas()[clave]
            if clave == "ca_b04_nombrados_por_anexo_b":
                if real < esperado:
                    problemas.append(f"{clave}: {real} (mínimo {esperado})")
                continue
            if real != esperado:
                problemas.append(f"{clave}: {real} (esperado {esperado})")
        if tuple(self.ficha_pdp7) != CAMPOS_PDP7_CANONICOS:
            problemas.append(
                "los campos de la ficha del PDP §7 no coinciden con el conjunto canónico: "
                f"leídos {list(self.ficha_pdp7)}"
            )
        sin_cobertura = sorted(f for f, d in self.familias.items() if not d["cobertura_minima"])
        if sin_cobertura:
            problemas.append(f"familias PDP sin texto de cobertura mínima: {sin_cobertura}")
        if self.anexo.keys() != self.registro_red.keys():
            problemas.append("el Anexo B y el Registro RED no cubren el mismo denominador")
        if not s1_prohibida_en_exhaustiva():
            problemas.append("no se localizó la regla «EXHAUSTIVA -> S1 deshabilitado»")
        if problemas:
            raise FuenteCanonicaError("; ".join(problemas))


def cargar_canon() -> Canon:
    canon = Canon()
    canon.comprobar_minimos()
    return canon


if __name__ == "__main__":  # pragma: no cover - inspección manual
    c = cargar_canon()
    for entrada in inventario_de_tablas():
        print(
            f"{entrada['identidad']:26s} tabla #{entrada['indice_fisico']:>3}  "
            f"{entrada['filas']:>3} filas  {entrada['descripcion']}"
        )
    print(f"medidas: {c.medidas()}")
    print(f"métricas del Anexo B: {metricas_del_anexo_b()}")
    print(f"PDP-CA anclados por el Anexo B: {sorted(asignaciones_canonicas_por_pdp_ca())}")
