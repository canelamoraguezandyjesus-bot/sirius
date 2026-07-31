"""Pruebas del verificador de identidad Git y de la fe de erratas 01.

No miden, no ejecutan corridas y no escriben nada. Comprueban que toda cita
de identidad del repositorio resuelve a un objeto Git —salvo las excepciones
inventariadas—, que la excepcion de una errata esta anclada al blob del
documento afectado, y que la evidencia v0.1 y v0.2 sigue intacta byte a byte.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from experiments.adr002.rederivation import controlled_conditions as cc
from experiments.adr002.rederivation import custody_errata as ce

RAIZ = Path(__file__).resolve().parents[3]

#: Los seis artefactos de evidencia, con los blobs que fija la fe de erratas.
EVIDENCIA = {
    "artifacts/adr002_tolerances/rederivacion_t0_v0.1.json": (
        "781132bfe0365f6b7ebcb9139330d10dc76fd0db"
    ),
    "artifacts/adr002_tolerances/rederivacion_t0_v0.1_muestras.json": (
        "04cd805181f9067318adaf84aaa676df1eb52c7c"
    ),
    "artifacts/adr002_tolerances/INFORME_REDERIVACION_T0_v0.1_PROPUESTO.md": (
        "11d41f42838a3fb3512bfe32dcf9e35689980611"
    ),
    "artifacts/adr002_tolerances/rederivacion_t0_v0.2.json": (
        "9140c1c031ed4bff891fc0fdabb04b4480a8d817"
    ),
    "artifacts/adr002_tolerances/rederivacion_t0_v0.2_muestras.json": (
        "8a61b8e519d6d854d782106aed19614ebd2377a5"
    ),
    "artifacts/adr002_tolerances/INFORME_REDERIVACION_T0_v0.2_PROPUESTO.md": (
        "dac5155914d55b7e1e294ebca1d16f0ef6e6e656"
    ),
}


# --------------------------------------------------------------------------
# La comprobacion sobre el repositorio real
# --------------------------------------------------------------------------


def test_toda_cita_de_identidad_resuelve_o_esta_inventariada() -> None:
    """La comprobacion que faltaba: ninguna cita rota sin declarar."""
    assert ce.fallos_de_identidad(RAIZ) == []


def test_las_erratas_declaradas_son_coherentes() -> None:
    assert ce.fallos_de_las_erratas_declaradas(RAIZ) == []


def test_la_errata_01_identifica_el_commit_real() -> None:
    errata = ce.ERRATAS[0]
    assert errata.sha_erroneo == "5797f5205cdb3054921054461f77dbdb8f550af4"
    assert errata.sha_correcto == "5797f523c9d4f0e0d3f99599493b6e3167b29f9d"
    # El prefijo abreviado es el mismo: por eso la lectura humana no lo vio.
    assert errata.sha_erroneo[:7] == errata.sha_correcto[:7] == "5797f52"


def test_la_fe_de_erratas_y_el_sucesor_existen_y_se_citan() -> None:
    fe = RAIZ / "docs/architecture" / ce.FE_DE_ERRATAS
    sucesor = RAIZ / "artifacts/adr002_tolerances/INFORME_REDERIVACION_T0_v0.2.1_PROPUESTO.md"
    assert fe.is_file()
    assert sucesor.is_file()
    texto_fe = fe.read_text(encoding="utf-8")
    texto_sucesor = sucesor.read_text(encoding="utf-8")
    errata = ce.ERRATAS[0]
    # La fe de erratas nombra ambos SHA y el documento afectado.
    assert errata.sha_erroneo in texto_fe
    assert errata.sha_correcto in texto_fe
    assert "INFORME_REDERIVACION_T0_v0.2_PROPUESTO.md" in texto_fe
    # El sucesor lleva el SHA correcto y enlaza la fe de erratas.
    assert errata.sha_correcto in texto_sucesor
    assert ce.FE_DE_ERRATAS in texto_sucesor


def test_el_informe_v02_original_conserva_su_errata_sin_reescribirse() -> None:
    """La evidencia no se corrige en el sitio: se sucede."""
    ruta = RAIZ / ce.ERRATAS[0].documento_afectado
    texto = ruta.read_text(encoding="utf-8")
    assert ce.ERRATAS[0].sha_erroneo in texto
    assert ce.blob_git_de(ruta) == ce.ERRATAS[0].blob_del_documento


# --------------------------------------------------------------------------
# La evidencia, intacta byte a byte
# --------------------------------------------------------------------------


def test_los_seis_artefactos_de_evidencia_estan_intactos() -> None:
    for ruta, esperado in EVIDENCIA.items():
        assert ce.blob_git_de(RAIZ / ruta) == esperado, ruta


def test_la_evidencia_v01_sigue_siendo_intangible_para_el_arnes() -> None:
    """Los tres blobs v0.1 que el arnes exige como precondicion."""
    for ruta, esperado in cc.EVIDENCIA_V01.items():
        assert EVIDENCIA[ruta] == esperado


# --------------------------------------------------------------------------
# Falla cerrado: el verificador denuncia lo que debe denunciar
# --------------------------------------------------------------------------


def _sin_ninguno(_shas: Sequence[str]) -> dict[str, bool]:
    """Un Git en el que NADA existe: el peor caso para el verificador."""
    return {}


def test_si_ninguna_cita_resolviera_se_denunciarian_todas() -> None:
    fallos = ce.fallos_de_identidad(RAIZ, existen=_sin_ninguno)
    assert fallos, "un verificador que nunca denuncia no verifica nada"
    assert any("no resuelve a ningun objeto Git" in f for f in fallos)


def test_una_cita_rota_nueva_falla_aunque_haya_erratas_declaradas(tmp_path: Path) -> None:
    """La excepcion no se hereda: un SHA roto nuevo es un fallo."""
    inventado = "f" * 40
    (tmp_path / "docs/architecture").mkdir(parents=True)
    (tmp_path / "artifacts").mkdir(parents=True)
    (tmp_path / "docs/architecture/NUEVO.md").write_text(
        f"commit citado: {inventado}\n", encoding="utf-8"
    )
    fallos = ce.fallos_de_identidad(tmp_path, existen=lambda shas: dict.fromkeys(shas, False))
    assert any(inventado in f for f in fallos)


def test_la_errata_declarada_en_un_documento_ajeno_falla(tmp_path: Path) -> None:
    """El SHA erroneo solo puede aparecer donde el inventario lo permite."""
    (tmp_path / "docs/architecture").mkdir(parents=True)
    (tmp_path / "artifacts").mkdir(parents=True)
    (tmp_path / "docs/architecture/AJENO.md").write_text(
        f"cita: {ce.ERRATAS[0].sha_erroneo}\n", encoding="utf-8"
    )
    fallos = ce.fallos_de_identidad(tmp_path, existen=lambda shas: dict.fromkeys(shas, False))
    assert any("no inventariados" in f for f in fallos)


def test_si_el_documento_afectado_cambiara_la_excepcion_caducaria(tmp_path: Path) -> None:
    """La excepcion esta anclada al blob: reescribir la evidencia la invalida."""
    errata = ce.ERRATAS[0]
    destino = tmp_path / errata.documento_afectado
    destino.parent.mkdir(parents=True)
    (tmp_path / "docs/architecture").mkdir(parents=True)
    destino.write_text(f"informe alterado que aun cita {errata.sha_erroneo}\n", encoding="utf-8")
    fallos = ce.fallos_de_identidad(tmp_path, existen=lambda shas: dict.fromkeys(shas, False))
    assert any("ha cambiado" in f for f in fallos)


def test_los_hashes_no_almacenados_estan_justificados_uno_a_uno() -> None:
    """Ninguna excepcion muda: cada una declara por que es correcta."""
    assert ce.HASHES_NO_ALMACENADOS
    for sha, motivo in ce.HASHES_NO_ALMACENADOS.items():
        assert len(sha) == 40
        assert len(motivo.strip()) > 40, sha


def test_la_huella_de_la_ficha_esta_entre_los_no_almacenados() -> None:
    """Y sigue siendo la de la ficha real: la excepcion no la desancla."""
    import json

    ficha = json.loads(
        (RAIZ / "artifacts/adr002_cards/ficha_T0-control_v1.json").read_text(encoding="utf-8")
    )
    assert ficha["congelacion"]["huella"] in ce.HASHES_NO_ALMACENADOS
