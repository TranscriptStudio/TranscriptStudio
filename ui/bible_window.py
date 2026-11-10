# ui/bible_window.py
"""
Page Bible — lecteur de Bible intégré (P18.10,
décision David du 2026-11-09 ; spec d'autorité
BIBLE_JND_V2_2026-11-09d §7, invariants 6-9).

Page CONSULTATIVE PURE : aucun LLM, aucun coût,
aucune écriture hors les réglages de l'app (dernier
passage consulté).

- accès par une icône sur la page Réunion,
  l'éditeur de transcription et la page Ouvrage ;
  navigation à pile unique (« Retour » = page
  appelante) ;
- sélecteurs version → livre → chapitre → verset
  (facultatif, défaut v1 = cible de
  défilement/surlignage dans le chapitre affiché),
  pilotés par les données OSIS de la version
  sélectionnée (jamais de listes en dur) ;
- dernier passage consulté mémorisé dans les
  réglages de l'app et restauré à l'ouverture ;
  version par défaut = dernière version consultée ;
- saisie directe de référence (« Luc 1:5 »),
  normalisée par le parsing P18.1 ; ambiguïté →
  suggestions ; introuvable dans la version → écart
  signalé comme information ;
- aucune version installée → message + renvoi vers
  le téléchargeur des réglages.
"""

from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from services.lecteur_bible import (
    libelle_version,
    resoudre_passage_initial,
    resoudre_saisie,
    structure_version,
    texte_chapitre,
    versions_affichables,
)
from services.settings import SettingsManager


class BibleWindow(QWidget):
    """
    Lecteur de Bible intégré (page consultative).
    """

    def __init__(
        self,
        settings=None,
        dossier_bibles=None,
        parent=None
    ):
        super().__init__(parent)

        self.settings = (
            settings
            if settings is not None
            else SettingsManager()
        )

        # Dossier des Bibles injectable (tests).
        self.dossier_bibles = dossier_bibles

        self.setWindowTitle("Bible")

        self.resize(760, 640)

        self._bible = None
        self._structure = []
        self._en_cours = False

        self.passage = resoudre_passage_initial(
            self.settings,
            self.dossier_bibles
        )

        self.build_ui()

        self._remplir_versions()

        self._afficher_passage()

    # ==================================================
    # Construction.
    # ==================================================

    def build_ui(self):

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(8)

        #
        # Ruban : titre, sélecteurs, saisie directe,
        # retour.
        #
        ruban = QHBoxLayout()

        self.titre_label = QLabel("Bible")
        self.titre_label.setStyleSheet(
            "font-size: 18px; font-weight: 600;"
        )

        ruban.addWidget(self.titre_label)

        self.combo_version = QComboBox()
        self.combo_version.setToolTip(
            "Version de la Bible (versions installées)"
        )

        self.combo_livre = QComboBox()
        self.combo_livre.setToolTip("Livre")

        self.combo_chapitre = QComboBox()
        self.combo_chapitre.setToolTip("Chapitre")

        self.combo_verset = QComboBox()
        self.combo_verset.setToolTip(
            "Verset (cible de surlignage — défaut v1)"
        )

        for combo in (
            self.combo_version,
            self.combo_livre,
            self.combo_chapitre,
            self.combo_verset,
        ):
            ruban.addWidget(combo)

        self.saisie = QLineEdit()
        self.saisie.setPlaceholderText(
            "Référence directe (ex. « Luc 1:5 »)…"
        )
        self.saisie.setToolTip(
            "Saisissez une référence biblique "
            "(ex. « Luc 1:5 », « Jn 3:16 »)…"
        )
        self.saisie.returnPressed.connect(
            self.aller_saisie
        )

        self.aller_button = QPushButton("Aller")
        self.aller_button.clicked.connect(
            self.aller_saisie
        )

        ruban.addWidget(self.saisie, stretch=1)
        ruban.addWidget(self.aller_button)

        self.retour_button = QPushButton("← Retour")
        self.retour_button.setToolTip(
            "Retour à la page appelante"
        )
        self.retour_button.clicked.connect(
            self.retour
        )

        ruban.addWidget(self.retour_button)

        layout.addLayout(ruban)

        #
        # Aucune version installée : message + renvoi
        # vers le téléchargeur des réglages (§7.6).
        #
        self.avertissement_label = QLabel("")
        self.avertissement_label.setWordWrap(True)
        self.avertissement_label.setStyleSheet(
            "color: #b35900;"
        )

        layout.addWidget(self.avertissement_label)

        self.telechargeur_button = QPushButton(
            "Ouvrir le téléchargeur de Bibles…"
        )
        self.telechargeur_button.setToolTip(
            "Ouvrir les réglages de l'application, "
            "onglet « Bibles » (téléchargeur intégré)"
        )
        self.telechargeur_button.clicked.connect(
            self.ouvrir_telechargeur
        )
        self.telechargeur_button.setVisible(False)

        layout.addWidget(self.telechargeur_button)

        #
        # Sélecteurs : cascades.
        #
        self.combo_version.currentIndexChanged.connect(
            self._sur_version
        )
        self.combo_livre.currentIndexChanged.connect(
            self._sur_livre
        )
        self.combo_chapitre.currentIndexChanged.connect(
            self._sur_chapitre
        )
        self.combo_verset.currentIndexChanged.connect(
            self._sur_verset
        )

        #
        # Texte du chapitre affiché.
        #
        self.texte = QTextBrowser()
        self.texte.setOpenLinks(False)

        layout.addWidget(self.texte, stretch=1)

        self.statut_label = QLabel("")
        self.statut_label.setWordWrap(True)
        self.statut_label.setStyleSheet(
            "font-size: 12px; color: #757575;"
        )

        layout.addWidget(self.statut_label)

    # ==================================================
    # Remplissage des sélecteurs (données OSIS).
    # ==================================================

    def _remplir_versions(self):

        self._en_cours = True

        try:

            self.combo_version.clear()

            installes = versions_affichables(
                self.dossier_bibles
            )

            for identifiant in installes:

                self.combo_version.addItem(
                    libelle_version(identifiant),
                    identifiant
                )

            if not installes:

                self.avertissement_label.setText(
                    "Aucune version de la Bible n'est "
                    "installée : utilisez le "
                    "téléchargeur des réglages de "
                    "l'application (onglet « Bibles »)."
                )

                self.telechargeur_button.setVisible(True)

            else:

                self.avertissement_label.setText("")

                self.telechargeur_button.setVisible(
                    False
                )

            # Version par défaut = dernière version
            # consultée (mémorisée), sinon darbyR.
            version = self.passage["version"]

            index = self.combo_version.findData(
                version
            )

            if index < 0:
                index = 0

            self.combo_version.setCurrentIndex(index)

            self._remplir_livres()

        finally:

            self._en_cours = False

    def _remplir_livres(self):

        self._en_cours = True

        try:

            self.combo_livre.clear()

            version = (
                self.combo_version.currentData()
            )

            self._structure = structure_version(
                version,
                self.dossier_bibles
            )

            self._bible = (
                self.passage["bible"]
                if self.passage["version"] == version
                else None
            )

            from services.lecteur_bible import (
                charger_version,
            )

            self._bible = charger_version(
                version,
                self.dossier_bibles
            )

            for livre in self._structure:

                self.combo_livre.addItem(
                    livre["nom"],
                    livre["osis_id"]
                )

            # Livre mémorisé (index 1-based / osis).
            cible = self.passage["livre_osis"]

            index = self.combo_livre.findData(cible)

            if index < 0:
                index = max(
                    0,
                    min(
                        self.passage["livre"] - 1,
                        self.combo_livre.count() - 1
                    )
                )

            self.combo_livre.setCurrentIndex(index)

            self._remplir_chapitres()

        finally:

            self._en_cours = False

    def _remplir_chapitres(self):

        self._en_cours = True

        try:

            self.combo_chapitre.clear()

            osis_id = self.combo_livre.currentData()

            livre = next(
                (
                    l for l in self._structure
                    if l["osis_id"] == osis_id
                ),
                None
            )

            if livre is None:
                self._remplir_versets()
                return

            for chapitre in livre["chapitres"]:

                self.combo_chapitre.addItem(
                    f"{chapitre['numero']}",
                    chapitre["numero"]
                )

            index = max(
                0,
                min(
                    self.passage["chapitre"] - 1,
                    self.combo_chapitre.count() - 1
                )
            )

            self.combo_chapitre.setCurrentIndex(index)

            self._remplir_versets()

        finally:

            self._en_cours = False

    def _remplir_versets(self):

        self._en_cours = True

        try:

            self.combo_verset.clear()

            chapitre = self._chapitre_courant()

            nb = (
                chapitre["nb_versets"]
                if chapitre is not None
                else 1
            )

            for numero in range(1, nb + 1):

                self.combo_verset.addItem(
                    f"v{numero}",
                    numero
                )

            index = max(
                0,
                min(
                    self.passage["verset"] - 1,
                    self.combo_verset.count() - 1
                )
            )

            self.combo_verset.setCurrentIndex(index)

        finally:

            self._en_cours = False

    def _chapitre_courant(self):

        osis_id = self.combo_livre.currentData()
        numero = self.combo_chapitre.currentData()

        if osis_id is None or numero is None:
            return None

        for livre in self._structure:

            if livre["osis_id"] == osis_id:

                for chapitre in livre["chapitres"]:

                    if (
                        chapitre["numero"]
                        == numero
                    ):
                        return chapitre

        return None

    # ==================================================
    # Affichage.
    # ==================================================

    def _afficher_passage(self):

        version = self.combo_version.currentData()

        if version is None:
            self.texte.setHtml(
                "<p>Aucune version installée.</p>"
            )
            return

        osis_id = self.combo_livre.currentData()
        chapitre = self.combo_chapitre.currentData()
        verset = (
            self.combo_verset.currentData() or 1
        )

        if osis_id is None or chapitre is None:
            return

        if self._bible is None:

            from services.lecteur_bible import (
                charger_version,
            )

            self._bible = charger_version(
                version,
                self.dossier_bibles
            )

        donnees = texte_chapitre(
            self._bible,
            osis_id,
            chapitre
        )

        morceaux = [
            "<h3>"
            + escape(donnees["titre"])
            + "</h3>"
        ]

        for v in donnees["versets"]:

            numero = v["numero"]

            corps = (
                f'<a name="v{numero}"/>'
                f"<sup>{numero}</sup> "
                + escape(v["texte"])
            )

            if numero == verset:

                corps = (
                    '<span style="background-color: '
                    'rgba(59,158,255,60);">'
                    + corps
                    + "</span>"
                )

            morceaux.append(f"<p>{corps}</p>")

        self.dernier_html = "".join(morceaux)

        self.verset_surligne = verset

        self.texte.setHtml(self.dernier_html)

        self.texte.scrollToAnchor(f"v{verset}")

        self.statut_label.setText(
            f"{libelle_version(version)} — "
            f"{donnees['titre']}"
        )

        self._memoriser_passage()

    def _memoriser_passage(self):

        version = self.combo_version.currentData()

        if version is None:
            return

        self.settings.set_dernier_passage_bible(
            version,
            self.combo_livre.currentIndex() + 1,
            self.combo_chapitre.currentData() or 1,
            self.combo_verset.currentData() or 1,
            livre_osis=self.combo_livre.currentData(),
        )

    # ==================================================
    # Cascades des sélecteurs.
    # ==================================================

    def _sur_version(self, index):

        if self._en_cours or index < 0:
            return

        self._remplir_livres()
        self._afficher_passage()

    def _sur_livre(self, index):

        if self._en_cours or index < 0:
            return

        self._en_cours = True

        try:
            self._remplir_chapitres()
        finally:
            self._en_cours = False

        self._afficher_passage()

    def _sur_chapitre(self, index):

        if self._en_cours or index < 0:
            return

        self._en_cours = True

        try:
            self._remplir_versets()
        finally:
            self._en_cours = False

        self._afficher_passage()

    def _sur_verset(self, index):

        if self._en_cours or index < 0:
            return

        self._afficher_passage()

    # ==================================================
    # Saisie directe de référence.
    # ==================================================

    def aller_saisie(self):

        texte = self.saisie.text().strip()

        if not texte:
            return

        version = self.combo_version.currentData()

        from services.bibles import (
            autres_versions_installees,
        )

        autres = autres_versions_installees(
            version,
            self.dossier_bibles
        )

        resultat = resoudre_saisie(
            texte,
            self._bible,
            autres
        )

        if resultat["statut"] == "aucune":

            self.statut_label.setText(
                "Aucune référence reconnue dans "
                f"« {texte} »."
            )
            return

        if resultat["statut"] == "ambigu":

            suggestions = resultat["suggestions"]

            libelles = [
                str(s["reference"])
                for s in suggestions
            ]

            choix, ok = QInputDialog.getItem(
                self,
                "Plusieurs références reconnues",
                "Quelle correspondance ?",
                libelles,
                0,
                False
            )

            if not ok:
                return

            reference = suggestions[
                libelles.index(choix)
            ]["reference"]

            self._aller_reference(reference, resultat)

            return

        self._aller_reference(
            resultat["reference"],
            resultat
        )

    def _aller_reference(self, reference, resultat):

        osis_id = reference.osis_id

        index_livre = self.combo_livre.findData(osis_id)

        if index_livre < 0:

            self.statut_label.setText(
                f"{reference} : livre absent de cette "
                "version."
            )
            return

        self._en_cours = True

        try:

            self.combo_livre.setCurrentIndex(
                index_livre
            )

            self._remplir_chapitres()

            index_chapitre = (
                self.combo_chapitre.findData(
                    reference.chapitre
                )
            )

            if index_chapitre < 0:

                self.statut_label.setText(
                    f"{reference} : chapitre absent "
                    "de cette version."
                )
                return

            self.combo_chapitre.setCurrentIndex(
                index_chapitre
            )

            self._remplir_versets()

            if reference.verset_debut is not None:

                index_verset = (
                    self.combo_verset.findData(
                        reference.verset_debut
                    )
                )

                if index_verset >= 0:

                    self.combo_verset.setCurrentIndex(
                        index_verset
                    )

        finally:

            self._en_cours = False

        self._afficher_passage()

        existe = resultat.get(
            "existe",
            True
        )

        if not existe:

            ailleurs = resultat.get(
                "existe_ailleurs"
            ) or []

            from services.bibles import (
                nom_court_bible,
            )

            if ailleurs:

                self.statut_label.setText(
                    f"{reference} n'existe pas dans "
                    "cette version — elle existe dans : "
                    + ", ".join(
                        nom_court_bible(v)
                        for v in ailleurs
                    )
                    + " (écart de versification = "
                    "information)."
                )

            else:

                self.statut_label.setText(
                    f"{reference} n'existe pas dans "
                    "cette version (écart de "
                    "versification = information)."
                )

    # ==================================================
    # Navigation.
    # ==================================================

    def retour(self):
        """
        « Retour » = page appelante (pile unique,
        invariant 8).
        """

        navigation = getattr(
            self,
            "navigation",
            None
        )

        if (
            navigation is not None
            and hasattr(navigation, "retour_bible")
        ):
            navigation.retour_bible()
            return

        self.close()

    def ouvrir_telechargeur(self):
        """
        Aucune version installée : renvoi vers le
        téléchargeur des réglages (onglet « Bibles »).
        """

        from ui.settings_dialog import SettingsDialog

        dialogue = SettingsDialog(
            self,
            settings=self.settings
        )

        selecteur = getattr(
            dialogue,
            "selecter_onglet_bibles",
            None
        )

        if selecteur is not None:
            selecteur()

        dialogue.exec()
