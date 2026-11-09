# tests/unit/test_p18_8a_titre.py
"""
P18.8a — Titre de réunion éditable dans le ruban du
volet Réunion : modifiable en place, persisté, SANS
effet sur les noms de dossiers/fichiers ni les
références de l'étude.

- réunion rattachée à une étude : persisté dans
  ``reunions/<nom>.json`` (titre_1) ;
- réunion autonome : persisté dans le tier
  (``transcriptstudio/reunion.json``, champ « titre »).
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.qt

from services.settings import SettingsManager
from tests.unit.test_reformulation_ui import (
    construire_etude_test,
    construire_projet_test,
)


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def fenetre_rattachee(qapp, tmp_path):
    from ui.reunion_window import ReunionWindow

    _projet, projet_v1, etude, nom = (
        construire_etude_test(tmp_path)
    )

    settings = SettingsManager(
        str(tmp_path / "reglages")
    )

    fenetre = ReunionWindow(
        projet_v1,
        settings=settings,
        etude=etude,
        nom=nom
    )

    yield fenetre, tmp_path, etude, nom, projet_v1

    fenetre.close()


@pytest.fixture
def fenetre_autonome(qapp, tmp_path):
    from ui.reunion_window import ReunionWindow

    _projet, projet_v1 = construire_projet_test(
        tmp_path
    )

    settings = SettingsManager(
        str(tmp_path / "reglages")
    )

    fenetre = ReunionWindow(
        projet_v1,
        settings=settings
    )

    assert not fenetre.rattachee()

    yield fenetre, tmp_path, projet_v1

    fenetre.close()


class TestTitreRattache:

    def test_titre_editable_en_place_dans_ruban(
        self, fenetre_rattachee
    ):
        fenetre, tmp_path, etude, nom, _pv = (
            fenetre_rattachee
        )

        # Le titre du ruban est un champ éditable.
        from PySide6.QtWidgets import QLineEdit

        assert isinstance(
            fenetre.titre_label,
            QLineEdit
        )

        avant = fenetre.titre_label.text()

        # Édition en place + validation.
        fenetre.titre_label.setText(
            "Chapitre 1 — Naissance de Jean-Baptiste"
        )
        fenetre._enregistrer_titre()

        assert fenetre.titre_label.text() == (
            "Chapitre 1 — Naissance de Jean-Baptiste"
        )

        # Persisté dans reunions/<nom>.json (titre_1).
        donnees = json.loads(
            (
                tmp_path / "Etude" / "reunions"
                / f"{nom}.json"
            ).read_text(encoding="utf-8")
        )

        assert donnees["titre_1"] == (
            "Chapitre 1 — Naissance de Jean-Baptiste"
        )

        # Persisté après réouverture.
        from services.etude_io import ouvrir_etude

        relue = ouvrir_etude(tmp_path / "Etude")

        assert relue.reunions[nom].titre_1 == (
            "Chapitre 1 — Naissance de Jean-Baptiste"
        )

        # SANS effet sur les noms de fichiers ni les
        # références : le nom de la réunion (clé des
        # références) et le dossier projet ne changent
        # pas.
        assert nom in relue.etude.ordre_reunions
        assert (tmp_path / nom).is_dir()
        assert (
            tmp_path / "Etude" / "reunions"
            / f"{nom}.json"
        ).is_file()

        # Le titre d'avant n'a pas créé de doublon.
        assert avant != fenetre.titre_label.text()

    def test_titre_vide_refuse(self, fenetre_rattachee):
        fenetre, tmp_path, etude, nom, _pv = (
            fenetre_rattachee
        )

        avant = fenetre.titre_label.text()

        fenetre.titre_label.setText("   ")
        fenetre._enregistrer_titre()

        assert fenetre.titre_label.text() == avant
        assert etude.reunions[nom].titre_1 != ""


class TestTitreAutonome:

    def test_titre_editable_persiste_dans_le_tier(
        self, fenetre_autonome
    ):
        fenetre, tmp_path, projet_v1 = fenetre_autonome

        dossier_projet = Path(
            projet_v1.project_file
        ).parent

        # Édition en place dans le ruban.
        fenetre.titre_label.setText("Culte du 13 octobre")
        fenetre._enregistrer_titre()

        # Persisté dans le tier (reunion.json, champ
        # « titre »), PAS de fichier renommé.
        racine = dossier_projet / "transcriptstudio"

        donnees = json.loads(
            (racine / "reunion.json").read_text(
                encoding="utf-8"
            )
        )

        assert donnees["titre"] == "Culte du 13 octobre"
        assert donnees["nom"] == dossier_projet.name

        # Aucun fichier/dossier renommé dans le projet.
        assert sorted(
            p.name for p in dossier_projet.iterdir()
        ) == ["project.sttproj", "transcriptstudio"]

        # Relu en autonome.
        from services.etude_io import (
            ouvrir_reunion_autonome,
        )

        etude2, nom2 = ouvrir_reunion_autonome(
            dossier_projet,
            creer=False
        )

        assert etude2.tiers[nom2].reunion.titre == (
            "Culte du 13 octobre"
        )

        # Le ruban réouvert affiche le titre persisté.
        from ui.reunion_window import ReunionWindow

        settings = SettingsManager(
            str(tmp_path / "reglages2")
        )

        fenetre2 = ReunionWindow(
            projet_v1,
            settings=settings
        )

        assert fenetre2.titre_label.text() == (
            "Culte du 13 octobre"
        )

        fenetre2.close()
