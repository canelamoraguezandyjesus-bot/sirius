"""``sirius-tablero``: escribe el cuerpo del tablero de una incidencia (ADR-175).

Cáscara y nada más, como ``sirius-memoria`` y ``sirius-reflejar``: lee el
espejo de la incidencia por los adaptadores de siempre, llama a la función pura
:func:`sirius_engine.tablero.generar_tablero` e imprime el resultado por la
salida estándar. **No publica nada**: publicar es cosa de
``notify-sirius-state.yml``, que ya tiene el permiso y el disparador.

Separarlo así no es ceremonia: es lo que permite probar el cuerpo entero sin
GitHub delante, y lo que deja al workflow con una sola responsabilidad —pegar
el texto donde toca—.

Códigos de salida: 0 escrito; 2 no se pudo leer la incidencia. El llamador
trata el 2 como «hoy no hay tablero» y sigue: este paso es secundario y jamás
debe bloquear el ciclo.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import UTC, datetime

from sirius_engine.adapters.github_cli_mirror import GitHubCliMirrorReader
from sirius_engine.domain.mirror import EspejoIlegibleError
from sirius_engine.issue_body_parsing import leer_cuerpo_declarado
from sirius_engine.mirror_projection import proyectar_work_item
from sirius_engine.ports.github_mirror import GitHubMirrorPort
from sirius_engine.tablero import generar_tablero

COMANDO = "sirius-tablero"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=COMANDO, description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo", required=True, help="owner/name del repositorio")
    parser.add_argument("--incidencia", type=int, required=True, help="número de la incidencia")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    salida: object = None,
    ahora: datetime | None = None,
    mirror: GitHubMirrorPort | None = None,
) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    escribir = getattr(salida, "write", None) or (lambda t: sys.stdout.write(t))
    ahora = ahora or datetime.now(UTC)
    mirror = mirror if mirror is not None else GitHubCliMirrorReader()

    # Las tres lecturas se hacen UNA vez y se reparten: la proyección las
    # necesita las tres, y el cuerpo lo necesita además el lector de secciones
    # declaradas. Llamar a `leer_y_proyectar_work_item` y después releer el
    # cuerpo costaría una llamada de más a GitHub por cada cambio de etiqueta,
    # y dejaría un camino de "cuerpo ilegible" que no puede ocurrir -la
    # proyección ya se niega sin cuerpo-: código muerto, que es la enfermedad
    # de esta casa (ADR-173).
    cuerpo = mirror.leer_cuerpo(repo=args.repo, numero=args.incidencia)
    try:
        espejo = proyectar_work_item(
            repo=args.repo,
            numero=args.incidencia,
            metadatos=mirror.leer_metadatos(repo=args.repo, numero=args.incidencia),
            cuerpo=cuerpo,
            comentarios=mirror.leer_comentarios(repo=args.repo, numero=args.incidencia),
            ahora=ahora,
        )
    except EspejoIlegibleError as error:
        print(
            f"{COMANDO}: no pude leer la incidencia #{args.incidencia} ({error}); "
            "no hay tablero esta vez.",
            file=sys.stderr,
        )
        return 2

    assert cuerpo.cuerpo is not None, "la proyección habría fallado sin cuerpo legible"
    escribir(
        generar_tablero(leer_cuerpo_declarado(cuerpo.cuerpo.texto), espejo, numero=args.incidencia)
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - entrada manual
    sys.exit(main())
