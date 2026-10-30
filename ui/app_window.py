# ui/app_window.py
"""
Fenêtre principale unique de l'application (P16-bis,
spec correctifs §11 — navigation à pile unique).

L'app possède une seule fenêtre principale dont les
pages sont empilées :

    Accueil → Étude → Réunion (Correction / Reformulation)

- « Accueil » ramène toujours à la page d'accueil
  de l'app (projets + études récents), jamais à la
  page Étude ;
- « Retour à l'étude » (pages Réunion) revient à la
  page Étude ;
- jamais de pages dupliquées : ouvrir une étude ou
  une réunion déjà affichée réactive la page
  existante ; la pile ne contient jamais deux fois
  la même page.

L'empilement « fenêtres séparées » (P14.3) est
remplacé par ce modèle ; les dialogues réellement
modaux (Résumé, Log, paramètres) restent des
QDialog — ils ne sont pas des pages.
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QStackedWidget,
)

from services.etude_schema import EtudeFormatError
from services.settings import SettingsManager


class AppWindow(QMainWindow):
    """
    Coquille de navigation : un QStackedWidget de
    pages, chacune identifiée par une clé unique
    (type + identifiant résolu).
    """

    def __init__(self, settings: SettingsManager = None):
        super().__init__()

        self.settings = (
            settings
            if settings is not None
            else SettingsManager()
        )

        self.setWindowTitle("Transcript Studio")

        self.resize(1200, 800)

        self.pile = QStackedWidget()

        self.setCentralWidget(self.pile)

        #
        # Pages ouvertes : clé -> page. Une clé déjà
        # présente réactive sa page (jamais de
        # doublon, spec §11.3).
        #
        self.pages = {}

        from ui.home_window import HomeWindow

        self.accueil = HomeWindow(
            settings=self.settings
        )

        self.ouvrir_page(
            ("accueil",),
            lambda: self.accueil
        )

    def closeEvent(self, event):
        """
        Fermeture de l'app : la page active sauvegarde
        son état (préférences, étude) via le même
        hook que la navigation sortante.
        """

        page = self.pile.currentWidget()

        sortie = getattr(
            page,
            "sur_navigation_sortante",
            None
        )

        if sortie is not None:
            sortie()

        super().closeEvent(event)

    #
    # ==================================================
    # Mécanique de la pile.
    # ==================================================
    #

    def ouvrir_page(self, cle, fabrique):
        """
        Ouvre (ou réactive) la page identifiée par
        cle. fabrique crée la page à la première
        ouverture ; elle peut retourner None pour
        annuler l'ouverture (erreur : rien ne
        s'empile).
        """

        page = self.pages.get(cle)

        if page is None:

            page = fabrique()

            if page is None:
                return None

            page.navigation = self

            self.pages[cle] = page

            self.pile.addWidget(page)

        courante = self.pile.currentWidget()

        if courante is not page:

            sortie = getattr(
                courante,
                "sur_navigation_sortante",
                None
            )

            if sortie is not None:
                sortie()

        self.pile.setCurrentWidget(page)

        #
        # P16-bis 3ᵉ série (spec correctifs §15.2) :
        # la page activée réinitialise son état
        # (lecteur audio jouable au retour, etc.).
        #
        entree = getattr(
            page,
            "sur_navigation_entrante",
            None
        )

        if entree is not None:
            entree()

        return page

    def page_active(self):
        """
        Page courante de la pile (None si vide).
        """

        return self.pile.currentWidget()

    def cles_ouvertes(self) -> list:
        """
        Clés des pages ouvertes (tests d'invariance :
        jamais deux fois la même page).
        """

        return list(self.pages.keys())

    def page_est_ouverte(self, cle) -> bool:

        return cle in self.pages

    #
    # ==================================================
    # Destinations de navigation.
    # ==================================================
    #

    def ouvrir_accueil(self):
        """
        « Accueil » : toujours la page d'accueil de
        l'app (spec §11.1).
        """

        return self.ouvrir_page(
            ("accueil",),
            lambda: self.accueil
        )

    def ouvrir_etudes(self):
        """
        Vue Études (P18.6-bis, spec correctifs §4) :
        la tuile « Études » du hub ouvre cette vue
        dédiée — le hub n'affiche jamais la liste
        des études. Clé unique : une seule vue.
        """

        cle = ("etudes",)

        def fabrique():

            from ui.etudes_window import (
                EtudesWindow
            )

            return EtudesWindow(
                settings=self.settings
            )

        return self.ouvrir_page(cle, fabrique)

    def ouvrir_etude(self, dossier):
        """
        Page Étude d'un dossier d'étude (clé : chemin
        résolu — une étude ouverte deux fois réactive
        sa page).
        """

        cle = (
            "etude",
            str(Path(dossier).resolve()),
        )

        def fabrique():

            from ui.etude_window import EtudeWindow

            try:
                return EtudeWindow(
                    dossier,
                    settings=self.settings
                )
            except EtudeFormatError as e:

                QMessageBox.warning(
                    self,
                    "Étude illisible",
                    (
                        "Ce dossier n'a pas pu être ouvert "
                        "comme étude :\n\n"
                        + str(e)
                    )
                )

                return None

        return self.ouvrir_page(cle, fabrique)

    def ouvrir_reunion(
        self,
        projet,
        etude=None,
        nom=None,
        etape=None
    ):
        """
        Page Réunion (P18.6b, spec navigation §3) :
        la réunion, objet de premier rang, a sa
        propre page — ruban + stepper ①→⑥, étapes
        ④⑤ optionnelles. Clé : fichier du projet v1
        résolu (une réunion déjà ouverte est
        réactivée — jamais de doublon).
        """

        chemin = getattr(
            projet,
            "project_file",
            None
        )

        if not chemin:
            return None

        cle = (
            "reunion",
            str(Path(chemin).resolve()),
        )

        def fabrique():

            from ui.reunion_window import (
                ReunionWindow
            )

            return ReunionWindow(
                projet,
                settings=self.settings,
                etude=etude,
                nom=nom
            )

        page = self.ouvrir_page(cle, fabrique)

        if page is not None and etape is not None:
            page.changer_etape(etape)

        return page

    def ouvrir_correction(self, projet):
        """
        Page Réunion « Correction de transcription »
        (éditeur v1) — clé : fichier du projet v1
        résolu.
        """

        from ui.main_window import MainWindow

        chemin = getattr(
            projet,
            "project_file",
            None
        )

        if not chemin:
            return None

        cle = (
            "correction",
            str(Path(chemin).resolve()),
        )

        return self.ouvrir_page(
            cle,
            lambda: MainWindow(
                projet,
                settings=self.settings
            )
        )

    def ouvrir_ouvrage(self, etude_ouverte):
        """
        Page Ouvrage d'une étude (P18.6, spec
        navigation §5) : l'assemblage et l'export
        final s'y font — la page Étude y renvoie.
        """

        cle = (
            "ouvrage",
            str(
                Path(etude_ouverte.dossier).resolve()
            ),
        )

        def fabrique():

            from ui.ouvrage_window import (
                OuvrageWindow
            )

            return OuvrageWindow(
                etude_ouverte,
                settings=self.settings
            )

        return self.ouvrir_page(cle, fabrique)

    def ouvrir_reformulation(self, etude_ouverte, nom):
        """
        Page Réunion « Reformulation littéraire » —
        clé : dossier d'étude résolu + réunion.
        """

        from ui.reformulation_window import (
            ReformulationWindow
        )

        cle = (
            "reformulation",
            str(
                Path(etude_ouverte.dossier).resolve()
            ),
            nom,
        )

        return self.ouvrir_page(
            cle,
            lambda: ReformulationWindow(
                etude_ouverte,
                nom,
                settings=self.settings
            )
        )
