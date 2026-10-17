"""La APM de livekit de verdad al salir de Python (ADR-252).

Si la APM sigue viva cuando Python se cierra, livekit pinta en rojo un error suyo, el de
``FfiHandle``: para entonces ya ha cerrado su lado. Por eso el cancelador la suelta al
cerrarse el altavoz. Aquí se mira con la de verdad, en un Python aparte que sale, con y sin
soltarla. ``livekit`` es del extra ``voz``, que Quality no instala: sin él, se salta.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

pytest.importorskip("livekit.rtc")

pytestmark = pytest.mark.integration

_GUION = """
import sys

from sirius.adapters.audio.echo_cancellation import load_echo_canceller
from sirius.ports.local_voice import Captured

echo = load_echo_canceller(22050)
assert echo is not None, "la APM de verdad no arranca"
echo.played(bytes(2 * 441), at=0.0)
echo.clean(Captured(bytes(2 * 480), age=0.0))
if sys.argv[1] == "suelta":
    echo.close()
print("sale")
"""


def _sale(como: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", _GUION, como],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )


def test_soltada_la_apm_python_sale_sin_el_error_rojo_de_livekit() -> None:
    soltandola = _sale("suelta")
    sin_soltarla = _sale("no-la-suelta")

    assert soltandola.stdout.strip() == "sale"
    assert "FfiHandle" not in soltandola.stderr
    # La prueba sabe verlo: sin soltarla, este livekit lo pinta.
    assert "FfiHandle" in sin_soltarla.stderr
