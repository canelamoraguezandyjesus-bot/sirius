"""Registro de evidencia por spike, con los 11 campos que exige el §6 del
paquete operativo, y ejecución doble desde base limpia."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

PASS = "PASS"
FAIL_IMPLEMENTATION = "FAIL_IMPLEMENTATION"
FAIL_STRUCTURAL_MODEL = "FAIL_STRUCTURAL_MODEL"
FAIL_ENGINE_SQLITE = "FAIL_ENGINE_SQLITE"
INCONCLUSIVE = "INCONCLUSIVE"

ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / "artifacts" / "adr001_spikes"


@dataclass
class SpikeEvidence:
    numero: int
    nombre: str
    objetivo: str
    incertidumbre: str
    dataset: str
    preparacion: str
    operacion: str
    resultado_esperado: str
    criterio_de_fallo: str
    evidencia: dict[str, Any] = field(default_factory=dict)
    resultado: str = INCONCLUSIVE
    repeticion_limpia: str = "no ejecutada"
    conclusion: str = ""


def sha256_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_twice(build: Callable[[], SpikeEvidence]) -> SpikeEvidence:
    """Ejecuta el spike dos veces, cada una desde una base limpia.

    Un spike solo puede quedar en PASS si ambas ejecuciones coinciden. Si
    difieren, el resultado se degrada a INCONCLUSIVE porque la evidencia no
    es reproducible.
    """
    first = build()
    second = build()
    if first.resultado != second.resultado:
        first.resultado = INCONCLUSIVE
        first.repeticion_limpia = (
            f"NO REPRODUCIBLE: primera pasada {first.resultado}, segunda {second.resultado}"
        )
        return first
    first.repeticion_limpia = (
        f"reproducido desde base limpia: segunda pasada tambien {second.resultado}"
    )
    return first


def write_bundle(evidences: list[SpikeEvidence], filename: str) -> Path:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    target = ARTIFACTS_DIR / filename
    payload = [asdict(evidence) for evidence in evidences]
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target
