# ui/resume_window.py
"""
Fenêtre Résumé d'une réunion (P17.1).

Même outillage que la page Reformulation (mécanismes
communs du moteur) : génération avec source au choix
et longueur cible paramétrable (confirmation du coût
avant lancement), relance complète avec consigne,
relance ciblée sur sélection (contexte identique +
versions antérieures), édition libre (chaque
sauvegarde = une nouvelle version edition_manuelle),
retour arrière, validation (résumé figé pour
l'export et la synthèse d'étude).

Avertissement si la source a évolué depuis la
génération — signalement seulement, jamais de mise à
jour automatique.
"""

import getpass

from PySide6.QtCore import (
    QObject,
    QThread,
    Signal,
    Slot,
)
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from services.controle_qualite import (
    compter_mots,
    interdits_stylistiques,
    INTERDITS_STYLISTIQUES_DEFAUT,
)
from services.etude_io import (
    EtudeOuverte,
    ajouter_version_resume,
    devalider_version_resume,
    sauvegarder_etude,
    valider_version_resume,
)
from services.traitements.resume import (
    ServiceResume,
    SOURCE_BRUTE,
    SOURCE_REFORMULEES,
    source_a_evolve,
)

try:
    VALIDATEUR_DEFAUT = getpass.getuser()
except Exception:
    VALIDATEUR_DEFAUT = "utilisateur"


class ResumeWorker(QObject):
    """
    Exécute une opération du service résumé dans un
    thread (génération, relance) : la fenêtre reste
    réactive, l'annulation est propre.
    """

    terminee = Signal(object)
    erreur = Signal(str)

    def __init__(self, operation):
        super().__init__()
        self.operation = operation

    @Slot()
    def run(self):

        try:
            self.terminee.emit(self.operation())
        except Exception as e:
            self.erreur.emit(str(e))


class ResumeWindow(QDialog):
    """
    Résumé d'une réunion : génération, édition,
    historique de versions, validation.
    """

    def __init__(
        self,
        etude_ouverte: EtudeOuverte,
        reunion: str,
        parent=None
    ):
        super().__init__(parent)

        self.etude = etude_ouverte
        self.reunion = reunion

        self.service = ServiceResume(self.etude)

        self.annulation = None
        self.thread = None
        self.worker = None

        self.non_enregistre = False

        self.setWindowTitle(
            f"Résumé — {reunion} — "
            f"{self.etude.etude.titre}"
        )

        self.resize(760, 620)

        self.build_ui()
        self.charger()

    #
    # Construction de l'interface.
    #

    def build_ui(self):

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        entete = QHBoxLayout()
        entete.setSpacing(10)

        self.titre_label = QLabel("<b>Résumé</b>")
        entete.addWidget(self.titre_label)

        self.version_label = QLabel("")
        self.version_label.setStyleSheet(
            "color: #888; font-size: 12px;"
        )
        entete.addWidget(self.version_label)

        entete.addStretch(1)

        self.statut_label = QLabel("")
        self.statut_label.setStyleSheet(
            "font-size: 12px;"
        )
        entete.addWidget(self.statut_label)

        layout.addLayout(entete)

        #
        # Ligne de lancement : source, longueur
        # cible, génération.
        #
        lancement = QHBoxLayout()
        lancement.setSpacing(8)

        lancement.addWidget(QLabel("Source :"))

        self.source_combo = QComboBox()
        self.source_combo.addItem(
            "Reformulations validées",
            SOURCE_REFORMULEES
        )
        self.source_combo.addItem(
            "Transcription brute corrigée",
            SOURCE_BRUTE
        )
        lancement.addWidget(self.source_combo)

        longueur_widget = QWidget()
        longueur_layout = QHBoxLayout(longueur_widget)
        longueur_layout.setContentsMargins(0, 0, 0, 0)
        longueur_layout.setSpacing(4)

        self.longueur_min_spin = QSpinBox()
        self.longueur_min_spin.setRange(100, 5000)
        self.longueur_min_spin.setSingleStep(50)
        self.longueur_min_spin.setValue(650)

        self.longueur_max_spin = QSpinBox()
        self.longueur_max_spin.setRange(100, 5000)
        self.longueur_max_spin.setSingleStep(50)
        self.longueur_max_spin.setValue(700)

        longueur_layout.addWidget(self.longueur_min_spin)
        longueur_layout.addWidget(QLabel("à"))
        longueur_layout.addWidget(self.longueur_max_spin)
        longueur_layout.addWidget(QLabel("mots"))

        lancement.addWidget(QLabel("Longueur :"))
        lancement.addWidget(longueur_widget)

        self.generer_button = QPushButton("Générer…")
        self.generer_button.clicked.connect(
            self.generer
        )
        lancement.addWidget(self.generer_button)

        lancement.addStretch(1)

        layout.addLayout(lancement)

        #
        # Éditeur du résumé.
        #
        self.resume_edit = QTextEdit()
        self.resume_edit.setPlaceholderText(
            "Aucun résumé pour cette réunion : "
            "choisissez la source et cliquez "
            "« Générer… »."
        )
        self.resume_edit.textChanged.connect(
            self.sur_texte_modifie
        )
        layout.addWidget(self.resume_edit, 1)

        #
        # Indicateur discret : contrôle qualité local
        # + avertissement de source évoluée.
        #
        self.cq_label = QLabel("")
        self.cq_label.setStyleSheet(
            "font-size: 12px; color: #888;"
        )
        self.cq_label.setWordWrap(True)
        layout.addWidget(self.cq_label)

        #
        # Opérations.
        #
        operations = QHBoxLayout()
        operations.setSpacing(8)

        self.sauvegarder_button = QPushButton(
            "Sauvegarder l'édition"
        )
        self.sauvegarder_button.clicked.connect(
            self.sauvegarder_edition
        )
        operations.addWidget(self.sauvegarder_button)

        self.retour_button = QPushButton(
            "Retour arrière"
        )
        self.retour_button.clicked.connect(
            self.retour_arriere
        )
        operations.addWidget(self.retour_button)

        self.relancer_button = QPushButton(
            "Relancer avec consigne…"
        )
        self.relancer_button.clicked.connect(
            self.relancer
        )
        operations.addWidget(self.relancer_button)

        self.selection_button = QPushButton(
            "Retravailler la sélection"
        )
        self.selection_button.clicked.connect(
            self.relancer_selection
        )
        operations.addWidget(self.selection_button)

        self.valider_button = QPushButton("Valider")
        self.valider_button.clicked.connect(
            self.valider
        )
        operations.addWidget(self.valider_button)

        self.devalider_button = QPushButton(
            "Dévalider"
        )
        self.devalider_button.clicked.connect(
            self.devalider
        )
        self.devalider_button.setVisible(False)
        operations.addWidget(self.devalider_button)

        self.annuler_button = QPushButton("Annuler")
        self.annuler_button.setVisible(False)
        self.annuler_button.clicked.connect(
            self.annuler
        )
        operations.addWidget(self.annuler_button)

        operations.addStretch(1)

        fermer = QPushButton("Fermer")
        fermer.clicked.connect(self.accept)
        operations.addWidget(fermer)

        layout.addLayout(operations)

    #
    # État et affichage.
    #

    def resultat(self):

        return self.etude.resumes.get(self.reunion)

    def derniere_version(self):

        resultat = self.resultat()

        if not resultat or not resultat.versions:
            return None

        return resultat.versions[-1]

    def version_validee(self):

        for version in reversed(
            self.dernieres_versions()
        ):

            if (
                version.validation
                and version.validation.statut
                == "valide"
            ):
                return version

        return None

    def dernieres_versions(self):

        resultat = self.resultat()

        return resultat.versions if resultat else []

    def charger(self):

        derniere = self.derniere_version()

        self.resume_edit.blockSignals(True)

        if derniere:
            self.resume_edit.setPlainText(
                derniere.texte
            )
        else:
            self.resume_edit.clear()

        self.resume_edit.blockSignals(False)

        self.non_enregistre = False

        self.rafraichir()

    def rafraichir(self):

        derniere = self.derniere_version()
        validee = self.version_validee()

        #
        # Résumé validé : figé pour l'édition et les
        # relances (dévalider pour reprendre).
        #
        fige = validee is not None

        self.resume_edit.setReadOnly(fige)

        for bouton in (
            self.generer_button,
            self.sauvegarder_button,
            self.relancer_button,
            self.selection_button,
            self.retour_button,
        ):
            bouton.setEnabled(not fige)

        if fige:
            self.statut_label.setText("Validé")
            self.statut_label.setStyleSheet(
                "color: #2E7D32; font-size: 12px;"
            )
        else:
            self.statut_label.setText("Brouillon")
            self.statut_label.setStyleSheet(
                "color: #888; font-size: 12px;"
            )

        self.valider_button.setVisible(not fige)
        self.devalider_button.setVisible(fige)

        if derniere:

            details = (
                f"v{derniere.numero} · "
                f"source : "
                f"{'brute corrigée' if derniere.source == SOURCE_BRUTE else 'reformulations validées'}"
                f" · origine : {derniere.origine}"
            )

            if derniere.stats:

                stats = derniere.stats

                details += (
                    f" · {stats.get('tokens_in', 0)}+"
                    f"{stats.get('tokens_out', 0)} tokens"
                    f" · "
                    f"{stats.get('cout_estime', 0):.3f} €"
                )

            self.version_label.setText(details)

        else:
            self.version_label.setText("aucune version")

        self.maj_controle_qualite()

    def maj_controle_qualite(self):

        texte = self.resume_edit.toPlainText()

        minimum = self.longueur_min_spin.value()
        maximum = self.longueur_max_spin.value()

        mots = compter_mots(texte)

        message = f"Longueur : {mots} mots "

        if mots == 0:
            message += "(cible : "
        elif mots < minimum:
            message += (
                f"(en dessous de la cible {minimum}–"
                f"{maximum} — "
            )
        elif mots > maximum:
            message += (
                f"(au-delà de la cible {minimum}–"
                f"{maximum} — "
            )
        else:
            message += "(dans la cible ; "

        message += f"cible : {minimum}–{maximum} mots)."

        interdits = interdits_stylistiques(
            texte,
            (
                self.etude.parametres
                .controle_qualite.get(
                    "interdits_stylistiques"
                )
                or INTERDITS_STYLISTIQUES_DEFAUT
            )
        )

        if interdits:

            resume = ", ".join(
                f"« {trouve['motif']} » "
                f"(×{trouve['occurrences']})"
                for trouve in interdits[:3]
            )

            message += (
                " Interdits stylistiques : " + resume
            )

        #
        # Avertissement : la source a-t-elle évolué
        # depuis la génération de la version courante ?
        #
        derniere = self.derniere_version()

        if derniere and source_a_evolve(
            self.etude,
            self.reunion,
            derniere
        ):
            message += (
                " La source a évolué depuis la "
                "génération de cette version — un "
                "résumé fait sur une autre source peut "
                "être obsolète."
            )

            self.cq_label.setStyleSheet(
                "font-size: 12px; color: #D32F2F;"
            )

        else:
            self.cq_label.setStyleSheet(
                "font-size: 12px; color: #888;"
            )

        self.cq_label.setText(message)

    def sur_texte_modifie(self):

        self.non_enregistre = True

        self.maj_controle_qualite()

    #
    # Lancement d'une opération en thread.
    #

    def lancer_operation(self, operation):

        if self.thread is not None:
            return

        self.annulation = type(
            "A", (), {"demandee": False}
        )()

        for bouton in (
            self.generer_button,
            self.sauvegarder_button,
            self.relancer_button,
            self.selection_button,
            self.retour_button,
            self.valider_button,
        ):
            bouton.setEnabled(False)

        self.annuler_button.setVisible(True)

        self.thread = QThread(self)
        self.worker = ResumeWorker(operation)

        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)

        self.worker.terminee.connect(
            self.sur_terminee
        )
        self.worker.erreur.connect(self.sur_erreur)

        self.thread.start()

    def sur_terminee(self, _resultat):

        self.thread.quit()
        self.thread = None
        self.worker = None
        self.annulation = None

        self.annuler_button.setVisible(False)

        self.non_enregistre = False

        self.charger()

    def sur_erreur(self, message):

        self.thread.quit()
        self.thread = None
        self.worker = None
        self.annulation = None

        self.annuler_button.setVisible(False)
        self.annuler_button.setEnabled(True)

        if "annul" in message.lower():
            QMessageBox.information(
                self,
                "Opération annulée",
                "Le résumé en cours a été arrêté ; rien "
                "n'a été consigné."
            )
        else:
            QMessageBox.warning(
                self,
                "Résumé non généré",
                message
            )

        self.rafraichir()

    def annuler(self):

        if self.annulation is not None:
            self.annulation.demandee = True

        self.annuler_button.setEnabled(False)

    #
    # Opérations.
    #

    def generer(self):
        """
        Génération : estimation du coût affichée puis
        confirmée avant lancement.
        """

        source = self.source_combo.currentData()

        try:
            estimation = self.service.estimer(
                self.reunion,
                source,
                [
                    self.longueur_min_spin.value(),
                    self.longueur_max_spin.value()
                ]
            )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Génération impossible",
                str(e)
            )
            return

        reponse = QMessageBox.question(
            self,
            "Générer le résumé",
            (
                "Générer le résumé de la réunion "
                f"« {self.reunion} » ?\n\n"
                f"Source : {source}\n"
                f"Modèle : {estimation['modele']}\n"
                f"Segments : {estimation['nb_segments']}\n"
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

        longueur = [
            self.longueur_min_spin.value(),
            self.longueur_max_spin.value()
        ]

        reunion = self.reunion

        def operation():

            return self.service.generer(
                reunion,
                source=source,
                longueur_cible=longueur,
                annulation=self.annulation
            )

        self.lancer_operation(operation)

    def relancer(self):
        """
        Relance complète avec consigne libre : le
        contexte reçoit la source, la formulation
        courante et toutes les versions antérieures.
        """

        consigne, ok = QInputDialog.getText(
            self,
            "Relancer le résumé",
            (
                "Consigne complémentaire (facultative) :\n"
                "(ex. « plus concis », « garder la "
                "question rhétorique finale »)"
            )
        )

        if not ok:
            return

        reunion = self.reunion

        def operation():

            return self.service.relancer(
                reunion,
                consigne=(
                    consigne.strip() or None
                ),
                annulation=self.annulation
            )

        self.lancer_operation(operation)

    def relancer_selection(self):
        """
        Relance ciblée sur la sélection : contexte
        identique + versions antérieures ; le reste
        du résumé est conservé tel quel.
        """

        curseur = self.resume_edit.textCursor()

        if not curseur.hasSelection():
            QMessageBox.information(
                self,
                "Aucune sélection",
                "Sélectionnez d'abord le passage à "
                "retravailler dans le résumé."
            )
            return

        consigne, ok = QInputDialog.getText(
            self,
            "Retravailler la sélection",
            (
                "Consigne complémentaire (facultative) :\n"
                "(le passage sélectionné sera retravaillé, "
                "le reste du résumé est conservé)"
            )
        )

        if not ok:
            return

        selection = {
            "debut": curseur.selectionStart(),
            "fin": curseur.selectionEnd(),
            "texte": curseur.selectedText(),
        }

        reunion = self.reunion

        def operation():

            return self.service.relancer_selection(
                reunion,
                selection=selection,
                consigne=(
                    consigne.strip() or None
                ),
                annulation=self.annulation
            )

        self.lancer_operation(operation)

    def sauvegarder_edition(self):
        """
        Sauvegarde de l'édition : nouvelle version
        edition_manuelle (jamais d'écrasement).

        P18.6e (spec navigation §7) : un résumé est
        saisissable directement, sans aucun appel
        LLM — y compris sans version préexistante
        (la source par défaut est alors la brute
        corrigée).
        """

        derniere = self.derniere_version()

        if not self.non_enregistre:
            return

        source = (
            derniere.source
            if derniere is not None
            else SOURCE_BRUTE
        )

        ajouter_version_resume(
            self.etude,
            self.reunion,
            self.resume_edit.toPlainText(),
            source=source,
            stats=None,
            origine="edition_manuelle"
        )

        sauvegarder_etude(self.etude)

        self.non_enregistre = False

        self.charger()

    def retour_arriere(self):
        """
        Retour à la dernière version (les
        modifications non sauvegardées sont perdues) ;
        une seconde invocation propose les versions
        antérieures.
        """

        versions = self.dernieres_versions()

        if not versions:
            return

        if self.non_enregistre:

            reponse = QMessageBox.question(
                self,
                "Modifications non enregistrées",
                (
                    "Le résumé comporte des modifications "
                    "non enregistrées.\n\n"
                    "Les abandonner et revenir à la "
                    "dernière version sauvegardée ?"
                )
            )

            if (
                reponse
                != QMessageBox.StandardButton.Yes
            ):
                return

            self.non_enregistre = False
            self.charger()
            return

        if len(versions) < 2:
            return

        etiquettes = [
            f"Version {version.numero} "
            f"({version.origine}, "
            f"{version.horodatage})"
            for version in versions
        ]

        choix, ok = QInputDialog.getItem(
            self,
            "Versions antérieures",
            "Version à afficher :",
            etiquettes,
            current=len(etiquettes) - 1,
            editable=False
        )

        if not ok:
            return

        index = etiquettes.index(choix)

        version = versions[index]

        self.resume_edit.blockSignals(True)
        self.resume_edit.setPlainText(version.texte)
        self.resume_edit.blockSignals(False)

        self.non_enregistre = True

        self.maj_controle_qualite()

    def valider(self):
        """
        Validation : possible sur une version
        sauvegardée (proposition de sauvegarder
        d'abord) ; le résumé fige pour l'export et
        la synthèse d'étude.
        """

        if not self.dernieres_versions():
            return

        if self.non_enregistre:

            reponse = QMessageBox.question(
                self,
                "Modifications non enregistrées",
                (
                    "Le résumé comporte des modifications "
                    "non enregistrées.\n\n"
                    "Les sauvegarder avant de valider "
                    "(elles deviendront la version "
                    "validée) ?"
                )
            )

            if (
                reponse
                == QMessageBox.StandardButton.Yes
            ):
                self.sauvegarder_edition()
            else:
                return

        derniere = self.derniere_version()

        valider_version_resume(
            self.etude,
            self.reunion,
            numero=derniere.numero,
            validateur=VALIDATEUR_DEFAUT
        )

        sauvegarder_etude(self.etude)

        self.rafraichir()

    def devalider(self):

        validee = self.version_validee()

        if validee is None:
            return

        devalider_version_resume(
            self.etude,
            self.reunion,
            numero=validee.numero
        )

        sauvegarder_etude(self.etude)

        self.rafraichir()
