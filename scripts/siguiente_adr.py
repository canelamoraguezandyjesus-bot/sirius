#!/usr/bin/env python3
"""Calcula el número del siguiente ADR y crea el archivo desde la plantilla.

El número es **el máximo existente más uno**, nunca un hueco histórico
(ADR-032). El registro tiene hoy dos `ADR-016` y ningún 017 ni 018: el hueco es
inofensivo —nadie busca un ADR por su posición—, pero el número repetido hace
que dos decisiones distintas se citen igual.

Esto es un ayudante, **no una puerta**. No impide crear un ADR a mano, y la
garantía sigue siendo la prueba que recorre `docs/decisions/` y falla si dos
archivos comparten número.

Lo que sí cambió (ADR-044) es de dónde saca el máximo. Antes miraba solo el árbol
de trabajo, y por eso dos ramas abiertas a la vez sobre el mismo `main` obtenían
ambas el mismo número: ocurrió el 20-08-2026 con ADR-042 —el arreglo de Qt y el
bloque A5 lo tomaron a la vez, y la colisión dejó Quality en rojo y una incidencia
atascada— y estuvo a punto de repetirse con el 043 el mismo día. Ahora el máximo
se calcula contra el árbol **y** contra los ADR que ya existen en cualquier rama
que el clon conozca.

Ese límite -«el guion solo ve las ramas TRAÍDAS»- estuvo escrito aquí desde
ADR-044 y no era teórico. **ADR-180 lo cierra**: medido el 12-09-2026, este
clon tenía **14** refs remotas de las **409** que hay en el remoto -el
**3,4 %**-, y con esa cobertura el guion repartió el mismo número, 177, a
**tres** ramas abiertas el mismo día; dos hubo que renumerarlos a mano. En una
sesión remota el clon nace con las ramas del arranque y nadie trae las demás,
así que la cobertura parcial es la norma, no la excepción.

Desde ADR-180 el guion **trae las cabezas del remoto** antes de calcular -4
segundos medidos- y **dice cuál de las dos cosas hizo**: si trajo, la cuenta de
ramas es toda la verdad; si no pudo -sin red, sin git, fuera de un
repositorio-, degrada al comportamiento anterior y avisa de que la cuenta es
solo lo que el clon ya tenía. Nunca aborta por no poder traer: quedarse sin
crear el ADR es peor que crearlo con la cobertura de ayer.

Lo que sigue sin garantizar, y por eso la puerta de `main` no sobra: dos
sesiones que pidan número **a la vez**, antes de que ninguna haya empujado,
seguirán recibiendo el mismo. El remoto no puede decir lo que aún no le han
contado. Esa colisión la caza `tests/automation/test_registro_de_decisiones.py`
al fusionar.

La fecha se inyecta en vez de leerse del reloj para que el resultado sea
función únicamente de los argumentos: una prueba que dependiera del día en que
corre mediría la máquina, no el código.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import unicodedata
from collections.abc import Callable, Iterable
from datetime import date
from pathlib import Path

# Insensible a mayúsculas a propósito: en Windows `adr-030-x.md` y
# `ADR-030-x.md` son el mismo archivo, así que ignorar la primera forma dejaría
# proponer un número ya ocupado. El título es opcional para que un
# `ADR-030.md` suelto también cuente como ocupado.
PATRON_ADR = re.compile(r"^ADR-(\d+)(?:-.*)?\.md$", re.IGNORECASE)

NOMBRE_PLANTILLA = "PLANTILLA.md"


def numeros_por_archivo(directorio: Path) -> dict[str, int]:
    """Número declarado por cada archivo de ADR del directorio."""
    if not directorio.is_dir():
        raise NotADirectoryError(f"no existe el registro de decisiones: {directorio}")
    encontrados: dict[str, int] = {}
    for ruta in sorted(directorio.iterdir()):
        if not ruta.is_file():
            continue
        casa = PATRON_ADR.match(ruta.name)
        if casa is not None:
            encontrados[ruta.name] = int(casa.group(1))
    return encontrados


def _correr_git(argumentos: list[str], raiz: Path) -> tuple[bool, str]:
    """`(funcionó, salida)` de un comando git. Nunca propaga el fallo.

    Se parte en dos lo que antes era una sola cadena porque `git fetch --quiet`
    **no imprime nada cuando va bien**: con la forma anterior, «trajo» y «no
    pudo traer» eran indistinguibles, las dos cadena vacía. Y esa distinción es
    justo lo que ADR-180 necesita decir en voz alta, porque un número calculado
    sobre el 3,4 % de las ramas y uno calculado sobre todas no merecen la misma
    confianza.
    """
    try:
        completado = subprocess.run(
            ["git", *argumentos],
            cwd=raiz,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    # Dos cláusulas y no `except (A, B):` a propósito: `ruff format` con
    # `target-version = "py314"` quita los paréntesis y deja sintaxis de PEP 758,
    # que el `python3` del sistema de un runner (3.12) no compila. Comprobado el
    # 24-08-2026 sobre este mismo fichero: poner los paréntesis y pasar el
    # formateador los deshace. Dos cláusulas sobreviven al formateador y compilan
    # en las dos versiones; es el patrón que `sirius_check_docs.py:236` ya
    # documenta. Este guion se invoca hoy siempre con `uv run`, así que la trampa
    # es latente, no viva: se cierra igual, porque cuesta nada.
    except OSError:
        return False, ""
    except subprocess.SubprocessError:
        return False, ""
    if completado.returncode != 0:
        return False, ""
    return True, completado.stdout


def _git(argumentos: list[str], raiz: Path) -> str:
    """Salida de un comando git, o cadena vacía si no se puede preguntar.

    La forma que usan los lectores -`for-each-ref`, `ls-tree`-, a los que solo
    les importa el texto: para ellos «no pude preguntar» y «no hay nada» llevan
    al mismo sitio, que es calcular con lo que haya. Quien necesita distinguir
    las dos cosas usa :func:`_correr_git`.
    """
    return _correr_git(argumentos, raiz)[1]


#: El refspec, explícito a propósito: trae TODAS las cabezas aunque el clon se
#: creara con uno estrecho, que es exactamente lo que hace una sesión remota al
#: clonar una sola rama. Con `git fetch origin` a secas, un clon así se queda
#: con las mismas 14 refs con las que nació.
REFSPEC_DE_LAS_CABEZAS = "+refs/heads/*:refs/remotes/origin/*"


def traer_las_cabezas(
    directorio: Path,
    correr: Callable[[list[str], Path], tuple[bool, str]] = _correr_git,
) -> bool:
    """Trae las cabezas del remoto al clon; dice si lo consiguió (ADR-180).

    Sin esto, «las ramas que el clon conoce» y «las ramas que hay» son cosas
    distintas, y la diferencia medida el 12-09-2026 era 14 frente a 409.

    No aborta nunca: un fallo solo significa que se calculará con lo que ya
    hubiera, como antes de ADR-180. Lo que no se hace es callarlo.
    """
    raiz = directorio.resolve().parent
    return correr(["fetch", "--quiet", "origin", REFSPEC_DE_LAS_CABEZAS], raiz)[0]


def numeros_en_ramas(
    directorio: Path,
    ejecutar: Callable[[list[str], Path], str] = _git,
) -> dict[int, list[str]]:
    """Números de ADR que ya usa cada rama conocida por el clon.

    Devuelve `{numero: [ramas que lo usan]}`. `ejecutar` se inyecta para que la
    prueba pueda fijar la respuesta de git: una prueba que dependiera de las
    ramas reales del clon mediría la máquina, no el código.
    """
    raiz = directorio.resolve().parent
    refs = [
        linea.strip()
        for linea in ejecutar(
            ["for-each-ref", "--format=%(refname)", "refs/remotes"], raiz
        ).splitlines()
        if linea.strip()
    ]
    encontrados: dict[int, list[str]] = {}
    for ref in refs:
        salida = ejecutar(["ls-tree", "--name-only", ref, f"{directorio.name}/"], raiz)
        for nombre in salida.splitlines():
            casa = PATRON_ADR.match(Path(nombre.strip()).name)
            if casa is not None:
                numero = int(casa.group(1))
                if ref not in encontrados.setdefault(numero, []):
                    encontrados[numero].append(ref)
    return encontrados


def siguiente_numero(directorio: Path, reservados: Iterable[int] = ()) -> int:
    """Máximo existente más uno; 1 si no hay ninguno.

    Deliberadamente NO devuelve el primer hueco libre: reutilizar 017 haría que
    un mismo número apuntara a decisiones distintas según la fecha del clon.

    `reservados` son los números que ya usa otra rama sin fusionar. Cuentan como
    ocupados aunque no estén en este árbol: si no contaran, dos ramas vivas a la
    vez volverían a llevarse el mismo número (ADR-044).
    """
    numeros = list(numeros_por_archivo(directorio).values()) + list(reservados)
    if not numeros:
        return 1
    return max(numeros) + 1


def duplicados(directorio: Path) -> dict[int, list[str]]:
    """Números usados por más de un archivo. Diagnóstico, no bloquea nada."""
    por_numero: dict[int, list[str]] = {}
    for nombre, numero in numeros_por_archivo(directorio).items():
        por_numero.setdefault(numero, []).append(nombre)
    return {
        numero: sorted(nombres)
        for numero, nombres in sorted(por_numero.items())
        if len(nombres) > 1
    }


def normalizar_titulo(titulo: str) -> str:
    """Título -> segmento del nombre de archivo, según el convenio del registro.

    Una sola regla, no una lista de casos: se descomponen los diacríticos y se
    conserva `[a-z0-9.]`; **todo** lo demás separa. Añadir una regla por cada
    carácter que aparezca —una tilde, luego una eñe, luego unas comillas— es la
    familia «reconstruir por fuera una semántica ajena» que costó quince
    defectos en la PR #139, y el criterio de parada de ADR-032 la prohíbe.

    Los puntos se conservan porque el convenio ya los usa: ADR-012 termina en
    `sirius-0.1`.
    """
    sin_diacriticos = "".join(
        caracter
        for caracter in unicodedata.normalize("NFKD", titulo)
        if not unicodedata.combining(caracter)
    )
    limpio = re.sub(r"[^a-z0-9.]+", "-", sin_diacriticos.lower()).strip("-.")
    if not limpio:
        raise ValueError(f"el titulo no deja ningun caracter utilizable: {titulo!r}")
    return limpio


def nombre_de_archivo(numero: int, titulo: str) -> str:
    """`ADR-NNN-titulo-normalizado.md`, con NNN a tres dígitos como mínimo."""
    if numero < 1:
        raise ValueError(f"el numero de un ADR empieza en 1: {numero}")
    return f"ADR-{numero:03d}-{normalizar_titulo(titulo)}.md"


def _indice_de_linea(lineas: list[str], criterio: Callable[[str], bool], descripcion: str) -> int:
    for indice, linea in enumerate(lineas):
        if criterio(linea):
            return indice
    raise ValueError(
        f"{NOMBRE_PLANTILLA} ya no contiene {descripcion}. El guion no rellena a ciegas: "
        "escribir el archivo igualmente dejaria un ADR con la cabecera sin poner, "
        "que es peor que no crearlo"
    )


def rellenar_plantilla(plantilla: str, numero: int, titulo: str, fecha: date) -> str:
    """Pone número, título y fecha en la plantilla; el resto queda para el autor."""
    lineas = plantilla.splitlines()
    encabezado = _indice_de_linea(
        lineas, lambda linea: linea.startswith("# ADR-"), "el encabezado «# ADR-...»"
    )
    lineas[encabezado] = f"# ADR-{numero:03d} — {titulo}"
    fecha_puesta = _indice_de_linea(
        lineas, lambda linea: linea.startswith("- Fecha:"), "la linea «- Fecha:»"
    )
    lineas[fecha_puesta] = f"- Fecha: {fecha.isoformat()}"
    return "\n".join(lineas) + "\n"


def crear_adr(directorio: Path, titulo: str, fecha: date, reservados: Iterable[int] = ()) -> Path:
    """Crea el ADR siguiente y devuelve su ruta. Nunca sobrescribe."""
    numero = siguiente_numero(directorio, reservados)
    destino = directorio / nombre_de_archivo(numero, titulo)
    if destino.exists():
        raise FileExistsError(f"ya existe {destino.name}; este guion no sobrescribe nunca")
    plantilla = directorio / NOMBRE_PLANTILLA
    if not plantilla.is_file():
        raise FileNotFoundError(f"falta la plantilla: {plantilla}")
    contenido = rellenar_plantilla(plantilla.read_text(encoding="utf-8"), numero, titulo, fecha)
    destino.write_text(contenido, encoding="utf-8")
    return destino


def _avisar_de_duplicados(directorio: Path) -> None:
    for numero, nombres in duplicados(directorio).items():
        print(
            f"aviso: ADR-{numero:03d} lo usan {len(nombres)} archivos: {', '.join(nombres)}",
            file=sys.stderr,
        )


def _como_se_consulto(ramas: int, *, trajo: bool) -> str:
    """El aviso de cobertura, que distingue lo que antes no se distinguía.

    Antes de ADR-180 decía siempre «consultadas N ramas del clon», y esa N
    podía ser el 3,4 % de la verdad sin que nada lo dijera. Ahora la frase
    cambia según lo que de verdad ocurrió, porque las dos situaciones piden
    cosas distintas de quien lee.
    """
    if trajo:
        return f"traidas las cabezas del remoto; consultadas {ramas} ramas con ADR"
    return (
        f"NO se pudieron traer las cabezas del remoto: consultadas solo las {ramas} ramas "
        "con ADR que el clon ya tenia. El numero puede estar cogido en una rama sin traer; "
        "haz `git fetch` y repite si puedes"
    )


def _avisar_de_reservas(reservas: dict[int, list[str]], tope_local: int) -> None:
    """Dice qué números están cogidos fuera de este árbol, y por quién."""
    fuera = {numero: ramas for numero, ramas in reservas.items() if numero > tope_local}
    if not fuera:
        return
    for numero, ramas in sorted(fuera.items()):
        cortas = ", ".join(rama.rsplit("/", 1)[-1] for rama in ramas)
        print(
            f"aviso: ADR-{numero:03d} ya esta cogido en una rama sin fusionar ({cortas}); "
            "no se reutiliza",
            file=sys.stderr,
        )


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(
        description="Crea el siguiente ADR (maximo existente + 1) desde PLANTILLA.md.",
    )
    analizador.add_argument("titulo", nargs="?", help="titulo del ADR, en imperativo")
    analizador.add_argument(
        "--directorio", type=Path, default=Path("docs/decisions"), help="registro de decisiones"
    )
    analizador.add_argument("--fecha", default=None, help="AAAA-MM-DD; por defecto, hoy")
    analizador.add_argument(
        "--solo-numero", action="store_true", help="imprime el numero siguiente sin crear nada"
    )
    analizador.add_argument(
        "--solo-local",
        action="store_true",
        help="no consultar las ramas del clon (comportamiento anterior a ADR-044)",
    )
    analizador.add_argument(
        "--sin-traer",
        action="store_true",
        help=(
            "no traer las cabezas del remoto antes de calcular; usa solo las ramas que el "
            "clon ya tenga (comportamiento anterior a ADR-180)"
        ),
    )
    args = analizador.parse_args(argv)
    directorio: Path = args.directorio

    try:
        _avisar_de_duplicados(directorio)
        trajo = False
        if not args.solo_local and not args.sin_traer:
            trajo = traer_las_cabezas(directorio)
        reservas: dict[int, list[str]] = {} if args.solo_local else numeros_en_ramas(directorio)
        ramas = len({rama for ramas_ in reservas.values() for rama in ramas_})
        if not args.solo_local:
            print(_como_se_consulto(ramas, trajo=trajo), file=sys.stderr)
        numeros_locales = list(numeros_por_archivo(directorio).values())
        _avisar_de_reservas(reservas, max(numeros_locales, default=0))
        if args.solo_numero:
            print(siguiente_numero(directorio, reservas))
            return 0
        if not args.titulo:
            print("error: hace falta un titulo (o --solo-numero)", file=sys.stderr)
            return 2
        fecha = date.fromisoformat(args.fecha) if args.fecha else date.today()
        print(crear_adr(directorio, args.titulo, fecha, reservas))
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
