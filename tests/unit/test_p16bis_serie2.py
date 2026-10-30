"""
Tests P16-bis, 2ᵉ série de correctifs de relecture
(spec UI_REFORMULATION_MODIFS_V2_2026-10-27c.md
§8-§14).

Règles d'invariance (§14) :
1. cliquer un bloc positionne toujours le curseur
   audio à son début ; cliquer la timeline
   sélectionne toujours le bloc contenant la
   position (aller-retour cohérent) ;
2. pendant la lecture, le bloc courant est
   surligné et visible sans intervention ;
3. le surlignage est lisible dans les deux thèmes
   (contraste AA, aucun jaune clair sur fond
   sombre) ;
4. gouttière gauche de la timeline = colonne
   locuteurs, aucune marge vide à droite des
   pistes ;
5. « Accueil » ouvre toujours la page d'accueil ;
   jamais deux pages de la même étude/réunion
   dans la pile ;
6. « Ouvrir depuis un dossier… » refuse
   proprement un dossier sans etude.json.
"""

import json
import os
from unittest.mock import patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from PySide6.QtWidgets import QApplication

from services.etude_io import (
    ajouter_reunion,
    creer_etude,
    enregistrer_decoupage,
    ouvrir_etude,
    sauvegarder_etude,
)
from services.decoupage import generer_decoupage
from services.project_io import load_project
from services.settings import SettingsManager
from services.theme_manager import (
    COULEUR_BLOC_JOUE_CLAIR,
    COULEUR_BLOC_JOUE_SOMBRE,
    COULEUR_SURLIGNAGE_MOT_CLAIR,
    COULEUR_SURLIGNAGE_MOT_SOMBRE,
    couleurs_surlignage,
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


def construire_projet_long(tmp_path, nb_blocs=40):
    """
    Projet v1 de 40 blocs courts : de quoi déborder
    la zone visible de la table (défilement
    paresseux).
    """

    projet = tmp_path / "2026-10-13_Long"
    projet.mkdir()

    words = []
    blocks = []

    for b in range(nb_blocs):

        speaker = (
            "speaker_0" if b % 2 == 0 else "speaker_1"
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
            "name": "Long",
            "audio_file": "",
            "transcription_id": None,
            "language_code": "fr",
            "duration_seconds": nb_blocs * 10.0,
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


@pytest.fixture
def fenetre_longue(qapp, tmp_path):
    """
    Page Reformulation d'une réunion de 40 blocs,
    réglages isolés.
    """

    projet, projet_v1 = construire_projet_long(
        tmp_path
    )

    etude = creer_etude(
        tmp_path / "Etude",
        "Longue étude"
    )

    nom = ajouter_reunion(etude, projet, "Long")

    decoupage = generer_decoupage(
        etude,
        nom,
        projet_v1
    )

    enregistrer_decoupage(etude, decoupage)
    sauvegarder_etude(etude)

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

    fenetre.resize(900, 500)

    fenetre.show()

    QApplication.processEvents()

    yield fenetre

    fenetre.close()


@pytest.fixture
def app(qapp, tmp_path):
    """
    Fenêtre principale unique (pile de navigation),
    réglages isolés, avec une étude d'une réunion.
    """

    from ui.app_window import AppWindow

    projet, projet_v1, etude, nom = (
        construire_etude_test(tmp_path)
    )

    settings = SettingsManager(
        str(tmp_path / "reglages")
    )

    settings.add_recent_etude(
        str(tmp_path / "Etude")
    )

    fenetre_app = AppWindow(settings=settings)

    yield fenetre_app, projet, projet_v1, etude, nom

    fenetre_app.close()


#
# ==================================================
# §14.1 — synchronisation bidirectionnelle.
# ==================================================
#

@pytest.mark.qt
class TestInvariance1TimelineBlocs:

    def test_clic_bloc_positionne_le_curseur(self, fenetre_longue):

        # Le bloc 3 commence à ~20 s (positions de
        # l'audio traité, contrat §6).
        ligne = fenetre_longue.lignes[3]

        fenetre_longue.positionner_audio(ligne, 0)

        attendu = fenetre_longue.lignes[
            3
        ].bloc.positions.debut

        from services.timecodes import lire_timecode

        assert fenetre_longue.timeline.current_time == (
            lire_timecode(attendu)
        )

    def test_aller_retour_bloc_timeline_bloc(self, fenetre_longue):
        """
        Bloc → position → bloc : l'aller-retour est
        cohérent (le bloc cliqué redevient le bloc
        courant à sa propre position).
        """

        ligne = fenetre_longue.lignes[3]

        fenetre_longue.positionner_audio(ligne, 0)

        position = fenetre_longue.timeline.current_time

        fenetre_longue.sur_clic_timeline(position)

        assert fenetre_longue.bloc_courant == 3

    def test_clic_timeline_selectionne_le_bloc(self, fenetre_longue):
        """
        Cliquer la timeline sélectionne le bloc
        contenant la position — même en pause.
        """

        fenetre_longue.sur_clic_timeline(21.0)

        assert fenetre_longue.bloc_courant == 3

        # Le bloc courant est surligné (bord gauche
        # non transparent), les autres non.
        style = fenetre_longue.lignes[
            3
        ].cellule_brute.styleSheet()

        assert "transparent" not in style

        style_avant = fenetre_longue.lignes[
            1
        ].cellule_brute.styleSheet()

        assert "transparent" in style_avant


#
# ==================================================
# §14.2 — bloc courant surligné et visible.
# ==================================================
#

@pytest.mark.qt
class TestInvariance2SuiviLecture:

    def test_bloc_courant_visible(self, fenetre_longue):
        """
        Le bloc en lecture sortant de la zone visible
        y est ramené sans intervention ; il est
        surligné.
        """

        # Un bloc lointain, hors zone visible.
        fenetre_longue.table.scrollTo(
            fenetre_longue.table.model().index(0, 0)
        )

        QApplication.processEvents()

        assert not fenetre_longue._rangée_visible(
            fenetre_longue.rangees[35]
        )

        fenetre_longue.sur_position_audio(351.0)

        QApplication.processEvents()

        assert fenetre_longue.bloc_courant is not None

        rangée = fenetre_longue.rangees[
            fenetre_longue.bloc_courant
        ]

        assert fenetre_longue._rangée_visible(rangée)

        style = fenetre_longue.lignes[
            fenetre_longue.bloc_courant
        ].cellule_brute.styleSheet()

        assert "transparent" not in style

    def test_pas_de_defilement_pendant_l_edition(self, fenetre_longue):
        """
        Défilement paresseux : jamais quand
        l'utilisateur a le focus dans la table
        (sélection/édition).
        """

        fenetre_longue.table.scrollTo(
            fenetre_longue.table.model().index(0, 0)
        )

        QApplication.processEvents()

        # Focus clavier dans une cellule de la table.
        fenetre_longue.lignes[
            1
        ].cellule_reformee.setFocus()

        QApplication.processEvents()

        fenetre_longue.sur_position_audio(351.0)

        rangée = fenetre_longue.rangees[
            fenetre_longue.bloc_courant
        ]

        assert not fenetre_longue._rangée_visible(
            rangée
        )

    def test_pas_de_defilement_si_deja_visible(self, fenetre_longue):
        """
        Le bloc courant déjà visible : la vue ne
        défile pas (paresseux).
        """

        fenetre_longue.table.scrollTo(
            fenetre_longue.table.model().index(0, 0)
        )

        QApplication.processEvents()

        fenetre_longue.sur_position_audio(1.0)

        # Le premier bloc est resté en haut : la
        # première rangée est toujours visible.
        assert fenetre_longue._rangée_visible(0)


#
# ==================================================
# §14.3 — surlignage lisible dans les deux thèmes.
# ==================================================
#

def _luminance_relative(hexadecimale: str) -> float:
    """
    Luminance relative WCAG d'une couleur #RRGGBB.
    """

    valeur = hexadecimale.lstrip("#")

    canaux = [
        int(valeur[i:i + 2], 16) / 255
        for i in (0, 2, 4)
    ]

    canaux = [
        c / 12.92
        if c <= 0.04045
        else ((c + 0.055) / 1.055) ** 2.4
        for c in canaux
    ]

    return (
        0.2126 * canaux[0]
        + 0.7152 * canaux[1]
        + 0.0722 * canaux[2]
    )


def _contraste(fond: str, texte: str) -> float:
    """
    Rapport de contraste WCAG entre deux couleurs.
    """

    l1 = _luminance_relative(fond)
    l2 = _luminance_relative(texte)

    plus = max(l1, l2)
    moins = min(l1, l2)

    return (plus + 0.05) / (moins + 0.05)


@pytest.mark.qt
class TestInvariance3Themes:

    def test_couleurs_par_theme(self):
        """
        Aucune couleur de surlignage partagée entre
        les thèmes (spec correctifs §9.1).
        """

        clair = couleurs_surlignage(False)
        sombre = couleurs_surlignage(True)

        assert clair["mot"] != sombre["mot"]
        assert clair["bloc"] != sombre["bloc"]

        assert clair["mot"] == (
            COULEUR_SURLIGNAGE_MOT_CLAIR
        )

        assert sombre["mot"] == (
            COULEUR_SURLIGNAGE_MOT_SOMBRE
        )

        # Le jaune clair disparaît du thème sombre.
        assert sombre["mot"] != "#FFF3B0"

    def test_contraste_aa_clair(self):
        """
        Thème clair : texte sombre sur fond de
        surlignage — contraste AA minimum (4,5).
        """

        clair = couleurs_surlignage(False)

        assert _contraste(
            clair["mot"],
            "#191919",
        ) >= 4.5

        assert _contraste(
            clair["bloc"],
            "#FFFFFF",
        ) >= 3.0

    def test_contraste_aa_sombre(self):
        """
        Thème sombre : texte clair sur fond de
        surlignage sombre — contraste AA minimum.
        """

        sombre = couleurs_surlignage(True)

        assert _contraste(
            sombre["mot"],
            "#E0E0E0",
        ) >= 4.5

        assert _contraste(
            sombre["bloc"],
            "#101010",
        ) >= 3.0

    def test_surlignage_prend_la_couleur_du_theme(self, fenetre_longue):
        """
        Le surlignage du mot lu utilise la couleur
        passée par la fenêtre (celle du thème
        courant), pas une couleur figée.
        """

        ligne = fenetre_longue.lignes[1]

        ligne.mots_ligne = [(0, 4)]

        ligne.surligner_mot(
            0,
            couleur=COULEUR_SURLIGNAGE_MOT_SOMBRE,
        )

        selections = (
            ligne.cellule_brute.extraSelections()
        )

        assert selections

        couleur = (
            selections[0].format.background().color()
        )

        assert couleur.name().lower() == (
            COULEUR_SURLIGNAGE_MOT_SOMBRE.lower()
        )

        # Sans couleur : défaut du thème clair.
        ligne.surligner_mot(0)

        selections = (
            ligne.cellule_brute.extraSelections()
        )

        couleur = (
            selections[0]
            .format
            .background()
            .color()
        )

        assert couleur.name().lower() == (
            COULEUR_SURLIGNAGE_MOT_CLAIR.lower()
        )


#
# ==================================================
# §14.4 — gouttière gauche et bord droit.
# ==================================================
#

@pytest.mark.qt
class TestInvariance4Timeline:

    def test_gouttiere_egale_colonne_locuteurs(self, fenetre_longue):

        assert (
            fenetre_longue.timeline_speakers.width()
            == fenetre_longue.table.columnWidth(0)
        )

    def test_pistes_jusqu_au_bord_droit(self, fenetre_longue):
        """
        Aucune marge vide à droite : la timeline
        remplit au minimum la largeur du viewport.
        """

        QApplication.processEvents()

        viewport = (
            fenetre_longue.zone_timeline.viewport()
        )

        assert fenetre_longue.timeline.width() >= (
            viewport.width()
        )

    def test_redimensionnement_colonne_suivi(self, fenetre_longue):

        fenetre_longue.table.setColumnWidth(0, 240)

        QApplication.processEvents()

        assert (
            fenetre_longue.timeline_speakers.width()
            == 240
        )


#
# ==================================================
# §14.5 — navigation à pile unique.
# ==================================================
#

@pytest.mark.qt
class TestInvariance5Navigation:

    def test_pas_de_pages_dupliquees(self, app, tmp_path):

        fenetre_app, projet, projet_v1, etude, nom = app

        etude_ouverte = ouvrir_etude(
            tmp_path / "Etude"
        )

        page1 = fenetre_app.ouvrir_etude(
            tmp_path / "Etude"
        )

        page2 = fenetre_app.ouvrir_etude(
            tmp_path / "Etude"
        )

        assert page1 is page2

        # Une réunion (correction) ouverte deux fois
        # réactive la même page.
        cor1 = fenetre_app.ouvrir_correction(projet_v1)
        cor2 = fenetre_app.ouvrir_correction(projet_v1)

        assert cor1 is cor2

        # La reformulation de la même réunion, de
        # même.
        ref1 = fenetre_app.ouvrir_reformulation(
            etude_ouverte,
            nom
        )

        ref2 = fenetre_app.ouvrir_reformulation(
            etude_ouverte,
            nom
        )

        assert ref1 is ref2

        # Jamais deux fois la même page dans la pile.
        cles = fenetre_app.cles_ouvertes()

        assert len(cles) == len(set(cles))

        assert fenetre_app.pile.count() == len(cles)

    def test_accueil_ramene_a_l_accueil(self, app, tmp_path):

        fenetre_app, projet, projet_v1, etude, nom = app

        fenetre_app.ouvrir_etude(tmp_path / "Etude")

        etude_ouverte = ouvrir_etude(
            tmp_path / "Etude"
        )

        ref = fenetre_app.ouvrir_reformulation(
            etude_ouverte,
            nom
        )

        # « Accueil » depuis la page Reformulation :
        # toujours la page d'accueil de l'app.
        ref.retour_accueil()

        assert fenetre_app.page_active() is (
            fenetre_app.accueil
        )

    def test_plus_de_bouton_retour_a_l_etude(
        self,
        app,
        tmp_path
    ):
        """
        P18.6-bis (spec correctifs §8) : « Retour à
        l'étude » est supprimé — remplacé par
        « Gestion de l'étude » du ruban de la page
        Réunion. Les barres d'outils n'exposent plus
        ce bouton.
        """

        fenetre_app, projet, projet_v1, etude, nom = app

        etude_ouverte = ouvrir_etude(
            tmp_path / "Etude"
        )

        ref = fenetre_app.ouvrir_reformulation(
            etude_ouverte,
            nom
        )

        assert not hasattr(
            ref,
            "retour_etude_button"
        )

        assert not hasattr(
            ref,
            "retour_a_l_etude"
        )

        # Le retour à l'étude passe par le ruban de
        # la page Réunion (Gestion de l'étude) ou
        # « Accueil ».
        assert hasattr(ref, "retour_accueil")

    def test_editeur_sans_bouton_retour_a_l_etude(
        self,
        app,
        tmp_path
    ):
        """
        P18.6-bis (spec correctifs §8) : l'éditeur
        n'expose plus « Retour à l'étude ».
        """

        fenetre_app, projet, projet_v1, etude, nom = app

        editeur = fenetre_app.ouvrir_correction(
            projet_v1
        )

        assert not hasattr(
            editeur,
            "retour_etude_button"
        )

        assert not hasattr(
            editeur,
            "retour_a_l_etude"
        )


#
# ==================================================
# §14.6 — « Ouvrir depuis un dossier… ».
# ==================================================
#

@pytest.mark.qt
class TestInvariance6OuvrirDepuisDossier:

    def test_dossier_sans_etude_refuse(self, app, tmp_path):

        fenetre_app, *_ = app

        mauvais = tmp_path / "pas_une_etude"
        mauvais.mkdir()
        (mauvais / "bricolage.txt").write_text("x")

        avec_etude = tmp_path / "Etude"

        with patch(
            "ui.home_window.QFileDialog"
            ".getExistingDirectory",
            return_value=str(mauvais),
        ), patch(
            "ui.home_window.QMessageBox.warning"
        ) as avertissement:

            fenetre_app.accueil.ouvrir_etude_dialogue()

        # Message clair, rien ne s'ouvre.
        assert avertissement.called

        assert fenetre_app.page_active() is (
            fenetre_app.accueil
        )

        assert not fenetre_app.page_est_ouverte(
            (
                "etude",
                str(mauvais.resolve()),
            )
        )

        # Le dossier valide s'ouvre, lui — la page
        # Étude s'ouvre DIRECTEMENT (P18.6-bis
        # série 4 §21).
        with patch(
            "ui.home_window.QFileDialog"
            ".getExistingDirectory",
            return_value=str(avec_etude),
        ):

            fenetre_app.accueil.ouvrir_etude_dialogue()

        assert fenetre_app.page_active() is not (
            fenetre_app.accueil
        )

        # Et rejoint les études récentes.
        assert str(avec_etude) in (
            fenetre_app.settings.get_recent_etudes()
        )
