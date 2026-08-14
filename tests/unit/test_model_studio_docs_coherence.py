"""El documento de reconciliación no puede decir que E3 no existe cuando existe.

Decía «Ni una línea de código» de la etapa de captura en el mismo commit que la
implementaba entera. Una instantánea que no se marca como tal se lee como estado
vigente, y quien la crea programa contra un repositorio que ya no está ahí.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCUMENTO = (
    REPO_ROOT
    / "docs"
    / "implementation"
    / "model_studio"
    / "SIRIUS_MODEL_STUDIO_RECONCILIACION_v1.0_PROPUESTA.md"
)
ADAPTADOR_DE_CAPTURA = REPO_ROOT / "src" / "sirius" / "adapters" / "capture" / "obs_websocket.py"

AFIRMACIONES_DE_AUSENCIA = ("E3 · Captura y cámaras — SIN EMPEZAR", "Ni una línea de código")


def test_una_afirmacion_de_ausencia_vive_dentro_de_una_instantanea_marcada() -> None:
    if not ADAPTADOR_DE_CAPTURA.exists():
        return  # sin captura implementada, la afirmación sería cierta

    lineas = DOCUMENTO.read_text(encoding="utf-8").splitlines()
    for numero, linea in enumerate(lineas):
        if not any(afirmacion in linea for afirmacion in AFIRMACIONES_DE_AUSENCIA):
            continue
        # Por sección y no por distancia en líneas: una ventana fija se rompe en
        # cuanto alguien añade un párrafo entre la marca y la afirmación, y
        # entonces la prueba mide la maquetación en vez del documento.
        seccion = _seccion_que_contiene(lineas, numero)
        assert "Instantánea congelada" in seccion, (
            f"{DOCUMENTO.name}:{numero + 1} afirma que la captura no está escrita, "
            "y el adaptador existe. O la sección se marca como instantánea "
            "congelada, o la afirmación se corrige."
        )


def _seccion_que_contiene(lineas: list[str], numero: int) -> str:
    """Texto de la sección de primer nivel (`## `) en la que cae esa línea."""
    inicio = 0
    for indice in range(numero, -1, -1):
        if lineas[indice].startswith("## "):
            inicio = indice
            break
    return "\n".join(lineas[inicio : numero + 1])
