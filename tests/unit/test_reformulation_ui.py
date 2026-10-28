"""
Tests d'invariance UI de la page Reformulation.

Deux jeux de règles :

1. spec UI_REFORMULATION_V2.md §7 (P16.2) :
   1. la colonne brute n'expose aucune commande de
      modification (ni active ni grisée) ;
   2. aucune opération ne modifie le texte brut ;
   3. l'alignement brut ↔ reformulé tient ; la
      timeline ancrée en bas n'est pas affectée
      par le défilement ;
   4. un bloc validé est figé (édition et relances
      verrouillées ; versions consultées non
      éditables) ;
   5. la validation n'est possible que sur une
      version sauvegardée ;
   6. le filtrage par locuteur ne masque ni le
      traitement en cours ni la barre d'état.

2. spec UI_REFORMULATION_MODIFS_V2_2026-10-27.md
   §6 (P16-bis, correctifs de relecture) :
   1. aucune barre de défilement verticale visible
      à l'intérieur d'une cellule de bloc ;
   2. à tout instant, le haut de la cellule brute
      et le haut de la cellule reformulée sont sur
      la même ligne horizontale ;
   3. la largeur de la zone gauche de la timeline
      est égale à celle de la colonne locuteurs ;
   4. après fermeture/réouverture, la taille de
      police et la largeur des colonnes sont
      conservées ;
   5. « Reformulation… » depuis l'éditeur v1
      aboutit à la page Reformulation de la même
      réunion, et n'est pas actif pour un projet
      hors étude.
"""

import json
import os
from unittest.mock import patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QScrollBar,
)

from services.etude_io import (
    ajouter_reunion,
    ajouter_version_reformulation,
    creer_etude,
    enregistrer_decoupage,
    ouvrir_etude,
    sauvegarder_etude,
    valider_version_reformulation,
)
from services.decoupage import generer_decoupage
from services.project_io import load_project
from services.settings import SettingsManager


@pytest.fixture(scope="module")
def qapp():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    yield application


def construire_projet_test(tmp_path):
    """
    Projet v1 fictif horodaté : 3 blocs de parole,
    2 locuteurs (Philippe : blocs 1-2, Daniel :
    bloc 3), mots horodatés.
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

    return projet, load_project(
        str(projet / "project.sttproj")
    )


def construire_etude_test(tmp_path):
    """
    Étude d'une réunion (le projet v1 de test),
    segmentation générée et enregistrée.
    """

    projet, projet_v1 = construire_projet_test(
        tmp_path
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

    return projet, projet_v1, etude, nom


@pytest.fixture
def fenetre(qapp, tmp_path):
    """
    Page Reformulation d'une étude de 3 blocs
    (2 locuteurs), construite sur un projet v1
    fictif horodaté. Réglages isolés (jamais la
    configuration réelle de l'utilisateur).
    """

    _projet, _projet_v1, _etude, nom = (
        construire_etude_test(tmp_path)
    )

    etude_disco = ouvrir_etude(tmp_path / "Etude")

    from ui.reformulation_window import (
        ReformulationWindow
    )

    fenetre = ReformulationWindow(
        etude_disco,
        nom,
        settings=SettingsManager(
            str(tmp_path / "reglages")
        )
    )

    yield fenetre

    fenetre.close()


@pytest.fixture
def editeur(qapp, tmp_path):
    """
    Éditeur v1 (correction de transcription) d'un
    projet appartenant à une étude (référencée
    dans les études récentes de réglages isolés).
    """

    from ui.main_window import MainWindow

    _projet, projet_v1, _etude, _nom = (
        construire_etude_test(tmp_path)
    )

    settings = SettingsManager(
        str(tmp_path / "reglages")
    )

    settings.add_recent_etude(
        str(tmp_path / "Etude")
    )

    editeur = MainWindow(projet_v1, settings=settings)

    yield editeur

    editeur.close()


@pytest.fixture
def editeur_hors_etude(qapp, tmp_path):
    """
    Éditeur v1 d'un projet n'appartenant à aucune
    étude (aucune étude récente).
    """

    from ui.main_window import MainWindow

    _projet, projet_v1, _etude, _nom = (
        construire_etude_test(tmp_path)
    )

    editeur = MainWindow(
        projet_v1,
        settings=SettingsManager(
            str(tmp_path / "reglages_hors_etude")
        )
    )

    yield editeur

    editeur.close()


@pytest.mark.qt
class TestRegle1ColonneBrute:
    """
    Règle 1 (spec §7) : la colonne brute n'expose
    aucune commande de modification — ni active ni
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
    Règle 2 (spec §7) : aucune opération ne modifie
    le texte brut d'un bloc ; toute écriture passe
    par la colonne reformulée et crée une version.
    """

    def test_operations_ne_touchent_pas_le_brut(self, fenetre):

        texte_brut_avant = {
            fid: ligne.cellule_brute.toPlainText()
            for fid, ligne in fenetre.lignes.items()
        }

        fenetre.lignes[
            2
        ].cellule_reformee.setPlainText(
            "Édition manuelle du bloc 2."
        )

        fenetre.sur_texte_change(2)
        fenetre.sauvegarder_bloc(2)

        assert len(fenetre.versions_bloc(2)) == 1

        for fid, texte in texte_brut_avant.items():
            assert fenetre.lignes[
                fid
            ].cellule_brute.toPlainText() == texte


@pytest.mark.qt
class TestRegle3Alignement:
    """
    Règle 3 (spec §7) : l'alignement brut ↔
    reformulé se maintient ; la timeline (composant
    v1, ancrée en bas) n'est jamais affectée par le
    défilement vertical des colonnes.
    """

    def test_cellules_de_taille_egale(self, fenetre):

        fenetre.show()
        QApplication.processEvents()

        for ligne in fenetre.lignes.values():

            assert (
                ligne.cellule_brute.height()
                == ligne.cellule_reformee.height()
            )

    def test_timeline_hors_de_la_table(self, fenetre):
        """
        La timeline est ancrée hors de la table (la
        seule barre de défilement vertical de la
        page ne l'atteint pas).
        """

        parents = []

        widget = fenetre.conteneur_timeline

        while widget is not None:
            parents.append(widget)
            widget = widget.parentWidget()

        assert fenetre.table not in parents

        # La timeline est masquable.
        fenetre.conteneur_timeline.setVisible(False)
        fenetre.conteneur_timeline.setVisible(True)


@pytest.mark.qt
class TestRegle4BlocValideFigé:
    """
    Règle 4 (spec §7) : un bloc validé est figé —
    aucune édition ni relance ; les versions
    consultées ne peuvent pas être éditées.
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
    Règle 5 (spec §7) : une validation n'est
    possible que sur une version sauvegardée
    (l'édition non sauvegardée est signalée ; la
    validation propose de sauvegarder d'abord).
    """

    def test_validation_refusee_sans_sauvegarde(self, fenetre):

        ajouter_version_reformulation(
            fenetre.etude,
            1,
            "Reformulation du bloc 1.",
            type_version="passe",
        )

        fenetre.rafraichir_ligne(1)

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

        derniere = fenetre.derniere_version(1)

        assert derniere.type == "edition_manuelle"
        assert derniere.texte == "Édition non sauvegardée."
        assert derniere.validation.statut == "valide"


@pytest.mark.qt
class TestRegle6Filtrage:
    """
    Règle 6 (spec §7) : le filtrage par locuteur
    (API conservée, retirée de l'UI en P16-bis)
    ne masque jamais le traitement en cours ni
    les indicateurs de la barre d'état.
    """

    def test_barre_etat_toujours_visible(self, fenetre):

        barre_avant = fenetre.barre_etat.text()

        fenetre.selectionner_locuteur("Daniel")

        # Les blocs de Philippe sont masqués, pas la
        # barre d'état ni les boutons de traitement.
        assert not fenetre.ligne_visible(1)
        assert not fenetre.ligne_visible(2)
        assert fenetre.ligne_visible(3)

        assert not fenetre.barre_etat.isHidden()
        assert fenetre.barre_etat.text() == barre_avant

        assert not fenetre.traiter_button.isHidden()

        # Dé-filtrage.
        fenetre.selectionner_locuteur("Daniel")

        assert all(
            fenetre.ligne_visible(fid)
            for fid in fenetre.lignes
        )

    def test_filtrage_par_locuteur(self, fenetre):
        """
        Le filtre conserve les blocs du locuteur
        choisi et masque les autres (les blocs 1-2
        sont Philippe, le bloc 3 est Daniel).
        """

        fenetre.selectionner_locuteur("Philippe")

        assert fenetre.ligne_visible(1)
        assert fenetre.ligne_visible(2)
        assert not fenetre.ligne_visible(3)

        fenetre.selectionner_locuteur("Philippe")

        fenetre.selectionner_locuteur("Daniel")

        assert not fenetre.ligne_visible(1)
        assert not fenetre.ligne_visible(2)
        assert fenetre.ligne_visible(3)

        fenetre.selectionner_locuteur("Daniel")

        assert all(
            fenetre.ligne_visible(fid)
            for fid in fenetre.lignes
        )

    def test_api_conservee_sans_cases_a_cocher(self, fenetre):
        """
        P16-bis (spec correctifs §2) : la colonne
        locuteurs est une colonne de la table (un
        nom par ligne de bloc), plus aucun panneau
        de cases à cocher ; l'API de filtrage reste
        utilisable (prête à être rebranchée).
        """

        assert not hasattr(fenetre, "boutons_locuteurs")

        for fid, ligne in fenetre.lignes.items():

            rangée = fenetre.rangees[fid]

            label = fenetre.table.cellWidget(rangée, 0)

            assert label is ligne.label_locuteurs

            # Noms attendus : Philippe (blocs 1-2),
            # Daniel (bloc 3).
            attendu = " / ".join(ligne.bloc.locuteurs)

            assert label.text() == attendu


#
# ==================================================
# P16-bis — règles d'invariance additionnelles
# (spec UI_REFORMULATION_MODIFS_V2_2026-10-27 §6).
# ==================================================
#

@pytest.mark.qt
class TestInvariance1SansDefilementInterne:
    """
    Règle 1 (spec correctifs §6.1) : aucune barre
    de défilement verticale visible à l'intérieur
    d'une cellule de bloc, quel que soit le
    contenu.
    """

    def test_cellules_sans_barre_visible(self, fenetre):

        fenetre.show()
        QApplication.processEvents()

        for fid, ligne in fenetre.lignes.items():

            for cellule in (
                ligne.cellule_brute,
                ligne.cellule_reformee,
            ):

                assert (
                    cellule.verticalScrollBarPolicy()
                    == Qt.ScrollBarPolicy
                    .ScrollBarAlwaysOff
                )

                barre = cellule.verticalScrollBar()

                assert not barre.isVisibleTo(cellule)

                # Le contenu tient entièrement dans la
                # cellule : pas de plage de défilement.
                assert barre.maximum() == 0

    def test_arbre_de_la_table_sans_defilement_interne(self, fenetre):
        """
        Parcours des widgets de la table : les
        seules barres visibles appartiennent à la
        table elle-même (défilement unique).
        """

        fenetre.show()
        QApplication.processEvents()

        for fid, ligne in fenetre.lignes.items():

            widgets = [
                ligne.cellule_brute,
                ligne.cellule_reformee,
                ligne.label_locuteurs,
                ligne.colonne_droite,
            ]

            for widget in widgets:

                for barre in widget.findChildren(
                    QScrollBar
                ):
                    assert not barre.isVisibleTo(widget)

    def test_contenu_long_sans_barre(self, fenetre):
        """
        Un contenu plus long que la hauteur par
        défaut étend la ligne au lieu de faire
        apparaître un défilement interne.
        """

        fenetre.show()
        QApplication.processEvents()

        texte_long = " ".join(
            f"mot{i}" for i in range(200)
        )

        fenetre.lignes[1].cellule_reformee.setPlainText(
            texte_long
        )

        fenetre.sur_texte_change(1)

        QApplication.processEvents()

        barre = (
            fenetre.lignes[1]
            .cellule_reformee
            .verticalScrollBar()
        )

        assert not barre.isVisibleTo(
            fenetre.lignes[1].cellule_reformee
        )

        assert barre.maximum() == 0


@pytest.mark.qt
class TestInvariance2AlignementHorizontal:
    """
    Règle 2 (spec correctifs §6.2) : à tout instant,
    pour chaque bloc visible, le haut de la cellule
    brute et le haut de la cellule reformulée sont
    sur la même ligne horizontale (hauteur de
    ligne = max des deux cellules, l'autre se cale
    en haut).
    """

    def test_hauts_des_cellules_alignes(self, fenetre):

        fenetre.show()
        QApplication.processEvents()

        for fid, ligne in fenetre.lignes.items():

            rangée = fenetre.rangees[fid]

            brute = fenetre.table.cellWidget(rangée, 1)
            reformee = fenetre.table.cellWidget(rangée, 2)

            assert brute.y() == reformee.y()

            # Hauteur de ligne = max des deux cellules
            # : les cellules remplissent la ligne.
            assert brute.height() == reformee.height()

    def test_alignement_malgre_hauteurs_differentes(self, fenetre):
        """
        Deux blocs de contenus différents ont des
        hauteurs de ligne différentes et restent
        alignés horizontalement ; la ligne s'agrandit
        au fil de la frappe (spec correctifs §1.4).
        """

        fenetre.show()
        QApplication.processEvents()

        hauteurs_avant = {
            fid: fenetre.table.rowHeight(
                fenetre.rangees[fid]
            )
            for fid in fenetre.lignes
        }

        # Toutes les cellules vides au départ :
        # hauteurs identiques (plancher commun).
        assert len(set(hauteurs_avant.values())) == 1

        texte_long = " ".join(
            f"mot{i}" for i in range(120)
        )

        fenetre.lignes[2].cellule_reformee.setPlainText(
            texte_long
        )

        fenetre.sur_texte_change(2)

        QApplication.processEvents()

        hauteur_1 = fenetre.table.rowHeight(
            fenetre.rangees[1]
        )
        hauteur_2 = fenetre.table.rowHeight(
            fenetre.rangees[2]
        )

        # La ligne du bloc édité a grandi.
        assert hauteur_2 > hauteur_1

        # Les deux cellules du bloc restent alignées.
        brute = fenetre.table.cellWidget(
            fenetre.rangees[2], 1
        )
        reformee = fenetre.table.cellWidget(
            fenetre.rangees[2], 2
        )

        assert brute.y() == reformee.y()


@pytest.mark.qt
class TestInvariance3LargeurZoneGaucheTimeline:
    """
    Règle 3 (spec correctifs §6.3) : la largeur de
    la zone gauche de la timeline est égale à celle
    de la colonne locuteurs (à la tolérance de
    bordure près).
    """

    def test_largeurs_egales(self, fenetre):

        assert (
            fenetre.timeline_speakers.width()
            == fenetre.table.columnWidth(0)
        )

    def test_largeurs_suivent_le_redimensionnement(self, fenetre):

        fenetre.table.setColumnWidth(0, 210)

        QApplication.processEvents()

        assert fenetre.table.columnWidth(0) == 210
        assert fenetre.timeline_speakers.width() == 210

        fenetre.table.setColumnWidth(0, 130)

        QApplication.processEvents()

        assert fenetre.timeline_speakers.width() == 130


@pytest.mark.qt
class TestInvariance4Persistance:
    """
    Règle 4 (spec correctifs §6.4) : après
    fermeture/réouverture, la taille de police
    configurée et la largeur des colonnes sont
    conservées.
    """

    def test_defaut_abaisse_double_colonne(self, tmp_path):
        """
        Le défaut est abaissé pour la double colonne
        (spec correctifs §5.2).
        """

        from ui.reformulation_window import (
            TAILLE_TEXTE_DEFAUT
        )

        prefs = SettingsManager(
            str(tmp_path / "reglages")
        ).get_reformulation_prefs()

        assert prefs["taille_texte"] == (
            TAILLE_TEXTE_DEFAUT
        )

        assert TAILLE_TEXTE_DEFAUT < 13

    def test_taille_et_largeurs_conservees(self, fenetre, tmp_path):

        fenetre.changer_taille(2)

        assert fenetre.taille_texte == 13

        fenetre.table.setColumnWidth(0, 200)

        fenetre.close()

        # Réouverture avec les mêmes réglages : tout
        # est réappliqué.
        from ui.reformulation_window import (
            ReformulationWindow
        )

        etude = fenetre.etude
        nom = fenetre.reunion

        fenetre2 = ReformulationWindow(
            etude,
            nom,
            settings=SettingsManager(
                str(tmp_path / "reglages")
            )
        )

        try:

            assert fenetre2.taille_texte == 13
            assert fenetre2.table.columnWidth(0) == 200

            # La taille est appliquée aux cellules.
            police = (
                fenetre2.lignes[1]
                .cellule_brute
                .font()
            )

            assert police.pointSize() == 13

        finally:
            fenetre2.close()

    def test_plage_bornee(self, fenetre):
        """
        La plage A+/A− reste bornée comme avant
        (spec correctifs §5.3).
        """

        fenetre.taille_texte = 24
        fenetre.changer_taille(1)
        assert fenetre.taille_texte == 24

        fenetre.taille_texte = 9
        fenetre.changer_taille(-1)
        assert fenetre.taille_texte == 9


@pytest.mark.qt
class TestInvariance5BoutonReformulationEditeur:
    """
    Règle 5 (spec correctifs §6.5) : «
    Reformulation… » depuis l'éditeur v1 aboutit
    toujours à la page Reformulation de la même
    réunion (jamais d'une autre), et n'est pas
    actif pour un projet hors étude.
    """

    def test_actif_si_projet_dans_une_etude(self, editeur):

        assert editeur.reformulation_button.isEnabled()

    def test_ouvre_la_page_de_la_meme_reunion(self, editeur, tmp_path):

        from pathlib import Path

        from services.etude_io import fichier_projet_v1
        from ui.reformulation_window import (
            ReformulationWindow
        )

        editeur.ouvrir_reformulation()

        fenetre = editeur.reformulation_window

        assert isinstance(fenetre, ReformulationWindow)

        # La même réunion : celle qui référence le
        # projet ouvert dans l'éditeur (jamais une
        # autre).
        chemin = fichier_projet_v1(
            fenetre.etude,
            fenetre.reunion
        )

        assert chemin is not None

        assert (
            Path(chemin).resolve()
            == Path(editeur.project.project_file).resolve()
        )

        fenetre.close()

    def test_inactif_si_projet_hors_etude(self, editeur_hors_etude):

        bouton = editeur_hors_etude.reformulation_button

        assert not bouton.isEnabled()

        assert (
            "n'appartient à aucune étude"
            in bouton.toolTip()
        )

        assert editeur_hors_etude.etudes_referencant_projet() == []
