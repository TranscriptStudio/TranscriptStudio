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
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, QObject, QThread, Signal, Slot

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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 14)
        layout.setSpacing(10)

        #
        # Titre.
        #
        self.titre_label = QLabel(
            self.etude.etude.titre
        )
        self.titre_label.setStyleSheet(
            "font-size: 20px; font-weight: bold;"
        )

        theme_libelle = {
            "livre": "Livre biblique",
            "libre": "Thème libre",
        }.get(
            self.etude.etude.theme,
            self.etude.etude.theme
        )

        self.theme_label = QLabel(theme_libelle)
        self.theme_label.setStyleSheet(
            "font-size: 12px; color: #666666;"
        )

        layout.addWidget(self.titre_label)
        layout.addWidget(self.theme_label)

        self.avertissement_label = QLabel("")
        self.avertissement_label.setStyleSheet(
            "font-size: 12px; color: #b35900;"
        )
        self.avertissement_label.setWordWrap(True)
        layout.addWidget(self.avertissement_label)

        #
        # Réunions.
        #
        layout.addWidget(QLabel("Réunions"))

        self.reunions_liste = QListWidget()
        self.reunions_liste.setToolTip(
            "Double-clic : correction de transcription "
            "dans l'éditeur v1 — ou utilisez les "
            "boutons explicites ci-dessous"
        )
        self.reunions_liste.itemDoubleClicked.connect(
            self.ouvrir_reunion_editeur
        )
        layout.addWidget(
            self.reunions_liste,
            stretch=1
        )

        boutons_reunions = QHBoxLayout()

        self.ajouter_button = QPushButton(
            "Ajouter une réunion..."
        )
        self.ajouter_button.clicked.connect(
            self.ajouter_reunion_ui
        )

        self.monter_button = QPushButton("Monter")
        self.monter_button.clicked.connect(
            self.monter_reunion
        )

        self.descendre_button = QPushButton(
            "Descendre"
        )
        self.descendre_button.clicked.connect(
            self.descendre_reunion
        )

        self.retirer_button = QPushButton(
            "Retirer la réunion"
        )
        self.retirer_button.clicked.connect(
            self.retirer_reunion_ui
        )

        self.ouvrir_button = QPushButton(
            "Correction de transcription…"
        )
        self.ouvrir_button.setToolTip(
            "Ouvrir le projet v1 dans l'éditeur de "
            "correction de transcription (étape de "
            "correction de l'oral, avant la "
            "reformulation) — le projet n'est pas "
            "modifié par l'étude"
        )
        self.ouvrir_button.clicked.connect(
            self.ouvrir_reunion_editeur
        )

        self.reformulation_button = QPushButton(
            "Reformulation littéraire…"
        )
        self.reformulation_button.setToolTip(
            "Ouvrir la page de relecture de la "
            "reformulation : texte brut en lecture "
            "seule, bloc reformulé éditable, "
            "validation par bloc"
        )
        self.reformulation_button.clicked.connect(
            self.ouvrir_reunion_reformulation
        )

        self.resume_button = QPushButton("Résumé…")
        self.resume_button.setToolTip(
            "Ouvrir le résumé de cette réunion "
            "(P17 : source au choix — reformulations "
            "validées ou brute corrigée —, éditable, "
            "validable)"
        )
        self.resume_button.clicked.connect(
            self.ouvrir_reunion_resume
        )

        self.relocaliser_button = QPushButton(
            "Relocaliser..."
        )
        self.relocaliser_button.clicked.connect(
            self.relocaliser_reunion_ui
        )

        for bouton in (
            self.ajouter_button,
            self.monter_button,
            self.descendre_button,
            self.retirer_button,
            self.ouvrir_button,
            self.reformulation_button,
            self.resume_button,
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
            self.recurrences_button
        )
        boutons_synthese.addWidget(
            self.synthese_statut_label
        )
        boutons_synthese.addStretch()

        layout.addLayout(boutons_synthese)

        #
        # Navigation.
        #
        boutons_bas = QHBoxLayout()

        self.accueil_button = QPushButton("Accueil")
        self.accueil_button.clicked.connect(
            self.retour_accueil
        )

        boutons_bas.addStretch()
        boutons_bas.addWidget(self.accueil_button)

        layout.addLayout(boutons_bas)

    def refresh_reunions(self):
        """
        Reconstitue la liste des réunions dans
        l'ordre de lecture, avec leur statut.
        """

        self.reunions_liste.clear()

        for nom in self.etude.etude.ordre_reunions:

            reunion = self.etude.reunions[nom]

            introuvable = (
                nom in self.etude.reunions_introuvables
            )

            libelle = (
                f"{reunion.numero}. "
                f"{reunion.titre_1 or nom} "
                f"({reunion.date})"
            )

            if introuvable:
                libelle += "  —  projet introuvable"

            elif reunion.resume_valide:
                libelle += "  —  résumé validé"

            item = QListWidgetItem(libelle)
            item.setData(
                Qt.ItemDataRole.UserRole,
                nom
            )

            if introuvable:
                item.setForeground(
                    Qt.GlobalColor.darkYellow
                )

            self.reunions_liste.addItem(item)

        introuvables = (
            self.etude.reunions_introuvables
        )

        if introuvables:
            self.avertissement_label.setText(
                "Mode dégradé : "
                f"{len(introuvables)} réunion(s) "
                "ont un projet v1 introuvable. "
                "Les autres réunions restent "
                "utilisables ; utilisez "
                "« Relocaliser... » après avoir "
                "sélectionné une réunion manquante."
            )
        else:
            self.avertissement_label.setText("")

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

    def ajouter_reunion_ui(self):
        """
        Ajoute un projet v1 existant comme réunion
        (référence, jamais copie).
        """

        dossier, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir un projet v1 (réunion)",
            self.settings.get_projects_root(),
            "Projet (*.sttproj)"
        )

        if not dossier:
            return

        try:
            nom = ajouter_reunion(
                self.etude,
                dossier
            )
        except EtudeError as e:
            QMessageBox.warning(
                self,
                "Réunion non ajoutée",
                str(e)
            )
            return

        sauvegarder_etude(self.etude)
        self.refresh_reunions()

        self.reunions_liste.setCurrentRow(
            self.etude.etude.ordre_reunions.index(nom)
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
                "seront retirés. Le projet v1 n'est pas "
                "touché."
            )
        )

        if resultat != QMessageBox.StandardButton.Yes:
            return

        retirer_reunion(self.etude, nom)
        sauvegarder_etude(self.etude)
        self.refresh_reunions()

    def deplacer_selection(self, offset: int):
        """
        Déplace la réunion sélectionnée dans
        l'ordre de lecture.
        """

        nom = self.reunion_selectionnee()

        if nom is None:
            return

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

    def monter_reunion(self):
        self.deplacer_selection(-1)

    def descendre_reunion(self):
        self.deplacer_selection(1)

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
                "Relocaliser le projet de la réunion "
                f"« {nom} »"
            ),
            "",
            "Projet (*.sttproj)"
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
        Ouvre le projet v1 de la réunion sélectionnée
        dans l'éditeur existant.
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
                "Projet introuvable",
                (
                    "Le projet v1 de cette réunion est "
                    "introuvable. Utilisez "
                    "« Relocaliser... » pour le "
                    "retouver."
                )
            )
            return

        projet = load_project(str(chemin))

        from ui.main_window import MainWindow

        self.editor = MainWindow(projet)
        self.editor.show()

    def ouvrir_reunion_reformulation(self):
        """
        Ouvre la page de traitement Reformulation
        de la réunion sélectionnée (P16.2) :
        table de relecture, pastilles, moteur.
        """

        nom = self.reunion_selectionnee()

        if nom is None:
            return

        if not self.etude.reunion_joignable(nom):
            QMessageBox.warning(
                self,
                "Projet introuvable",
                (
                    "Le projet v1 de cette réunion est "
                    "introuvable : la page Reformulation "
                    "a besoin du projet (audio, mots "
                    "horodatés). Relocalisez le projet "
                    "d'abord."
                )
            )
            return

        if not self._assurer_decoupage(nom):
            return

        from ui.reformulation_window import (
            ReformulationWindow
        )

        self.reformulation_window = (
            ReformulationWindow(
                self.etude,
                nom
            )
        )

        self.reformulation_window.show()

    def _assurer_decoupage(self, nom: str) -> bool:
        """
        La reformulation (et le résumé depuis la
        brute) exigent une segmentation de la réunion
        en blocs de parole (P14.4). La génération
        n'était exposée nulle part dans l'UI : elle
        est proposée ici, depuis la diarisation
        validée du projet v1.

        Retour : True si la segmentation existe (ou
        vient d'être générée).
        """

        if self.etude.decoupages.get(nom):
            return True

        reponse = QMessageBox.question(
            self,
            "Segmentation de la réunion",
            (
                "Aucune segmentation n'existe encore pour "
                f"la réunion « {nom} » : la reformulation "
                "travaille par blocs de parole.\n\n"
                "La générer maintenant à partir de la "
                "diarisation validée du projet v1 ?\n\n"
                "(Le projet v1 n'est pas modifié.)"
            )
        )

        if reponse != QMessageBox.StandardButton.Yes:
            return False

        from services.decoupage import (
            DecoupageError,
            enregistrer_decoupage,
            generer_decoupage,
        )

        chemin = fichier_projet_v1(self.etude, nom)

        try:

            projet = load_project(str(chemin))

            decoupage = generer_decoupage(
                self.etude,
                nom,
                projet
            )

            if not decoupage.blocs:

                QMessageBox.warning(
                    self,
                    "Diarisation absente",
                    (
                        "Le projet v1 de cette réunion ne "
                        "comporte aucun bloc de parole : "
                        "validez d'abord la diarisation "
                        "dans l'éditeur de correction de "
                        "transcription, puis relancez."
                    )
                )

                return False

            enregistrer_decoupage(self.etude, decoupage)
            sauvegarder_etude(self.etude)

        except (DecoupageError, EtudeError) as e:

            QMessageBox.warning(
                self,
                "Segmentation impossible",
                str(e)
            )

            return False

        return True

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
            )

        else:
            self.synthese_edit.clear()
            self.synthese_statut_label.setText(
                "aucune version"
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
        Sauvegarde l'étude et revient à l'accueil.
        """

        sauvegarder_etude(self.etude)

        from ui.home_window import HomeWindow

        self.accueil = HomeWindow()
        self.accueil.show()

        self.close()
