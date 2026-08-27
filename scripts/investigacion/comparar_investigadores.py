#!/usr/bin/env python3
"""Compara varias configuraciones del investigador, cada una en su propio proceso.

**Este fichero existe por una sola razón, y es una medición, no una preferencia
de diseño.** Leído hoy (26-08-2026) el código de `gpt-researcher` 0.15.1:

- el proveedor de modelo lee ``OPENAI_BASE_URL`` cuando el proveedor es
  ``openai`` o ``custom`` (`llm_provider/generic/base.py`), y
- el de vectorización hace exactamente lo mismo (`memory/embeddings.py`).

Es decir: **dos configuraciones dentro del mismo proceso se pisan las
variables**. Una vía compatible con OpenAI —NVIDIA— secuestra ``OPENAI_BASE_URL``
para el proceso entero, así que la configuración de Google acabaría hablando con
el servidor de NVIDIA y devolviendo *un informe perfecto*. No fallaría: mentiría.
Un verde que mide dos veces lo mismo y lo presenta como una comparación es
justamente la familia de defecto que este repositorio persigue.

De ahí las dos decisiones que gobiernan todo lo demás:

1. Cada configuración corre en un **subproceso** con el entorno **construido
   desde cero**. Nada de ``dict(os.environ)``: se copia una lista blanca corta de
   variables del sistema y se añade únicamente lo que la configuración declara.
   La regla que separa una cosa de la otra es *se hereda lo que dice **cómo**
   salir a la red; jamás lo que dice **con quién** hablar*.
2. La comparación **se demuestra**, no se promete: cada medición declara en su
   JSON contra qué servidor habló, y aquí se comprueba que no coinciden.

Códigos de salida —y esto importa porque en este repositorio las validaciones se
leen por CÓDIGO DE SALIDA, nunca por la última línea impresa—:

===  ==========================================================================
0    Hay comparación: dos o más configuraciones medidas y servidores distintos.
2    NO CONCLUYENTE: se midió menos de dos. Criterio de parada (b) de la nota de
     arranque. No es un fallo del programa —no revienta y escribe los informes—,
     pero tampoco es un 0: un 0 significaría que la comparación existe.
3    COMPARACIÓN FALSA: dos mediciones declaran el mismo servidor.
4    Configuración inválida: no se llegó a medir nada (aquí no hay informes que
     escribir, porque no hay nada que informar).
===  ==========================================================================

Lo que este guion NO hace, dicho aquí para que no se le suponga: no juzga la
calidad de la redacción, no sabe lo que cuesta en dinero ninguna de las dos vías,
y no convierte una ejecución única en una tendencia. Todo eso está declarado
también en el Markdown que emite, que es donde lo va a leer quien decida.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import yaml

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
MEDIDOR = AQUI / "medir_investigador.py"
CONFIGURACIONES = AQUI / "configuraciones.yml"

CODIGO_OK = 0
CODIGO_NO_CONCLUYENTE = 2
CODIGO_COMPARACION_FALSA = 3
CODIGO_CONFIGURACION_INVALIDA = 4
#: Se pidio medir un modelo del que no consta que responda. Es un codigo propio y
#: no un `CONFIGURACION_INVALIDA` porque la configuracion puede estar impecable:
#: lo que falta es la COMPROBACION de que ese nombre siga vivo (ADR-095).
CODIGO_SIN_ATESTADO = 5

#: Lo único que se hereda del entorno de quien llama. La lista es corta a
#: propósito y cada grupo tiene su motivo:
#:
#: - ``PATH``/``HOME``/``LANG``/temporales: sin esto el intérprete y las
#:   bibliotecas no arrancan igual en Linux y en Windows.
#: - proxy y certificados: dicen **cómo** salir a la red. En la máquina donde se
#:   escribió esto la salida HTTPS va por un proxy con su propio CA; quitarlas
#:   dejaría al subproceso sin red y el fallo parecería del proveedor.
#:
#: Ninguna de ellas dice **con quién** hablar, que es la propiedad que hace que
#: heredarlas no contamine la comparación. ``OPENAI_BASE_URL``, ``FAST_LLM``,
#: ``EMBEDDING`` y las claves NO están aquí, y no pueden estarlo.
VARIABLES_DEL_SISTEMA: tuple[str, ...] = (
    "PATH",
    "HOME",
    "USERPROFILE",
    "LANG",
    "LC_ALL",
    "TMPDIR",
    "TEMP",
    "TMP",
    "SYSTEMROOT",
    "PATHEXT",
    "COMSPEC",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "no_proxy",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "REQUESTS_CA_BUNDLE",
    "CURL_CA_BUNDLE",
)

#: Variables que configuran al investigador. Si alguna se colara en el entorno
#: del subproceso sin que la configuración la haya declarado, la medición estaría
#: contaminada. Se comprueba en `entorno_desde_cero`: es el guardarraíl contra el
#: `dict(os.environ)` que alguien añadirá dentro de seis meses con la mejor
#: intención.
VARIABLES_QUE_CONTAMINAN: tuple[str, ...] = (
    "OPENAI_BASE_URL",
    "OPENAI_API_KEY",
    "OPENAI_EMBEDDING_MODEL",
    "GOOGLE_API_KEY",
    "ANTHROPIC_API_KEY",
    "NVIDIA_API_KEY",
    "GROQ_API_KEY",
    "LLM_PROVIDER",
    "EMBEDDING_PROVIDER",
    "FAST_LLM",
    "FAST_LLM_MODEL",
    "SMART_LLM",
    "SMART_LLM_MODEL",
    "STRATEGIC_LLM",
    "EMBEDDING",
    "RETRIEVER",
    "CONFIG_PATH",
    "REASONING_EFFORT",
)

#: Criterio de parada (a) de la nota de arranque: «si hiciera falta clave de
#: OpenAI o Anthropic, se para y se sube al propietario». Se comprueba sobre el
#: ORIGEN de la clave, jamás sobre su destino: NVIDIA entra por la vía compatible
#: con OpenAI y su clave viaja dentro del subproceso llamándose
#: ``OPENAI_API_KEY``, lo cual es legítimo y no dispara nada.
CLAVES_QUE_OBLIGAN_A_PARAR: tuple[str, ...] = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY")

#: Un nombre de variable que acabe así casi seguro contiene un secreto. Sirve
#: para que `configuraciones.yml` no pueda convertirse en el sitio donde alguien
#: pega una clave «solo para probar».
NOMBRE_DE_SECRETO = re.compile(r"(API_KEY|_TOKEN|SECRET|PASSWORD)$", re.IGNORECASE)

OCULTO = "«clave oculta»"

ESTADO_MEDIDA = "medida"
ESTADO_SIN_CLAVE = "sin_clave"
ESTADO_FALLO = "fallo"
ESTADO_TIEMPO_AGOTADO = "agotado_el_tiempo"

#: El código con el que `medir_investigador.py` dice «medí algo y NO te lo creas»:
#: escribe su JSON entero, con el motivo dentro, y sale con 3.
#:
#: TIENE QUE COMPROBARSE ANTES que «código != 0», y por eso está aquí arriba con
#: su explicación. Hasta el 27-08-2026 no se comprobaba, y la consecuencia fue una
#: rama inalcanzable: la guarda genérica atrapaba el 3, ponía como detalle la cola
#: de unos registros del buscador y volvía; el bloque de abajo que lee
#: `motivo_no_fiable` -con su comentario diciendo «el hijo ya sabe que lo suyo no
#: vale y lo dice»- no se ejecutaba NUNCA. Medido en la primera pasada real: no se
#: pudo saber por qué NVIDIA no fue fiable porque el motivo se tiró.
CODIGO_MEDICION_NO_FIABLE = 3


class ConfiguracionInvalida(Exception):
    """El fichero de configuraciones no sirve para medir. Se para antes de medir."""


@dataclass(frozen=True)
class Configuracion:
    """Una vía a comparar. `entorno` son variables literales; la clave, nunca."""

    nombre: str
    proveedor: str
    modelo: str
    variable_de_clave: str
    clave_destino: str
    entorno: dict[str, str]


@dataclass
class Medicion:
    """Lo que se sabe de una configuración después de intentar medirla.

    `estado` es el campo que separa «respondió mal» de «no llegó a intentarlo»
    —criterio de parada (c)—: solo `medida` tiene números, y solo `medida` cuenta
    para las dos configuraciones que exige el criterio (b).
    """

    nombre: str
    proveedor: str
    modelo: str
    estado: str
    detalle: str
    variable_de_clave: str
    variables_puestas: list[str]
    codigo_de_salida: int | None = None
    servidor: str | None = None
    aciertos: int | None = None
    total: int | None = None
    porcentaje: float | None = None
    segundos: float | None = None
    fuentes_medias: float | None = None
    resultado: dict[str, Any] | None = None


def cargar_configuraciones(ruta: Path) -> list[Configuracion]:
    """Lee y VALIDA el fichero de configuraciones. Prefiere no correr a correr mal.

    Cada comprobación de aquí corresponde a un modo de fallo que produciría un
    número creíble y equivocado, que es peor que una excepción:

    - un `modelo` que no coincide con lo que se pone en `FAST_LLM`/`SMART_LLM`
      haría que el informe atribuyera el resultado a un modelo que no corrió;
    - dos configuraciones con el mismo nombre se pisarían el fichero de salida;
    - un nombre de variable con pinta de secreto significa que alguien ha pegado
      una clave en un fichero versionado.
    """
    if not ruta.is_file():
        raise ConfiguracionInvalida(f"no existe el fichero de configuraciones: {ruta}")
    datos: Any = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, dict) or not datos.get("configuraciones"):
        raise ConfiguracionInvalida(f"{ruta} no declara ninguna configuración")

    configuraciones: list[Configuracion] = []
    vistos: set[str] = set()
    for cruda in datos["configuraciones"]:
        for campo in ("nombre", "proveedor", "modelo", "variable_de_clave", "clave_destino"):
            if not cruda.get(campo):
                raise ConfiguracionInvalida(f"una configuración de {ruta} no declara «{campo}»")
        nombre = str(cruda["nombre"])
        if nombre in vistos:
            raise ConfiguracionInvalida(f"la configuración «{nombre}» está declarada dos veces")
        vistos.add(nombre)

        variable_de_clave = str(cruda["variable_de_clave"])
        if variable_de_clave in CLAVES_QUE_OBLIGAN_A_PARAR:
            raise ConfiguracionInvalida(
                f"«{nombre}» pide la clave de {variable_de_clave}. Criterio de parada (a) de la "
                "nota de arranque: si hiciera falta clave de OpenAI o Anthropic, se para y se "
                "sube al propietario. (Ojo: esto mira el ORIGEN de la clave; que NVIDIA la use "
                "dentro como OPENAI_API_KEY es otra cosa y está permitido.)"
            )

        entorno_crudo: Any = cruda.get("entorno") or {}
        if not isinstance(entorno_crudo, dict):
            raise ConfiguracionInvalida(f"el «entorno» de «{nombre}» no es un mapa de variables")
        entorno: dict[str, str] = {}
        for clave, valor in entorno_crudo.items():
            nombre_variable = str(clave)
            if NOMBRE_DE_SECRETO.search(nombre_variable):
                raise ConfiguracionInvalida(
                    f"«{nombre}» declara la variable {nombre_variable} en el YAML. Las claves se "
                    "NOMBRAN (variable_de_clave), no se escriben: este fichero está versionado y "
                    "AGENTS.md prohíbe guardar claves en ficheros de texto."
                )
            entorno[nombre_variable] = str(valor)

        modelo = str(cruda["modelo"])
        for variable in ("FAST_LLM", "SMART_LLM"):
            valor = entorno.get(variable, "")
            if modelo not in valor:
                raise ConfiguracionInvalida(
                    f"«{nombre}» declara el modelo «{modelo}» pero pone {variable}={valor!r}. El "
                    "informe atribuiría el resultado a un modelo que no ha corrido."
                )

        configuraciones.append(
            Configuracion(
                nombre=nombre,
                proveedor=str(cruda["proveedor"]),
                modelo=modelo,
                variable_de_clave=variable_de_clave,
                clave_destino=str(cruda["clave_destino"]),
                entorno=entorno,
            )
        )
    return configuraciones


def entorno_desde_cero(configuracion: Configuracion, clave: str) -> dict[str, str]:
    """Construye el entorno del subproceso PARTIENDO DE UN DICCIONARIO VACÍO.

    Aquí es donde vive la razón de ser del fichero. No se parte de
    ``os.environ``: se parte de ``{}`` y se añade (1) la lista blanca de
    variables del sistema, (2) lo que la configuración declara y (3) la clave,
    con el nombre que espera la herramienta.

    La comprobación final no es decorativa. Hoy es trivialmente cierta —el
    diccionario empieza vacío—, y por eso mismo es una prueba de regresión
    barata: el día que alguien «arregle» un fallo de entorno metiendo un
    ``dict(os.environ)`` aquí, el guion se parará en vez de publicar una
    comparación en la que una configuración habló con el servidor de la otra.
    """
    entorno: dict[str, str] = {}
    for variable in VARIABLES_DEL_SISTEMA:
        valor = os.environ.get(variable)
        if valor is not None:
            entorno[variable] = valor
    entorno.update(configuracion.entorno)
    entorno[configuracion.clave_destino] = clave

    declaradas = set(configuracion.entorno) | {configuracion.clave_destino}
    coladas = [v for v in VARIABLES_QUE_CONTAMINAN if v in entorno and v not in declaradas]
    if coladas:
        raise ConfiguracionInvalida(
            f"el entorno de «{configuracion.nombre}» arrastra {', '.join(coladas)} sin haberlas "
            "declarado. Eso es exactamente la contaminación que este guion existe para impedir: "
            "una configuración hablaría con el servidor de la otra y el informe saldría perfecto."
        )
    return entorno


def sin_secretos(texto: str, secretos: Iterable[str]) -> str:
    """Tapa cualquier clave que se haya colado en la salida capturada.

    No se espera que un mensaje de error traiga la clave, pero «no se espera» no
    es una garantía y este texto acaba en un fichero versionado y en el registro
    de GitHub Actions. Se ignoran los valores muy cortos: sustituir una cadena de
    tres letras destrozaría el mensaje sin proteger nada.
    """
    limpio = texto
    for secreto in secretos:
        if secreto and len(secreto) >= 8:
            limpio = limpio.replace(secreto, OCULTO)
    return limpio


def _fuentes_medias(resultado: dict[str, Any]) -> float:
    preguntas = list(resultado.get("preguntas") or [])
    if not preguntas:
        return 0.0
    return round(sum(int(p.get("fuentes", 0)) for p in preguntas) / len(preguntas), 1)


def desglose_por_pregunta(medicion: Medicion, tope: int = 220) -> list[str]:
    """Una línea por pregunta, para el REGISTRO del trabajo.

    POR QUÉ EXISTE, y no es adorno. El detalle de cada pregunta —qué error dio,
    cuántas fuentes trajo, cuánto tardó— viaja en el JSON, y el JSON se sube como
    artefacto. Un artefacto **no se puede leer desde una sesión**: hay que
    descargarlo a mano. El 27-08-2026 eso significó una pasada entera de treinta
    minutos, con las dos APIs gastadas, tras la cual la única pista disponible era
    «el subproceso terminó con código 3».

    El registro del trabajo sí se lee. Así que lo que hace falta para no volver a
    adivinar se escribe donde se puede mirar, y el JSON sigue siendo la fuente
    completa para quien lo descargue.
    """
    resultado = medicion.resultado or {}
    lineas: list[str] = []
    for pregunta in list(resultado.get("preguntas") or []):
        marca = "ok" if pregunta.get("acierta") else "NO"
        error = str(pregunta.get("error") or "").replace("\n", " ")
        cola = f" error={error[:tope]}" if error else ""
        lineas.append(
            f"    [{marca}] {pregunta.get('id')} "
            f"fuentes={pregunta.get('fuentes')} "
            f"segundos={pregunta.get('segundos')} "
            f"cortada={pregunta.get('cortada_por_plazo')}{cola}"
        )
    return lineas


def medir_configuracion(
    configuracion: Configuracion,
    carpeta: Path,
    tiempo_maximo: int,
) -> Medicion:
    """Lanza `medir_investigador.py` para UNA configuración y recoge su JSON.

    Se lee el JSON del FICHERO que escribe el hijo, no de su stdout: la
    herramienta imprime mucho por su cuenta durante la búsqueda y parsear esa
    mezcla convertiría un informe ruidoso en un fallo de medición.

    Una configuración sin clave se informa y se salta: si el propietario solo ha
    puesto una de las dos, la que hay se mide igual. Que falten mediciones lo
    resuelve el veredicto final, no una excepción aquí.
    """
    base = Medicion(
        nombre=configuracion.nombre,
        proveedor=configuracion.proveedor,
        modelo=configuracion.modelo,
        estado=ESTADO_SIN_CLAVE,
        detalle="",
        variable_de_clave=configuracion.variable_de_clave,
        variables_puestas=sorted(configuracion.entorno),
    )

    clave = os.environ.get(configuracion.variable_de_clave, "").strip()
    if not clave:
        base.detalle = (
            f"la variable {configuracion.variable_de_clave} no está en el entorno; no se ha "
            "intentado medir. Esto NO es un suspenso de la configuración."
        )
        return base

    entorno = entorno_desde_cero(configuracion, clave)
    salida_json = carpeta / f"{configuracion.nombre}.json"
    orden = [
        sys.executable,
        str(MEDIDOR),
        configuracion.nombre,
        "--salida",
        str(salida_json),
        # EL HIJO SABE DE CUÁNTO DISPONE. Sin esto reparte sobre un valor por
        # defecto que no tiene nada que ver con el plazo real del padre, y vuelve
        # a morir con las respuestas dentro. El padre sigue matando a los
        # `tiempo_maximo` s: eso pasa a ser la red de seguridad, no el mecanismo.
        "--presupuesto",
        str(tiempo_maximo),
    ]
    try:
        # Sin `shell=True` y con la orden como lista: nada de lo que viene del YAML
        # llega a un intérprete de órdenes.
        proceso = subprocess.run(
            orden,
            env=entorno,
            cwd=str(RAIZ),
            capture_output=True,
            text=True,
            timeout=tiempo_maximo,
            check=False,
        )
    except subprocess.TimeoutExpired:
        base.estado = ESTADO_TIEMPO_AGOTADO
        base.detalle = (
            f"el subproceso pasó de {tiempo_maximo} s y se cortó. Sin informe no hay corrección "
            "posible: no llegó a intentarlo, no es que respondiera mal."
        )
        return base

    cola = sin_secretos((proceso.stderr or proceso.stdout or "").strip(), [clave])[-2000:]
    base.codigo_de_salida = proceso.returncode
    # UN 3 CON JSON NO ES UN FALLO: es un veredicto con motivo escrito, y pasa de
    # largo esta guarda a propósito para que abajo se lea. Un 3 SIN JSON sí es un
    # fallo -el hijo se murió antes de escribirlo- y cae aquí como cualquier otro.
    fiable_pero_dice_que_no = (
        proceso.returncode == CODIGO_MEDICION_NO_FIABLE and salida_json.is_file()
    )
    if (proceso.returncode != 0 and not fiable_pero_dice_que_no) or not salida_json.is_file():
        base.estado = ESTADO_FALLO
        base.detalle = (
            f"el subproceso terminó con código {proceso.returncode}. Final de su salida:\n{cola}"
        )
        return base

    # EL JSON DEL HIJO SE TAPA ENTERO ANTES DE TOCARLO. `medir_investigador.py`
    # guarda `error = f"{type(exc).__name__}: {exc}"`, y el texto de una excepción
    # de un cliente HTTP puede traer dentro la cabecera de autenticación. Ese JSON
    # se sube como artefacto: antes solo se tapaba la cola de un subproceso que
    # había fallado, así que el único canal por el que una clave podía salir de
    # verdad era justo el que no se tapaba.
    crudo = sin_secretos(salida_json.read_text(encoding="utf-8"), [clave])
    resultado: dict[str, Any] = json.loads(crudo)
    if not resultado.get("medicion_fiable", True):
        # El hijo ya sabe que lo suyo no vale y lo dice. Copiar su porcentaje como
        # «medida completa» seria volver a la raiz que la refutacion tumbo.
        #
        # SIGUE SIN CONTAR COMO MEDIDA: lo unico que cambia desde el 27-08-2026 es
        # que ahora se llega hasta aqui y el informe puede decir POR QUE. El
        # porcentaje no se copia, y `resultado` viaja entero al JSON crudo para
        # que quien dude lea las respuestas en vez de creerse una etiqueta.
        base.estado = ESTADO_FALLO
        base.detalle = str(resultado.get("motivo_no_fiable", "medicion no fiable"))
        base.resultado = resultado
        return base
    base.estado = ESTADO_MEDIDA
    base.detalle = "medida completa"
    base.servidor = str(resultado.get("servidor", "(sin declarar)"))
    base.aciertos = int(resultado.get("aciertos", 0))
    base.total = int(resultado.get("total", 0))
    base.porcentaje = float(resultado.get("porcentaje", 0.0))
    base.segundos = float(resultado.get("segundos_totales", 0.0))
    base.fuentes_medias = _fuentes_medias(resultado)
    base.resultado = resultado
    return base


def veredicto_de_servidores(medidas: list[Medicion]) -> tuple[bool, str]:
    """¿Hablaron con servidores distintos, o es la misma medición contada dos veces?

    Se compara el campo `servidor` que declara cada medición, que sale del
    ``OPENAI_BASE_URL`` que de verdad tenía el subproceso —lo que se USÓ, no lo
    que se pidió—.

    LÍMITE, y hay que decirlo porque cambia lo que significa un verde: este campo
    solo demuestra la distinción cuando al menos una configuración declara una
    URL explícita. Dos proveedores nativos distintos (Google y otro cualquiera)
    dirían los dos «(por defecto del proveedor)» y saldrían coincidentes aunque
    de hecho hablaran con servidores diferentes. Se grita igual: no poder
    demostrar que la comparación es real y que sea falsa se tratan igual aquí,
    porque publicar el número sería lo mismo en los dos casos.
    """
    if len(medidas) < 2:
        return True, "con menos de dos mediciones no hay nada que distinguir."
    por_servidor: dict[str, list[str]] = {}
    for medida in medidas:
        por_servidor.setdefault(medida.servidor or "(sin declarar)", []).append(medida.nombre)
    repetidos = {s: n for s, n in por_servidor.items() if len(n) > 1}
    if not repetidos:
        return True, "cada configuración declaró un servidor distinto."
    partes = [f"«{s}» ← {', '.join(nombres)}" for s, nombres in repetidos.items()]
    return False, (
        "hay configuraciones que declaran el MISMO servidor: "
        + "; ".join(partes)
        + ". O una secuestró el entorno de la otra —y entonces esto es una comparación falsa, dos "
        "medidas del mismo sitio con dos etiquetas—, o ninguna declaró URL explícita y el campo no "
        "puede demostrar nada. En los dos casos el número NO se puede publicar como comparación."
    )


def informe_markdown(
    mediciones: list[Medicion],
    veredicto: str,
    motivo: str,
    servidores_ok: bool,
    motivo_servidores: str,
    fecha: str,
) -> str:
    """El informe que lee una persona. Declara primero lo que NO sostiene."""
    medidas = [m for m in mediciones if m.estado == ESTADO_MEDIDA]
    otras = [m for m in mediciones if m.estado != ESTADO_MEDIDA]

    lineas: list[str] = []
    lineas.append(f"# Comparación de investigadores — {fecha}")
    lineas.append("")
    lineas.append(f"**Veredicto: {veredicto}.** {motivo}")
    lineas.append("")
    # La segunda frase solo se escribe si de verdad corrió algo. Decir «cada una
    # corrió en su propio proceso» con cero mediciones sería afirmar en un informe
    # algo que no ha pasado, que es justo lo que este trabajo persigue.
    if medidas:
        lineas.append(
            f"Configuraciones medidas: {len(medidas)} de {len(mediciones)} declaradas. "
            "Cada una corrió en su propio proceso, con el entorno construido desde cero."
        )
    else:
        lineas.append(
            f"Ninguna de las {len(mediciones)} configuraciones declaradas llegó a medirse. "
            "No hay números que interpretar; el porqué de cada una está más abajo."
        )
    lineas.append("")

    lineas.append("## Resultado")
    lineas.append("")
    if medidas:
        lineas.append(
            "| Configuración | Proveedor | Modelo | Aciertos | % | Segundos | Fuentes medias |"
        )
        lineas.append("|---|---|---|---:|---:|---:|---:|")
        for m in sorted(medidas, key=lambda x: -(x.porcentaje or 0.0)):
            lineas.append(
                f"| {m.nombre} | {m.proveedor} | `{m.modelo}` | {m.aciertos}/{m.total} | "
                f"{m.porcentaje} | {m.segundos} | {m.fuentes_medias} |"
            )
    else:
        lineas.append("No se midió ninguna configuración. La tabla estaría vacía y lo dice así.")
    lineas.append("")

    lineas.append("## Configuraciones no medidas")
    lineas.append("")
    if otras:
        lineas.append("| Configuración | Estado | Por qué |")
        lineas.append("|---|---|---|")
        for m in otras:
            detalle = m.detalle.replace("\n", " ").replace("|", "\\|")
            lineas.append(f"| {m.nombre} | `{m.estado}` | {detalle[:300]} |")
        lineas.append("")
        lineas.append(
            "`sin_clave` significa que la clave no estaba en el entorno: **no es un suspenso**, "
            "es que no se intentó. `fallo` y `agotado_el_tiempo` tampoco cuentan como fallos de "
            "la configuración: sin informe no hay nada que corregir, y confundir «respondió mal» "
            "con «no llegó a intentarlo» es lo que prohíbe el criterio de parada (c)."
        )
    else:
        lineas.append("Ninguna: se midieron todas las declaradas.")
    lineas.append("")

    lineas.append("## Prueba de que no es la misma medición contada dos veces")
    lineas.append("")
    lineas.append(
        "`gpt-researcher` 0.15.1 lee `OPENAI_BASE_URL` tanto para el modelo "
        "(`llm_provider/generic/base.py`) como para la vectorización (`memory/embeddings.py`). "
        "Dos configuraciones en un mismo proceso se pisarían esa variable y la segunda hablaría "
        "con el servidor de la primera, devolviendo un informe impecable y falso. Por eso cada "
        "una declara con qué servidor habló de verdad:"
    )
    lineas.append("")
    if medidas:
        lineas.append("| Configuración | Servidor con el que habló |")
        lineas.append("|---|---|")
        for m in medidas:
            lineas.append(f"| {m.nombre} | `{m.servidor}` |")
        lineas.append("")
    marca = "Comprobado" if servidores_ok else "**AVISO**"
    lineas.append(f"{marca}: {motivo_servidores}")
    lineas.append("")

    lineas.append("## Qué NO mide esta comparación")
    lineas.append("")
    lineas.append(
        "- **El precio en dinero.** No hay forma de saberlo desde aquí: ni la herramienta ni "
        "este guion ven la factura, y el consumo real depende de tarifas por proveedor y por "
        "modelo que no están en el repositorio. Los segundos de la tabla son tiempo de reloj, "
        "no coste, y no se pueden convertir en uno."
    )
    lineas.append(
        "- **La calidad de la redacción.** La corrección busca cadenas obligatorias dentro del "
        "informe. Da por bueno un texto que nombre el dato de pasada sin sostenerlo, y puede "
        "suspender uno correcto que use un sinónimo no previsto. El informe entero se guarda en "
        "el JSON crudo justamente para que quien dude lo lea en vez de creerse el porcentaje."
    )
    lineas.append(
        "- **Nada estable en el tiempo.** Es una ejecución. El buscador devuelve fuentes "
        "distintas de un día para otro, así que una diferencia pequeña entre dos configuraciones "
        "puede ser ruido. Con cinco preguntas, cada acierto vale 20 puntos: un 20 % de diferencia "
        "es una sola pregunta."
    )
    lineas.append(
        "- **La distinción de servidores, cuando ninguna declara URL explícita.** El campo "
        "`servidor` sale de `OPENAI_BASE_URL`; dos proveedores nativos distintos dirían los dos "
        "«(por defecto del proveedor)» y esta prueba no podría separarlos."
    )
    lineas.append("")
    return "\n".join(lineas) + "\n"


ATESTADO = Path(__file__).resolve().parent / "modelos_atestiguados.yml"

#: Cuantos dias vale un atestado. Un catalogo de modelos se pudre en semanas
#: -medido: la familia `gemini-2.5` entera murio en ese plazo-, asi que siete dias
#: es generoso y sigue siendo mucho mas corto que la vida de un documento.
DIAS_DE_VALIDEZ = 7


def modelos_sin_atestado(
    configuraciones: list[Any], atestado: Path = ATESTADO, ahora: str | None = None
) -> list[str]:
    """Que modelos configurados NO constan como usables y recientes.

    LA PIEZA QUE HACE IMPOSIBLE LO QUE CASI PASA CUATRO VECES: medir con 33
    guardianes en verde sobre un modelo que el proveedor ya habia retirado
    (ADR-095). Hasta hoy nada lo impedia, porque el resultado de cada llamada
    moria en la cola de un log y ningun programa podia leerlo.

    Devuelve la lista de los que fallan. Vacia significa que todos constan.

    ANTE LA DUDA, SE PARA: si el atestado no existe, no se puede leer o esta
    caducado, TODOS los modelos cuentan como sin atestiguar. No poder comprobarlo
    es el peor motivo para seguir.
    """
    from datetime import UTC, datetime, timedelta

    nombres: list[str] = []
    for configuracion in configuraciones:
        for clave, valor in (getattr(configuracion, "entorno", None) or {}).items():
            if clave in ("FAST_LLM", "SMART_LLM", "STRATEGIC_LLM", "EMBEDDING"):
                nombres.append(str(valor).split(":", 1)[-1])
    nombres = sorted(set(nombres))
    if not nombres:
        return []

    if not atestado.is_file():
        return nombres
    try:
        datos = yaml.safe_load(atestado.read_text(encoding="utf-8")) or {}
    except Exception:
        return nombres

    momento = datetime.now(UTC) if ahora is None else datetime.fromisoformat(ahora)
    limite = momento - timedelta(days=DIAS_DE_VALIDEZ)

    vivos: set[str] = set()
    for proveedor in (datos.get("proveedores") or {}).values():
        for nombre, ficha in (proveedor.get("modelos") or {}).items():
            if not isinstance(ficha, dict) or not ficha.get("usable"):
                continue
            fecha = str(ficha.get("fecha_utc", ""))
            try:
                cuando = datetime.fromisoformat(fecha.replace("Z", "+00:00"))
            except ValueError:
                continue
            if cuando >= limite:
                vivos.add(str(nombre))

    def _consta(nombre: str) -> bool:
        return any(nombre == v or v.endswith(nombre) or nombre.endswith(v) for v in vivos)

    return [n for n in nombres if not _consta(n)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compara configuraciones del investigador, cada una en un subproceso con el entorno "
            "construido desde cero para que no se contaminen entre ellas."
        )
    )
    parser.add_argument("--configuraciones", default=str(CONFIGURACIONES))
    parser.add_argument(
        "--atestado",
        default=str(ATESTADO),
        # Se inyecta para que una prueba pueda montar su propio atestado sin
        # tocar el de produccion. NO existe forma de saltarse la comprobacion:
        # apuntar a un fichero que no existe hace que TODOS los modelos cuenten
        # como sin atestiguar, que es lo que debe pasar.
        help="fichero de atestado de modelos (por defecto, el del repositorio)",
    )
    parser.add_argument("--salida-md", required=True, help="informe comparativo en Markdown")
    parser.add_argument("--salida-json", required=True, help="JSON crudo con todo lo medido")
    parser.add_argument(
        "--tiempo-maximo",
        type=int,
        default=1800,
        help="segundos como mucho por configuración (por defecto 1800)",
    )
    parser.add_argument(
        "--fecha",
        default=None,
        # Se inyecta para que el informe sea función de sus entradas y no del reloj
        # de la máquina: un documento que cambia solo porque ha pasado un día no se
        # puede comparar con el anterior.
        help="fecha que aparece en el informe (por defecto, hoy)",
    )
    args = parser.parse_args(argv)
    fecha = args.fecha or date.today().isoformat()

    try:
        configuraciones = cargar_configuraciones(Path(args.configuraciones))
    except ConfiguracionInvalida as exc:
        sys.stderr.write(f"configuración inválida: {exc}\n")
        return CODIGO_CONFIGURACION_INVALIDA

    # ANTES DE GASTAR UN CENTIMO: que conste que estos modelos responden.
    # Un numero medido sobre un modelo muerto es peor que no tener numero,
    # porque se cree. Esto es ADR-095 hecho guardian.
    sin_atestado = modelos_sin_atestado(list(configuraciones), Path(args.atestado))
    if sin_atestado:
        sys.stderr.write(
            "no consta que estos modelos respondan, o su atestado ha caducado: "
            + ", ".join(sin_atestado)
            + "\nEjecuta el preflight con --atestiguar antes de medir. "
            "Medir sobre un nombre sin comprobar es como se perdio la noche del "
            "26-08-2026 (ADR-095).\n"
        )
        return CODIGO_SIN_ATESTADO

    mediciones: list[Medicion] = []
    with TemporaryDirectory(prefix="sirius-comparacion-") as temporal:
        carpeta = Path(temporal)
        for configuracion in configuraciones:
            sys.stderr.write(f"→ {configuracion.nombre}: preparando subproceso propio\n")
            try:
                medicion = medir_configuracion(configuracion, carpeta, args.tiempo_maximo)
            except ConfiguracionInvalida as exc:
                sys.stderr.write(f"configuración inválida: {exc}\n")
                return CODIGO_CONFIGURACION_INVALIDA
            sys.stderr.write(
                f"  {configuracion.nombre}: {medicion.estado} — {medicion.detalle[:600]}\n"
            )
            # SIEMPRE, no solo cuando falla: en una medición que sí sale, saber
            # cuántas fuentes trajo cada pregunta es lo que separa «investigó y
            # acertó» de «se lo sabía».
            for linea in desglose_por_pregunta(medicion):
                sys.stderr.write(linea + "\n")
            mediciones.append(medicion)

    medidas = [m for m in mediciones if m.estado == ESTADO_MEDIDA]
    servidores_ok, motivo_servidores = veredicto_de_servidores(medidas)

    if len(medidas) < 2:
        codigo = CODIGO_NO_CONCLUYENTE
        concluyente = False
        veredicto = "NO CONCLUYENTE"
        cuantas = (
            "No se midió ninguna configuración"
            if not medidas
            else "Se midió una sola configuración"
        )
        motivo = (
            f"{cuantas} de las {len(configuraciones)} declaradas, y una comparación necesita dos. "
            "Criterio de parada (b) de la nota de arranque: «si acaba midiendo UNA sola "
            "configuración, no vale». No es un fallo del programa: es que la comparación no "
            "existe. Lo que sí se haya medido sigue abajo, y vale como medida suelta."
        )
    elif not servidores_ok:
        codigo = CODIGO_COMPARACION_FALSA
        concluyente = False
        # Etiqueta propia: esto NO es lo mismo que quedarse corto de mediciones.
        # Aquí hay dos números y el peligro es justamente que parecen comparables.
        veredicto = "COMPARACIÓN FALSA"
        motivo = (
            "Dos mediciones declaran el MISMO servidor, así que el par de números no compara "
            "nada: el detalle está en «Prueba de que no es la misma medición contada dos veces»."
        )
    else:
        codigo = CODIGO_OK
        concluyente = True
        veredicto = "CONCLUYENTE"
        motivo = (
            f"{len(medidas)} configuraciones medidas en procesos separados, cada una contra un "
            "servidor distinto y sobre el mismo banco de preguntas."
        )

    informe = informe_markdown(
        mediciones, veredicto, motivo, servidores_ok, motivo_servidores, fecha
    )
    crudo = {
        "version": 1,
        "fecha": fecha,
        "veredicto": veredicto,
        "concluyente": concluyente,
        "motivo": motivo,
        "servidores_distintos": servidores_ok,
        "motivo_servidores": motivo_servidores,
        "codigo_de_salida": codigo,
        "configuraciones_declaradas": len(configuraciones),
        "configuraciones_medidas": len(medidas),
        "mediciones": [asdict(m) for m in mediciones],
    }

    Path(args.salida_md).write_text(informe, encoding="utf-8")
    Path(args.salida_json).write_text(
        json.dumps(crudo, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    sys.stdout.write(informe)
    # El código de salida es el veredicto. La última línea impresa NO lo es: en
    # este repositorio las validaciones se leen por código, nunca por el texto.
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
