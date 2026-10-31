"""
Tests P20 — UI REFORMULATION (retour David
31/10, points 1 à 9) :

- point 1 : réunion AUTONOME (couvert aussi dans
  test_p18_6b_reunion) ;
- point 2 : icônes A+/A− EXACTEMENT celles de la
  page transcription (A à la couleur du texte du
  thème appliqué, signe +/− en bleu #2A7DDC —
  services.icons.make_text_size_icon partagé) ;
- point 3 : timeline SUPPRIMÉE (couvert dans
  test_p16bis_serie2 et test_reformulation_ui) ;
- point 4 : barre épurée (plus de Sauvegarder /
  Aide / Accueil / Timeline), barre remparentable
  alignée sur la ligne du stepper de la page
  Réunion ;
- point 5 : blocs SANS bordure, voile de survol
  progressif ~100 ms ;
- point 6 : en-têtes « Orateur » (aligné à
  gauche), « Transcription d'origine », « version
  reformulée » ;
- point 7 : icône Audio = icônes SVG teintées de
  la page transcription ;
- point 8 : défilement FIN (ScrollPerPixel, une à
  deux lignes par crant) et LISSE (animation
  ~140 ms non cumulable) ;
- point 9 : info-bulles de la colonne droite au
  thème de l'application, multi-lignes.
"""

import os

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from PySide6.QtCore import (
    QPoint,
    QPointF,
    Qt,
)
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QPushButton,
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
def fenetre(qapp, tmp_path):
    """
    Page Reformulation d'une réunion d'étude,
    réglages isolés.
    """

    _projet, _projet_v1, etude, nom = (
        construire_etude_test(tmp_path)
    )

    settings = SettingsManager(
        str(tmp_path / "reglages")
    )

    from ui.reformulation_window import (
        ReformulationWindow
    )

    fen = ReformulationWindow(
        etude,
        nom,
        settings=settings
    )

    yield fen

    fen.close()


def _couleurs_icone(bouton):
    image = (
        bouton.icon()
        .pixmap(32, 32)
        .toImage()
    )

    couleurs = {}

    for y in range(image.height()):
        for x in range(image.width()):

            couleur = image.pixelColor(x, y)

            if couleur.alpha() < 128:
                continue

            couleurs[couleur.name()] = (
                couleurs.get(couleur.name(), 0) + 1
            )

    return couleurs


#
# ==================================================
# Point 4 : barre épurée, alignée sur le stepper.
# ==================================================
#

class TestBarreEpuree:

    def test_boutons_supprimes(self, fenetre):

        for attribut in (
            "sauvegarder_button",
            "aide_button",
            "accueil_button",
            "timeline_button",
        ):
            assert not hasattr(
                fenetre,
                attribut
            )

    def test_boutons_conserves(self, fenetre):

        for attribut in (
            "traiter_button",
            "couts_button",
            "annuler_button",
            "augmenter_button",
            "diminuer_button",
            "jouer_button",
            "log_button",
        ):
            assert hasattr(fenetre, attribut)

    def test_barre_reparentable(self, fenetre):

        from PySide6.QtWidgets import QWidget

        assert isinstance(
            fenetre.barre_outils,
            QWidget
        )

    def test_barre_sur_la_ligne_du_stepper(
        self,
        qapp,
        tmp_path
    ):
        """
        La page Réunion place la barre de la
        reformulation dans sa zone d'outils (rangée
        du stepper) quand l'étape est active — et
        la retire quand on change d'étape.
        """

        _p, projet_v1, _etude, _nom = (
            construire_etude_test(tmp_path)
        )

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        from unittest.mock import patch
        from PySide6.QtWidgets import QMessageBox
        from ui.reunion_window import ReunionWindow

        fenetre_reunion = ReunionWindow(
            projet_v1,
            settings=settings,
            etude=_etude,
            nom=_nom,
        )

        try:

            with patch.object(
                QMessageBox,
                "question",
                staticmethod(
                    lambda *a, **k:
                    QMessageBox.StandardButton.Yes
                )
            ):
                fenetre_reunion.changer_etape(
                    "reformulation"
                )

            disposition = (
                fenetre_reunion.zone_outils
            )

            assert not disposition.isHidden()

            assert (
                disposition.layout().count() == 1
            )

            fenetre_reunion.changer_etape("export")

            assert disposition.isHidden()
        finally:
            fenetre_reunion.close()


#
# ==================================================
# Point 2 : icônes A+/A− identiques à la
# transcription.
# ==================================================
#

class TestIconesTailleTexte:

    def test_meme_generateur_que_transcription(
        self,
        fenetre
    ):
        """
        Le générateur est PARTAGÉ avec la page
        transcription : services.icons
        .make_text_size_icon.
        """

        from services.icons import (
            make_text_size_icon
        )

        icone = make_text_size_icon("+")

        assert icone is not None

    def test_signe_bleu_et_a_au_theme(
        self,
        fenetre,
        qapp
    ):
        from services.icons import (
            text_color_effectif
        )
        from services.theme_manager import (
            ThemeManager,
        )

        fenetre.show()

        ThemeManager.apply_theme(
            qapp,
            ThemeManager.DARK
        )

        couleurs = _couleurs_icone(
            fenetre.augmenter_button
        )

        #
        # « A » à la couleur du texte du thème
        # appliqué, signe en bleu #2A7DDC.
        #
        assert (
            text_color_effectif().lower()
            in couleurs
        )

        assert "#2a7ddc" in couleurs


#
# ==================================================
# Point 5 : blocs sans bordure, survol progressif.
# ==================================================
#

class TestBlocsSansBordure:

    def test_aucune_bordure(self, fenetre):

        for ligne in fenetre.lignes.values():

            for widget in (
                ligne.cellule_brute,
                ligne.cellule_reformee,
                ligne.label_locuteurs,
            ):

                assert (
                    "border: none"
                    in widget.styleSheet()
                )

    def test_aucun_effet_de_survol(
        self,
        fenetre
    ):
        """
        P20-bis, point 3 : la surbrillance des
        cellules survolées est ABANDONNÉE — le
        survol d'un bloc ne change RIEN.
        """

        ligne = next(
            iter(fenetre.lignes.values())
        )

        avant = ligne.cellule_brute.styleSheet()

        ligne.cellule_brute.enterEvent(None)

        assert (
            ligne.cellule_brute.styleSheet()
            == avant
        )

    def test_justifie_et_sans_grille(
        self,
        fenetre
    ):
        """
        P20-bis, point 2 : FIN de la logique tableur
        — texte JUSTIFIÉ (la délimitation visuelle
        des blocs), AUCUNE grille ni contour.
        """

        assert not fenetre.table.showGrid()

        for ligne in fenetre.lignes.values():

            for cellule in (
                ligne.cellule_brute,
                ligne.cellule_reformee,
            ):

                assert (
                    cellule.document()
                    .defaultTextOption()
                    .alignment()
                    == (
                        Qt.AlignmentFlag
                        .AlignJustify
                    )
                )

    def test_selection_sans_fond(
        self,
        fenetre
    ):
        """
        P20-ter (retour David 31/10) : sélectionner
        un bloc ne change PLUS son fond (le « bleu »
        a disparu) — la cellule reste transparente,
        seul le mot lu est surligné.
        """

        fenetre.sur_position_audio(21.0)

        style = (
            next(
                iter(
                    fenetre.lignes.values()
                )
            ).cellule_brute.styleSheet()
        )

        assert "transparent" in style

        assert "background-color: rgba" not in style

    def test_modele_et_parametres_dans_libelle(
        self,
        fenetre
    ):
        """
        P20-ter : la version mémorise le modèle LLM
        et ses paramètres EFFECTIFS — le libellé les
        affiche (traçabilité des écarts).
        """

        from services.etude_io import (
            ajouter_version_reformulation
        )

        ajouter_version_reformulation(
            fenetre.etude,
            1,
            "Version reformulée de test.",
            type_version="passe",
            stats={
                "duree_ms": 29_000,
                "tokens_in": 3400,
                "tokens_out": 2400,
                "cout_estime": 0.02,
                "modele": "mistral-large-4",
                "temperature": 0.3,
                "effort": "high",
                "max_tokens": 4000,
            }
        )

        version = fenetre.derniere_version(1)

        libelle = fenetre.libelle_version(version)

        assert "v1" in libelle

        assert "mistral-large-4" in libelle

        assert "T 0.3" in libelle

        assert "max 4000" in libelle


#
# ==================================================
# Point 6 : en-têtes épurés.
# ==================================================
#

class TestEntetes:

    def test_libelles(self, fenetre):

        entete = fenetre.table.horizontalHeader()

        assert (
            entete.model().headerData(
                0,
                Qt.Orientation.Horizontal
            )
            == "Orateur"
        )

        assert (
            entete.model().headerData(
                1,
                Qt.Orientation.Horizontal
            )
            == "Transcription d'origine"
        )

        assert (
            entete.model().headerData(
                2,
                Qt.Orientation.Horizontal
            )
            == "Version reformulée"
        )

    def test_orateur_aligne_a_gauche(self, fenetre):

        item = fenetre.table.horizontalHeaderItem(
            0
        )

        assert item.textAlignment() & (
            Qt.AlignmentFlag.AlignLeft
        )


#
# ==================================================
# Point 7 : icône Audio = icônes de transcription.
# ==================================================
#

class TestIconeAudio:

    def test_audio_avec_texte(self, fenetre):
        """
        P20-bis, point 7 : « Audio » à droite de
        l'icône.
        """

        assert fenetre.jouer_button.text() == (
            "Audio"
        )

    def test_bascule_lecture_pause(self, fenetre):
        """
        Play → pause : l'icône CHANGE (triangle →
        deux barres), l'état est porté par
        _lecture_en_cours.
        """

        fenetre.maj_icone_lecture(True)

        assert fenetre._lecture_en_cours

        image_pause = (
            fenetre.jouer_button
            .icon()
            .pixmap(32, 32)
            .toImage()
        )

        fenetre.maj_icone_lecture(False)

        assert not fenetre._lecture_en_cours

        image_lecture = (
            fenetre.jouer_button
            .icon()
            .pixmap(32, 32)
            .toImage()
        )

        assert image_pause != image_lecture

    def test_meme_icone_que_transcription(
        self,
        fenetre
    ):
        """
        Point 7 : le bouton Audio rend EXACTEMENT
        l'icône du lecteur de la page transcription
        (même générateur, mêmes SVG teintés).
        """

        from services.icons import (
            make_tinted_icon,
            text_color_effectif,
        )

        attendue = make_tinted_icon(
            text_color_effectif(),
            "icons/player-play.svg",
            22,
            fenetre.jouer_button.devicePixelRatioF()
        )

        image_attendue = (
            attendue.pixmap(32, 32).toImage()
        )

        fenetre.maj_icone_lecture(False)

        image_rendue = (
            fenetre.jouer_button
            .icon()
            .pixmap(32, 32)
            .toImage()
        )

        assert image_rendue == image_attendue


#
# ==================================================
# Point 8 : défilement fin et lissé.
# ==================================================
#

class TestDefilement:

    def test_scroll_par_pixel(self, fenetre):

        assert fenetre.table.verticalScrollMode(
        ) == (
            fenetre.table.ScrollMode
            .ScrollPerPixel
        )

    def test_molette_sur_les_cellules(
        self,
        fenetre
    ):
        """
        P20-ter : la molette fonctionne AU-DESSUS
        DES CELLULES (leur scrollbar interne
        masquée l'avale sinon) — le filtre la
        consomme et anime la table.
        """

        ligne = next(
            iter(fenetre.lignes.values())
        )

        fenetre.table.verticalScrollBar(
        ).setMaximum(1000)

        evenement = QWheelEvent(
            QPointF(5, 5),
            QPointF(5, 5),
            QPoint(0, -120),
            QPoint(0, -120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )

        for cible in (
            ligne.cellule_brute.viewport(),
            ligne.cellule_reformee.viewport(),
        ):

            fenetre._molette._cible = None

            assert fenetre._molette.eventFilter(
                cible,
                evenement
            )

            assert fenetre._molette._cible > 0

    def test_molette_deux_lignes_par_crant(
        self,
        fenetre
    ):
        """
        Un crant de molette (~120/120) déplace la
        cible de ~2 lignes de texte — pas d'un
        bloc entier ; l'animation est NON
        cumulable (la cible se RECALE depuis la
        cible courante).
        """

        barre = fenetre.table.verticalScrollBar()

        barre.setMaximum(1000)

        fenetre._molette._cible = None

        evenement = QWheelEvent(
            QPointF(5, 5),
            QPointF(5, 5),
            QPoint(0, -120),
            QPoint(0, -120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )

        assert fenetre._molette.eventFilter(
            fenetre.table.viewport(),
            evenement
        )

        premiere = fenetre._molette._cible

        assert premiere > barre.value()

        #
        # Deuxième crant PENDANT l'animation : la
        # cible repart de la cible (non cumulable,
        # pas d'annulation).
        #
        fenetre._molette.eventFilter(
            fenetre.table.viewport(),
            evenement
        )

        assert (
            fenetre._molette._cible
            > premiere
        )


#
# ==================================================
# Point 9 : info-bulles au thème de l'app,
# multi-lignes.
# ==================================================
#

class TestInfoBulles:

    def test_version_label_multiligne(
        self,
        fenetre
    ):
        """
        L'indicateur de version est un QLabel à
        RETOUR À LA LIGNE (le libellé
        « v3 · 29s · 3.4k→2.4k · 0.02 € » ne tient
        pas sur 130 px).
        """

        ligne = next(
            iter(fenetre.lignes.values())
        )

        assert isinstance(
            ligne.version_label,
            QLabel
        )

        assert ligne.version_label.wordWrap()

    def test_bulle_au_theme_applique(
        self,
        fenetre,
        qapp
    ):
        from services.theme_manager import (
            ThemeManager,
        )

        ligne = next(
            iter(fenetre.lignes.values())
        )

        bulle = ligne.bulle_pastille

        ThemeManager.apply_theme(
            qapp,
            ThemeManager.LIGHT
        )

        bulle.definir_texte("Essai")

        assert "#ffffff" in bulle.styleSheet()

        ThemeManager.apply_theme(
            qapp,
            ThemeManager.DARK
        )

        bulle.definir_texte("Essai")

        assert "#26272d" in bulle.styleSheet()

    def test_bulle_police_explicite(
        self,
        fenetre
    ):
        """
        La taille de police est EXPLICITE dans la
        feuille de l'info-bulle — la pastille
        parente (« font-size: 20px ») ne déteint
        PLUS dessus (retour David : police énorme).
        """

        ligne = next(
            iter(fenetre.lignes.values())
        )

        bulle = ligne.bulle_pastille

        bulle.definir_texte("Essai")

        assert "font-size:" in bulle.styleSheet()

        assert "font-size: 20px" not in (
            bulle.styleSheet()
        )

    def test_bulle_restylee_a_l_affichage(
        self,
        fenetre,
        qapp
    ):
        """
        Le thème de l'info-bulle est recalculé à
        CHAQUE affichage : un changement de thème à
        chaud ne laisse plus le fond du thème
        précédent (retour David : fond inversé).
        """

        from services.theme_manager import (
            ThemeManager,
        )

        ligne = next(
            iter(fenetre.lignes.values())
        )

        bulle = ligne.bulle_pastille

        bulle.definir_texte("Essai")

        ThemeManager.apply_theme(
            qapp,
            ThemeManager.DARK
        )

        bulle.montrer()

        assert "#26272d" in bulle.styleSheet()

        ThemeManager.apply_theme(
            qapp,
            ThemeManager.LIGHT
        )

        bulle.montrer()

        assert "#ffffff" in bulle.styleSheet()

        assert "#26272d" not in (
            bulle.styleSheet()
        )

    def test_bulle_multiligne(self, fenetre):

        ligne = next(
            iter(fenetre.lignes.values())
        )

        ligne.bulle_pastille.definir_texte(
            "Première ligne\nDeuxième ligne"
        )

        assert "<br>" in ligne.bulle_pastille.text()
