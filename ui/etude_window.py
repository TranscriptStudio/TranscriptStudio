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

    def build_ui(self):
        """
        Page Étude (P18.6c, spec navigation §4) :
        ruban (titre, thème, nombre de réunions,
        badge Bible · versification, boutons
        Modifier l'étude / Accueil / ⚙ / ?), liste
        des réunions en une colonne (mini-tuiles :
        titre, rang, date, durée, avancement ①→⑤
        SANS ⑥, coût, ouverture, réordonnancement),
        synthèse d'étude (régénérer / éditer),
        récurrences, renvoi export ouvrage vers la
        page Ouvrage.
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
        self.badge_bible_label.setToolTip(
            "Version de Bible retenue par l'étude "
            "(paramètres de l'étude) et sa "
            "versification — un écart de "
            "versification est une information "
            "consultable, jamais une décision "
            "automatique (P18.5)"
        )

        ruban_layout.addWidget(
            self.badge_bible_label
        )

        ruban_layout.addStretch()

        self.modifier_button = QPushButton(
            "Modifier l'étude"
        )
        self.modifier_button.setToolTip(
            "Modifier le titre et le thème de "
            "l'étude"
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

        entete_reunions.addStretch()
        entete_reunions.addWidget(self.ajouter_button)

        layout.addLayout(entete_reunions)

        self.reunions_liste = QListWidget()
        self.reunions_liste.setToolTip(
            "Sélectionnez une réunion : les boutons "
            "de la mini-tuile ouvrent la page Réunion "
            "(correction, reformulation, résumé)"
        )
        self.reunions_liste.itemDoubleClicked.connect(
            self.ouvrir_reunion_editeur
        )

        layout.addWidget(
            self.reunions_liste,
            stretch=1
        )

        boutons_reunions = QHBoxLayout()

        self.retirer_button = QPushButton(
            "Retirer la réunion"
        )
        self.retirer_button.clicked.connect(
            self.retirer_reunion_ui
        )

        self.relocaliser_button = QPushButton(
            "Relocaliser..."
        )
        self.relocaliser_button.clicked.connect(
            self.relocaliser_reunion_ui
        )

        for bouton in (
            self.retirer_button,
            self.relocaliser_button,
        ):
            boutons_reunions.addWidget(bouton)

        boutons_reunions.addStretch()

        layout.addLayout(boutons_reunions)

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

        boutons_synthese = QHBoxLayout()

        self.synthese_regenerer_button = QPushButton(
            "Régénérer…"
        )
        self.synthese_regenerer_button.setToolTip(
            "Régénérer la synthèse d'étude à partir "
            "des textes validés (coût marginal)"
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

        self.recurrences_button = QPushButton(
            "Récurrences…"
        )
        self.recurrences_button.setToolTip(
            "Expressions récurrentes entre réunions "
            "(gratuit, indicatif)"
        )
        self.recurrences_button.clicked.connect(
            self.afficher_recurrences
        )

        self.synthese_statut_label = QLabel("")
        self.synthese_statut_label.setStyleSheet(
            "font-size: 12px; color: #666666;"
        )

        boutons_synthese.addWidget(
            self.synthese_regenerer_button
        )
        boutons_synthese.addWidget(
            self.synthese_editer_button
        )
        boutons_synthese.addWidget(
            self.synthese_sauver_button
        )
        boutons_synthese.addWidget(
            self.recurrences_button
        )
        boutons_synthese.addWidget(
            self.synthese_statut_label
        )

        boutons_synthese.addStretch()

        layout.addLayout(boutons_synthese)

        #
        # Renvoi export ouvrage vers la page
        # Ouvrage (spec §4.5 : l'assemblage et
        # l'export final s'y font).
        #
        ouvrage_layout = QHBoxLayout()

        self.ouvrage_button = QPushButton(
            "Ouvrage…"
        )
        self.ouvrage_button.setToolTip(
            "Ouvrir la page Ouvrage : assemblage des "
            "textes validés et export final de "
            "l'étude"
        )
        self.ouvrage_button.clicked.connect(
            self.ouvrir_ouvrage
        )

        ouvrage_note = QLabel(
            "L'assemblage et l'export final de "
            "l'ouvrage se font sur la page Ouvrage."
        )
        ouvrage_note.setStyleSheet(
            "font-size: 12px; color: #757575;"
        )

        ouvrage_layout.addWidget(self.ouvrage_button)
        ouvrage_layout.addWidget(ouvrage_note)
        ouvrage_layout.addStretch()

        layout.addLayout(ouvrage_layout)

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

    def _texte_badge_bible(self) -> str:
        """
        Badge COURT (P18.6-bis, spec correctifs §11) :
        « Bible : Darby révisée · versification :
        Darby » — les détails d'édition restent
        consultables dans les réglages, jamais
        affichés dans le ruban.
        """

        from services.bibles import (
            nom_court_bible,
            version_bible_etude,
            versification_bible,
        )

        try:

            version = version_bible_etude(
                self.etude.parametres
            )

            return (
                "Bible : "
                + nom_court_bible(version)
                + " · versification : "
                + versification_bible(version)
            )

        except Exception:
            return "Bible : —"

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
        « Modifier l'étude » : mini-fenêtre titre +
        thème (extensible — spec §4.1).
        """

        from ui.modifier_etude_dialog import (
            ModifierEtudeDialog
        )

        dialogue = ModifierEtudeDialog(
            self.etude.etude.titre,
            self.etude.etude.theme,
            parent=self
        )

        if not dialogue.exec():
            return

        titre, theme = dialogue.resultat()

        if titre:
            self.etude.etude.titre = titre

        if theme:
            self.etude.etude.theme = theme

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

        self.synthese_edit.setReadOnly(False)
        self.synthese_sauver_button.setVisible(True)
        self.synthese_editer_button.setVisible(False)

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
        avancement ; coût ; « Ouvrir » et la
        poignée de réordonnancement (l'ordre vaut
        ordre d'ouvrage). Le clic sur la tuile ouvre
        la page Réunion (spec correctifs §12-§14).
        """

        from ui.stepper import StepperBar

        cadre = QFrame()
        cadre.setObjectName("etude_mini_tuile")

        if introuvable:
            cadre.setStyleSheet(
                "QFrame#etude_mini_tuile {"
                "border: 1px solid #b35900;"
                "border-radius: 6px;"
                "}"
            )
        else:
            cadre.setStyleSheet(
                "QFrame#etude_mini_tuile {"
                "border: 1px solid #C8C8C8;"
                "border-radius: 6px;"
                "}"
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

            stepper = StepperBar(
                etapes=etats.keys(),
                cliquable=False,
                compact=True
            )

            stepper.definir_etats(etats)

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

        ligne_actions = QHBoxLayout()

        ouvrir_button = QPushButton("Ouvrir")
        ouvrir_button.setFixedHeight(26)
        ouvrir_button.setToolTip(
            "Ouvrir la page Réunion de cette "
            "réunion (correction, reformulation, "
            "résumé, export)"
        )
        ouvrir_button.clicked.connect(
            lambda checked=False, n=nom: (
                self._ouvrir_reunion(n)
            )
        )

        monter_button = QPushButton("↑")
        monter_button.setFixedHeight(26)
        monter_button.setToolTip(
            "Réordonner : la réunion monte dans "
            "l'ordre d'ouvrage"
        )
        monter_button.clicked.connect(
            lambda checked=False, n=nom: (
                self._deplacer_reunion(n, -1)
            )
        )

        descendre_button = QPushButton("↓")
        descendre_button.setFixedHeight(26)
        descendre_button.setToolTip(
            "Réordonner : la réunion descend dans "
            "l'ordre d'ouvrage"
        )
        descendre_button.clicked.connect(
            lambda checked=False, n=nom: (
                self._deplacer_reunion(n, 1)
            )
        )

        for bouton in (
            ouvrir_button,
            monter_button,
            descendre_button,
        ):
            ligne_actions.addWidget(bouton)

        ligne_actions.addStretch()

        layout.addLayout(ligne_actions)

        cadre.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        cadre.mousePressEvent = (
            lambda event, n=nom: (
                self._ouvrir_reunion(n)
            )
        )

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
        Bouton « Ouvrir » d'une mini-tuile : page
        Réunion de la réunion (objet de premier
        rang), avec l'étude et le nom connus.
        """

        self._selectionner(nom)

        self.ouvrir_reunion_editeur(nom)

    def _ouvrir_reformulation(self, nom: str):

        self._selectionner(nom)

        self.ouvrir_reunion_reformulation()

    def _ouvrir_resume(self, nom: str):

        self._selectionner(nom)

        self.ouvrir_reunion_resume()

    def _deplacer_reunion(self, nom: str, offset: int):
        """
        Poignée de réordonnancement (l'ordre vaut
        ordre d'ouvrage, spec §4.2).
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
        Retire la réunion sélectionnée de l'étude :
        sa référence et ses résultats d'étude ;
        jamais le projet v1 ni le registre FID.
        """

        nom = self.reunion_selectionnee()

        if nom is None:
            return

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
        Relocalisation guidée d'une réunion au
        projet v1 introuvable.
        """

        nom = self.reunion_selectionnee()

        if nom is None:
            return

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
        Ouvre la fenêtre Résumé de la réunion
        sélectionnée (P17.1) — dialogue modal, la
        synthèse se rafraîchit à la fermeture.
        """

        nom = self.reunion_selectionnee()

        if nom is None:
            return

        if not self._assurer_decoupage(nom):
            return

        from ui.resume_window import ResumeWindow

        fenetre = ResumeWindow(
            self.etude,
            nom,
            parent=self
        )

        fenetre.exec()

        self.maj_synthese()
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
