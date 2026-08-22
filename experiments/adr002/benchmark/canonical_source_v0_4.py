"""Lector canónico v0.4 · extiende el v0.3 sin sustituirlo.

Dos endurecimientos sobre ``canonical_source_v0_3`` —que se conserva intacto—:

1. **Censo global de cabeceras.** El v0.3 detecta dos candidatas cuando ambas
   comparten cabecera y contexto, pero una tabla adicional con la misma
   cabecera bajo *otro* contexto quedaba invisible. El v0.4 cuenta cuántas
   tablas de cada documento llevan cada cabecera y cuántas identidades
   registradas la reclaman: cualquier tabla de más produce error explícito.
   La comprobación contextual del v0.3 no se sustituye: se aplican ambas.

2. **Expansión estricta de métricas.** ``_expandir_metricas`` del v0.3
   devolvía texto crudo ante una forma desconocida y dejaba que el validador
   lo descubriera después. La versión estricta soporta únicamente las formas
   realmente observadas en el Anexo B —``B04-M16``, ``B08-M12/M25``,
   ``B04-M21/B05-M16``, ``PDP-M01..M17`` (rango con raya)— conservando el prefijo en las
   continuaciones, y falla de inmediato ante una pieza o separador no
   reconocido.

Determinista: bytes fijos verificados por SHA-256 contra ``MANIFEST.md``.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from experiments.adr002.benchmark import canonical_source_v0_3 as CS3

# Reexportado para los consumidores v0.4: el lector base no cambia.
FuenteCanonicaError = CS3.FuenteCanonicaError
TablaCanonicaError = CS3.TablaCanonicaError
Canon = CS3.Canon
CasoCanonico = CS3.CasoCanonico
FilaAnexoB = CS3.FilaAnexoB
CasoPdp = CS3.CasoPdp
IDENTIDADES = CS3.IDENTIDADES
INVARIANTES = CS3.INVARIANTES
CAMPOS_PDP7_CANONICOS = CS3.CAMPOS_PDP7_CANONICOS
B04 = CS3.B04
PDP = CS3.PDP
ARQ00 = CS3.ARQ00

tablas = CS3.tablas
tabla = CS3.tabla
inventario_de_tablas = CS3.inventario_de_tablas
verificar_huellas = CS3.verificar_huellas
casos_b04 = CS3.casos_b04
anexo_b = CS3.anexo_b
registro_red = CS3.registro_red
asignaciones_canonicas_por_ca = CS3.asignaciones_canonicas_por_ca
asignaciones_canonicas_por_pdp_ca = CS3.asignaciones_canonicas_por_pdp_ca
metricas_del_anexo_b = CS3.metricas_del_anexo_b
ficha_obligatoria_pdp7 = CS3.ficha_obligatoria_pdp7
familias_pdp = CS3.familias_pdp
casos_transversales_pdp = CS3.casos_transversales_pdp
destinos_pdp_arq00 = CS3.destinos_pdp_arq00
expandir_destinos = CS3.expandir_destinos
familias_destino_adr002 = CS3.familias_destino_adr002
alternativas_minimas_arq00 = CS3.alternativas_minimas_arq00
reglas_cardinalidad_b04 = CS3.reglas_cardinalidad_b04
s1_prohibida_en_exhaustiva = CS3.s1_prohibida_en_exhaustiva
normalizar = CS3.normalizar


# ---------------------------------------------------------------------------
# 1. Censo global de cabeceras
# ---------------------------------------------------------------------------


def censo_de_cabeceras() -> list[dict[str, Any]]:
    """Cabeceras reclamadas por identidades: tablas reales frente a esperadas."""
    esperadas: Counter[tuple[str, tuple[str, ...]]] = Counter()
    for ident in IDENTIDADES.values():
        esperadas[(ident.documento, ident.cabecera)] += 1
    salida: list[dict[str, Any]] = []
    for (documento, cabecera), n_esperadas in sorted(esperadas.items()):
        reales = [t.indice for t in tablas(documento) if t.cabecera == cabecera]
        salida.append(
            {
                "documento": documento,
                "cabecera": list(cabecera),
                "tablas_reales": reales,
                "n_reales": len(reales),
                "n_identidades": n_esperadas,
            }
        )
    return salida


def verificar_censo_de_cabeceras() -> None:
    """Una tabla de más con una cabecera reclamada falla, esté donde esté."""
    problemas: list[str] = []
    for entrada in censo_de_cabeceras():
        if entrada["n_reales"] != entrada["n_identidades"]:
            problemas.append(
                f"{entrada['documento']}: la cabecera {tuple(entrada['cabecera'])} aparece en "
                f"{entrada['n_reales']} tablas (índices {entrada['tablas_reales']}) pero "
                f"{entrada['n_identidades']} identidad(es) la reclaman"
            )
    if problemas:
        raise TablaCanonicaError("; ".join(problemas))


# ---------------------------------------------------------------------------
# 2. Expansión estricta de métricas
# ---------------------------------------------------------------------------

_RX_PIEZA_COMPLETA = re.compile(r"([A-Z0-9]+)-M(\d{2})(?:\s*[\u2013-]\s*M?(\d{2}))?\Z")
_RX_PIEZA_CONTINUA = re.compile(r"M(\d{2})(?:\s*[\u2013-]\s*M?(\d{2}))?\Z")


def expandir_metricas_estricta(celda: str) -> list[str]:
    """Como ``CS3._expandir_metricas`` pero cerrada: pieza desconocida = error.

    Formas soportadas —las realmente observadas en las 79 filas del Anexo B—:

    * ``B04-M16``                      métrica completa;
    * ``B08-M12/M25``                  continuación que hereda el prefijo;
    * ``B04-M21/B05-M16``              cambio de bloque explícito;
    * ``PDP-M01..M17``                 rango con raya (U+2013) o guion;
    * separador exclusivamente ``/``.
    """
    salida: list[str] = []
    prefijo = ""
    for bruto in celda.strip().split("/"):
        pieza = bruto.strip()
        if not pieza:
            raise FuenteCanonicaError(f"métrica vacía en la celda {celda!r}")
        m = _RX_PIEZA_COMPLETA.match(pieza)
        if m:
            prefijo = m.group(1)
            inicio, fin = int(m.group(2)), int(m.group(3) or m.group(2))
            salida.extend(f"{prefijo}-M{n:02d}" for n in range(inicio, fin + 1))
            continue
        m = _RX_PIEZA_CONTINUA.match(pieza)
        if m and prefijo:
            inicio, fin = int(m.group(1)), int(m.group(2) or m.group(1))
            salida.extend(f"{prefijo}-M{n:02d}" for n in range(inicio, fin + 1))
            continue
        raise FuenteCanonicaError(
            f"forma de métrica no reconocida en el Anexo B: {pieza!r} (celda {celda!r}); "
            "el lector v0.4 no acepta texto crudo"
        )
    return salida


def verificar_metricas_estrictas() -> None:
    """Toda celda de métrica del Anexo B debe expandir de forma estricta e igual."""
    for celdas in tabla("pdp_anexo_b").filas:
        estricta = expandir_metricas_estricta(celdas[3])
        laxa = CS3._expandir_metricas(celdas[3])
        if estricta != laxa:
            raise FuenteCanonicaError(
                f"{celdas[0]}: la expansión estricta {estricta} difiere de la del lector "
                f"v0.3 {laxa} para {celdas[3]!r}"
            )


# ---------------------------------------------------------------------------
# 3. Carga del canon con las dos comprobaciones nuevas
# ---------------------------------------------------------------------------


def cargar_canon() -> Canon:
    """Canon v0.3 más censo de cabeceras y métricas estrictas."""
    canon = CS3.cargar_canon()
    verificar_censo_de_cabeceras()
    verificar_metricas_estrictas()
    return canon


if __name__ == "__main__":  # pragma: no cover - inspección manual
    cargar_canon()
    for fila in censo_de_cabeceras():
        print(
            f"{fila['documento'].split('_')[2]:8s} x{fila['n_reales']} tablas "
            f"(identidades {fila['n_identidades']}): {tuple(fila['cabecera'])!s:.70s}"
        )
    print("censo de cabeceras y métricas estrictas: OK")
