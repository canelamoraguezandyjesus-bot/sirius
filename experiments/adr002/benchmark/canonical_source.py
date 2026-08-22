"""Lector de las fuentes canónicas DOCX de ADR-002.

Este módulo **no resume ni reescribe** el canon: lo lee. Abre los tres
`.docx` materializados en `docs/architecture/canonical_sources/` con
`zipfile` y `xml.etree` de la biblioteca estándar —sin añadir ninguna
dependencia— y extrae literalmente:

* los cincuenta casos de aceptación de B04 §17 y §17.1, con riesgo, entrada,
  resultado esperado y fallo observable **carácter a carácter**;
* la regla de cardinalidad y las paradas de B04 §15.2 y §15.3;
* el Anexo B del Plan de Pruebas: asignación `RED -> familia / casos /
  métrica / evidencia`;
* la ficha obligatoria de caso del PDP §7;
* las veinticinco familias del PDP §8;
* los casos transversales `PDP-CA-01` a `PDP-CA-28`;
* el destino por familia de ARQ-00 §20.

Es la pieza que convierte la validación de «coherencia interna» en
**validación de fidelidad**: si un artefacto derivado se separa del canon, la
comparación falla.

Determinista: los ficheros son bytes fijos y verificados por SHA-256 contra
`MANIFEST.md`. No usa reloj, ni red, ni aleatoriedad.
"""

from __future__ import annotations

import hashlib
import re
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


# ---------------------------------------------------------------------------
# 1. Lectura del DOCX
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
class Bloque:
    """Un párrafo (``clase='p'``) o una fila de tabla (``clase='fila'``)."""

    clase: str
    texto: str = ""
    celdas: tuple[str, ...] = ()


@lru_cache(maxsize=8)
def bloques(nombre: str) -> tuple[Bloque, ...]:
    """Devuelve el cuerpo del DOCX como secuencia de párrafos y filas."""
    ruta = FUENTES / nombre
    if not ruta.is_file():
        raise FuenteCanonicaError(f"fuente canónica ausente: {ruta}")
    with zipfile.ZipFile(ruta) as zf:
        xml = zf.read("word/document.xml")
    cuerpo = ElementTree.fromstring(xml).find(f"{_W}body")
    if cuerpo is None:
        raise FuenteCanonicaError(f"{nombre}: sin cuerpo OOXML")
    salida: list[Bloque] = []
    for nodo in cuerpo:
        etiqueta = nodo.tag[len(_W) :] if nodo.tag.startswith(_W) else nodo.tag
        if etiqueta == "p":
            salida.append(Bloque("p", texto=_texto_nodo(nodo).strip()))
        elif etiqueta == "tbl":
            for tr in nodo.findall(f"{_W}tr"):
                celdas = tuple(
                    " ".join(_texto_nodo(p) for p in tc.findall(f"{_W}p")).strip()
                    for tc in tr.findall(f"{_W}tc")
                )
                salida.append(Bloque("fila", celdas=celdas))
    return tuple(salida)


def _filas(nombre: str) -> list[tuple[str, ...]]:
    return [b.celdas for b in bloques(nombre) if b.clase == "fila"]


# ---------------------------------------------------------------------------
# 2. Huellas
# ---------------------------------------------------------------------------


def sha256(nombre: str) -> str:
    ruta = FUENTES / nombre
    if not ruta.is_file():
        raise FuenteCanonicaError(f"fuente canónica ausente: {ruta}")
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def huellas_del_manifest() -> dict[str, str]:
    """Lee el bloque de huellas del §6 de ``MANIFEST.md``."""
    if not MANIFEST.is_file():
        raise FuenteCanonicaError(f"manifiesto ausente: {MANIFEST}")
    salida: dict[str, str] = {}
    for linea in MANIFEST.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([0-9a-f]{64})\s+(\S+\.docx)\s*$", linea.strip())
        if m:
            salida[m.group(2)] = m.group(1)
    return salida


def verificar_huellas() -> dict[str, dict[str, Any]]:
    """Contrasta el SHA-256 real de cada DOCX con el declarado en el manifiesto."""
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
# 3. B04 · casos de aceptación §17 y §17.1
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CasoCanonico:
    """Las cinco columnas literales de B04 §17 / §17.1."""

    identificador: str
    riesgo: str
    entrada: str
    resultado_esperado: str
    fallo_observable: str
    seccion: str


def casos_b04() -> dict[str, CasoCanonico]:
    """`B04-CA-01` … `B04-CA-50` leídos de la tabla canónica.

    §17 contiene CA-01 a CA-39 y §17.1 los añadidos y corregidos CA-40 a CA-50. La
    cabecera de ambas tablas es idéntica: ID · Riesgo · Entrada · Resultado
    esperado · Fallo observable.
    """
    salida: dict[str, CasoCanonico] = {}
    for celdas in _filas(B04):
        if len(celdas) != 5:
            continue
        m = re.fullmatch(r"CA-(\d{2})", celdas[0].strip())
        if not m:
            continue
        numero = int(m.group(1))
        ident = f"B04-CA-{numero:02d}"
        if ident in salida:
            raise FuenteCanonicaError(f"{ident} aparece dos veces en B04")
        salida[ident] = CasoCanonico(
            identificador=ident,
            riesgo=celdas[1],
            entrada=celdas[2],
            resultado_esperado=celdas[3],
            fallo_observable=celdas[4],
            seccion="B04 v1.0 APROBADO §17" if numero <= 39 else "B04 v1.0 APROBADO §17.1",
        )
    return salida


def reglas_cardinalidad_b04() -> dict[str, str]:
    """B04 §15.2: definición y regla de parada por cardinalidad."""
    salida: dict[str, str] = {}
    for celdas in _filas(B04):
        if len(celdas) == 3 and celdas[0].strip() in ("EXACTA", "ACOTADA", "EXHAUSTIVA"):
            salida[celdas[0].strip()] = celdas[2].strip()
    return salida


def paradas_b04() -> dict[str, str]:
    """B04 §15.3: los siete criterios de parada, con su condición literal."""
    salida: dict[str, str] = {}
    for celdas in _filas(B04):
        if len(celdas) != 2:
            continue
        m = re.match(r"^(S[1-7])\s*·\s*(.+)$", celdas[0].strip())
        if m:
            salida[m.group(1)] = celdas[1].strip()
    return salida


def s1_prohibida_en_exhaustiva() -> bool:
    """Única regla cardinalidad->parada que el canon fija literalmente."""
    regla = reglas_cardinalidad_b04().get("EXHAUSTIVA", "")
    return "S1 deshabilitado" in regla


def etapas_b04() -> dict[str, str]:
    """B04 §15.1: comportamiento de cada etapa E0-E5."""
    salida: dict[str, str] = {}
    for celdas in _filas(B04):
        if len(celdas) != 3:
            continue
        m = re.match(r"^(E[0-5])\s*·\s*(.+)$", celdas[0].strip())
        if m:
            salida[m.group(1)] = celdas[1].strip()
    return salida


def modos_b04() -> dict[str, str]:
    """B04 §5: los cinco modos de recuperación y su elegibilidad."""
    salida: dict[str, str] = {}
    for celdas in _filas(B04):
        if len(celdas) != 3:
            continue
        m = re.match(r"^(M[1-5])\s*·\s*(.+)$", celdas[0].strip())
        if m:
            salida[m.group(1)] = celdas[2].strip()
    return salida


def requisitos_b04() -> dict[str, str]:
    salida: dict[str, str] = {}
    for celdas in _filas(B04):
        if len(celdas) == 2 and re.fullmatch(r"B04-RF-\d{2}", celdas[0].strip()):
            salida[celdas[0].strip()] = celdas[1].strip()
    return salida


def metricas_b04() -> dict[str, dict[str, str]]:
    salida: dict[str, dict[str, str]] = {}
    for celdas in _filas(B04):
        if len(celdas) == 4 and re.fullmatch(r"B04-M\d{2}", celdas[0].strip()):
            salida[celdas[0].strip()] = {
                "metrica": celdas[1].strip(),
                "calculo": celdas[2].strip(),
                "umbral": celdas[3].strip(),
            }
    return salida


# ---------------------------------------------------------------------------
# 4. Plan de Pruebas · Anexo B, ficha §7, familias §8, PDP-CA
# ---------------------------------------------------------------------------


def _expandir_ids(texto: str, prefijo_por_defecto: str = "") -> list[str]:
    """Expande listas abreviadas del Anexo B.

    ``"B04-CA-01, 05, 08, 15"`` -> cuatro ids completos.
    ``"B08-CA-04-15, 35-41"``   -> los rangos, con raya o con guion.
    ``"B04-CA-39, PDP-CA-09, 22"`` -> el prefijo cambia al aparecer otro.
    """
    salida: list[str] = []
    prefijo = prefijo_por_defecto
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


def _expandir_familias(texto: str) -> list[str]:
    """``"F01-F06"`` -> F01..F06 · ``"F02/F03"`` -> [F02, F03]."""
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

    def metricas_b04(self) -> tuple[str, ...]:
        return tuple(m for m in self.metricas if m.startswith("B04-M"))


def anexo_b() -> dict[str, FilaAnexoB]:
    """Matriz concreta RED->PDP del Anexo B del Plan de Pruebas."""
    salida: dict[str, FilaAnexoB] = {}
    for celdas in _filas(PDP):
        if len(celdas) != 6:
            continue
        red = celdas[0].strip()
        if not re.fullmatch(r"RED-\d{3}", red):
            continue
        salida[red] = FilaAnexoB(
            red=red,
            familias_texto=celdas[1].strip(),
            familias=tuple(_expandir_familias(celdas[1])),
            casos=tuple(_expandir_ids(celdas[2])),
            metricas=tuple(p.strip() for p in re.split(r"[/,]\s*", celdas[3].strip()) if p.strip()),
            evidencia=celdas[4].strip(),
            estado=celdas[5].strip(),
        )
    return salida


def asignaciones_canonicas_por_ca() -> dict[str, dict[str, list[str]]]:
    """Invierte el Anexo B: por cada `B04-CA`, qué RED, métricas y familias lo fijan."""
    salida: dict[str, dict[str, list[str]]] = {}
    for red, fila in sorted(anexo_b().items()):
        for caso in fila.casos_b04():
            entrada = salida.setdefault(caso, {"red": [], "metricas": [], "familias": []})
            if red not in entrada["red"]:
                entrada["red"].append(red)
            for metrica in fila.metricas_b04():
                if metrica not in entrada["metricas"]:
                    entrada["metricas"].append(metrica)
            for familia in fila.familias:
                if familia not in entrada["familias"]:
                    entrada["familias"].append(familia)
    return {k: {kk: sorted(vv) for kk, vv in v.items()} for k, v in sorted(salida.items())}


def ficha_obligatoria_pdp7() -> dict[str, str]:
    """PDP §7 · unidad de caso: campo -> cuándo se congela."""
    esperados = {
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
    }
    salida: dict[str, str] = {}
    for celdas in _filas(PDP):
        if len(celdas) == 3 and celdas[0].strip() in esperados:
            salida[celdas[0].strip()] = celdas[2].strip()
    return salida


def familias_pdp() -> dict[str, str]:
    """PDP §8 · corpus obligatorio: familia -> cobertura mínima literal."""
    salida: dict[str, str] = {}
    for celdas in _filas(PDP):
        if len(celdas) == 3 and re.fullmatch(r"F\d{2}", celdas[0].strip()):
            salida[celdas[0].strip()] = celdas[2].strip()
    return salida


@dataclass(frozen=True)
class CasoPdp:
    identificador: str
    entrada_adversarial: str
    resultado_esperado: str


def casos_transversales_pdp() -> dict[str, CasoPdp]:
    """`PDP-CA-01` … `PDP-CA-28`, los veintiocho casos transversales del Plan."""
    salida: dict[str, CasoPdp] = {}
    for celdas in _filas(PDP):
        if len(celdas) != 3:
            continue
        ident = celdas[0].strip()
        if not re.fullmatch(r"PDP-CA-\d{2}", ident):
            continue
        salida[ident] = CasoPdp(
            identificador=ident,
            entrada_adversarial=celdas[1].strip(),
            resultado_esperado=celdas[2].strip(),
        )
    return salida


# ---------------------------------------------------------------------------
# 5. ARQ-00 · §20 cobertura del PDP y §23 alternativas mínimas
# ---------------------------------------------------------------------------


def destinos_pdp_arq00() -> dict[str, dict[str, str]]:
    """ARQ-00 §20: familia -> área responsable y destino."""
    salida: dict[str, dict[str, str]] = {}
    for celdas in _filas(ARQ00):
        if len(celdas) == 5 and re.fullmatch(r"F\d{2}", celdas[0].strip()):
            salida[celdas[0].strip()] = {
                "familia": celdas[1].strip(),
                "cobertura_minima": celdas[2].strip(),
                "area": celdas[3].strip(),
                "destino": celdas[4].strip(),
            }
    return salida


def expandir_destinos(texto: str) -> list[str]:
    """Expande la columna «Destino» abreviada de ARQ-00 §20.

    ``"ADR-001/002"``       -> ``["ADR-001", "ADR-002"]``
    ``"ADR-003A/003B/004/PDP"`` -> los tres ADR más ``PDP``
    """
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
    """Familias cuyo **destino** en ARQ-00 §20 incluye ADR-002."""
    return sorted(
        f for f, d in destinos_pdp_arq00().items() if "ADR-002" in expandir_destinos(d["destino"])
    )


def alternativas_minimas_arq00() -> dict[str, str]:
    """ARQ-00 §23 · alternativas mínimas de ADR-002, texto literal."""
    salida: dict[str, str] = {}
    en_seccion_23 = False
    dentro = False
    for bloque in bloques(ARQ00):
        if bloque.clase != "p":
            continue
        if bloque.texto.startswith("23. ADR-002"):
            en_seccion_23 = True
            continue
        if not en_seccion_23:
            continue
        if bloque.texto == "Alternativas mínimas":
            dentro = True
            continue
        if dentro:
            m = re.match(r"^([ABCD]):\s*(.+)$", bloque.texto)
            if m:
                salida[m.group(1)] = m.group(2).strip()
                continue
            if bloque.texto and len(salida) == 4:
                break
    return salida


# ---------------------------------------------------------------------------
# 6. Resumen legible por máquina
# ---------------------------------------------------------------------------


@dataclass
class Canon:
    """Vista consolidada del canon, para el generador y el validador."""

    huellas: dict[str, dict[str, Any]] = field(default_factory=verificar_huellas)
    casos: dict[str, CasoCanonico] = field(default_factory=casos_b04)
    anexo: dict[str, FilaAnexoB] = field(default_factory=anexo_b)
    familias: dict[str, str] = field(default_factory=familias_pdp)
    ficha_pdp7: dict[str, str] = field(default_factory=ficha_obligatoria_pdp7)
    casos_pdp: dict[str, CasoPdp] = field(default_factory=casos_transversales_pdp)
    destinos: dict[str, dict[str, str]] = field(default_factory=destinos_pdp_arq00)

    def comprobar_minimos(self) -> None:
        """Falla pronto si la extracción no encontró lo que el canon contiene."""
        problemas: list[str] = []
        malas = [n for n, h in self.huellas.items() if not h["coincide"]]
        if malas:
            problemas.append(f"huellas que no coinciden con el MANIFEST: {malas}")
        if len(self.casos) != 50:
            problemas.append(f"casos B04 extraídos: {len(self.casos)} (esperados 50)")
        if len(self.anexo) != 79:
            problemas.append(f"filas del Anexo B extraídas: {len(self.anexo)} (esperadas 79)")
        if len(self.familias) != 25:
            problemas.append(f"familias PDP extraídas: {len(self.familias)} (esperadas 25)")
        if len(self.ficha_pdp7) != 14:
            problemas.append(f"campos del PDP §7: {len(self.ficha_pdp7)} (esperados 14)")
        if len(self.casos_pdp) != 28:
            problemas.append(f"casos PDP-CA: {len(self.casos_pdp)} (esperados 28)")
        if len(self.destinos) != 25:
            problemas.append(f"destinos ARQ-00 §20: {len(self.destinos)} (esperados 25)")
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
    print(f"huellas verificadas: {sum(1 for h in c.huellas.values() if h['coincide'])}/3")
    print(f"casos B04: {len(c.casos)}  Anexo B: {len(c.anexo)}  familias: {len(c.familias)}")
    print(f"ficha PDP §7: {len(c.ficha_pdp7)}  PDP-CA: {len(c.casos_pdp)}")
    print(f"familias con destino ADR-002: {familias_destino_adr002()}")
    for ca, asig in asignaciones_canonicas_por_ca().items():
        print(f"  {ca}: RED={asig['red']} M={asig['metricas']} F={asig['familias']}")
