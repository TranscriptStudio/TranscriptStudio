# ui/etude_window.py
"""
Page Étude (P14.3) : vue d'ensemble d'une étude.

Réunions dans l'ordre de lecture, statuts, ordre
modifiable, ajout de réunions (projets v1 existants,
jamais modifiés), retrait, relocalisation guidée et
ouverture d'une réunion dans l'éditeur existant.

Un projet v1 introuvable n'empêche pas l'ouverture :
l'étude s'affiche en mode dégradé (réunions
joignables uniquement).
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QFrame,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import (
    Qt,
    QObject,
    QThread,
    QUrl,
    Signal,
    Slot,
)

from services.etude_io import (
    EtudeError,
    EtudeOuverte,
    ajouter_reunion,
    deplacer_reunion,
    fichier_projet_v1,
    ouvrir_etude,
    relocaliser_reunion,
    retirer_reunion,
    sauvegarder_etude,
)
from services.etude_schema import EtudeFormatError
from services.project_io import load_project
from services.help import open_user_manual
from services.settings import SettingsManager


class SyntheseWorker(QObject):
    """
    Génère la synthèse d'étude en arrière-plan
    (P17.2) : la page reste réactive.
    """

    terminee = Signal(object)
    erreur = Signal(str)

    def __init__(self, service, declencheur: str):
        super().__init__()

        self.service = service
        self.declencheur = declencheur

    @Slot()
    def run(self):

        try:

            resultat = self.service.generer(
                declencheur=self.declencheur
            )

            self.terminee.emit(resultat)

        except Exception as e:
            self.erreur.emit(str(e))


def assurer_decoupage(
    parent,
    etude_ouverte: EtudeOuverte,
    nom: str
) -> bool:
    """
    La reformulation (et le résumé depuis la brute)
    exigent une segmentation de la réunion en blocs
    de parole (P14.4). La génération n'était exposée
    nulle part dans l'UI : elle est proposée ici,
    depuis la diarisation validée du projet v1.

    Partagée par la page Étude et le bouton
    « Reformulation… » de l'éditeur v1 (P16-bis,
    spec correctifs §4).

    Retour : True si la segmentation existe (ou
    vient d'être générée).
    """

    if etude_ouverte.decoupages.get(nom):
        return True

    reponse = QMessageBox.question(
        parent,
        "Segmentation de la réunion",
        (
            "Aucune segmentation n'existe encore pour "
            f"la réunion « {nom} » : la reformulation "
            "travaille par blocs de parole.\n\n"
            "La générer maintenant à partir de la "
            "diarisation validée de la réunion ?\n\n"
            "(La réunion n'est pas modifiée.)"
        )
    )

    if reponse != QMessageBox.StandardButton.Yes:
        return False

    from services.decoupage import (
        DecoupageError,
        generer_decoupage,
    )
    from services.etude_io import (
        enregistrer_decoupage,
    )

    chemin = fichier_projet_v1(etude_ouverte, nom)

    try:

        projet = load_project(str(chemin))

        decoupage = generer_decoupage(
            etude_ouverte,
            nom,
            projet
        )

        if not decoupage.blocs:

            QMessageBox.warning(
                parent,
                "Diarisation absente",
                (
                    "La réunion ne "
                    "comporte aucun bloc de parole : "
                    "validez d'abord la diarisation "
                    "dans l'éditeur de correction de "
                    "transcription, puis relancez."
                )
            )

            return False

        enregistrer_decoupage(etude_ouverte, decoupage)
        sauvegarder_etude(etude_ouverte)

    except (DecoupageError, EtudeError) as e:

        QMessageBox.warning(
            parent,
            "Segmentation impossible",
            str(e)
        )

        return False

    return True


#
# Rôle de données portant les étapes affichées d'une
# tuile (pour le menu contextuel clic droit).
#
ROLE_ETATS = Qt.ItemDataRole.UserRole + 1


class ListeReunionsEtude(QListWidget):
    """
    P18.9a : conteneur des tuiles de réunion de la
    page Étude — réordonnancement par GLISSER-DÉPOSER
    (clic gauche sur le corps d'une tuile = déplacement
    uniquement, aucune navigation) ; le conteneur
    DÉFILE INDÉPENDAMMENT (P18.9f : une étude peut
    compter plusieurs dizaines de réunions).

    Le signal ``ordre_modifie`` est émis avec la liste
    des noms de réunions dans le nouvel ordre après
    chaque dépôt (la page persiste alors l'ordre dans
    etude.json).
    """

    ordre_modifie = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
        )

        self.setDefaultDropAction(
            Qt.DropAction.MoveAction
        )

        self.setMovement(
            QListWidget.Movement.Snap
        )

        self.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )

        #
        # P18.9b : marge intérieure du viewport pour
        # que l'effet de rehaussement au survol (~2 px
        # vers le haut) ne soit PAS rogné sur la
        # première tuile en haut du conteneur.
        #
        from ui.tuiles import ELEVATION_SURVOL

        self.setViewportMargins(
            6,
            ELEVATION_SURVOL + 4,
            6,
            ELEVATION_SURVOL + 4,
        )

        self.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )

    def dropEvent(self, event):
        """
        Après un dépôt (glisser-déposer interne) :
        émet le nouvel ordre des réunions.
        """

        super().dropEvent(event)

        noms = [
            self.item(index).data(
                Qt.ItemDataRole.UserRole
            )
            for index in range(self.count())
        ]

        self.ordre_modifie.emit(noms)


class EtudeWindow(QWidget):

    def __init__(self, dossier_etude, settings=None):
        super().__init__()

        # SettingsManager injectable : les tests et
        # fumées isolent la configuration réelle de
        # l'utilisateur (jamais d'écriture dedans).
        self.settings = (
            settings
            if settings is not None
            else SettingsManager()
        )

        self.etude = None

        try:
            self.etude = ouvrir_etude(dossier_etude)
        except EtudeFormatError as e:
            QMessageBox.critical(
                None,
                "Étude illisible",
                f"L'étude n'a pas pu être ouverte :\n\n{e}"
            )
            raise

        self.editor = None

        self.setWindowTitle(
            f"Étude — {self.etude.etude.titre}"
        )

        self.resize(700, 500)

        self.build_ui()

        self.settings.add_recent_etude(
            self.etude.dossier
        )

        self.synthese_thread = None
        self.synthese_worker = None

        self.refresh_reunions()
        self.maj_synthese()

        #
        # P18.7d : toute divergence etudes[] du tier d'une
        # réunion vs ordre_reunions de l'étude est SIGNALÉE
        # à l'ouverture — jamais auto-corrigée.
        #
        if self.etude.divergences:
            QMessageBox.warning(
                self,
                "Divergences de rattachement signalées",
                (
                    "Le tier d'une ou plusieurs réunions "
                    "référence des études qui ne correspondent "
                    "pas à l'ordre des réunions de cette étude "
                    ":\n\n"
                    + "\n".join(self.etude.divergences)
                    + "\n\nAucune correction automatique n'a "
                    "été faite."
                )
            )

    def build_ui(self):
        """
        Page Étude (P18.6c, spec navigation §4 ;
        correctifs P18.9) : ruban (titre, thème,
        nombre de réunions, badge Bible simplifié,
        boutons Paramètres de l'étude / Accueil /
        ⚙ / ?), liste des réunions en une colonne
        de tuiles GLISSER-DÉPOSER (titre, rang,
        date, durée, avancement ①→⑤ SANS ⑥,
        stepper cliquable, coût — PAS de bouton
        « Ouvrir » ni de flèches ; menu contextuel
        clic droit : étapes, retirer, relocaliser),
        « ＋ Ajouter une réunion… » puis « Édition
        ouvrage final » en tête de liste, synthèse
        d'étude (boutons à côté), récurrences.
        """

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(8)

        #
        # Ruban.
        #
        self.ruban = QWidget()
        self.ruban.setObjectName("ruban_etude")

        ruban_layout = QHBoxLayout(self.ruban)
        ruban_layout.setContentsMargins(0, 0, 0, 0)
        ruban_layout.setSpacing(10)

        colonne_titre = QVBoxLayout()
        colonne_titre.setSpacing(2)

        self.titre_label = QLabel(
            self.etude.etude.titre
        )
        self.titre_label.setStyleSheet(
            "font-size: 18px; font-weight: 600;"
        )

        nb_reunions = len(
            self.etude.etude.ordre_reunions
        )

        sous_titre = self._libelle_nb_reunions(
            nb_reunions
        )

        theme_libelle = self._libelle_theme()

        if theme_libelle:
            sous_titre = (
                f"{theme_libelle} · {sous_titre}"
            )

        self.sous_titre_label = QLabel(
            sous_titre
        )
        self.sous_titre_label.setStyleSheet(
            "font-size: 12px; color: #757575;"
        )

        colonne_titre.addWidget(self.titre_label)
        colonne_titre.addWidget(
            self.sous_titre_label
        )

        ruban_layout.addLayout(colonne_titre)

        self.badge_bible_label = QLabel(
            self._texte_badge_bible()
        )
        self.badge_bible_label.setStyleSheet(
            "font-size: 12px; color: #1565C0;"
        )
        #
        # P18.8d : info-bulle = version commune, ou
        # liste par réunion si « Bibles mixtes ».
        #
        self.badge_bible_label.setToolTip(
            self._tooltip_badge_bible()
        )

        ruban_layout.addWidget(
            self.badge_bible_label
        )

        ruban_layout.addStretch()

        #
        # P18.8b : « Paramètres de l'étude » (anciennement
        # « Modifier l'étude ») — ouvre les paramètres de
        # l'étude (bloc Général : titre + thème inclus).
        #
        self.modifier_button = QPushButton(
            "Paramètres de l'étude"
        )
        self.modifier_button.setToolTip(
            "Paramètres de l'étude : titre, thème, "
            "prompts, modèles, Bible retenue..."
        )
        self.modifier_button.clicked.connect(
            self.modifier_etude
        )

        self.accueil_button = QPushButton(
            "Accueil"
        )
        self.accueil_button.clicked.connect(
            self.retour_accueil
        )

        self.parametres_button = QPushButton(
            "⚙ Paramètres"
        )
        self.parametres_button.clicked.connect(
            self.ouvrir_parametres
        )

        self.aide_button = QPushButton("? Aide")
        self.aide_button.clicked.connect(
            open_user_manual
        )

        for bouton in (
            self.modifier_button,
            self.accueil_button,
            self.parametres_button,
            self.aide_button,
        ):
            ruban_layout.addWidget(bouton)

        layout.addWidget(self.ruban)

        self.avertissement_label = QLabel("")
        self.avertissement_label.setStyleSheet(
            "font-size: 12px; color: #b35900;"
        )
        self.avertissement_label.setWordWrap(True)
        layout.addWidget(self.avertissement_label)

        #
        # Réunions : liste en une colonne de
        # mini-tuiles (même langage que le hub).
        # « ＋ Ajouter une réunion » en tête de
        # liste, à côté du titre de section
        # (spec correctifs §16).
        #
        entete_reunions = QHBoxLayout()

        titre_section = QLabel(
            "Réunions de l'étude"
        )
        titre_section.setStyleSheet(
            "font-size: 14px; font-weight: 600;"
        )

        entete_reunions.addWidget(titre_section)

        self.ajouter_button = QPushButton(
            "＋ Ajouter une réunion…"
        )
        self.ajouter_button.setToolTip(
            "Nouvel audio, ou reprise d'une réunion "
            "autonome (rattachement)"
        )
        self.ajouter_button.clicked.connect(
            self.ajouter_reunion_ui
        )

        #
        # P18.9d : accès à l'ouvrage EN HAUT DE PAGE,
        # à droite de « ＋ Ajouter une réunion… »,
        # libellé « Édition ouvrage final » (les
        # boutons liés à la synthèse seront placés
        # à côté, P20.6).
        #
        self.ouvrage_button = QPushButton(
            "Édition ouvrage final"
        )
        self.ouvrage_button.setToolTip(
            "Ouvrir la page Ouvrage : édition de "
            "l'ouvrage final (structure, paragraphs, "
            "aides à la relecture, export)"
        )
        self.ouvrage_button.clicked.connect(
            self.ouvrir_ouvrage
        )

        entete_reunions.addStretch()
        entete_reunions.addWidget(self.ajouter_button)
        entete_reunions.addWidget(self.ouvrage_button)

        #
        # P18.9d + P20.6 : les boutons liés à la
        # synthèse sont placés à côté du bouton
        # « Édition ouvrage final » (invariant 5).
        #
        self.synthese_regenerer_button = QPushButton(
            "(Re)générer la synthèse…"
        )
        self.synthese_regenerer_button.setToolTip(
            "P20.6 : régénérer INTÉGRALEMENT la "
            "synthèse d'étude à partir de toutes les "
            "réunions à blocs validés (avertissement "
            "de remplacement intégral, confirmation "
            "requise) — ou l'alimenter réunion par "
            "réunion (clic droit sur une tuile)"
        )
        self.synthese_regenerer_button.clicked.connect(
            self.regenerer_synthese
        )

        self.synthese_editer_button = QPushButton(
            "Éditer"
        )
        self.synthese_editer_button.setToolTip(
            "Éditer la synthèse à la main (saisie "
            "manuelle, sans LLM — même statut une "
            "fois sauvegardée)"
        )
        self.synthese_editer_button.clicked.connect(
            self.editer_synthese
        )

        self.synthese_sauver_button = QPushButton(
            "Sauvegarder l'édition"
        )
        self.synthese_sauver_button.setToolTip(
            "Enregistrer le texte édité comme "
            "nouvelle version de la synthèse "
            "(déclencheur « manuel »)"
        )
        self.synthese_sauver_button.clicked.connect(
            self.sauvegarder_edition_synthese
        )
        self.synthese_sauver_button.setVisible(False)

        #
        # P20.6e : « Annuler l'édition », à côté de
        # la sauvegarde, EN MODE ÉDITION UNIQUEMENT
        # — restaure le texte antérieur à l'édition.
        #
        self.synthese_annuler_button = QPushButton(
            "Annuler l'édition"
        )
        self.synthese_annuler_button.setToolTip(
            "Annuler l'édition en cours et "
            "restaurer le texte antérieur"
        )
        self.synthese_annuler_button.clicked.connect(
            self.annuler_edition_synthese
        )
        self.synthese_annuler_button.setVisible(False)

        for bouton in (
            self.synthese_regenerer_button,
            self.synthese_editer_button,
            self.synthese_sauver_button,
            self.synthese_annuler_button,
        ):
            entete_reunions.addWidget(bouton)

        self.entete_reunions = entete_reunions

        layout.addLayout(entete_reunions)

        #
        # P18.9a/f : conteneur des tuiles —
        # glisser-déposer (réordonnancement) et
        # défilement indépendant.
        #
        self.reunions_liste = ListeReunionsEtude()
        self.reunions_liste.setToolTip(
            "Glissez-déposez une tuile pour "
            "réordonner l'étude (l'ordre vaut ordre "
            "d'ouvrage) ; clic droit sur une tuile : "
            "menu (étapes, retirer, relocaliser) ; "
            "clic sur une pastille du stepper : ouvrir "
            "la page Réunion à cette étape"
        )
        self.reunions_liste.ordre_modifie.connect(
            self._persister_ordre
        )
        self.reunions_liste.customContextMenuRequested.connect(
            self._sur_menu_contextuel_liste
        )

        layout.addWidget(
            self.reunions_liste,
            stretch=1
        )

        #
        # Synthèse d'étude (P17.2) : contexte de
        # niveau 2 des réunions suivantes.
        #
        layout.addWidget(QLabel("Synthèse d'étude"))

        self.synthese_edit = QPlainTextEdit()
        self.synthese_edit.setReadOnly(True)
        self.synthese_edit.setPlaceholderText(
            "Aucune synthèse : elle est générée quand "
            "une réunion devient entièrement validée, "
            "ou via « Régénérer… »."
        )
        self.synthese_edit.setMaximumHeight(140)
        layout.addWidget(self.synthese_edit)

        #
        # P20.3 (amendement du 09/11) : l'outillage
        # « récurrences » vit EXCLUSIVEMENT dans la
        # page Ouvrage — plus rien sur la page Étude
        # (P17.3/P18.6c abrogés sur ce seul point).
        # Les boutons de la synthèse sont en haut de
        # page, à côté de « Édition ouvrage final ».
        #
        ligne_statut = QHBoxLayout()

        self.synthese_statut_label = QLabel("")
        self.synthese_statut_label.setStyleSheet(
            "font-size: 12px; color: #666666;"
        )

        ligne_statut.addWidget(
            self.synthese_statut_label
        )

        ligne_statut.addStretch()

        layout.addLayout(ligne_statut)

        #
        # P18.9e : fond de page des maquettes, bandeau
        # et labels à la teinte EXACTE du fond de page
        # (correctif transverse, helper partagé).
        #
        self._appliquer_fond_page()

    def _appliquer_fond_page(self):
        """
        P18.9e : fond de page des maquettes dans les
        DEUX thèmes, bandeau (ruban) et labels à la
        teinte EXACTE du fond de page — helper partagé
        ``feuille_fond_page`` (correctif transverse aux
        pages concernées). La liste des réunions reste
        transparente (spec 30f §27 : qdarktheme peindrait
        sinon son viewport d'une autre teinte).
        """

        from services.theme_manager import (
            est_sombre,
            feuille_fond_page,
        )

        self.setAttribute(
            Qt.WidgetAttribute
            .WA_StyledBackground,
            True
        )

        self.setStyleSheet(
            feuille_fond_page(
                "EtudeWindow",
                est_sombre(self)
            )
            + "QListWidget {"
            "background: transparent;"
            "border: none;"
            "}"
            "QListWidget::item {"
            "background: transparent;"
            "border: none;"
            "}"
        )

    def _libelle_theme(self) -> str:

        theme = self.etude.etude.theme

        if theme in ("livre", "libre"):
            return {
                "livre": "Livre biblique",
                "libre": "Thème libre",
            }.get(theme, "")

        return theme

    @staticmethod
    def _libelle_nb_reunions(nombre: int) -> str:
        """
        Pluriel propre (spec correctifs §15) :
        « 1 réunion », « 2 réunions ».
        """

        if nombre > 1:
            return f"{nombre} réunions"

        return f"{nombre} réunion"

    def _version_ouvrage(self):
        """
        P20.5b : référence d'uniformité de l'ouvrage
        persistée dans ouvrage.json (chaîne vide si
        non choisie) — le badge de la page Étude
        l'affiche dès qu'elle est choisie.
        """

        try:

            from services.ouvrage_document import (
                charger_ouvrage,
            )

            if not self.etude.dossier:
                return ""

            document = charger_ouvrage(
                self.etude.dossier
            )

            if document is None:
                return ""

            return getattr(
                document,
                "reference_bible",
                ""
            ) or ""

        except Exception:
            return ""

    def _texte_badge_bible(self) -> str:
        """
        P18.9c : badge simplifié — « Bible : Darby
        révisée », JAMAIS de champ « versification »
        distinct (la versification découle de la
        version retenue) ; « Bibles mixtes » si les
        tiers divergent. P20.5b : la version ouvrage
        prime dès qu'elle est choisie. Logique dans
        services.bibles.badge_bible_etude.
        """

        from services.bibles import (
            badge_bible_etude,
        )

        try:
            texte, _tooltip = badge_bible_etude(
                self.etude,
                version_ouvrage=self._version_ouvrage()
                or None
            )
            return texte
        except Exception:
            return "Bible : —"

    def _tooltip_badge_bible(self) -> str:
        """
        P18.9c : info-bulle ÉPURÉE du badge Bible —
        libellé simple, aucun commentaire de spec
        (aucune mention P18.5 ou autre référence
        interne).
        """

        from services.bibles import (
            badge_bible_etude,
        )

        try:
            _texte, tooltip = badge_bible_etude(
                self.etude,
                version_ouvrage=self._version_ouvrage()
                or None
            )
            return tooltip
        except Exception:
            return ""

    def ouvrir_parametres(self):
        """
        ⚙ Paramètres (dialogue modal existant).
        """

        from ui.settings_dialog import SettingsDialog

        dialogue = SettingsDialog(
            self,
            settings=self.settings
        )

        if dialogue.exec():
            self.settings.load()

    def modifier_etude(self):
        """
        P18.8b : « Paramètres de l'étude » — ouvre le
        dialogue des paramètres de l'étude (le bloc
        Général reprend titre + thème de l'ancienne
        mini-fenêtre « Modifier l'étude »).
        """

        from ui.parametres_etude_dialog import (
            ParametresEtudeDialog,
        )

        dialogue = ParametresEtudeDialog(
            self.etude,
            parent=self
        )

        if not dialogue.exec():
            return

        sauvegarder_etude(self.etude)

        self.titre_label.setText(
            self.etude.etude.titre
        )
        self.sous_titre_label.setText(
            self._libelle_theme()
            + " · "
            + self._libelle_nb_reunions(
                len(
                    self.etude.etude.ordre_reunions
                )
            )
        )

    def editer_synthese(self):
        """
        « Éditer » : la synthèse devient éditable à
        la main (saisie manuelle, sans LLM — le
        bouton Sauvegarder crée une version
        « manuel »).
        """

        self._texte_avant_edition = (
            self.synthese_edit.toPlainText()
        )

        self.synthese_edit.setReadOnly(False)
        self.synthese_sauver_button.setVisible(True)
        self.synthese_annuler_button.setVisible(True)
        self.synthese_editer_button.setVisible(False)

    def annuler_edition_synthese(self):
        """
        P20.6e : « Annuler l'édition » (visible en
        mode édition uniquement) — restaure le
        texte antérieur à l'édition et quitte le
        mode édition, sans rien consigner.
        """

        if self.synthese_edit.isReadOnly():
            return

        self.synthese_edit.setPlainText(
            getattr(
                self,
                "_texte_avant_edition",
                ""
            )
        )

        self.synthese_edit.setReadOnly(True)
        self.synthese_sauver_button.setVisible(False)
        self.synthese_annuler_button.setVisible(False)
        self.synthese_editer_button.setVisible(True)

    def sauvegarder_edition_synthese(self):
        """
        Sauvegarde de l'édition manuelle : nouvelle
        version de la synthèse (déclencheur
        « manuel »), puis retour en lecture seule.
        """

        from services.etude_io import (
            ajouter_version_synthese,
        )

        texte = (
            self.synthese_edit.toPlainText().strip()
        )

        if not texte:
            QMessageBox.information(
                self,
                "Synthèse vide",
                "La synthèse ne peut pas être vide."
            )
            return

        ajouter_version_synthese(
            self.etude,
            texte,
            declencheur="manuel"
        )

        sauvegarder_etude(self.etude)

        self.synthese_edit.setReadOnly(True)
        self.synthese_sauver_button.setVisible(False)
        self.synthese_editer_button.setVisible(True)

        self.maj_synthese()

    def ouvrir_ouvrage(self):
        """
        Renvoi vers la page Ouvrage (spec §4.5).
        """

        navigation = getattr(
            self,
            "navigation",
            None
        )

        if navigation is not None:
            navigation.ouvrir_ouvrage(self.etude)
            return

        from ui.ouvrage_window import OuvrageWindow

        self.fenetre_ouvrage = OuvrageWindow(
            self.etude,
            settings=self.settings
        )

        self.fenetre_ouvrage.show()

    def sur_changement_theme(self):
        """
        Broadcast de ThemeManager : reconstruit la
        liste des réunions (les mini-tuiles portent
        leurs couleurs à la construction) et
        réapplique le fond de page (P18.9e).
        """

        self._appliquer_fond_page()

        if getattr(self, "reunions_liste", None) is not None:
            self.refresh_reunions()

    def refresh_reunions(self):
        """
        Reconstitue la liste des réunions en une
        colonne de mini-tuiles (ordre de lecture) :
        titre, rang, date, durée, avancement ①→⑤
        SANS ⑥ (invariant §9.4), coût, ouverture,
        poignée de réordonnancement.
        """

        self.reunions_liste.clear()

        from services.avancement import (
            cout_reunion,
            etapes_reunion_page_etude,
        )

        projets = {}

        for nom in self.etude.etude.ordre_reunions:

            reunion = self.etude.reunions[nom]

            introuvable = (
                nom in self.etude.reunions_introuvables
            )

            projet = None

            if not introuvable:

                try:
                    projet = load_project(
                        str(
                            fichier_projet_v1(
                                self.etude,
                                nom
                            )
                        )
                    )

                except Exception:
                    projet = None

            projets[nom] = projet

            etats = etapes_reunion_page_etude(
                self.etude,
                nom,
                projet
            )

            tuile = self._construire_mini_tuile(
                nom,
                reunion,
                projet,
                etats,
                cout_reunion(self.etude, nom),
                introuvable
            )

            item = QListWidgetItem(
                reunion.titre_1 or nom
            )
            item.setData(
                Qt.ItemDataRole.UserRole,
                nom
            )

            #
            # P18.9a : les étapes affichées de la tuile
            # (pour le menu contextuel clic droit).
            #
            item.setData(
                ROLE_ETATS,
                list(etats.keys()) if etats else [],
            )

            self.reunions_liste.addItem(item)

            self.reunions_liste.setItemWidget(
                item,
                tuile
            )

            item.setSizeHint(
                tuile.sizeHint()
            )

        introuvables = (
            self.etude.reunions_introuvables
        )

        if introuvables:
            self.avertissement_label.setText(
                "Mode dégradé : "
                + self._libelle_nb_reunions(
                    len(introuvables)
                )
                + " "
                "ont une réunion introuvable. "
                "Les autres réunions restent "
                "utilisables ; utilisez "
                "« Relocaliser... » après avoir "
                "sélectionné une réunion manquante."
            )
        else:
            self.avertissement_label.setText("")

    def _construire_mini_tuile(
        self,
        nom,
        reunion,
        projet,
        etats,
        cout,
        introuvable
    ):
        """
        Mini-tuile d'une réunion de l'étude (même
        langage que le hub) : titre lisible de la
        réunion (pas de numérotation ni de nom de
        fichier brut), rang en information annexe,
        DATE DE RÉUNION (audio, jamais la date
        technique de rattachement), durée ;
        avancement ; coût.

        P18.9a : PLUS de bouton « Ouvrir » ni de
        flèches de réordonnancement sur la tuile —
        le clic gauche sur le corps sert UNIQUEMENT
        au glisser-déposer (aucune navigation) ; la
        navigation se fait par le clic sur une
        pastille du stepper (ouvre la page Réunion à
        l'étape visée) ou par le menu contextuel du
        clic droit (étapes, « Retirer la réunion »,
        « Relocaliser »). L'ordre vaut ordre
        d'ouvrage et persiste (etude.json).
        """

        from ui.stepper import StepperBar

        cadre = QFrame()
        cadre.setObjectName("etude_mini_tuile")

        #
        # §22 : CONTOUR VISIBLE (1 px, la tuile se
        # détache du fond de page) + survol (contour
        # au bleu d'accent) ; réunion introuvable =
        # contour avertisseur.
        #
        from services.theme_manager import (
            BORD_BLEU_ACCENT,
            couleurs_tuiles,
            est_sombre,
        )

        couleurs = couleurs_tuiles(
            est_sombre(self)
        )

        bord = (
            "#b35900" if introuvable
            else couleurs["bord"]
        )

        #
        # Survol animé (spec 30f §22-§23, invariant
        # 10) : contour glissant du gris (ou de
        # l'orange d'avertissement) vers l'accent
        # #3b9eff, élévation ~2 px, ombre portée,
        # transition ~120 ms — partagé avec les
        # cartes du hub via ui/tuiles.py.
        #
        from ui.tuiles import (
            activer_survol_anime,
            style_rangee,
        )

        bord_base = bord

        def appliquer_style(progression):
            cadre.setStyleSheet(
                style_rangee(
                    cadre,
                    "etude_mini_tuile",
                    bord_base,
                    couleurs["fond"],
                    couleurs["fond_survol"],
                    progression,
                )
            )

        appliquer_style(0.0)

        # Référence conservée pour les tests
        # (pixels rendus au terme du survol).
        cadre._appliquer_style = appliquer_style

        activer_survol_anime(
            cadre,
            appliquer_style
        )

        layout = QVBoxLayout(cadre)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(3)

        ligne_titre = QHBoxLayout()

        titre = QLabel(
            reunion.titre_1
            or (
                getattr(projet, "name", None)
                if projet is not None
                else None
            )
            or nom
        )
        titre.setStyleSheet("font-weight: 600;")

        ligne_titre.addWidget(titre)

        rang = QLabel(f"Réunion {reunion.numero}")
        rang.setStyleSheet(
            "color: #8A8A8A; font-size: 11px;"
        )

        ligne_titre.addWidget(rang)
        ligne_titre.addStretch()

        from services.avancement import (
            date_reunion,
        )

        date_affichee = date_reunion(
            projet,
            reunion
        )

        infos = QLabel(date_affichee)

        if projet is not None:

            from ui.reunion_window import (
                formater_duree
            )

            duree = getattr(
                projet,
                "duration_seconds",
                None
            )

            if duree:

                texte = (
                    f"{date_affichee} · "
                    f"{formater_duree(duree)}"
                    if date_affichee
                    else formater_duree(duree)
                )

                infos.setText(texte)

        infos.setStyleSheet(
            "color: #8A8A8A; font-size: 11px;"
        )

        ligne_titre.addWidget(infos)

        if introuvable:
            badge = QLabel("introuvable")
            badge.setStyleSheet(
                "color: #b35900; font-size: 11px;"
            )
            ligne_titre.addWidget(badge)

        layout.addLayout(ligne_titre)

        ligne_stepper = QHBoxLayout()

        if etats is None:

            # Réunion non transcrite : AUCUN
            # stepper, mention discrète
            # (P18.6-bis §19, invariant 9).
            mention = QLabel(
                "transcription en attente"
            )
            mention.setStyleSheet(
                "color: #8A8A8A;"
                "font-style: italic;"
                "font-size: 11px;"
            )

            ligne_stepper.addWidget(mention)

        else:

            #
            # P18.9a : stepper CLIQUABLE — le clic
            # gauche sur une pastille ouvre la page
            # Réunion directement à l'étape visée.
            #
            stepper = StepperBar(
                etapes=etats.keys(),
                cliquable=True,
                compact=True
            )

            stepper.definir_etats(etats)

            stepper.etape_cliquee.connect(
                lambda etape, n=nom: (
                    self._ouvrir_etape(n, etape)
                )
            )

            ligne_stepper.addWidget(stepper)

        ligne_stepper.addStretch()

        cout_label = QLabel(
            f"Coût : {cout:.4f} $"
            if cout
            else "Coût : —"
        )
        cout_label.setStyleSheet(
            "color: #8A8A8A; font-size: 11px;"
        )

        ligne_stepper.addWidget(cout_label)

        layout.addLayout(ligne_stepper)

        #
        # P18.9a : le clic gauche sur le corps de la
        # tuile NE DÉCLENCHE AUCUNE navigation ni
        # ouverture — il sert uniquement au
        # glisser-déposer (l'événement est ignoré pour
        # laisser la liste amorcer le drag interne).
        # La navigation passe par le stepper (pastilles
        # cliquables) et le menu contextuel (clic
        # droit, géré par la liste).
        #
        cadre.setCursor(
            Qt.CursorShape.ArrowCursor
        )

        cadre.nom_reunion = nom

        def _presse(event, n=nom):

            if event is not None:
                event.ignore()

        cadre.mousePressEvent = _presse

        return cadre

    def reunion_selectionnee(self):
        """
        Nom de la réunion sélectionnée, ou None.
        """

        item = (
            self.reunions_liste.currentItem()
        )

        if item is None:
            return None

        return item.data(
            Qt.ItemDataRole.UserRole
        )

    def _selectionner(self, nom: str):

        if nom not in (
            self.etude.etude.ordre_reunions
        ):
            return

        self.reunions_liste.setCurrentRow(
            self.etude.etude.ordre_reunions.index(
                nom
            )
        )

    def _ouvrir_reunion(self, nom: str):
        """
        Page Réunion de la réunion (objet de
        premier rang), avec l'étude et le nom connus
        — appelé par le stepper (pastille
        « Transcription ») et le menu contextuel.
        """

        self._selectionner(nom)

        self.ouvrir_reunion_editeur(nom)

    def _ouvrir_etape(self, nom: str, etape: str):
        """
        P18.9a : navigation par tuile — ouvre la page
        Réunion directement à l'étape visée (clic sur
        une pastille du stepper ou menu contextuel).
        """

        from services.avancement import (
            ETAPE_REFORMULATION,
            ETAPE_RESUME,
            ETAPE_TRANSCRIPTION,
        )

        if etape == ETAPE_REFORMULATION:
            self._selectionner(nom)
            self.ouvrir_reunion_reformulation()
            return

        if etape == ETAPE_RESUME:
            self._selectionner(nom)
            self.ouvrir_reunion_resume()
            return

        if etape == ETAPE_TRANSCRIPTION:
            self._ouvrir_reunion(nom)
            return

    def _persister_ordre(self, noms: list):
        """
        P18.9a : après un glisser-déposer, persiste le
        nouvel ordre des réunions (l'ordre vaut ordre
        d'ouvrage, etude.json) — seulement si c'est une
        permutation valide.
        """

        ordre = self.etude.etude.ordre_reunions

        if (
            not noms
            or sorted(noms) != sorted(ordre)
        ):
            self.refresh_reunions()
            return

        selection = self.reunion_selectionnee()

        ordre[:] = noms

        sauvegarder_etude(self.etude)

        self.refresh_reunions()

        if selection in ordre:
            self.reunions_liste.setCurrentRow(
                ordre.index(selection)
            )

    def _sur_menu_contextuel_liste(self, position):
        """
        P18.9a : clic droit sur une tuile — ouvre
        UNIQUEMENT le menu contextuel (étapes,
        « Retirer la réunion », « Relocaliser »).
        """

        item = self.reunions_liste.itemAt(position)

        if item is None:
            return

        nom = item.data(Qt.ItemDataRole.UserRole)

        if not nom:
            return

        menu = self._construire_menu_tuile(nom, item)

        self._executer_menu(
            menu,
            self.reunions_liste.viewport()
            .mapToGlobal(position)
        )

    def _executer_menu(self, menu, position_globale):
        """
        Exécute le menu contextuel (séparé pour les
        tests — ``QMenu.exec`` n'est pas monkeypatchable
        sous PySide6).
        """

        menu.exec(position_globale)

    def _construire_menu_tuile(self, nom: str, item=None) -> QMenu:
        """
        P18.9a : menu contextuel d'une tuile de
        réunion : accès aux étapes (idem clic sur une
        pastille du stepper), « Retirer la réunion »,
        « Relocaliser ».

        ``item`` : l'item de liste porteur (les étapes
        affichées y sont rattachées) — sinon
        l'item courant.
        """

        from services.avancement import (
            LIBELLES_ETAPES,
        )

        if item is None:
            item = self.reunions_liste.currentItem()

        menu = QMenu(self)

        etats = (
            item.data(ROLE_ETATS)
            if item is not None
            else []
        ) or []

        for etape in etats:

            action = menu.addAction(
                LIBELLES_ETAPES.get(etape, etape)
            )

            action.triggered.connect(
                lambda checked=False, n=nom, e=etape: (
                    self._ouvrir_etape(n, e)
                )
            )

        if etats:
            menu.addSeparator()

        retirer = menu.addAction(
            "Retirer la réunion"
        )
        retirer.triggered.connect(
            lambda checked=False, n=nom: (
                self._retirer_reunion(n)
            )
        )

        relocaliser = menu.addAction(
            "Relocaliser…"
        )
        relocaliser.triggered.connect(
            lambda checked=False, n=nom: (
                self._relocaliser_reunion(n)
            )
        )

        #
        # P20.6b : alimentation manuelle de la
        # synthèse — proposée UNIQUEMENT pour une
        # réunion à blocs validés (invariant 9).
        #
        from services.traitements.synthese import (
            reunion_entierement_validee,
        )

        if reunion_entierement_validee(
            self.etude,
            nom
        ):
            menu.addSeparator()

            alimenter = menu.addAction(
                "Alimenter la synthèse globale"
            )

            alimenter.triggered.connect(
                lambda checked=False, n=nom: (
                    self.alimenter_synthese(n)
                )
            )

        return menu

    def _deplacer_reunion(self, nom: str, offset: int):
        """
        Réordonnancement par déplacement relatif
        (l'ordre vaut ordre d'ouvrage, spec §4.2) —
        conservé pour les tests et appels internes.
        """

        index = (
            self.etude.etude.ordre_reunions.index(nom)
        )

        try:
            deplacer_reunion(
                self.etude,
                nom,
                index + offset
            )
        except EtudeError:
            return

        sauvegarder_etude(self.etude)
        self.refresh_reunions()

        self.reunions_liste.setCurrentRow(
            self.etude.etude.ordre_reunions.index(nom)
        )

    def ajouter_reunion_ui(self):
        """
        « ＋ Ajouter une réunion » (spec §4.3) :
        nouvel audio, ou reprise d'une réunion
        autonome (rattachement §6).
        """

        menu = QMenu(self)

        depuis_fichier = menu.addAction(
            "Depuis un fichier de réunion…"
        )
        depuis_fichier.triggered.connect(
            self.ajouter_reunion_depuis_fichier
        )

        depuis_autonome = menu.addAction(
            "Depuis une réunion autonome…"
        )
        depuis_autonome.triggered.connect(
            self.ajouter_reunion_depuis_autonome
        )

        menu.addSeparator()

        nouvel_audio = menu.addAction(
            "Nouvel audio…"
        )
        nouvel_audio.triggered.connect(
            self.nouvel_audio
        )

        menu.exec(
            self.ajouter_button.mapToGlobal(
                self.ajouter_button.rect()
                .bottomLeft()
            )
        )

    def ajouter_reunion_depuis_fichier(self):
        """
        Ajoute un projet v1 existant comme réunion
        (référence, jamais copie) — l'exclusivité
        (une réunion ∈ 0 ou 1 étude) est vérifiée
        par le service de rattachement.
        """

        from services.rattachement import (
            RattachementError,
            rattacher,
        )

        dossier, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir une réunion (fichier v1)",
            self.settings.get_projects_root(),
            "Réunion (*.sttproj)"
        )

        if not dossier:
            return

        etudes_connues = (
            self.settings.cleanup_recent_etudes()
        )

        try:
            nom = rattacher(
                self.etude.dossier,
                dossier,
                etudes_connues=etudes_connues
            )
        except RattachementError as e:

            QMessageBox.warning(
                self,
                "Réunion non ajoutée",
                str(e)
            )

            return

        except EtudeError as e:

            QMessageBox.warning(
                self,
                "Réunion non ajoutée",
                str(e)
            )

            return

        self.refresh_reunions()

        self.reunions_liste.setCurrentRow(
            self.etude.etude.ordre_reunions.index(nom)
        )

    def ajouter_reunion_depuis_autonome(self):
        """
        Reprise d'une réunion autonome : les
        réunions récentes n'appartenant à aucune
        étude sont proposées au rattachement.
        """

        from services.rattachement import (
            RattachementError,
            rattacher,
            verifier_exclusivite,
        )

        etudes = (
            self.settings.cleanup_recent_etudes()
        )

        autonomes = []

        for chemin in (
            self.settings.cleanup_recent_projects()
        ):

            conflit = verifier_exclusivite(
                chemin,
                etudes
            )

            if conflit is None:
                autonomes.append(chemin)

        if not autonomes:

            QMessageBox.information(
                self,
                "Aucune réunion autonome",
                (
                    "Aucune réunion récente n'est "
                    "autonome : les réunions récentes "
                    "appartiennent déjà toutes à une "
                    "étude.\n\n"
                    "Utilisez « Depuis un fichier de "
                    "réunion… » pour choisir un "
                    "fichier sur le disque."
                )
            )

            return

        libelles = [
            str(Path(chemin).parent.name)
            for chemin in autonomes
        ]

        choix, ok = QInputDialog.getItem(
            self,
            "Rattacher une réunion autonome",
            "Réunion à rattacher à l'étude :",
            libelles,
            0,
            False
        )

        if not ok:
            return

        chemin = autonomes[libelles.index(choix)]

        try:
            nom = rattacher(
                self.etude.dossier,
                chemin,
                etudes_connues=etudes
            )
        except Exception as e:

            QMessageBox.warning(
                self,
                "Réunion non ajoutée",
                str(e)
            )

            return

        self.refresh_reunions()

        self.reunions_liste.setCurrentRow(
            self.etude.etude.ordre_reunions.index(nom)
        )

    def nouvel_audio(self):
        """
        « Nouvel audio… » : la création d'une
        réunion (enregistrement → transcription)
        part du hub (« Nouvelle transcription ») ;
        une fois créée, la réunion se rattache ici
        (« Depuis une réunion autonome… ») ou
        depuis sa page Réunion (« Gestion de
        l'étude »).
        """

        QMessageBox.information(
            self,
            "Nouvel audio",
            (
                "La création d'une réunion part de "
                "l'accueil : tuile « Nouvelle "
                "transcription ».\n\n"
                "Une fois la réunion créée, rattachez-"
                "la à cette étude : « ＋ Ajouter une "
                "réunion… » → « Depuis une réunion "
                "autonome… », ou bouton « Gestion de "
                "l'étude » de sa page Réunion."
            )
        )

    def retirer_reunion_ui(self):
        """
        Retire la réunion sélectionnée de l'étude
        (délègue à ``_retirer_reunion``).
        """

        nom = self.reunion_selectionnee()

        if nom is None:
            return

        self._retirer_reunion(nom)

    def _retirer_reunion(self, nom: str):
        """
        P18.9a : « Retirer la réunion » (menu
        contextuel de la tuile) : retire la réunion
        de l'étude — sa référence et ses résultats
        d'étude ; jamais le projet v1 ni le
        registre FID.
        """

        self._selectionner(nom)

        resultat = QMessageBox.question(
            self,
            "Retirer la réunion",
            (
                "Retirer cette réunion de l'étude ?\n\n"
                "Sa référence et ses résultats d'étude "
                "seront retirés. La réunion n'est pas "
                "touchée."
            )
        )

        if resultat != QMessageBox.StandardButton.Yes:
            return

        retirer_reunion(self.etude, nom)
        sauvegarder_etude(self.etude)
        self.refresh_reunions()

    def relocaliser_reunion_ui(self):
        """
        Relocalisation guidée de la réunion
        sélectionnée (délègue à
        ``_relocaliser_reunion``).
        """

        nom = self.reunion_selectionnee()

        if nom is None:
            return

        self._relocaliser_reunion(nom)

    def _relocaliser_reunion(self, nom: str):
        """
        P18.9a : « Relocaliser » (menu contextuel de
        la tuile) : relocalisation guidée d'une
        réunion au projet v1 introuvable — garde
        son rôle de résolution du dossier déplacé.
        """

        self._selectionner(nom)

        dossier, _ = QFileDialog.getOpenFileName(
            self,
            (
                "Relocaliser la réunion "
                f"« {nom} »"
            ),
            "",
            "Réunion (*.sttproj)"
        )

        if not dossier:
            return

        try:
            relocaliser_reunion(
                self.etude,
                nom,
                dossier
            )
        except EtudeError as e:
            QMessageBox.warning(
                self,
                "Relocalisation impossible",
                str(e)
            )
            return

        sauvegarder_etude(self.etude)
        self.refresh_reunions()

    def ouvrir_reunion_editeur(self, *args):
        """
        Ouvre la page Réunion de la réunion
        sélectionnée (l'éditeur v1 reste l'étape ③
        de la page Réunion).
        """

        nom = self.reunion_selectionnee()

        if nom is None:
            return

        chemin = fichier_projet_v1(
            self.etude,
            nom
        )

        if chemin is None:
            QMessageBox.warning(
                self,
                "Réunion introuvable",
                (
                    "La réunion est "
                    "introuvable. Utilisez "
                    "« Relocaliser... » pour le "
                    "retouver."
                )
            )
            return

        projet = load_project(str(chemin))

        navigation = getattr(self, "navigation", None)

        if (
            navigation is not None
            and hasattr(
                navigation,
                "ouvrir_reunion"
            )
        ):
            navigation.ouvrir_reunion(
                projet,
                etude=self.etude,
                nom=nom
            )
            return

        from ui.reunion_window import ReunionWindow

        self.editor = ReunionWindow(
            projet,
            settings=self.settings,
            etude=self.etude,
            nom=nom
        )

        self.editor.show()

    def ouvrir_reunion_reformulation(self):
        """
        Ouvre la page Réunion de la réunion
        sélectionnée, directement à l'étape ④
        Reformulation (P16.2).
        """

        nom = self.reunion_selectionnee()

        if nom is None:
            return

        if not self.etude.reunion_joignable(nom):
            QMessageBox.warning(
                self,
                "Réunion introuvable",
                (
                    "La réunion est "
                    "introuvable : la page Reformulation "
                    "a besoin de la réunion (audio, mots "
                    "horodatés). Relocalisez-la "
                    "d'abord."
                )
            )
            return

        if not self._assurer_decoupage(nom):
            return

        chemin = fichier_projet_v1(
            self.etude,
            nom
        )

        projet = load_project(str(chemin))

        navigation = getattr(self, "navigation", None)

        if (
            navigation is not None
            and hasattr(
                navigation,
                "ouvrir_reunion"
            )
        ):
            navigation.ouvrir_reunion(
                projet,
                etude=self.etude,
                nom=nom,
                etape="reformulation"
            )
            return

        from ui.reformulation_window import (
            ReformulationWindow
        )

        self.reformulation_window = (
            ReformulationWindow(
                self.etude,
                nom,
                settings=self.settings
            )
        )

        self.reformulation_window.show()

    def _assurer_decoupage(self, nom: str) -> bool:
        """
        Segmentation de la réunion : fonction partagée
        (voir assurer_decoupage, en tête de module).
        """

        return assurer_decoupage(
            self,
            self.etude,
            nom
        )

    def ouvrir_reunion_resume(self):
        """
        Série 8 (SPEC_NAVIGATION_MODIFS 31e §31) :
        le bouton « Résumé » de la mini-tuile mène à
        la PAGE Réunion, directement à l'étape ⑤
        Résumé — l'outillage y vit dans la page ; la
        fenêtre secondaire « Résumé… » est supprimée
        de l'app (invariant complémentaire 17).
        """

        nom = self.reunion_selectionnee()

        if nom is None:
            return

        if not self.etude.reunion_joignable(nom):
            QMessageBox.warning(
                self,
                "Réunion introuvable",
                (
                    "La réunion est "
                    "introuvable : l'étape Résumé "
                    "a besoin de la réunion (audio, mots "
                    "horodatés). Relocalisez-la "
                    "d'abord."
                )
            )
            return

        if not self._assurer_decoupage(nom):
            return

        chemin = fichier_projet_v1(
            self.etude,
            nom
        )

        projet = load_project(str(chemin))

        navigation = getattr(
            self,
            "navigation",
            None
        )

        if (
            navigation is not None
            and hasattr(
                navigation,
                "ouvrir_reunion"
            )
        ):
            navigation.ouvrir_reunion(
                projet,
                etude=self.etude,
                nom=nom,
                etape="resume"
            )
            return

        # Sans adaptateur de navigation (page
        # orpheline, tests) : pas de fenêtre —
        # indiquer où vit le résumé.
        QMessageBox.information(
            self,
            "Résumé",
            (
                "Le résumé se rédige sur la page "
                "Réunion, étape ⑤ Résumé : ouvrez "
                "la réunion pour l'éditer."
            )
        )
    #
    # Synthèse d'étude (P17.2).
    #

    def maj_synthese(self):

        from services.bibles import (
            VERSIONS_BIBLE,
            version_bible_etude,
        )

        version_bible = version_bible_etude(
            self.etude.parametres
        )

        nom_bible = VERSIONS_BIBLE[version_bible]["nom"]

        versions = self.etude.synthese.versions

        if versions:

            derniere = versions[-1]

            self.synthese_edit.setPlainText(
                derniere.texte
            )

            self.synthese_statut_label.setText(
                f"v{derniere.numero} · "
                f"{derniere.horodatage} · "
                f"{derniere.declencheur}"
                f" · Bible : {nom_bible}"
            )

        else:
            self.synthese_edit.clear()
            self.synthese_statut_label.setText(
                f"Bible : {nom_bible}"
            )

    def regenerer_synthese(self):
        """
        Régénération manuelle (déclencheur « manuel »)
        avec estimation du coût avant lancement.
        """

        from services.traitements.synthese import (
            ServiceSynthese
        )

        service = ServiceSynthese(self.etude)

        try:
            estimation = service.estimer()
        except Exception as e:
            QMessageBox.warning(
                self,
                "Synthèse impossible",
                str(e)
            )
            return

        reponse = QMessageBox.question(
            self,
            "Régénérer la synthèse d'étude",
            (
                "Régénérer la synthèse d'étude à partir "
                "des textes validés ?\n\n"
                f"Réunions sources : "
                f"{estimation['nb_reunions']}\n"
                f"Modèle : {estimation['modele']}\n"
                f"Tokens estimés : "
                f"{estimation['tokens_in_estimes']} en "
                f"entrée, "
                f"{estimation['tokens_out_estimes']} en "
                "sortie\n"
                f"Coût estimé : "
                f"{estimation['cout_estime']:.3f} $"
            )
        )

        if reponse != QMessageBox.StandardButton.Yes:
            return

        self._lancer_synthese(
            service,
            declencheur="manuel"
        )

    def _lancer_synthese(self, service, declencheur):
        """
        Génère la synthèse en arrière-plan (thread) :
        la page reste réactive.
        """

        if getattr(self, "synthese_thread", None):
            return

        self.synthese_statut_label.setText(
            "Génération en cours…"
        )

        #
        # Fenêtre de chargement (règle 2026-11-07) :
        # un appel LLM — temps écoulé affiché.
        #
        from ui.fenetre_chargement_llm import (
            FenetreChargementLLM,
        )

        self.fenetre_chargement = FenetreChargementLLM(
            "Synthèse d'étude en cours…",
            parent=self,
            message=(
                "Appel LLM en cours "
                "(synthèse d'étude)…"
            ),
        )

        self.fenetre_chargement.set_indeterminee()
        self.fenetre_chargement.show()

        self.synthese_thread = QThread(self)

        self.synthese_worker = SyntheseWorker(
            service,
            declencheur
        )

        self.synthese_worker.moveToThread(
            self.synthese_thread
        )

        self.synthese_thread.started.connect(
            self.synthese_worker.run
        )

        self.synthese_worker.terminee.connect(
            self._sur_synthese_terminee
        )
        self.synthese_worker.erreur.connect(
            self._sur_synthese_erreur
        )

        self.synthese_thread.start()

    def _sur_synthese_terminee(self, resultat):

        if getattr(
            self,
            "fenetre_chargement",
            None
        ) is not None:
            self.fenetre_chargement.fermer()
            self.fenetre_chargement = None

        version, stats = resultat

        self.synthese_thread.quit()
        self.synthese_thread = None
        self.synthese_worker = None

        self.maj_synthese()

        cout = stats.get("cout_estime", 0.0)

        QMessageBox.information(
            self,
            "Synthèse mise à jour",
            (
                f"Synthèse d'étude version "
                f"{version.numero} générée "
                f"(coût réel : {cout:.4f} $)."
            )
        )

    def _sur_synthese_erreur(self, message):

        if getattr(
            self,
            "fenetre_chargement",
            None
        ) is not None:
            self.fenetre_chargement.fermer()
            self.fenetre_chargement = None

        self.synthese_thread.quit()
        self.synthese_thread = None
        self.synthese_worker = None

        QMessageBox.warning(
            self,
            "Synthèse non générée",
            message
        )

        self.maj_synthese()

    #
    # Récurrences entre réunions (P17.3).
    #

    def afficher_recurrences(self):

        from services.controle_qualite import (
            expressions_recurrentes
        )

        recurrentes = expressions_recurrentes(self.etude)

        if not recurrentes:

            QMessageBox.information(
                self,
                "Expressions récurrentes",
                (
                    "Aucune expression récurrente "
                    "signalée entre les réunions "
                    "(il faut des textes validés dans "
                    "au moins deux réunions)."
                )
            )

            return

        lignes = []

        for item in recurrentes:

            reunions = ", ".join(
                reunion
                for reunion in item["reunions"]
            )

            lignes.append(
                f"« {item['expression']} » — "
                f"{item['occurrences']} occurrence(s), "
                f"réunions : {reunions}"
            )

        QMessageBox.information(
            self,
            "Expressions récurrentes (indicatif)",
            (
                "Formules les plus fréquentes de "
                "l'étude, présentes dans plusieurs "
                "réunions — signalement indicatif, "
                "jamais de remplacement suggéré :\n\n"
                + "\n".join(lignes[:20])
            )
        )

    def retour_accueil(self):
        """
        Sauvegarde l'étude et revient à l'accueil —
        toujours la page d'accueil de l'app (spec
        correctifs §11.1), jamais une nouvelle
        fenêtre.
        """

        sauvegarder_etude(self.etude)

        navigation = getattr(self, "navigation", None)

        if navigation is not None:
            navigation.ouvrir_accueil()
            return

        from ui.home_window import HomeWindow

        self.accueil = HomeWindow()
        self.accueil.show()

        self.close()
