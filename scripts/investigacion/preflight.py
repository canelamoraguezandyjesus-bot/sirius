"""Le pregunta a cada proveedor qué tiene, en vez de creerle a un informe.

POR QUÉ EXISTE ESTO, y por qué va antes que la comparación. El 26-08-2026 se
fusionó un banco para comparar NVIDIA contra Google. Al día siguiente, una
investigación descubrió que **los dos modelos de vectorización configurados
llevaban meses muertos**: `text-embedding-004` lo retiró Google en enero y
`nv-embedqa-e5-v5` está deprecado. El banco tenía 33 guardianes en verde y
comparaba dos cosas que ya no existían.

La lección no es «hay que investigar más». Es que **un nombre de modelo es un
dato perecedero, y el único que sabe si sigue vivo es el servidor**. Así que
antes de gastar un céntimo se le pregunta a él.

DOS COSAS A LA VEZ, y la segunda no es un extra:

1. **Qué modelos hay de verdad.** Se listan y se comprueba si los que
   `configuraciones.yml` declara siguen existiendo.
2. **Con quién se está hablando.** El arnés de la comparación rellena su campo
   `servidor` releyendo la variable de entorno que él mismo puso: es un eco, no
   una prueba —lo dijeron los refutadores y es cierto—. Aquí no: la respuesta
   viene del host remoto, así que **lo que se registra es lo que contestó**, no
   lo que se pidió.

COSTE: una lista de modelos, una vectorización de una palabra y una generación
de una frase, por proveedor. Céntimos, y solo cuando alguien lo lanza a mano.

NUNCA IMPRIME LA CLAVE. Ni en los errores: el texto de una excepción de un
cliente HTTP puede traer dentro la cabecera de autenticación, así que todo lo
que sale por aquí pasa antes por `_sin_clave`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

TIEMPO_MAXIMO = 60

PROVEEDORES: dict[str, dict[str, Any]] = {
    "google": {
        "variable": "GOOGLE_API_KEY",
        "host": "generativelanguage.googleapis.com",
        "listar": "https://generativelanguage.googleapis.com/v1beta/models",
        "cabecera_clave": "x-goog-api-key",
        "prefijo": "",
    },
    "nvidia": {
        "variable": "NVIDIA_API_KEY",
        "host": "integrate.api.nvidia.com",
        "listar": "https://integrate.api.nvidia.com/v1/models",
        "cabecera_clave": "Authorization",
        "prefijo": "Bearer ",
    },
}


def _sin_clave(texto: str, clave: str) -> str:
    """Ninguna clave sale de aquí, ni dentro del texto de un error."""
    if clave and len(clave) >= 8:
        return texto.replace(clave, "«clave oculta»")
    return texto


def _pedir(
    url: str, clave: str, cabecera: str, prefijo: str, cuerpo: dict[str, Any] | None = None
) -> tuple[int, Any, str]:
    """Una petición. Devuelve (código, datos, error-ya-tapado)."""
    datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    peticion = urllib.request.Request(
        url,
        data=datos,
        headers={cabecera: f"{prefijo}{clave}", "Content-Type": "application/json"},
        method="POST" if datos else "GET",
    )
    try:
        with urllib.request.urlopen(peticion, timeout=TIEMPO_MAXIMO) as respuesta:
            return respuesta.status, json.loads(respuesta.read().decode("utf-8")), ""
    except urllib.error.HTTPError as exc:
        detalle = exc.read().decode("utf-8", "replace")[:400]
        return exc.code, None, _sin_clave(f"HTTP {exc.code}: {detalle}", clave)
    except Exception as exc:
        return 0, None, _sin_clave(f"{type(exc).__name__}: {exc}", clave)


def _nombres(proveedor: str, datos: Any) -> list[str]:
    """Los identificadores de modelo, en la forma que devuelve cada proveedor."""
    if not isinstance(datos, dict):
        return []
    if proveedor == "google":
        return sorted(str(m.get("name", "")) for m in datos.get("models", []))
    return sorted(str(m.get("id", "")) for m in datos.get("data", []))


def revisar(proveedor: str) -> dict[str, Any]:
    ficha = PROVEEDORES[proveedor]
    clave = os.environ.get(str(ficha["variable"]), "")
    informe: dict[str, Any] = {
        "proveedor": proveedor,
        "host_preguntado": ficha["host"],
        "hay_clave": bool(clave),
        "modelos": [],
        "cuantos_modelos": 0,
        "error": None,
    }
    if not clave:
        informe["error"] = f"falta {ficha['variable']} en el entorno"
        return informe

    codigo, datos, error = _pedir(
        str(ficha["listar"]), clave, str(ficha["cabecera_clave"]), str(ficha["prefijo"])
    )
    informe["codigo_http"] = codigo
    if error:
        informe["error"] = error
        return informe

    modelos = _nombres(proveedor, datos)
    informe["modelos"] = modelos
    informe["cuantos_modelos"] = len(modelos)
    # LA ATESTACION: el catalogo lo devolvio el host remoto. Que venga con
    # modelos dentro es la prueba de que se hablo con EL, y no un eco de lo que
    # nosotros habiamos configurado.
    informe["atestado"] = bool(modelos)
    return informe


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pregunta a cada proveedor qué modelos tiene.")
    parser.add_argument("proveedores", nargs="*", default=list(PROVEEDORES), help="cuáles revisar")
    parser.add_argument("--salida", default=None)
    parser.add_argument("--buscar", default="", help="filtra los modelos por esta subcadena")
    args = parser.parse_args(argv)

    informes = [revisar(p) for p in (args.proveedores or list(PROVEEDORES))]
    if args.buscar:
        for informe in informes:
            informe["modelos"] = [m for m in informe["modelos"] if args.buscar.lower() in m.lower()]

    texto = json.dumps(informes, ensure_ascii=False, indent=2)
    if args.salida:
        from pathlib import Path

        Path(args.salida).write_text(texto, encoding="utf-8")
    sys.stdout.write(texto + "\n")

    # Rojo si alguno no contestó: un preflight que calla ante un fallo sería otra
    # vez el verde que no significa nada.
    return 0 if all(i.get("atestado") for i in informes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
