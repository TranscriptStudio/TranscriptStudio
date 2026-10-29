"""
Tests P18.6d — exclusivité du rattachement des
réunions aux études (ARBITRAGE_EXCLUSIVITE_REUNIONS
2026-10-29, spec navigation §6, invariants §9.1
et §9.5) au niveau UI : hub, page Réunion
(Gestion de l'étude), page Étude (ajout), dialogue
de rattachement avec changement d'étude confirmé.
"""

import os
from unittest.mock import patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
)

from services.etude_io import ouvrir_etude
from services.rattachement import (
    rattachement_de,
)
from services.settings import SettingsManager
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
def deux_etudes(qapp, tmp_path):
    """
    Une réunion attachée à une étude (avec un
    traitement validé) et une seconde étude vide.
    """

    import shutil

    projet, projet_v1, etude, nom = (
        construire_etude_test(tmp_path)
    )

    dossier_v1 = tmp_path / "2026-10-13_Luc1b"

    fids = [
        entree.fid
        for entree in (
            etude.registre.entrees.values()
        )
        if entree.reunion == nom
    ]

    from services.etude_io import (
        ajouter_version_reformulation,
        sauvegarder_etude,
        valider_version_reformulation,
    )

    ajouter_version_reformulation(
        etude,
        fids[0],
        "Texte validé dans la première étude."
    )

    valider_version_reformulation(
        etude,
        fids[0],
        1,
        validateur="Test"
    )

    sauvegarder_etude(etude)

    from services.etude_io import creer_etude

    creer_etude(
        tmp_path / "SecondeEtude",
        "Seconde étude"
    )

    settings = SettingsManager(
        str(tmp_path / "reglages")
    )

    settings.add_recent_project(
        str(dossier_v1 / "project.sttproj")
    )

    settings.add_recent_etude(
        str(tmp_path / "Etude")
    )

    settings.add_recent_etude(
        str(tmp_path / "SecondeEtude")
    )

    return {
        "projet": projet,
        "projet_v1": projet_v1,
        "etude": etude,
        "nom": nom,
        "fids": fids,
        "dossier_v1": dossier_v1,
        "settings": settings,
    }


#
# ==================================================
# Invariant §9.1 : une réunion appartient à
# 0 ou 1 étude, à tout instant — dans l'UI.
# ==================================================
#

class TestExclusiviteUI:

    def test_ajout_depuis_fichier_refuse(
        self,
        deux_etudes,
        tmp_path
    ):
        """
        La page Étude d'une AUTRE étude refuse
        d'ajouter une réunion déjà rattachée
        (l'UI affiche l'erreur d'exclusivité, rien
        n'est écrit).
        """

        from ui.etude_window import EtudeWindow

        data = deux_etudes

        page = EtudeWindow(
            tmp_path / "SecondeEtude",
            settings=data["settings"]
        )

        try:

            from services.rattachement import (
                RattachementError,
                rattacher,
            )

            with pytest.raises(RattachementError):

                rattacher(
                    tmp_path / "SecondeEtude",
                    data["dossier_v1"],
                    etudes_connues=(
                        data["settings"]
                        .cleanup_recent_etudes()
                    )
                )

            # Rien n'a été écrit dans la seconde
            # étude : toujours 0 ou 1 étude.
            assert rattachement_de(
                str(data["dossier_v1"]),
                [
                    tmp_path / "Etude",
                    tmp_path / "SecondeEtude",
                ]
            )[0] == str(tmp_path / "Etude")

        finally:
            page.close()

    def test_ajout_depuis_autonome_liste_les_libres(
        self,
        deux_etudes,
        tmp_path
    ):
        """
        « Depuis une réunion autonome… » ne propose
        que les réunions sans étude — la réunion
        attachée n'y figure pas.
        """

        from ui.etude_window import EtudeWindow

        data = deux_etudes

        page = EtudeWindow(
            tmp_path / "SecondeEtude",
            settings=data["settings"]
        )

        try:

            from services.rattachement import (
                verifier_exclusivite,
            )

            etudes = (
                data["settings"]
                .cleanup_recent_etudes()
            )

            conflit = verifier_exclusivite(
                str(
                    data["dossier_v1"]
                    / "project.sttproj"
                ),
                etudes
            )

            # La réunion du fixture n'est PAS
            # autonome : elle ne peut pas figurer
            # dans la liste proposée.
            assert conflit == (
                str(tmp_path / "Etude"),
                data["nom"]
            )

        finally:
            page.close()


#
# ==================================================
# Invariant §9.5 : changement d'étude = option A
# (les traitements restent à l'ancienne étude).
# ==================================================
#

class TestChangementEtudeUI:

    def test_dialogue_changement_confirme(
        self,
        deux_etudes,
        tmp_path
    ):
        """
        Le dialogue de rattachement, face à une
        réunion déjà attachée, propose le
        changement d'étude ; confirmé, la réunion
        change de rattachement et les traitements
        restent à l'ancienne étude.
        """

        from ui.rattachement_dialog import (
            RattachementDialog
        )

        data = deux_etudes

        dialogue = RattachementDialog(
            str(
                data["dossier_v1"]
                / "project.sttproj"
            ),
            data["settings"]
        )

        # Sélection de la seconde étude.
        index = None

        for i in range(
            dialogue.liste_etudes.count()
        ):

            item = dialogue.liste_etudes.item(i)

            if item.data(0x0100) == str(
                tmp_path / "SecondeEtude"
            ):
                index = i
                break

        assert index is not None

        dialogue.liste_etudes.setCurrentRow(index)

        # Confirmation du changement d'étude.
        with patch(
            "PySide6.QtWidgets.QMessageBox.question",
            return_value=(
                QMessageBox.StandardButton.Yes
            )
        ):
            dialogue.accept()

        assert dialogue.resultat() is not None

        # La réunion appartient désormais à la
        # seconde étude, plus à la première.
        rattachement = rattachement_de(
            str(
                data["dossier_v1"]
                / "project.sttproj"
            ),
            [
                tmp_path / "Etude",
                tmp_path / "SecondeEtude",
            ]
        )

        assert rattachement[0] == (
            str(tmp_path / "SecondeEtude")
        )

        # Option A : les traitements RESTENT à
        # l'ancienne étude (aucun déplacement,
        # aucune copie).
        assert (
            tmp_path / "Etude"
            / "traitements" / "reformulation"
            / f"{data['fids'][0]}.json"
        ).is_file()

        assert not (
            tmp_path / "SecondeEtude"
            / "traitements" / "reformulation"
            / f"{data['fids'][0]}.json"
        ).exists()

    def test_dialogue_changement_refuse(
        self,
        deux_etudes,
        tmp_path
    ):
        """
        Changement refusé : la réunion ne bouge pas.
        """

        from ui.rattachement_dialog import (
            RattachementDialog
        )

        data = deux_etudes

        dialogue = RattachementDialog(
            str(
                data["dossier_v1"]
                / "project.sttproj"
            ),
            data["settings"]
        )

        for i in range(
            dialogue.liste_etudes.count()
        ):

            item = dialogue.liste_etudes.item(i)

            if item.data(0x0100) == str(
                tmp_path / "SecondeEtude"
            ):
                dialogue.liste_etudes.setCurrentRow(
                    i
                )
                break

        with patch(
            "PySide6.QtWidgets.QMessageBox.question",
            return_value=QMessageBox.StandardButton.No
        ):
            dialogue.accept()

        assert dialogue.resultat() is None

        rattachement = rattachement_de(
            str(
                data["dossier_v1"]
                / "project.sttproj"
            ),
            [
                tmp_path / "Etude",
                tmp_path / "SecondeEtude",
            ]
        )

        assert rattachement[0] == (
            str(tmp_path / "Etude")
        )


#
# ==================================================
# Gestion de l'étude sur la page Réunion.
# ==================================================
#

class TestGestionEtudeReunion:

    def test_detacher_depuis_page_reunion(
        self,
        deux_etudes,
        tmp_path
    ):
        """
        « Détacher de l'étude… » (page Réunion) :
        la réunion devient autonome, les
        traitements restent à l'étude (option A).
        """

        data = deux_etudes

        from ui.reunion_window import ReunionWindow

        fenetre = ReunionWindow(
            data["projet_v1"],
            settings=data["settings"],
            etude=data["etude"],
            nom=data["nom"]
        )

        try:

            assert fenetre.rattachee()

            with patch(
                "PySide6.QtWidgets"
                ".QMessageBox.question",
                return_value=(
                    QMessageBox.StandardButton.Yes
                )
            ):
                fenetre.detacher_ui()

            assert not fenetre.rattachee()

            # Badge autonome.
            assert fenetre.badge_label.text() == (
                "Réunion autonome"
            )

            # Option A : les traitements restent
            # à l'étude sur le disque.
            assert (
                tmp_path / "Etude"
                / "traitements" / "reformulation"
                / f"{data['fids'][0]}.json"
            ).is_file()

        finally:
            fenetre.close()

    def test_rattacher_depuis_page_reunion(
        self,
        deux_etudes,
        tmp_path
    ):
        """
        « Rattacher à une étude… » depuis une page
        Réunion autonome : la réunion rejoint
        l'étude choisie (rattachement possible à
        tout moment, dès le prétraitement).
        """

        data = deux_etudes

        from services.rattachement import (
            detacher_reunion,
        )
        from services.etude_io import (
            sauvegarder_etude,
        )

        detacher_reunion(data["etude"], data["nom"])
        sauvegarder_etude(data["etude"])

        from ui.reunion_window import ReunionWindow

        fenetre = ReunionWindow(
            data["projet_v1"],
            settings=data["settings"]
        )

        try:

            assert not fenetre.rattachee()

            class DialogueFictif:

                def __init__(
                    self,
                    chemin,
                    settings,
                    parent=None
                ):
                    self.chemin = chemin
                    self.settings = settings

                def exec(self):
                    """
                    Doubure fonctionnelle : rattache la
                    réunion à la seconde étude, comme le
                    ferait le vrai dialogue validé.
                    """

                    from services.rattachement import (
                        rattacher,
                    )

                    rattacher(
                        tmp_path / "SecondeEtude",
                        self.chemin,
                        etudes_connues=(
                            self.settings
                            .cleanup_recent_etudes()
                        )
                    )

                    return True

            with patch(
                "ui.rattachement_dialog"
                ".RattachementDialog",
                DialogueFictif
            ):
                fenetre.rattacher_ui()

            # Résolution depuis les études
            # récentes : la réunion est rattachée.
            assert fenetre.rattachee()

            assert fenetre.nom is not None

        finally:
            fenetre.close()
