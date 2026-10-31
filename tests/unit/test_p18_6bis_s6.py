"""
Tests P18.6-bis, SÉRIE 6 — retour David du
31/10/2026 (points 1 à 5) :

- logo à la taille de la V1 (120 px) ;
- info-bulles des pastilles de services
  (« clé API ElevenLabs configurée », liste
  verticale « clé API {fournisseur} configurée »)
  et plaque COMPACTE ;
- tuiles de réunion compactes (hauteur divisée
  par deux), fond de tuile rendu dans les DEUX
  thèmes (plus jamais repeint #202124 par
  qdarktheme) ;
- clic GAUCHE sur la tuile → ouverture à
  l'ÉTAPE EN COURS ; clic droit → menu
  contextuel (ouvrir à l'étape en cours,
  rattacher — ABSENT si déjà rattachée,
  retirer des récentes) ;
- thème clair : fond de page gris Windows
  #f3f3f3 (plus aucun blanc pur), tuiles
  légèrement plus foncées ; thème sombre :
  fond unique #1e1f24 hors tuiles.
"""

import os
from unittest.mock import patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from PySide6.QtCore import (
    QEvent,
    QPoint,
    QSize,
    Qt,
)
from PySide6.QtGui import QMouseEvent
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
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


def construire_accueil(tmp_path, avec_etude=True):
    """
    Hub avec une réunion récente (le projet v1 de
    test), rattachée à l'étude si ``avec_etude`` —
    autonome sinon.
    """

    from services.llm.catalogue import (
        catalogue_par_defaut,
    )
    from ui.home_window import HomeWindow

    construire_etude_test(tmp_path)

    settings = SettingsManager(
        str(tmp_path / "reglages")
    )

    settings.add_recent_project(
        str(
            tmp_path
            / "2026-10-13_Luc1b"
            / "project.sttproj"
        )
    )

    if avec_etude:
        settings.add_recent_etude(
            str(tmp_path / "Etude")
        )

    with patch(
        "services.llm.catalogue"
        ".charger_catalogue",
        return_value=catalogue_par_defaut(),
    ):
        accueil = HomeWindow(settings=settings)

    accueil.resize(1200, 800)
    accueil.grab()

    return accueil


class NavigationFantine:
    """
    Pile de navigation factice : enregistre les
    ouvertures de réunion (projet, étape).
    """

    def __init__(self):
        self.ouvertures = []

    def ouvrir_reunion(
        self,
        projet,
        etape=None
    ):
        self.ouvertures.append(
            (projet, etape)
        )


#
# ==================================================
# Point 1 : logo à la taille de la V1.
# ==================================================
#

class TestLogoV1:

    def test_logo_120_px(self, qapp, tmp_path):
        """
        Le logo du bandeau retrouve la taille de la
        V1 diffusée (120 × 120 — retour David,
        point 1).
        """

        from pathlib import Path
        import tempfile

        from services.llm.catalogue import (
            catalogue_par_defaut,
        )
        from ui.home_window import HomeWindow

        settings = SettingsManager(
            str(
                Path(tempfile.mkdtemp())
                / "reglages"
            )
        )

        with patch(
            "services.llm.catalogue"
            ".charger_catalogue",
            return_value=catalogue_par_defaut(),
        ):
            accueil = HomeWindow(settings=settings)

        try:

            assert (
                accueil.logo_label
                .pixmap()
                .size()
                == QSize(120, 120)
            )

        finally:
            accueil.close()


#
# ==================================================
# Point 2 : info-bulles des services + plaque
# compacte.
# ==================================================
#

class TestPlaqueServices:

    @pytest.fixture
    def hub_vide(self, qapp, tmp_path):

        from services.llm.catalogue import (
            catalogue_par_defaut,
        )
        from ui.home_window import HomeWindow

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        with patch(
            "services.llm.catalogue"
            ".charger_catalogue",
            return_value=catalogue_par_defaut(),
        ):
            accueil = HomeWindow(settings=settings)

        accueil.resize(1200, 800)
        accueil.grab()

        yield accueil

        accueil.close()

    def test_info_bulle_elevenlabs(
        self,
        hub_vide
    ):
        """
        Survol du service de transcription (point 2) :
        « clé API ElevenLabs configurée » (ou
        « non configurée ») — l'info-bulle est portée
        par la LIGNE complète du service.
        """

        accueil = hub_vide

        with patch(
            "ui.home_window"
            ".has_transcription_api",
            return_value=False,
        ):
            accueil.update_api_status()

        assert accueil.ligne_api.toolTip() == (
            "clé API ElevenLabs non configurée"
        )

        with patch(
            "ui.home_window"
            ".has_transcription_api",
            return_value=True,
        ):
            accueil.update_api_status()

        assert accueil.ligne_api.toolTip() == (
            "clé API ElevenLabs configurée"
        )

    def test_info_bulle_ia_liste_verticale(
        self,
        hub_vide
    ):
        """
        Survol du service IA (point 2) : liste
        VERTICALE « clé API {fournisseur}
        configurée », une ligne par fournisseur
        configuré.
        """

        from services.credential_store import (
            CredentialStore
        )

        accueil = hub_vide

        assert accueil.ligne_llm.toolTip() == (
            "aucune clé API configurée"
        )

        store = CredentialStore(
            accueil.settings.app_folder
            / "settings.json"
        )

        store.set_cle_llm("openai", "sk-test")
        store.set_cle_llm("mistral", "sk-test")

        accueil.maj_statut_llm()

        lignes = (
            accueil.ligne_llm.toolTip().split("\n")
        )

        assert lignes == [
            "clé API OpenAI configurée",
            "clé API Mistral AI configurée",
        ]

    def test_plaque_compacte(
        self,
        hub_vide
    ):
        """
        La plaque des services est COMPACTE (retour
        David, point 2 : la largeur était
        démesurée) : libellés à 11 px par QFont (le
        sizeHint suit le rendu), plaque centrée
        verticalement — elle ne s'étire plus sur la
        hauteur du bandeau du logo 120 px.
        """

        accueil = hub_vide

        # Libellés réellement en 11 px.
        libelles = [
            l for l in (
                accueil
                .plaque_services
                .findChildren(QLabel)
            )
            if l.text()
        ]

        assert libelles

        assert all(
            l.font().pixelSize() == 11
            for l in libelles
        )

        # Plaque centrée, jamais étirée : sa
        # hauteur reste compacte face au bandeau
        # (le logo fait 120 px).
        assert (
            accueil.plaque_services.height()
            <= 60
        )

        assert (
            accueil.plaque_services.height()
            < accueil.bandeau.height()
        )


#
# ==================================================
# Point 3 : tuiles de réunion compactes, clic
# gauche → étape en cours, clic droit → menu.
# ==================================================
#

class TestTuilesReunionCompactes:

    def test_hauteur_divisee_par_deux(
        self,
        qapp,
        tmp_path
    ):
        """
        Point 3b : hauteur de chaque tuile de
        réunion DIVISÉE PAR DEUX — la rangée tient
        sur UNE ligne de texte (~40 px maximum au
        lieu de ~81).
        """

        from ui.home_window import HomeWindow
        from ui.tuiles import TuileReunion

        accueil = construire_accueil(tmp_path)

        try:

            tuiles = accueil.findChildren(
                TuileReunion
            )

            assert tuiles

            assert all(
                20 <= t.size().height() <= 45
                for t in tuiles
            )

        finally:
            accueil.close()

    def test_hauteur_suivit_page_empilee(
        self,
        qapp,
        tmp_path
    ):
        """
        La hauteur suit la page empilée COURANTE
        (une ligne large / deux lignes étroites) —
        le QStackedLayout ne réclame plus la
        hauteur de la plus haute des deux pages.
        """

        from ui.tuiles import TuileReunion

        accueil = construire_accueil(tmp_path)

        try:

            tuile = accueil.findChildren(
                TuileReunion
            )[0]

            tuile._basculer_selon_largeur(900)

            assert tuile.maximumHeight() == (
                tuile
                .page_une_ligne
                .sizeHint()
                .height()
            )

            tuile._basculer_selon_largeur(400)

            assert tuile.maximumHeight() == (
                tuile
                .page_deux_lignes
                .sizeHint()
                .height()
            )

        finally:
            accueil.close()

    def test_clic_gauche_uniquement(
        self,
        qapp,
        tmp_path
    ):
        """
        Point 3c : le clic GAUCHE sur la tuile ouvre
        la réunion ; le clic DROIT n'ouvre RIEN
        (il relève du menu contextuel, point 3d).
        """

        from ui.tuiles import TuileReunion

        accueil = construire_accueil(
            tmp_path,
            avec_etude=False
        )

        try:

            tuile = accueil.findChildren(
                TuileReunion
            )[0]

            ouverts = []
            tuile.ouvrir_demandee.connect(
                ouverts.append
            )

            def evenement(bouton):
                return QMouseEvent(
                    QEvent.Type.MouseButtonPress,
                    QPointF(3, 3),
                    QPointF(3, 3),
                    QPointF(3, 3),
                    bouton,
                    Qt.MouseButton.NoButton,
                    Qt.KeyboardModifier
                    .NoModifier,
                )

            tuile.mousePressEvent(
                evenement(
                    Qt.MouseButton.LeftButton
                )
            )

            assert ouverts == [tuile.chemin]

            tuile.mousePressEvent(
                evenement(
                    Qt.MouseButton.RightButton
                )
            )

            assert ouverts == [tuile.chemin]

        finally:
            accueil.close()

    def test_fond_tuile_rendu_sombre(
        self,
        qapp,
        tmp_path
    ):
        """
        Point 4 : le FOND de la tuile de réunion est
        rendu #2a2b31 en thème sombre — jamais
        repeint #202124 par qdarktheme (la « légère
        différence de couleur » constatée).
        """

        from services.theme_manager import (
            ThemeManager,
            reinitialiser_theme_actif,
        )
        from ui.tuiles import TuileReunion

        ThemeManager.apply_theme(
            qapp,
            ThemeManager.DARK
        )

        accueil = construire_accueil(tmp_path)

        try:

            tuile = accueil.findChildren(
                TuileReunion
            )[0]

            origine = tuile.mapTo(
                accueil,
                QPoint(0, 0)
            )

            image = (
                accueil
                .grab()
                .toImage()
            )

            centre = image.pixelColor(
                origine.x() + tuile.width() // 2,
                origine.y() + tuile.height() // 2,
            )

            assert (
                centre.red(),
                centre.green(),
                centre.blue(),
            ) == (42, 43, 49)

        finally:
            accueil.close()

            ThemeManager.apply_theme(
                qapp,
                ThemeManager.LIGHT
            )

            reinitialiser_theme_actif()

    def test_fond_tuile_rendu_clair(
        self,
        qapp,
        tmp_path
    ):
        """
        Point 5 : en thème clair, la tuile de réunion
        est LÉGÈREMENT PLUS FONCÉE que le fond de
        page gris Windows (#e9eaee sur #f3f3f3) —
        plus jamais un rectangle blanc pur.
        """

        from services.theme_manager import (
            ThemeManager,
            reinitialiser_theme_actif,
        )
        from ui.tuiles import TuileReunion

        ThemeManager.apply_theme(
            qapp,
            ThemeManager.LIGHT
        )

        accueil = construire_accueil(tmp_path)

        try:

            tuile = accueil.findChildren(
                TuileReunion
            )[0]

            origine = tuile.mapTo(
                accueil,
                QPoint(0, 0)
            )

            image = (
                accueil
                .grab()
                .toImage()
            )

            centre = image.pixelColor(
                origine.x() + tuile.width() // 2,
                origine.y() + tuile.height() // 2,
            )

            assert (
                centre.red(),
                centre.green(),
                centre.blue(),
            ) == (233, 234, 238)

        finally:
            accueil.close()

            reinitialiser_theme_actif()


#
# ==================================================
# Point 3c/3d : ouverture à l'étape en cours,
# menu contextuel.
# ==================================================
#

class TestOuvertureAEtapeEnCours:

    def test_etape_courante(self):
        """
        Étape en cours (service d'avancement) : la
        PREMIÈRE étape « en cours » l'emporte ; à
        défaut la première NON terminée ; None si
        tout est terminé ou si la réunion n'est pas
        transcrite.
        """

        from services.avancement import (
            A_FAIRE,
            EN_COURS,
            TERMINE,
            etape_courante,
        )

        # Plusieurs étapes en cours : la PREMIÈRE.
        assert etape_courante({
            "transcription": TERMINE,
            "reformulation": EN_COURS,
            "resume": EN_COURS,
            "export": A_FAIRE,
        }) == "reformulation"

        # Aucune en cours : la première non
        # terminée.
        assert etape_courante({
            "transcription": TERMINE,
            "reformulation": A_FAIRE,
            "resume": A_FAIRE,
            "export": A_FAIRE,
        }) == "reformulation"

        # Tout terminé : None (la page Réunion
        # s'ouvre sur son étape par défaut).
        assert etape_courante({
            "transcription": TERMINE,
            "reformulation": TERMINE,
            "resume": TERMINE,
            "export": TERMINE,
        }) is None

        # Réunion non transcrite : aucun stepper,
        # aucune étape.
        assert etape_courante(None) is None

    def test_clic_ouvre_a_etape_courante(
        self,
        qapp,
        tmp_path
    ):
        """
        Point 3c : le clic (gauche) sur la tuile
        ouvre la réunion à SON étape en cours —
        la pile de navigation reçoit l'étape.
        """

        from ui.tuiles import TuileReunion

        accueil = construire_accueil(tmp_path)

        try:

            tuile = accueil.findChildren(
                TuileReunion
            )[0]

            nav = NavigationFantine()
            accueil.navigation = nav

            tuile.mousePressEvent(None)

            assert len(nav.ouvertures) == 1

            projet, etape = nav.ouvertures[0]

            assert etape == "reformulation"

            # L'étape en cours est aussi celle du
            # menu contextuel (point 3d).
            menu = accueil._construire_menu_mini_tuile(
                tuile,
                tuile.chemin
            )

            nav.ouvertures.clear()

            menu.actions()[0].trigger()

            assert len(nav.ouvertures) == 1

            assert (
                nav.ouvertures[0][1]
                == "reformulation"
            )

        finally:
            accueil.close()

    def test_menu_contextuel_rattachee(
        self,
        qapp,
        tmp_path
    ):
        """
        Point 3d : réunion RATTACHÉE — l'option
        « Rattacher la réunion à une étude existante »
        est ABSENTE du menu (et non grisée).
        """

        from ui.tuiles import TuileReunion

        accueil = construire_accueil(
            tmp_path,
            avec_etude=True
        )

        try:

            tuile = accueil.findChildren(
                TuileReunion
            )[0]

            assert tuile.rattachee is True

            menu = accueil._construire_menu_mini_tuile(
                tuile,
                tuile.chemin
            )

            textes = [
                a.text()
                for a in menu.actions()
                if a.text()
            ]

            assert textes == [
                "Ouvrir la réunion "
                "à l'étape en cours",
                "Retirer de la liste "
                "des réunions récentes",
            ]

        finally:
            accueil.close()

    def test_menu_contextuel_autonome(
        self,
        qapp,
        tmp_path
    ):
        """
        Point 3d : réunion AUTONOME — le menu offre
        le rattachement à une étude existante.
        """

        from ui.tuiles import TuileReunion

        accueil = construire_accueil(
            tmp_path,
            avec_etude=False
        )

        try:

            tuile = accueil.findChildren(
                TuileReunion
            )[0]

            assert tuile.rattachee is False

            menu = accueil._construire_menu_mini_tuile(
                tuile,
                tuile.chemin
            )

            textes = [
                a.text()
                for a in menu.actions()
                if a.text()
            ]

            assert textes == [
                "Ouvrir la réunion "
                "à l'étape en cours",
                "Rattacher la réunion "
                "à une étude existante",
                "Retirer de la liste "
                "des réunions récentes",
            ]

        finally:
            accueil.close()


#
# ==================================================
# Points 4 et 5 : fonds de page par thème.
# ==================================================
#

class TestFondsDePage:

    def test_couleurs_theme_clair(self):
        """
        Point 5 : fond de page clair = gris élégant
        de Windows #f3f3f3 (plus aucun blanc pur) ;
        tuiles LÉGÈREMENT PLUS FONCÉES que ce fond.
        """

        from services.theme_manager import (
            FOND_PAGE_CLAIR,
            couleurs_tuiles,
        )

        assert FOND_PAGE_CLAIR == "#f3f3f3"

        clair = couleurs_tuiles(False)

        assert clair["fond"] == "#e9eaee"
        assert clair["fond"] != "#ffffff"

    def test_hub_clair_gris_windows(
        self,
        qapp,
        tmp_path
    ):
        """
        Point 5 : en thème clair, le hub peint le
        fond gris Windows #f3f3f3 (zones non-tuile
        transparentes) et la plaque des services
        prend ses couleurs CLAIRES.
        """

        from services.theme_manager import (
            ThemeManager,
            reinitialiser_theme_actif,
        )

        ThemeManager.apply_theme(
            qapp,
            ThemeManager.LIGHT
        )

        accueil = construire_accueil(tmp_path)

        try:

            assert "#f3f3f3" in (
                accueil.styleSheet()
            )

            style = (
                accueil
                .plaque_services
                .styleSheet()
            )

            assert "#f0f1f4" in style
            assert "#e8e9ee" in style
            assert "#c4c7cf" in style

        finally:
            accueil.close()

            reinitialiser_theme_actif()

    def test_hub_sombre_fond_unique(
        self,
        qapp,
        tmp_path
    ):
        """
        Point 4 : en thème sombre, TOUT ce qui n'est
        pas une tuile affiche le fond de page
        #1e1f24 — la fenêtre ET la zone des
        dernières réunions (aucune teinte
        intermédiaire entre les tuiles).
        """

        from services.theme_manager import (
            ThemeManager,
            reinitialiser_theme_actif,
        )

        ThemeManager.apply_theme(
            qapp,
            ThemeManager.DARK
        )

        accueil = construire_accueil(tmp_path)

        try:

            assert "#1e1f24" in (
                accueil.styleSheet()
            )

            # Pixel ENTRE deux tuiles de réunion :
            # strictement le fond de page.
            image = (
                accueil
                .grab()
                .toImage()
            )

            from ui.tuiles import TuileReunion

            tuile = accueil.findChildren(
                TuileReunion
            )[0]

            origine = tuile.mapTo(
                accueil,
                QPoint(0, 0)
            )

            entre = image.pixelColor(
                origine.x() + 30,
                origine.y() + tuile.height() + 3,
            )

            assert entre.name() == "#1e1f24"

        finally:
            accueil.close()

            ThemeManager.apply_theme(
                qapp,
                ThemeManager.LIGHT
            )

            reinitialiser_theme_actif()
