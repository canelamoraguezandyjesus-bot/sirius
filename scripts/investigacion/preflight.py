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
        "generar": "https://generativelanguage.googleapis.com/v1beta/{modelo}:generateContent",
        "vectorizar": "https://generativelanguage.googleapis.com/v1beta/{modelo}:embedContent",
    },
    "nvidia": {
        "variable": "NVIDIA_API_KEY",
        "host": "integrate.api.nvidia.com",
        "listar": "https://integrate.api.nvidia.com/v1/models",
        "cabecera_clave": "Authorization",
        "prefijo": "Bearer ",
        "generar": "https://integrate.api.nvidia.com/v1/chat/completions",
        "vectorizar": "https://integrate.api.nvidia.com/v1/embeddings",
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


def _prueba_de_vida(proveedor: str, clave: str, modelos_configurados: list[str]) -> dict[str, Any]:
    """Que un modelo EXISTA en el catálogo no significa que puedas usarlo.

    Son dos preguntas distintas y confundirlas cuesta una noche: un modelo puede
    estar listado y quedar fuera de la cuota gratuita de la cuenta, o exigir un
    campo que la vía compatible con OpenAI no manda —el vectorizador de NVIDIA
    pide `input_type: query|passage`, y una llamada estándar no lo lleva—.

    Aquí se USA cada uno, una vez: una frase de generación y una palabra de
    vectorización. Es la diferencia entre «figura en la lista» y «me contesta».

    COSTE: unas decenas de tokens por proveedor. Céntimos.
    """
    ficha = PROVEEDORES[proveedor]
    cabecera, prefijo = str(ficha["cabecera_clave"]), str(ficha["prefijo"])
    resultado: dict[str, Any] = {}

    for modelo in modelos_configurados:
        es_vector = "embed" in modelo.lower()
        if proveedor == "google":
            plantilla = ficha["vectorizar"] if es_vector else ficha["generar"]
            # Google exige el prefijo `models/` en la ruta; el catálogo ya lo trae
            # en unos nombres y en otros no, así que se normaliza aquí.
            ruta = modelo if modelo.startswith("models/") else f"models/{modelo}"
            url = str(plantilla).format(modelo=ruta)
            cuerpo: dict[str, Any] = (
                {"content": {"parts": [{"text": "hola"}]}}
                if es_vector
                else {"contents": [{"parts": [{"text": "Responde solo: hola"}]}]}
            )
        else:
            url = str(ficha["vectorizar"] if es_vector else ficha["generar"])
            cuerpo = (
                # `input_type` es obligatorio en los vectorizadores de NVIDIA y
                # NO lo manda una llamada compatible con OpenAI estandar. Es
                # justo el detalle que solo se descubre usandolo.
                {"input": ["hola"], "model": modelo, "input_type": "query"}
                if es_vector
                else {
                    "model": modelo,
                    "messages": [{"role": "user", "content": "Responde solo: hola"}],
                    "max_tokens": 8,
                }
            )

        codigo, datos, error = _pedir(url, clave, cabecera, prefijo, cuerpo)
        resultado[modelo] = {
            "usable": bool(codigo == 200 and datos),
            "codigo_http": codigo,
            "error": error or None,
        }
    return resultado


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

    # LA PREGUNTA QUE DE VERDAD IMPORTA: ¿existen los que tengo configurados?
    # Sin esto habia que leerse el catalogo entero a ojo, y asi fue como tres
    # modelos muertos sobrevivieron a un plan, a un spike y a una investigacion.
    informe["configurados"] = {
        nombre: any(nombre in m or m.endswith(nombre) for m in modelos)
        for nombre in _configurados(proveedor)
    }

    # Y USARLOS. Existir no es poder usarse: cuota, permisos y forma de la
    # llamada solo se comprueban llamando.
    vivos = [n for n, existe in informe["configurados"].items() if existe]
    informe["prueba_de_vida"] = _prueba_de_vida(proveedor, clave, vivos) if vivos else {}
    return informe


def _configurados(proveedor: str) -> list[str]:
    """Los modelos que `configuraciones.yml` declara para este proveedor.

    Se leen del fichero real, no de una lista escrita aqui: una copia se queda
    atras en cuanto alguien toca el original, y entonces el preflight diria que
    todo esta vivo mientras produccion apunta a un modelo muerto. Es la misma
    familia de defecto que ya mordio dos veces en este repositorio.
    """
    import re as _re
    from pathlib import Path as _Path

    ruta = _Path(__file__).resolve().parent / "configuraciones.yml"
    if not ruta.is_file():
        return []
    texto = ruta.read_text(encoding="utf-8")
    # `FAST_LLM: "openai:meta/llama-3.3-70b"` -> `meta/llama-3.3-70b`
    encontrados = _re.findall(
        r'(?:FAST_LLM|SMART_LLM|STRATEGIC_LLM|EMBEDDING):\s*"([^:"]+):([^"]+)"', texto
    )
    familia = "google_genai" if proveedor == "google" else "openai"
    return sorted({modelo for adaptador, modelo in encontrados if adaptador == familia})


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

    # EL RESUMEN VA AL FINAL, Y NO ES ESTETICA. La cola de un log de Actions es
    # lo unico que se lee sin descargar nada, y un catalogo de 84 modelos empuja
    # fuera de ella justo la linea que importa. Con esto, la respuesta a «existen
    # los modelos que tengo configurados» se lee de un vistazo.
    sys.stdout.write("\n===== RESUMEN =====\n")
    for informe in informes:
        estado = "OK" if informe.get("atestado") else "FALLO"
        sys.stdout.write(
            f"{informe['proveedor']:8} {estado:6} "
            f"{informe.get('cuantos_modelos', 0)} modelos"
            f"{'  ' + str(informe['error']) if informe.get('error') else ''}\n"
        )
        prueba = informe.get("prueba_de_vida") or {}
        for nombre, existe in (informe.get("configurados") or {}).items():
            if not existe:
                sys.stdout.write(f"         NO EXISTE  {nombre}\n")
                continue
            uso = prueba.get(nombre) or {}
            if uso.get("usable"):
                sys.stdout.write(f"         USABLE     {nombre}\n")
            else:
                detalle = str(uso.get("error") or f"HTTP {uso.get('codigo_http')}")[:110]
                sys.stdout.write(f"         NO RESPONDE {nombre}  ->  {detalle}\n")

    # Rojo si alguno no contestó: un preflight que calla ante un fallo sería otra
    # vez el verde que no significa nada.
    # Rojo si alguno no contesto, si algun modelo configurado no existe, o si
    # existe y NO RESPONDE. Un preflight que se conforma con «esta en la lista»
    # deja pasar exactamente el fallo que este paso existe para cazar.
    def _bien(informe: dict[str, Any]) -> bool:
        if not informe.get("atestado"):
            return False
        if not all((informe.get("configurados") or {}).values()):
            return False
        prueba = informe.get("prueba_de_vida") or {}
        return bool(prueba) and all(u.get("usable") for u in prueba.values())

    return 0 if all(_bien(i) for i in informes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
