"""
Tests P18.6f — exports à trois portées (spec
navigation §8) : réunion (⑥ de la page Réunion,
y compris autonome ou intermédiaire) / ouvrage
(page Ouvrage) / résumé (inclus en tête de
l'export de réunion, selon P17).

Couvre aussi l'invariant §9.7 dans son périmètre
local : rien n'est jamais inséré dans un document
exporté sans validation explicite.
"""

import os

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from PySide6.QtWidgets import (
    QApplication,
    QPushButton,
)

from services.etude_io import (
    ajouter_version_reformulation,
    ajouter_version_resume,
    valider_version_reformulation,
    valider_version_resume,
)
from services.export_ouvrage import (
    assembler_reunion,
    exporter_docx,
    exporter_txt,
)
from tests.unit.test_reformulation_ui import (
    construire_etude_test,
)


@pytest.fixture(scope="module")
def qapp():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    yield application


@pytest.fixture
def etude_reunion(tmp_path):

    _p, _pv, etude, nom = (
        construire_etude_test(tmp_path)
    )

    fids = [
        entree.fid
        for entree in (
            etude.registre.entrees.values()
        )
        if entree.reunion == nom
    ]

    return etude, nom, fids, tmp_path


#
# ==================================================
# Portée réunion : assemblage d'une seule réunion.
# ==================================================
#

class TestAssemblageReunion:

    def test_intermediaire(self, etude_reunion):
        """
        Export de réunion INTERMÉDIAIRE : une partie
        des blocs seulement est validée — l'export
        assemble ce qui est validé, sans exiger une
        réunion entière.
        """

        etude, nom, fids, _t = etude_reunion

        ajouter_version_reformulation(
            etude,
            fids[0],
            "Premier bloc validé."
        )

        valider_version_reformulation(
            etude,
            fids[0],
            1,
            validateur="Test"
        )

        ajouter_version_reformulation(
            etude,
            fids[1],
            "Deuxième bloc, simple brouillon."
        )

        resultat = assembler_reunion(etude, nom)

        assert len(resultat["reunions"]) == 1

        section = resultat["reunions"][0]

        # Seul le bloc VALIDÉ figure — jamais un
        # brouillon (invariant §9.7 : rien sans
        # validation explicite).
        assert section["blocs"] == [
            "Premier bloc validé."
        ]

        assert resultat["titre"] == "Chapitre 1"

    def test_resume_en_tete(self, etude_reunion):
        """
        Portée « résumé » (spec §8.3, selon P17) :
        le résumé validé figure en tête de
        l'export de réunion.
        """

        etude, nom, fids, _t = etude_reunion

        version = ajouter_version_resume(
            etude,
            nom,
            "Résumé validé de la réunion.",
            source="brute_corrigee"
        )

        valider_version_resume(
            etude,
            nom,
            version.numero,
            validateur="Test"
        )

        resultat = assembler_reunion(etude, nom)

        assert len(resultat["reunions"]) == 1

        section = resultat["reunions"][0]

        assert section["resume"] == (
            "Résumé validé de la réunion."
        )

        assert section["blocs"] == []

    def test_aucun_valide(self, etude_reunion):

        etude, nom, fids, _t = etude_reunion

        ajouter_version_reformulation(
            etude,
            fids[0],
            "Brouillon jamais validé."
        )

        resultat = assembler_reunion(etude, nom)

        # Rien de validé : aucune section — jamais
        # de brouillon dans un document exporté.
        assert resultat["reunions"] == []

    def test_ordre_ouvrage(self, etude_reunion):
        """
        Les reformulations validées suivent l'ordre
        d'ouvrage de la réunion.
        """

        etude, nom, fids, _t = etude_reunion

        for fid, texte in zip(
            fids,
            [
                "Bloc un.",
                "Bloc deux.",
                "Bloc trois.",
            ]
        ):
            ajouter_version_reformulation(
                etude,
                fid,
                texte
            )

            valider_version_reformulation(
                etude,
                fid,
                1,
                validateur="Test"
            )

        from services.decoupage import (
            definir_ordre_ouvrage,
        )

        definir_ordre_ouvrage(
            etude,
            nom,
            list(reversed(fids))
        )

        resultat = assembler_reunion(etude, nom)

        section = resultat["reunions"][0]

        assert section["blocs"] == [
            "Bloc trois.",
            "Bloc deux.",
            "Bloc un.",
        ]

    def test_export_docx_et_txt(
        self,
        etude_reunion,
        tmp_path
    ):

        etude, nom, fids, _t = etude_reunion

        ajouter_version_reformulation(
            etude,
            fids[0],
            "Bloc validé pour l'export."
        )

        valider_version_reformulation(
            etude,
            fids[0],
            1,
            validateur="Test"
        )

        ouvrage = assembler_reunion(etude, nom)

        chemin_docx = exporter_docx(
            ouvrage,
            tmp_path / "reunion.docx"
        )

        chemin_txt = exporter_txt(
            ouvrage,
            tmp_path / "reunion.txt"
        )

        assert chemin_docx.is_file()
        assert chemin_txt.is_file()

        texte = chemin_txt.read_text(
            encoding="utf-8"
        )

        assert "Bloc validé pour l'export." in texte


#
# ==================================================
# Page Réunion, étape ⑥ : boutons d'export.
# ==================================================
#

class TestPageReunionExport:

    def test_boutons_rattachee(
        self,
        qapp,
        etude_reunion
    ):

        etude, nom, fids, tmp_path = etude_reunion

        from services.project_io import load_project

        projet_v1 = load_project(
            str(
                tmp_path
                / "2026-10-13_Luc1b"
                / "project.sttproj"
            )
        )

        from services.settings import (
            SettingsManager
        )
        from ui.reunion_window import ReunionWindow

        fenetre = ReunionWindow(
            projet_v1,
            settings=SettingsManager(
                str(tmp_path / "reglages")
            ),
            etude=etude,
            nom=nom
        )

        try:

            fenetre.changer_etape("export")

            page = fenetre.pages_etape["export"]

            boutons = [
                b.text()
                for b in (
                    page.findChildren(QPushButton)
                )
            ]

            # Portée réunion complète :
            # transcription + textes validés.
            assert (
                "Exporter la transcription…"
                in boutons
            )

            assert (
                "Exporter les textes validés…"
                in boutons
            )

        finally:
            fenetre.close()

    def test_boutons_autonome(
        self,
        qapp,
        tmp_path
    ):
        """
        Réunion autonome : l'export de transcription
        (portée réunion) reste disponible — les
        textes validés exigent une étude.
        """

        _p, _pv, _e, _n = (
            construire_etude_test(tmp_path)
        )

        from services.project_io import load_project

        projet_v1 = load_project(
            str(
                tmp_path
                / "2026-10-13_Luc1b"
                / "project.sttproj"
            )
        )

        from services.settings import (
            SettingsManager
        )
        from ui.reunion_window import ReunionWindow

        fenetre = ReunionWindow(
            projet_v1,
            settings=SettingsManager(
                str(tmp_path / "reglages")
            )
        )

        try:

            fenetre.changer_etape("export")

            page = fenetre.pages_etape["export"]

            boutons = [
                b.text()
                for b in (
                    page.findChildren(QPushButton)
                )
            ]

            assert (
                "Exporter la transcription…"
                in boutons
            )

            assert (
                "Exporter les textes validés…"
                not in boutons
            )

        finally:
            fenetre.close()


#
# ==================================================
# Portée ouvrage : la page Ouvrage porte l'export
# final (renvoi depuis la page Étude — P18.6c).
# ==================================================
#

class TestPorteeOuvrage:

    def test_bouton_export_sur_page_ouvrage(
        self,
        qapp,
        etude_reunion
    ):

        etude, _nom, _fids, _t = etude_reunion

        from services.settings import (
            SettingsManager
        )
        from ui.ouvrage_window import OuvrageWindow

        fenetre = OuvrageWindow(
            etude,
            settings=SettingsManager(
                str(_t / "reglages")
            )
        )

        try:

            assert (
                fenetre.exporter_button.text()
                .strip()
                == "📤 Exporter l'ouvrage…"
            )

        finally:
            fenetre.close()
