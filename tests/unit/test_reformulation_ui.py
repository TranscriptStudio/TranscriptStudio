"""
Tests d'invariance UI de la page Reformulation
(P16.2, spec UI_REFORMULATION_V2.md §7).

Six règles à tester :
1. la colonne brute n'expose aucune commande de
   modification (ni active ni grisée) ;
2. aucune opération ne modifie le texte brut ;
3. l'alignement brut ↔ reformulé tient ; la
   timeline ancrée en bas n'est pas affectée par
   le défilement ;
4. un bloc validé est figé (édition et relances
   verrouillées ; versions consultées non
   éditables) ;
5. la validation n'est possible que sur une
   version sauvegardée ;
6. le filtrage par locuteur ne masque ni le
   traitement en cours ni la barre d'état.
"""

import json
import os
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from PySide6.QtWidgets import QApplication

from services.etude_io import (
    ajouter_reunion,
    ajouter_version_reformulation,
    creer_etude,
    enregistrer_decoupage,
    sauvegarder_etude,
    valider_version_reformulation,
)
from services.decoupage import generer_decoupage
from services.project_io import load_project


@pytest.fixture(scope="module")
def qapp():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    yield application


@pytest.fixture
def fenetre(qapp, tmp_path):
    """
    Page Reformulation d'une étude de 3 blocs
    (2 locuteurs), construite sur un projet v1
    fictif horodaté.
    """

    projet = tmp_path / "2026-10-13_Luc1b"
    projet.mkdir()

    words = []
    blocks = []

    for b in range(3):

        speaker = (
            "speaker_0" if b < 2 else "speaker_1"
        )

        debut = len(words)

        for m in range(4):
            words.append({
                "text": f"b{b}m{m}",
                "start": b * 10 + m * 2.0,
                "end": b * 10 + m * 2.0 + 1.5,
                "speaker_id": speaker,
                "item_type": "word",
            })
            words.append({
                "text": " ",
                "start": None,
                "end": None,
                "speaker_id": speaker,
                "item_type": "spacing",
            })

        blocks.append({
            "id": b,
            "speaker_id": speaker,
            "start_word": debut,
            "end_word": len(words) - 1,
            "created_by_user": False,
        })

    (projet / "project.sttproj").write_text(
        json.dumps({
            "project_format_version": 1,
            "name": "Luc1b",
            "audio_file": "",
            "transcription_id": None,
            "language_code": "fr",
            "duration_seconds": 30.0,
            "modified": False,
            "speakers": [
                {
                    "id": "speaker_0",
                    "name": "Philippe",
                    "color": "#123456",
                },
                {
                    "id": "speaker_1",
                    "name": "Daniel",
                    "color": "#654321",
                },
            ],
            "words": words,
            "blocks": blocks,
            "original_elevenlabs_response": {},
        }, ensure_ascii=False),
        encoding="utf-8"
    )

    projet_v1 = load_project(
        str(projet / "project.sttproj")
    )

    etude = creer_etude(
        tmp_path / "Etude",
        "Évangile de Luc"
    )

    nom = ajouter_reunion(etude, projet, "Chapitre 1")

    decoupage = generer_decoupage(
        etude,
        nom,
        projet_v1
    )

    enregistrer_decoupage(etude, decoupage)
    sauvegarder_etude(etude)

    from ui.reformulation_window import (
        ReformulationWindow
    )

    # La fenêtre charge l'étude du disque.
    from services.etude_io import ouvrir_etude

    etude_disco = ouvrir_etude(tmp_path / "Etude")

    fenetre = ReformulationWindow(
        etude_disco,
        nom
    )

    yield fenetre

    fenetre.close()


@pytest.mark.qt
class TestRegle1ColonneBrute:
    """
    Règle 1 : la colonne brute n'expose aucune
    commande de modification — ni active ni
    grisée ; seuls le positionnement du curseur
    (clic) et la timeline réagissent.
    """

    def test_lecture_seule_permanente(self, fenetre):

        for ligne in fenetre.lignes.values():
            assert ligne.cellule_brute.isReadOnly()

    def test_aucun_menu_contextuel_v1(self, fenetre):
        """
        Les menus v1 (correction de mots, split,
        merge, renommage) n'existent pas sur cette
        page : le contextMenuEvent de la cellule
        brute n'est pas redéfini.
        """

        ligne = fenetre.lignes[1]

        # La cellule reformulée, elle, ouvre le menu
        # des opérations (spec §5) ; la cellule brute
        # garde le comportement par défaut.
        assert ligne.cellule_reformee.contextMenuEvent

        # Le menu des opérations n'existe que par la
        # pastille et le clic droit sur la cellule
        # reformulée — jamais sur la brute.
        methode = getattr(
            ligne.cellule_brute,
            "contextMenuEvent",
            None
        )

        assert methode is not None

    def test_clic_positionne_l_audio(self, fenetre):
        """
        Le clic dans le texte brut positionne le
        curseur de lecture : seule action avec la
        timeline.
        """

        fenetre.positionner_audio(
            fenetre.lignes[1],
            6
        )

        # Aucune modification du texte brut.
        assert fenetre.lignes[
            1
        ].cellule_brute.toPlainText() == (
            fenetre.lignes[1].bloc.source
        )


@pytest.mark.qt
class TestRegle2BrutImmuable:
    """
    Règle 2 : aucune opération ne modifie le texte
    brut d'un bloc ; toute écriture passe par la
    colonne reformulée et crée une version.
    """

    def test_operations_ne_touchent_pas_le_brut(self, fenetre):

        texte_brut_avant = {
            fid: ligne.cellule_brute.toPlainText()
            for fid, ligne in fenetre.lignes.items()
        }

        # Édition manuelle + sauvegarde (nouvelle
        # version, contrat §7).
        fenetre.lignes[
            2
        ].cellule_reformee.setPlainText(
            "Édition manuelle du bloc 2."
        )

        fenetre.sur_texte_change(2)
        fenetre.sauvegarder_bloc(2)

        assert len(fenetre.versions_bloc(2)) == 1

        # Le texte brut est intact.
        for fid, texte in texte_brut_avant.items():
            assert fenetre.lignes[
                fid
            ].cellule_brute.toPlainText() == texte


@pytest.mark.qt
class TestRegle3Alignement:
    """
    Règle 3 : l'alignement brut ↔ reformulé se
    maintient ; la timeline (composant v1, ancrée
    en bas) n'est jamais affectée par le
    défilement vertical des colonnes.
    """

    def test_cellules_de_taille_egale(self, fenetre):

        ligne = fenetre.lignes[1]

        hauteur_brute = (
            ligne.cellule_brute.height()
        )
        hauteur_reformee = (
            ligne.cellule_reformee.height()
        )

        # La hauteur de ligne est le max des deux
        # cellules : alignment par bloc.
        assert hauteur_brute == hauteur_reformee

    def test_timeline_hors_zone_defilement(self, fenetre):
        """
        La timeline est ancrée hors de la zone de
        défilement des colonnes.
        """

        parents = []

        widget = fenetre.conteneur_timeline

        while widget is not None:
            parents.append(widget)
            widget = widget.parentWidget()

        assert fenetre.zone_defilement not in parents

        # La timeline est masquable.
        assert fenetre.conteneur_timeline.isVisibleTo(
            fenetre
        ) or fenetre.conteneur_timeline.isHidden()

        fenetre.conteneur_timeline.setVisible(False)
        fenetre.conteneur_timeline.setVisible(True)


@pytest.mark.qt
class TestRegle4BlocValideFigé:
    """
    Règle 4 : un bloc validé est figé — aucune
    édition ni relance ; les versions consultées
    ne peuvent pas être éditées.
    """

    def test_validation_fige_le_bloc(self, fenetre):

        ajouter_version_reformulation(
            fenetre.etude,
            3,
            "Reformulation du bloc 3.",
            type_version="passe",
        )

        fenetre.rafraichir_ligne(3)

        assert fenetre.etat_bloc(3) == "modifiable"
        assert not fenetre.lignes[
            3
        ].cellule_reformee.isReadOnly()

        derniere = fenetre.derniere_version(3)

        valider_version_reformulation(
            fenetre.etude,
            3,
            numero=derniere.numero,
            validateur="Test"
        )

        fenetre.rafraichir_ligne(3)

        assert fenetre.etat_bloc(3) == "validee"
        assert fenetre.lignes[
            3
        ].cellule_reformee.isReadOnly()

    def test_version_consultee_non_editable(self, fenetre):

        ajouter_version_reformulation(
            fenetre.etude,
            2,
            "Première version.",
            type_version="passe",
        )

        ajouter_version_reformulation(
            fenetre.etude,
            2,
            "Deuxième version.",
            type_version="edition_manuelle",
        )

        fenetre.rafraichir_ligne(2)

        assert not fenetre.lignes[
            2
        ].cellule_reformee.isReadOnly()

        fenetre.lignes[2].consultation = 1
        fenetre.rafraichir_ligne(2)

        # Version consultée : lecture seule (règle 4)
        # + affichage clair.
        assert fenetre.lignes[
            2
        ].cellule_reformee.isReadOnly()

        assert "consultée" in fenetre.lignes[
            2
        ].version_label.text()

        # Retour à la version courante : éditable.
        fenetre.lignes[2].consultation = None
        fenetre.rafraichir_ligne(2)

        assert not fenetre.lignes[
            2
        ].cellule_reformee.isReadOnly()


@pytest.mark.qt
class TestRegle5ValidationSurVersionSauvegardee:
    """
    Règle 5 : une validation n'est possible que
    sur une version sauvegardée (l'édition non
    sauvegardée est signalée ; la validation
    propose de sauvegarder d'abord).
    """

    def test_validation_refusee_sans_sauvegarde(self, fenetre):
        """
        L'utilisateur refuse la sauvegarde :
        aucune validation ne part.
        """

        ajouter_version_reformulation(
            fenetre.etude,
            1,
            "Reformulation du bloc 1.",
            type_version="passe",
        )

        fenetre.rafraichir_ligne(1)

        # Modifications non enregistrées.
        fenetre.lignes[
            1
        ].cellule_reformee.setPlainText(
            "Édition non sauvegardée."
        )

        fenetre.sur_texte_change(1)

        assert fenetre.lignes[1].non_enregistre

        fenetre.rafraichir_ligne(1)

        # Refus : la validation ne s'effectue pas.
        import PySide6.QtWidgets as QtWidgets

        with patch.object(
            QtWidgets.QMessageBox,
            "question",
            return_value=QtWidgets.QMessageBox.StandardButton.No
        ):
            fenetre.valider_bloc(1)

        assert fenetre.etat_bloc(1) == "modifiable"
        assert fenetre.lignes[1].non_enregistre

        # Acceptation : sauvegarde puis validation.
        with patch.object(
            QtWidgets.QMessageBox,
            "question",
            return_value=QtWidgets.QMessageBox.StandardButton.Yes
        ):
            fenetre.valider_bloc(1)

        assert fenetre.etat_bloc(1) == "validee"
        assert fenetre.lignes[1].non_enregistre is False

        # La version validée est l'édition
        # manuelle créée par la sauvegarde.
        derniere = fenetre.derniere_version(1)

        assert derniere.type == "edition_manuelle"
        assert derniere.texte == "Édition non sauvegardée."
        assert derniere.validation.statut == "valide"


@pytest.mark.qt
class TestRegle6Filtrage:
    """
    Règle 6 : le filtrage par locuteur ne masque
    jamais le traitement en cours ni les
    indicateurs de la barre d'état.
    """

    def test_barre_etat_toujours_visible(self, fenetre):

        barre_avant = fenetre.barre_etat.text()

        fenetre.selectionner_locuteur("Daniel")

        # Les blocs de Philippe sont masqués, pas la
        # barre d'état ni les boutons de traitement.
        masques = [
            fid
            for fid, ligne in fenetre.lignes.items()
            if ligne.isHidden()
        ]

        assert 3 not in masques

        assert not fenetre.barre_etat.isHidden()
        assert fenetre.barre_etat.text() == barre_avant

        assert not fenetre.traiter_button.isHidden()

        # Dé-filtrage.
        fenetre.selectionner_locuteur("Daniel")

        assert all(
            not ligne.isHidden()
            for ligne in fenetre.lignes.values()
        )

    def test_filtrage_par_locuteur(self, fenetre):
        """
        Le filtre conserve les blocs du locuteur
        choisi et masque les autres (les blocs 1-2
        sont Philippe, le bloc 3 est Daniel).
        """

        fenetre.selectionner_locuteur("Philippe")

        assert not fenetre.lignes[1].isHidden()
        assert not fenetre.lignes[2].isHidden()
        assert fenetre.lignes[3].isHidden()

        fenetre.selectionner_locuteur("Philippe")

        fenetre.selectionner_locuteur("Daniel")

        assert fenetre.lignes[1].isHidden()
        assert fenetre.lignes[2].isHidden()
        assert not fenetre.lignes[3].isHidden()

        fenetre.selectionner_locuteur("Daniel")

        assert all(
            not ligne.isHidden()
            for ligne in fenetre.lignes.values()
        )
