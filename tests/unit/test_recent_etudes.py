"""
Tests de la liste des études récentes
(SettingsManager, v2 - P14.3).
"""

from pathlib import Path

from services.settings import SettingsManager


def _settings(tmp_path):
    return SettingsManager(app_folder=tmp_path)


def _creer_dossier_etude(parent: Path, nom: str) -> Path:
    dossier = parent / nom
    dossier.mkdir(parents=True)
    (dossier / "etude.json").touch()
    return dossier


def test_add_recent_etude_ordre_et_doublon(tmp_path):
    manager = _settings(tmp_path)

    etude_a = _creer_dossier_etude(tmp_path, "etude_a")
    etude_b = _creer_dossier_etude(tmp_path, "etude_b")

    manager.add_recent_etude(etude_a)
    manager.add_recent_etude(etude_b)

    assert manager.get_recent_etudes() == [
        str(Path(etude_b)),
        str(Path(etude_a)),
    ]

    # Ré-ajouter une étude la remet en tête,
    # sans doublon.
    manager.add_recent_etude(etude_a)

    assert manager.get_recent_etudes() == [
        str(Path(etude_a)),
        str(Path(etude_b)),
    ]


def test_remove_recent_etude(tmp_path):
    manager = _settings(tmp_path)

    etude = _creer_dossier_etude(tmp_path, "etude_a")
    manager.add_recent_etude(etude)

    removed = manager.remove_recent_etude(etude)

    assert removed is True
    assert manager.get_recent_etudes() == []

    # La référence seule est retirée : le dossier
    # reste sur le disque.
    assert (Path(etude) / "etude.json").is_file()

    assert manager.remove_recent_etude(etude) is False


def test_cleanup_recent_etudes(tmp_path):
    manager = _settings(tmp_path)

    etude_valide = _creer_dossier_etude(
        tmp_path, "etude_valide"
    )

    dossier_sans_etude = tmp_path / "pas_une_etude"
    dossier_sans_etude.mkdir()

    dossier_disparu = tmp_path / "disparue"
    dossier_disparu.mkdir()

    manager.add_recent_etude(etude_valide)
    manager.add_recent_etude(dossier_sans_etude)
    manager.add_recent_etude(dossier_disparu)

    dossier_disparu.rmdir()

    restantes = manager.cleanup_recent_etudes()

    assert restantes == [str(Path(etude_valide))]
