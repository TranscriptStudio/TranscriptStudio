# ui/gestion_prompts_dialog.py
"""
Gestion des prompts (P16-ter, spec
UI_GESTION_PROMPTS_V2_2026-10-31a.md).

Deux modes d'édition :

- MODE_BIBLIOTHEQUE : les fichiers de la
  bibliothèque du dossier de paramétrage
  (``prompts/<usage>.md``) — onglet « Prompts »
  des réglages de l'app (éditeur multiligne,
  « Réinitialiser aux défauts embarqués »,
  import/export .md/.txt) ;
- MODE_ETUDE : depuis la page Reformulation et la
  page Résumé (boutons « ⚙ Prompts ») — édition de
  la COPIE LOCALE de l'étude uniquement, avec
  indicateurs de divergence (hash court) et
  actions « Recharger depuis la bibliothèque » et
  « Promulguer dans la bibliothèque » (confirmation).

Invariants (spec §6) : les défauts embarqués ne
sont jamais modifiés ; la bibliothèque ne change
jamais une étude existante ; l'import n'écrit
rien tant que « Enregistrer » n'est pas pressé.
"""

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.prompts import (
    LIBELLES_USAGES,
    USAGE_FUSION,
    USAGE_REFORMULATION,
    chemin_bibliotheque,
    ecrire_bibliotheque,
    hash_prompt,
    lire_bibliotheque,
    lire_defaut_embarque,
    reinitialiser_bibliotheque,
)


MODE_BIBLIOTHEQUE = "bibliotheque"
MODE_ETUDE = "etude"

FILTRE_FICHIERS = (
    "Prompt Markdown (*.md *.txt);;"
    "Tous les fichiers (*)"
)


class PanneauGestionPrompts(QWidget):
    """
    Éditeur partagé de la gestion des prompts,
    en mode bibliothèque ou en mode étude
    (une étude ouverte pour le mode étude).
    """

    def __init__(
        self,
        parent=None,
        mode: str = MODE_BIBLIOTHEQUE,
        etude_ouverte=None,
        usage_initial: str = USAGE_REFORMULATION,
        dossier_prompts=None
    ):
        super().__init__(parent)

        self.mode = mode
        self.etude = etude_ouverte
        self.usage = usage_initial
        self._dossier_prompts = dossier_prompts

        # Mode bibliothèque : modifications en
        # attente par usage (rien n'est écrit avant
        # « Enregistrer » — invariant 6).
        self._modifications = {}

        if self.mode == MODE_ETUDE and (
            self.etude is None
        ):
            raise ValueError(
                "Le mode étude exige une étude ouverte."
            )

        self.build_ui()
        self.recharger_editeur()

    # ------------------------------------------------------------
    # Construction.
    # ------------------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        ligne_usage = QHBoxLayout()
        ligne_usage.setSpacing(8)

        ligne_usage.addWidget(
            QLabel("Usage :")
        )

        self.usage_combo = QComboBox()

        for usage, libelle in (
            LIBELLES_USAGES.items()
        ):
            self.usage_combo.addItem(libelle, usage)

        self.usage_combo.setCurrentIndex(
            max(
                0,
                self.usage_combo.findData(self.usage)
            )
        )

        self.usage_combo.currentIndexChanged.connect(
            self.sur_changement_usage
        )

        ligne_usage.addWidget(self.usage_combo)
        ligne_usage.addStretch()

        layout.addLayout(ligne_usage)

        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setPlaceholderText(
            "Prompt système (texte Markdown, "
            "multiligne)"
        )

        layout.addWidget(
            self.prompt_edit,
            stretch=1
        )

        #
        # Indicateurs : origine (mode bibliothèque)
        # et divergence locale/bibliothèque (hash
        # court, 8 caractères).
        #
        self.origine_label = QLabel("")
        self.origine_label.setStyleSheet(
            "font-size: 12px; color: #888;"
        )
        self.origine_label.setWordWrap(True)
        layout.addWidget(self.origine_label)

        self.divergence_label = QLabel("")
        self.divergence_label.setStyleSheet(
            "font-size: 12px;"
        )
        self.divergence_label.setWordWrap(True)
        layout.addWidget(self.divergence_label)

        #
        # Actions propres au mode.
        #
        actions = QHBoxLayout()
        actions.setSpacing(8)

        if self.mode == MODE_BIBLIOTHEQUE:

            self.reinitialiser_button = QPushButton(
                "Réinitialiser aux défauts "
                "embarqués"
            )
            self.reinitialiser_button.clicked.connect(
                self.reinitialiser_defauts
            )

            self.importer_button = QPushButton(
                "Importer…"
            )
            self.importer_button.clicked.connect(
                self.importer
            )

            self.exporter_button = QPushButton(
                "Exporter…"
            )
            self.exporter_button.clicked.connect(
                self.exporter
            )

            for bouton in (
                self.reinitialiser_button,
                self.importer_button,
                self.exporter_button,
            ):
                actions.addWidget(bouton)

        else:

            self.recharger_button = QPushButton(
                "⟳ Recharger depuis la "
                "bibliothèque"
            )
            self.recharger_button.setToolTip(
                "Remplace le texte de l'éditeur par "
                "celui de la bibliothèque (rien "
                "n'est écrit avant « Enregistrer »)"
            )
            self.recharger_button.clicked.connect(
                self.recharger_depuis_bibliotheque
            )

            self.promulguer_button = QPushButton(
                "⬆ Promulguer dans la "
                "bibliothèque"
            )
            self.promulguer_button.setToolTip(
                "Écrit le texte de l'éditeur dans le "
                "fichier de la bibliothèque "
                "(confirmé) ; aucune étude n'est "
                "touchée"
            )
            self.promulguer_button.clicked.connect(
                self.promulguer
            )

            for bouton in (
                self.recharger_button,
                self.promulguer_button,
            ):
                actions.addWidget(bouton)

        actions.addStretch()

        layout.addLayout(actions)

        self.prompt_edit.textChanged.connect(
            self.maj_indicateurs
        )

    # ------------------------------------------------------------
    # Sources de texte.
    # ------------------------------------------------------------

    def _parametres_usage(self) -> dict:
        """
        Bloc de paramètres de l'étude portant la
        copie locale de l'usage courant.
        """

        if self.usage == USAGE_REFORMULATION:
            return self.etude.parametres.reformulation

        if self.usage == USAGE_FUSION:
            # P19.4-bis : bloc optionnel (les études
            # antérieures n'ont pas de copie locale
            # — la lecture vaut la bibliothèque,
            # l'édition ENRISTRE la copie).
            return self.etude.parametres.fusion

        return self.etude.parametres.resume

    def _texte_local(self) -> str:
        """
        Copie LOCALE de l'usage courant (paramètres
        de l'étude), mode étude.
        """

        return (
            self._parametres_usage().get(
                "prompt", ""
            )
            or ""
        )

    def _texte_source(self, usage: str) -> str:
        """
        Texte source d'un usage pour l'éditeur :
        copie locale (mode étude), ou modification
        en attente / bibliothèque (mode
        bibliothèque).
        """

        if self.mode == MODE_ETUDE:
            return self._texte_local()

        texte = self._modifications.get(usage)

        if texte is not None:
            return texte

        return lire_bibliotheque(
            usage,
            self._dossier_prompts
        )[0]

    def recharger_editeur(self):
        """
        (Re)charge l'éditeur avec la valeur source de
        l'usage courant (les modifications en cours
        de l'usage sont perdues).
        """

        self.prompt_edit.setPlainText(
            self._texte_source(self.usage)
        )

        self.usage_combo.setCurrentIndex(
            max(
                0,
                self.usage_combo.findData(self.usage)
            )
        )

        self.maj_indicateurs()

    def sur_changement_usage(self, _index):

        ancien = self.usage

        if ancien == self.usage_combo.currentData():
            return

        #
        # Mode bibliothèque : les modifications de
        # l'usage quitté restent en attente (elles
        # seront écrites par « Enregistrer »).
        #
        if self.mode == MODE_BIBLIOTHEQUE:
            self._modifications[ancien] = (
                self.prompt_edit.toPlainText()
            )

        self.usage = (
            self.usage_combo.currentData()
        )

        self.prompt_edit.setPlainText(
            self._texte_source(self.usage)
        )

        self.maj_indicateurs()

    # ------------------------------------------------------------
    # Indicateurs (hash court).
    # ------------------------------------------------------------

    def maj_indicateurs(self):

        texte_editeur = (
            self.prompt_edit.toPlainText()
        )

        hash_editeur = hash_prompt(texte_editeur)

        if self.mode == MODE_ETUDE:

            hash_local = hash_prompt(
                self._texte_local()
            )

            biblio, _personnalise = (
                lire_bibliotheque(
                    self.usage,
                    self._dossier_prompts
                )
            )

            hash_biblio = hash_prompt(biblio)

            if hash_editeur == hash_local:

                if hash_local == hash_biblio:
                    divergences = (
                        "Copie locale, bibliothèque et "
                        "éditeur : identiques "
                        f"({hash_biblio or '—'})"
                    )

                else:
                    divergences = (
                        f"Copie locale : {hash_local} · "
                        f"Bibliothèque : {hash_biblio} · "
                        "DIVERGENTES"
                    )

            else:
                divergences = (
                    f"Éditeur : {hash_editeur or '—'} · "
                    f"Copie locale : {hash_local or '—'} · "
                    f"Bibliothèque : {hash_biblio or '—'} · "
                    "modifications non enregistrées"
                )

            self.origine_label.setText(
                "Édition de la COPIE LOCALE de "
                "l'étude — la bibliothèque n'est "
                "touchée que par « Promulguer »."
            )

            self.divergence_label.setText(
                divergences
            )

            return

        #
        # Mode bibliothèque.
        #
        texte_biblio, personnalise = (
            lire_bibliotheque(
                self.usage,
                self._dossier_prompts
            )
        )

        chemin = chemin_bibliotheque(
            self.usage,
            self._dossier_prompts
        )

        if personnalise:
            origine = (
                f"Fichier bibliothèque : {chemin}"
            )

        else:
            origine = (
                "Aucun fichier de bibliothèque "
                f"({chemin}) — valeur du défaut "
                "embarqué"
            )

        hash_biblio = hash_prompt(texte_biblio)

        if hash_editeur == hash_biblio:
            divergences = (
                f"Éditeur et bibliothèque : "
                f"identiques ({hash_biblio})"
            )

        else:
            divergences = (
                f"Éditeur : {hash_editeur or '—'} · "
                f"Bibliothèque : {hash_biblio or '—'} · "
                "modifications non enregistrées"
            )

        self.origine_label.setText(origine)
        self.divergence_label.setText(divergences)

    # ------------------------------------------------------------
    # Écritures.
    # ------------------------------------------------------------

    def enregistrer(self) -> bool:
        """
        Écrit les modifications selon le mode :

        - mode étude : la copie locale de l'étude
          (parametres.json) uniquement ;
        - mode bibliothèque : les usages modifiés
          (édition en attente ou usage affiché).

        Retour : True si quelque chose a été écrit.
        """

        if self.mode == MODE_ETUDE:

            self._parametres_usage()["prompt"] = (
                self.prompt_edit.toPlainText()
            )

            from services.etude_io import (
                sauvegarder_etude,
            )

            sauvegarder_etude(self.etude)

            #
            # P18.7e : la copie locale du prompt vit dans
            # les paramètres DU TIER de chaque réunion —
            # on propage explicitement la valeur éditée
            # vers tous les tiers et on les sauvegarde.
            #
            from services.tier_reunion import (
                sauvegarder_tier,
            )

            for tier in self.etude.tiers.values():

                parametres = (
                    self.etude.parametres_traitement_de(
                        tier.nom
                    )
                )

                if self.usage == USAGE_REFORMULATION:
                    parametres.reformulation["prompt"] = (
                        self.prompt_edit.toPlainText()
                    )
                elif self.usage == USAGE_FUSION:
                    parametres.fusion["prompt"] = (
                        self.prompt_edit.toPlainText()
                    )
                else:
                    parametres.resume["prompt"] = (
                        self.prompt_edit.toPlainText()
                    )

                sauvegarder_tier(tier)

            self.maj_indicateurs()

            return True

        if self.usage in LIBELLES_USAGES:
            self._modifications[self.usage] = (
                self.prompt_edit.toPlainText()
            )

        ecrit = False

        for usage in LIBELLES_USAGES:

            texte = self._modifications.get(usage)

            if texte is None:
                continue

            biblio = lire_bibliotheque(
                usage,
                self._dossier_prompts
            )[0]

            if hash_prompt(texte) == hash_prompt(
                biblio
            ):
                continue

            ecrire_bibliotheque(
                usage,
                texte,
                self._dossier_prompts
            )

            ecrit = True

        self._modifications.clear()

        self.maj_indicateurs()

        return ecrit

    # ------------------------------------------------------------
    # Actions du mode bibliothèque.
    # ------------------------------------------------------------

    def reinitialiser_defauts(self):
        """
        Retour au DÉFAUT EMBARQUÉ : supprime le
        fichier de bibliothèque de l'usage courant
        (confirmation ; les défauts embarqués ne
        sont jamais modifiés — invariant 1).
        """

        usage = self.usage

        texte_defaut = lire_defaut_embarque(usage)

        biblio, personnalise = lire_bibliotheque(
            usage,
            self._dossier_prompts
        )

        if (
            not personnalise
            and hash_prompt(biblio) == hash_prompt(
                self.prompt_edit.toPlainText()
            )
        ):
            QMessageBox.information(
                self,
                "Déjà aux défauts",
                "Le prompt « {libelle} » est déjà "
                "au défaut embarqué (aucun fichier "
                "de bibliothèque).".format(
                    libelle=(
                        LIBELLES_USAGES[usage]
                    )
                )
            )

            return

        reponse = QMessageBox.question(
            self,
            "Réinitialiser le prompt",
            "Réinitialiser le prompt "
            f"« {LIBELLES_USAGES[usage]} » aux "
            "défauts embarqués ?\n\n"
            "Le fichier de bibliothèque sera "
            "supprimé ; les défauts embarqués ne "
            "sont jamais modifiés.",
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if reponse != (
            QMessageBox.StandardButton.Yes
        ):
            return

        reinitialiser_bibliotheque(
            usage,
            self._dossier_prompts
        )

        self._modifications.pop(usage, None)

        self.prompt_edit.setPlainText(texte_defaut)

        self.maj_indicateurs()

    def importer(self):
        """
        Importe un fichier .md/.txt dans l'éditeur
        de l'usage courant — AUCUNE écriture avant
        « Enregistrer » (invariant 6).
        """

        chemin, _filtre = QFileDialog.getOpenFileName(
            self,
            "Importer un prompt "
            f"({LIBELLES_USAGES[self.usage]})",
            "",
            FILTRE_FICHIERS,
        )

        if not chemin:
            return

        try:

            with open(
                chemin,
                "r",
                encoding="utf-8"
            ) as fichier:
                texte = fichier.read()

        except (OSError, UnicodeDecodeError) as e:
            QMessageBox.critical(
                self,
                "Import impossible",
                f"Fichier illisible ({chemin}) : {e}"
            )

            return

        self.prompt_edit.setPlainText(texte)

    def exporter(self):
        """
        Écrit exactement le texte de l'éditeur au
        chemin choisi (.md ou .txt).
        """

        chemin, _filtre = QFileDialog.getSaveFileName(
            self,
            "Exporter le prompt "
            f"({LIBELLES_USAGES[self.usage]})",
            (
                LIBELLES_USAGES[self.usage].lower()
                + ".md"
            ),
            FILTRE_FICHIERS,
        )

        if not chemin:
            return

        try:

            with open(
                chemin,
                "w",
                encoding="utf-8",
                newline="\n"
            ) as fichier:
                fichier.write(
                    self.prompt_edit.toPlainText()
                )

        except OSError as e:
            QMessageBox.critical(
                self,
                "Export impossible",
                f"Écriture impossible ({chemin}) : {e}"
            )

    # ------------------------------------------------------------
    # Actions du mode étude.
    # ------------------------------------------------------------

    def recharger_depuis_bibliotheque(self):
        """
        Remplace le texte de l'éditeur par le prompt
        de la bibliothèque (confirmation ; la copie
        locale ne change qu'à « Enregistrer »).
        """

        usage = self.usage

        biblio, _personnalise = lire_bibliotheque(
            usage,
            self._dossier_prompts
        )

        if hash_prompt(biblio) == hash_prompt(
            self.prompt_edit.toPlainText()
        ):
            QMessageBox.information(
                self,
                "Déjà identiques",
                "L'éditeur contient déjà le texte de "
                "la bibliothèque "
                f"({hash_prompt(biblio) or '—'})."
            )

            return

        reponse = QMessageBox.question(
            self,
            "Recharger depuis la bibliothèque",
            "Remplacer le texte de l'éditeur par le "
            f"prompt de la bibliothèque "
            f"« {LIBELLES_USAGES[usage]} » ?\n\n"
            "La copie locale de l'étude ne change "
            "qu'après « Enregistrer ».",
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if reponse != (
            QMessageBox.StandardButton.Yes
        ):
            return

        self.prompt_edit.setPlainText(biblio)

    def promulguer(self):
        """
        Écrit le texte de l'éditeur dans le fichier
        de bibliothèque de l'usage courant
        (confirmation ; aucune étude n'est
        touchée — invariant 4).
        """

        usage = self.usage

        chemin = chemin_bibliotheque(
            usage,
            self._dossier_prompts
        )

        reponse = QMessageBox.question(
            self,
            "Promulguer dans la bibliothèque",
            "Écrire le texte de l'éditeur dans la "
            "bibliothèque ?\n\n"
            f"Fichier : {chemin}\n\n"
            "Les défauts embarqués et les autres "
            "études ne sont jamais touchés.",
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if reponse != (
            QMessageBox.StandardButton.Yes
        ):
            return

        ecrire_bibliotheque(
            usage,
            self.prompt_edit.toPlainText(),
            self._dossier_prompts
        )

        self.maj_indicateurs()


class GestionPromptsDialog(QDialog):
    """
    Gestionnaire de prompts : le panneau d'édition
    (bibliothèque ou étude) avec Enregistrer /
    Annuler.

    Depuis la page Reformulation et la page
    Résumé, le bouton « ⚙ Prompts » l'ouvre en
    MODE ÉTUDE (usage de la page présélectionné).
    """

    def __init__(
        self,
        parent=None,
        mode: str = MODE_ETUDE,
        etude_ouverte=None,
        usage_initial: str = USAGE_REFORMULATION,
        dossier_prompts=None
    ):
        super().__init__(parent)

        if mode == MODE_ETUDE:

            titre = "Prompts de l'étude"

            if etude_ouverte is not None:
                titre += (
                    " — "
                    + etude_ouverte.etude.titre
                )

        else:
            titre = "Bibliothèque de prompts"

        self.setWindowTitle(titre)

        self.resize(720, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        self.panneau = PanneauGestionPrompts(
            self,
            mode=mode,
            etude_ouverte=etude_ouverte,
            usage_initial=usage_initial,
            dossier_prompts=dossier_prompts,
        )

        layout.addWidget(self.panneau, stretch=1)

        boutons = QHBoxLayout()
        boutons.addStretch()

        self.annuler_button = QPushButton("Annuler")
        self.annuler_button.clicked.connect(self.reject)

        self.enregistrer_button = QPushButton(
            "Enregistrer"
        )
        self.enregistrer_button.clicked.connect(
            self.enregistrer
        )

        boutons.addWidget(self.annuler_button)
        boutons.addWidget(self.enregistrer_button)

        layout.addLayout(boutons)

    def enregistrer(self):

        self.panneau.enregistrer()

        self.accept()
