"""El padre que atiende una orden de investigación (B1, ADR-099).

Lee el ``## Objetivo`` del cuerpo de la incidencia, construye el entorno del
investigador DESDE CERO -reutilizando las piezas ya medidas de
``comparar_investigadores``: la configuración elegida por ADR-098, la clave por
su nombre declarado, las opcionales, el tapado de secretos- y lanza al hijo
(``investigar_orden.py``). Con el informe y sus fuentes compone el documento en
``docs/investigaciones/`` con la cabecera de caducidad que su guardián exige
—ese guardián corre en Quality sobre la PR del propio informe: un documento sin
cabecera moriría en su propia revisión—.

El protocolo con el ciclo es EXACTAMENTE el del implementador (criterio de
parada (a) de la nota de arranque: hablar el idioma del ciclo, no enseñarle
otro): el veredicto PROVISIONAL ``FAILED_SAFELY`` se escribe ANTES de tocar
nada, y la última acción lo sustituye por el definitivo. La PR y el comentario
``PR abierta:`` los pone el workflow, que es quien tiene el token; este guion
deja el fichero y el veredicto.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from comparar_investigadores import (
    ConfiguracionInvalida,
    cargar_configuraciones,
    entorno_desde_cero,
    sin_secretos,
)

RAIZ = Path(__file__).resolve().parents[2]
HIJO = Path(__file__).resolve().parent / "investigar_orden.py"
CONFIGURACIONES = Path(__file__).resolve().parent / "configuraciones.yml"

#: Margen del hijo respecto al plazo del padre, mismo criterio que el banco:
#: el plazo de dentro SIEMPRE antes que el de fuera, para morir escribiendo.
MARGEN_DEL_HIJO = 0.9


def extraer_pregunta(cuerpo: str) -> str:
    """El texto del ``## Objetivo``, que es la pregunta de la orden.

    El cuerpo lo escribió el propio despachador (`issue_body.py`), así que el
    formato es conocido; aun así se lee con tolerancia a espacios porque un
    cuerpo editado a mano no puede convertir la orden en silencio.
    """
    encaje = re.search(r"^##\s*Objetivo\s*\n(.*?)(?=^##\s|\Z)", cuerpo, re.MULTILINE | re.DOTALL)
    return encaje.group(1).strip() if encaje else ""


def _slug(texto: str, tope: int = 60) -> str:
    plano = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    plano = re.sub(r"[^A-Za-z0-9]+", "-", plano).strip("-").lower()
    return plano[:tope].rstrip("-") or "orden"


def componer_documento(
    *, pregunta: str, informe: str, fuentes: list[str], numero: int, fecha: str
) -> str:
    """El documento con la cabecera que exige el guardián de caducidad."""
    pregunta_yaml = " ".join(pregunta.split())
    lineas = [
        "---",
        f"titulo: Investigación de la orden #{numero}",
        f"fecha: {fecha}",
        "autor: el investigador del motor (B1, ADR-099; configuración de ADR-098)",
        "pregunta: >-",
        f"  {pregunta_yaml}",
        "caduca_con:",
        "  - los datos y las fuentes que cita el informe",
        "  - la fecha de esta ejecución: es UNA pasada del investigador, no un hecho estable",
        "estado: VIGENTE",
        "---",
        "",
        f"# Investigación de la orden #{numero} — {fecha}",
        "",
        "> Informe producido por el investigador del motor (gpt-researcher "
        f"{'0.15.1'}, `research_report`, NVIDIA + Tavily) a partir del "
        "`## Objetivo` de la incidencia. Las fuentes están al final; el número "
        "de fuentes es la misma unión que gobierna la medición del banco.",
        "",
        informe.strip(),
        "",
        "## Fuentes",
        "",
    ]
    lineas += [f"- {url}" for url in fuentes]
    lineas.append("")
    return "\n".join(lineas)


def _escribir_veredicto(ruta: Path, veredicto: str, resumen: str, **extra: Any) -> None:
    ruta.write_text(
        json.dumps({"verdict": veredicto, "summary": resumen, **extra}, ensure_ascii=False),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Atiende una orden de investigación (B1).")
    parser.add_argument("--cuerpo", required=True, help="fichero con el cuerpo de la incidencia")
    parser.add_argument("--numero", required=True, type=int)
    parser.add_argument("--veredicto", required=True, help="ruta del JSON de veredicto")
    parser.add_argument("--plazo", type=int, default=1200)
    parser.add_argument("--salida-dir", default=str(RAIZ / "docs" / "investigaciones"))
    parser.add_argument("--configuraciones", default=str(CONFIGURACIONES))
    args = parser.parse_args(argv)

    veredicto = Path(args.veredicto)
    # PRIMERO el provisional: si esto muere a mitad, el ciclo encuentra un
    # veredicto y no un silencio. Es el mismo protocolo del implementador.
    _escribir_veredicto(
        veredicto,
        "FAILED_SAFELY",
        "Investigación interrumpida antes de terminar: este veredicto provisional "
        "se escribió al empezar y no llegó a sustituirse.",
    )

    pregunta = extraer_pregunta(Path(args.cuerpo).read_text(encoding="utf-8"))
    if not pregunta:
        _escribir_veredicto(
            veredicto,
            "FAILED_SAFELY",
            "El cuerpo de la incidencia no tiene sección `## Objetivo` legible: "
            "no hay pregunta que investigar.",
        )
        return 3

    try:
        configuraciones = cargar_configuraciones(Path(args.configuraciones))
    except ConfiguracionInvalida as exc:
        _escribir_veredicto(veredicto, "FAILED_SAFELY", f"Configuración inválida: {exc}")
        return 4
    configuracion = configuraciones[0]
    import os

    clave = os.environ.get(configuracion.variable_de_clave, "").strip()
    if not clave:
        _escribir_veredicto(
            veredicto,
            "FAILED_SAFELY",
            f"Falta la clave {configuracion.variable_de_clave} en el entorno: "
            "sin ella no se puede investigar.",
        )
        return 4
    secretos = [clave] + [
        os.environ.get(origen, "").strip()
        for origen, _destino in configuracion.claves_opcionales
        if os.environ.get(origen, "").strip()
    ]

    salida_json = veredicto.parent / f"investigacion-{args.numero}.json"
    plazo_hijo = max(60, int(args.plazo * MARGEN_DEL_HIJO))
    proceso = subprocess.run(
        [
            sys.executable,
            str(HIJO),
            "--pregunta",
            pregunta,
            "--salida",
            str(salida_json),
            "--plazo",
            str(plazo_hijo),
        ],
        env=entorno_desde_cero(configuracion, clave),
        cwd=str(RAIZ),
        capture_output=True,
        text=True,
        timeout=args.plazo,
        check=False,
    )
    cola = sin_secretos((proceso.stderr or proceso.stdout or "").strip(), secretos)[-1500:]

    if proceso.returncode != 0 or not salida_json.is_file():
        _escribir_veredicto(
            veredicto,
            "FAILED_SAFELY",
            f"El investigador terminó con código {proceso.returncode}. Final de su salida:\n{cola}",
        )
        return 3
    resultado = json.loads(sin_secretos(salida_json.read_text(encoding="utf-8"), secretos))
    if resultado.get("error"):
        _escribir_veredicto(veredicto, "FAILED_SAFELY", str(resultado["error"]))
        return 3

    fecha = datetime.now(UTC).strftime("%Y-%m-%d")
    nombre = f"{fecha}-orden-{args.numero}-{_slug(pregunta)}.md"
    destino = Path(args.salida_dir) / nombre
    destino.write_text(
        componer_documento(
            pregunta=pregunta,
            informe=str(resultado["informe"]),
            fuentes=[str(u) for u in resultado.get("fuentes") or []],
            numero=args.numero,
            fecha=fecha,
        ),
        encoding="utf-8",
    )
    # Relativa solo si de verdad cuelga de la raíz: las pruebas escriben en un
    # directorio propio y una ruta absoluta ahí es tan válida como la real.
    ruta = destino.relative_to(RAIZ) if destino.is_relative_to(RAIZ) else destino
    fuentes = len(resultado.get("fuentes") or [])
    _escribir_veredicto(
        veredicto,
        "READY_FOR_REVIEW",
        f"Informe escrito en {ruta} con {fuentes} fuentes.",
        ruta_informe=str(ruta),
    )
    sys.stdout.write(f"INFORME={ruta}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
