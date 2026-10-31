# ui/ouvrage_window.py
"""
Page Ouvrage — P19.2/P19.3 (feuille de route
v2.1 §P19, maquette validée 2026-10-29) :
l'assemblage, l'édition et l'export final de
l'ouvrage se font ici, sur le document dérivé
P19.1 (services/ouvrage_document.py).

TROIS ZONES :

- à GAUCHE, l'arborescence à la Word (largeur
  réglable) : chapitres (Titre 1, ajoutés
  MANUELLEMENT — l'enchaînement des réunions ne
  suit pas les chapitres), sous-titres,
  paragraphes avec leur réunion source (R1, R2…)
  et les réunions non placées en « Réserves » ;
- au CENTRE, le manuscrit compilé ÉDITABLE :
  titres, sous-titres, séparateurs et
  paragraphes (avec leur provenance) ;
- à DROITE, le rapport : état de la génération,
  signalements « réunion re-reformulée depuis
  la génération », réunions non placées
  (l'analyse de cohérence et la re-vérification
  des versets arrivent avec P20).

Le document ouvrage vit sa PROPRENE vie :
régénérer ÉCRASE tout (avertissement), jamais de
mise à jour automatique incrémentale. L'export
final P18.3 (assemblage des textes validés à la
volée) reste accessible à côté de l'export du
document édité.
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import Qt, QUrl

from models.ouvrage import (
    TYPE_PARAGRAPHE,
    TYPE_SEPARATEUR,
    TYPE_SOUS_TITRE,
    TYPE_TITRE_1,
)
from services.etude_io import EtudeOuverte
from services.help import open_user_manual
from services.ouvrage_document import (
    charger_ouvrage,
    generer_document,
    reformulees_depuis_generation,
    reunions_non_placees,
    sauvegarder_ouvrage,
)
from services.settings import SettingsManager


class OuvrageWindow(QWidget):
    """
    Page Ouvrage d'une étude : arborescence,
    manuscrit éditable, rapport — sur le document
    dérivé P19.1 (ouvrage.json), plus l'export
    final (P18.3).
    """

    def __init__(
        self,
        etude: EtudeOuverte,
        settings=None
    ):
        super().__init__()

        self.etude = etude

        self.settings = (
            settings
            if settings is not None
            else SettingsManager()
        )

        self.document = None
        self.modifie = False

        self.editeurs = {}

        try:
            self.document = charger_ouvrage(
                self.etude.dossier
            )
        except Exception as e:

            self.document = None

            QMessageBox.warning(
                self,
                "Ouvrage illisible",
                (
                    "Le document ouvrage de cette étude "
                    "n'a pas pu être lu :\\n\\n"
                    + str(e)
                    + "\\n\\n"
                    "Il peut être régénéré depuis les "
                    "textes validés (l'opération "
                    "écrase le document existant)."
                )
            )

        self.build_ui()

        self._reconstruire_zones()

    # ==================================================
    # Construction de l'interface.
    # ==================================================

    def build_ui(self):

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(8)

        #
        # Ruban (même langage que la page Réunion).
        #
        ruban = QWidget()
        ruban.setObjectName("ruban_ouvrage")

        ruban_layout = QHBoxLayout(ruban)
        ruban_layout.setContentsMargins(0, 0, 0, 0)
        ruban_layout.setSpacing(10)

        self.titre_label = QLabel(
            "Ouvrage — "
            + (
                self.etude.etude.titre
                or "Étude"
            )
        )

        self.titre_label.setStyleSheet(
            "font-size: 18px; font-weight: 600;"
        )

        ruban_layout.addWidget(self.titre_label)
        ruban_layout.addStretch()

        self.etude_button = QPushButton(
            "Gestion de l'étude"
        )
        self.etude_button.setToolTip(
            "Ouvrir la page Étude (réunions, "
            "synthèse, paramètres de l'étude)"
        )
        self.etude_button.clicked.connect(
            self.ouvrir_etude
        )

        self.accueil_button = QPushButton(
            "Accueil"
        )
        self.accueil_button.clicked.connect(
            self.ouvrir_accueil
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
            self.etude_button,
            self.accueil_button,
            self.parametres_button,
            self.aide_button,
        ):
            ruban_layout.addWidget(bouton)

        layout.addWidget(ruban)

        #
        # Barre d'actions de l'ouvrage : générer /
        # régénérer, structure manuelle,
        # sauvegarde, export.
        #
        actions = QHBoxLayout()
        actions.setSpacing(8)

        self.generer_button = QPushButton(
            "⚡ Générer l'ouvrage"
        )
        self.generer_button.setToolTip(
            "Initialise le document ouvrage depuis "
            "les reformulations validées de "
            "l'étude, dans l'ordre d'ouvrage de "
            "chaque réunion (chaque paragraphe "
            "conserve sa provenance)"
        )
        self.generer_button.clicked.connect(
            self.generer_ouvrage
        )

        self.chapitre_button = QPushButton(
            "＋ Chapitre"
        )
        self.chapitre_button.setToolTip(
            "Ajouter un titre de chapitre avant "
            "l'élément sélectionné dans "
            "l'arborescence (ou au début) — "
            "les chapitres sont ajoutés "
            "manuellement"
        )
        self.chapitre_button.clicked.connect(
            lambda: self._ajouter_element(
                TYPE_TITRE_1,
                "Nouveau chapitre",
            )
        )

        self.sous_titre_button = QPushButton(
            "＋ Sous-titre"
        )
        self.sous_titre_button.setToolTip(
            "Ajouter un sous-titre thématique avant "
            "l'élément sélectionné"
        )
        self.sous_titre_button.clicked.connect(
            lambda: self._ajouter_element(
                TYPE_SOUS_TITRE,
                "Nouveau sous-titre",
            )
        )

        self.separateur_button = QPushButton(
            "＋ Séparateur"
        )
        self.separateur_button.setToolTip(
            "Ajouter un séparateur de section avant "
            "l'élément sélectionné"
        )
        self.separateur_button.clicked.connect(
            lambda: self._ajouter_element(
                TYPE_SEPARATEUR,
                "",
            )
        )

        self.sauvegarder_button = QPushButton(
            "💾 Sauvegarder"
        )
        self.sauvegarder_button.setToolTip(
            "Écrire le document ouvrage dans "
            "l'étude (ouvrage.json)"
        )
        self.sauvegarder_button.clicked.connect(
            self.sauvegarder_document
        )

        self.exporter_button = QPushButton(
            "📤 Exporter l'ouvrage…"
        )
        self.exporter_button.setToolTip(
            "Assembler les textes validés (résumés "
            "en tête de section, reformulations "
            "dans l'ordre d'ouvrage) et exporter "
            "en document Word ou texte — export "
            "final de l'étude (P18.3)"
        )
        self.exporter_button.clicked.connect(
            self.exporter_ouvrage
        )

        for bouton in (
            self.generer_button,
            self.chapitre_button,
            self.sous_titre_button,
            self.separateur_button,
            self.sauvegarder_button,
            self.exporter_button,
        ):
            actions.addWidget(bouton)

        actions.addStretch()

        layout.addLayout(actions)

        #
        # Trois zones (maquette validée) :
        # arborescence | manuscrit | rapport.
        #
        split = QSplitter(
            Qt.Orientation.Horizontal
        )

        split.addWidget(
            self._construire_zone_arborescence()
        )

        split.addWidget(
            self._construire_zone_manuscrit()
        )

        split.addWidget(
            self._construire_zone_rapport()
        )

        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setStretchFactor(2, 0)

        split.setSizes([260, 700, 260])

        layout.addWidget(split, stretch=1)

        self._maj_outils()

    def _construire_zone_arborescence(self) -> QWidget:
        """
        Zone GAUCHE : arborescence à la Word —
        chapitres, sous-titres, paragraphes avec
        leur réunion source, et les réunions non
        placées en « Réserves ».
        """

        zone = QWidget()

        colonne = QVBoxLayout(zone)
        colonne.setContentsMargins(0, 0, 0, 0)
        colonne.setSpacing(4)

        entete = QLabel("Structure")
        entete.setStyleSheet(
            "font-weight: 600;"
        )

        colonne.addWidget(entete)

        self.arbre = QTreeWidget()
        self.arbre.setHeaderHidden(True)
        self.arbre.setAnimated(True)

        self.arbre.itemClicked.connect(
            self._sur_clic_arbre
        )

        colonne.addWidget(self.arbre, stretch=1)

        return zone

    def _construire_zone_manuscrit(self) -> QWidget:
        """
        Zone CENTRE : le manuscrit compilé,
        ÉDITABLE — titres, sous-titres,
        séparateurs, paragraphes avec leur
        provenance.
        """

        zone = QWidget()

        colonne = QVBoxLayout(zone)
        colonne.setContentsMargins(0, 0, 0, 0)
        colonne.setSpacing(4)

        entete = QLabel("Manuscrit")
        entete.setStyleSheet(
            "font-weight: 600;"
        )

        colonne.addWidget(entete)

        self.manuscrit_defile = QScrollArea()
        self.manuscrit_defile.setWidgetResizable(
            True
        )

        self.manuscrit_defile.setFrameShape(
            QScrollArea.Shape.NoFrame
        )

        self.manuscrit_conteneur = QWidget()

        self.manuscrit_layout = QVBoxLayout(
            self.manuscrit_conteneur
        )

        self.manuscrit_layout.setContentsMargins(
            6, 6, 6, 6
        )

        self.manuscrit_layout.setSpacing(10)

        self.manuscrit_layout.addStretch()

        self.manuscrit_defile.setWidget(
            self.manuscrit_conteneur
        )

        colonne.addWidget(
            self.manuscrit_defile,
            stretch=1
        )

        return zone

    def _construire_zone_rapport(self) -> QWidget:
        """
        Zone DROITE : rapport — état de la
        génération, signalements de divergence,
        réunions non placées ; l'analyse de
        cohérence et la re-vérification des
        versets arrivent avec P20.
        """

        zone = QWidget()

        colonne = QVBoxLayout(zone)
        colonne.setContentsMargins(0, 0, 0, 0)
        colonne.setSpacing(4)

        entete = QLabel("Rapport")
        entete.setStyleSheet(
            "font-weight: 600;"
        )

        colonne.addWidget(entete)

        self.rapport_zone = QPlainTextEdit()
        self.rapport_zone.setReadOnly(True)

        colonne.addWidget(
            self.rapport_zone,
            stretch=1
        )

        self.rapport_note = QLabel(
            "Analyse de cohérence et "
            "re-vérification des versets : "
            "série P20."
        )

        self.rapport_note.setWordWrap(True)
        self.rapport_note.setStyleSheet(
            "color: #8a8b92; font-size: 11px;"
        )

        colonne.addWidget(self.rapport_note)

        return zone

    # ==================================================
    # Reconstruction des zones depuis le document.
    # ==================================================

    def _reconstruire_zones(self):
        """
        Reconstruit l'arborescence, le manuscrit
        et le rapport depuis le document courant.
        """

        self._reconstruire_manuscrit()
        self._reconstruire_arborescence()
        self._reconstruire_rapport()
        self._maj_outils()

    def _reconstruire_manuscrit(self):
        """
        Le manuscrit : un éditeur par élément —
        titres et sous-titres éditables en place,
        séparateur discret, paragraphe éditable
        avec sa provenance dessous.
        """

        while self.manuscrit_layout.count() > 1:

            item = self.manuscrit_layout.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        self.editeurs = {}

        if self.document is None:
            return

        for element in self.document.elements:

            if (
                element.type == TYPE_TITRE_1
                or element.type
                == TYPE_SOUS_TITRE
            ):

                editeur = self._editeur_titre(
                    element
                )

            elif element.type == TYPE_SEPARATEUR:

                editeur = self._editeur_separateur(
                    element
                )

            else:

                editeur = self._editeur_paragraphe(
                    element
                )

            self.manuscrit_layout.addWidget(
                editeur
            )

            self.editeurs[element.id] = editeur

        self.manuscrit_layout.addStretch()

    def _editeur_titre(self, element) -> QWidget:
        """
        Titre (chapitre) ou sous-titre : édité en
        place — chapitre en 16 px gras,
        sous-titre en 13 px.
        """

        editeur = QLineEdit(element.texte)

        if element.type == TYPE_TITRE_1:
            editeur.setStyleSheet(
                "font-size: 16px; font-weight: 600;"
                "border: none;"
                "background: transparent;"
            )
        else:
            editeur.setStyleSheet(
                "font-size: 13px; font-weight: 600;"
                "border: none;"
                "background: transparent;"
            )

        editeur.textChanged.connect(
            lambda texte, e=element: (
                self._sur_texte_element(e, texte)
            )
        )

        editeur.element_id = element.id

        return editeur

    def _editeur_separateur(
        self,
        element
    ) -> QWidget:
        """
        Séparateur de section : filet discret, non
        éditable.
        """

        filet = QFrame()
        filet.setFrameShape(
            QFrame.Shape.HLine
        )

        filet.setStyleSheet(
            "color: #8a8b92;"
        )

        filet.element_id = element.id

        return filet

    def _editeur_paragraphe(self, element) -> QWidget:
        """
        Paragraphe : texte éditable, provenance en
        dessous (réunion source, date, FID —
        métadonnées NON structurelles).
        """

        bloc = QWidget()

        colonne = QVBoxLayout(bloc)
        colonne.setContentsMargins(0, 0, 0, 0)
        colonne.setSpacing(2)

        editeur = QTextEdit(element.texte)
        editeur.setAcceptRichText(False)

        editeur.setTabChangesFocus(True)

        editeur.textChanged.connect(
            lambda e=element,
            t=editeur: (
                self._sur_texte_element(
                    e,
                    t.toPlainText()
                )
            )
        )

        editeur.textChanged.connect(
            lambda t=editeur: (
                self._ajuster_hauteur_editeur(t)
            )
        )

        colonne.addWidget(editeur)

        provenances = []

        for p in element.provenances:

            morceau = (
                f"R{p.numero_reunion}"
                if p.numero_reunion
                else p.reunion
            )

            if p.date_reunion:
                morceau += f" · {p.date_reunion}"

            if p.fid:
                morceau += f" · bloc {p.fid}"

            provenances.append(morceau)

        provenance_label = QLabel(
            " — ".join(provenances)
        )

        provenance_label.setStyleSheet(
            "color: #8a8b92; font-size: 11px;"
        )

        colonne.addWidget(provenance_label)

        bloc.element_id = element.id

        return bloc

    def _ajuster_hauteur_editeur(self, editeur):
        """
        Hauteur du paragraphe = son contenu (pas de
        défilement interne).
        """

        hauteur = int(
            editeur.document()
            .size()
            .height()
        ) + 12

        editeur.setFixedHeight(hauteur)

    # ==================================================
    # Arborescence.
    # ==================================================

    def _reconstruire_arborescence(self):
        """
        L'arborescence : chapitres avec leurs
        sous-titres et paragraphes (réunion source
        R1, R2…), et les paragraphes non placés
        sous « Réserves ».
        """

        self.arbre.clear()

        if self.document is None:
            return

        chapitre_courant = None
        sous_titre_courant = None

        for element in self.document.elements:

            if element.type == TYPE_TITRE_1:

                chapitre_courant = (
                    QTreeWidgetItem(
                        [element.texte or "Chapitre"]
                    )
                )

                self._gras(chapitre_courant)

                chapitre_courant.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    element.id,
                )

                self.arbre.addTopLevelItem(
                    chapitre_courant
                )

                sous_titre_courant = None

                continue

            if element.type == TYPE_SOUS_TITRE:

                parent = (
                    sous_titre_courant
                    or chapitre_courant
                )

                if parent is None:
                    continue

                sous_titre_courant = (
                    QTreeWidgetItem(
                        [element.texte or "Sous-titre"]
                    )
                )

                sous_titre_courant.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    element.id,
                )

                parent.addChild(
                    sous_titre_courant
                )

                continue

            if element.type != TYPE_PARAGRAPHE:
                continue

            extrait = (
                (element.texte or "")[:60].strip()
                or "Paragraphe"
            )

            numero = (
                element.provenances[0].numero_reunion
                if element.provenances
                else 0
            )

            libelle = (
                f"R{numero} — {extrait}"
                if numero
                else extrait
            )

            item = QTreeWidgetItem([libelle])

            item.setData(
                0,
                Qt.ItemDataRole.UserRole,
                element.id,
            )

            parent = (
                sous_titre_courant
                or chapitre_courant
            )

            if parent is not None:
                parent.addChild(item)

        #
        # Réserves : les paragraphes non placés
        # (avant le premier chapitre).
        #
        reserves = (
            self.document.paragraphes_reserves()
        )

        if reserves:

            noeud = QTreeWidgetItem(
                ["Réserves"]
            )

            self._gras(noeud)

            for element in reserves:

                extrait = (
                    (element.texte or "")[:60].strip()
                    or "Paragraphe"
                )

                numero = (
                    element.provenances[0]
                    .numero_reunion
                    if element.provenances
                    else 0
                )

                libelle = (
                    f"R{numero} — {extrait}"
                    if numero
                    else extrait
                )

                item = QTreeWidgetItem([libelle])

                item.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    element.id,
                )

                noeud.addChild(item)

            self.arbre.addTopLevelItem(noeud)

        self.arbre.expandAll()

    @staticmethod
    def _gras(item):
        """
        Met un élément d'arborescence en gras
        (chapitre, Réserves).
        """

        from PySide6.QtGui import QFont

        police = item.font(0)
        police.setBold(True)
        item.setFont(0, police)

    def _sur_clic_arbre(self, item):
        """
        Navigation par structure : le clic amène le
        manuscrit à l'élément correspondant.
        """

        identifiant = item.data(
            0,
            Qt.ItemDataRole.UserRole
        )

        if not identifiant:
            return

        editeur = self.editeurs.get(identifiant)

        if editeur is not None:

            self.manuscrit_defile.ensureWidgetVisible(
                editeur
            )

            editeur.setFocus()

    # ==================================================
    # Rapport.
    # ==================================================

    def _reconstruire_rapport(self):
        """
        Le rapport : état de la génération,
        signalements « réunion re-reformulée depuis
        la génération », réunions non placées.
        """

        if self.document is None:

            self.rapport_zone.setPlainText(
                "Aucun ouvrage généré.\n\n"
                "« Générer l'ouvrage » initialise le "
                "document depuis les reformulations "
                "validées de l'étude."
            )

            return

        lignes = []

        generation = (
            self.document.generation or {}
        )

        horodatage = generation.get(
            "horodatage"
        )

        paragraphes = (
            len(self.document.paragraphes())
        )

        chapitres = [
            e for e in self.document.elements
            if e.type == TYPE_TITRE_1
        ]

        lignes.append(
            "Ouvrage généré le "
            + (horodatage or "?")
        )

        lignes.append(
            f"{paragraphes} paragraphe(s) · "
            f"{len(chapitres)} chapitre(s)"
        )

        #
        # Signalements de divergence (le document
        # dérivé n'est JAMAIS mis à jour
        # automatiquement).
        #
        divergences = (
            reformulees_depuis_generation(
                self.document,
                self.etude
            )
        )

        if divergences:

            lignes.append("")
            lignes.append(
                "Re-reformulé depuis la génération :"
            )

            for d in divergences:

                lignes.append(
                    f"· R{d['reunion'][:24]} — "
                    f"bloc {d['fid']} "
                    f"(v{d['version_courante']} > "
                    f"v{d['version_generation']})"
                )

        non_placees = reunions_non_placees(
            self.document,
            self.etude
        )

        if non_placees:

            lignes.append("")
            lignes.append("Non placées (Réserves) :")

            for nom in non_placees:
                lignes.append("· " + nom)

        self.rapport_zone.setPlainText(
            "\n".join(lignes)
        )

    # ==================================================
    # Actions.
    # ==================================================

    def _maj_outils(self):
        """
        Active les outils selon la présence du
        document (générer vs régénérer, structure,
        sauvegarde) et l'état modifié.
        """

        avec_document = self.document is not None

        self.generer_button.setText(
            "⟳ Régénérer…"
            if avec_document
            else "⚡ Générer l'ouvrage"
        )

        for bouton in (
            self.chapitre_button,
            self.sous_titre_button,
            self.separateur_button,
        ):
            bouton.setEnabled(avec_document)

        self.sauvegarder_button.setEnabled(
            avec_document and self.modifie
        )

    def generer_ouvrage(self):
        """
        P19.3 : génère — ou RÉGÉNÈRE, opération qui
        ÉCRASE le document existant (avertissement
        explicite ; jamais de mise à jour
        incrémentale).
        """

        if self.document is not None:

            reponse = QMessageBox.warning(
                self,
                "Régénérer l'ouvrage ?",
                (
                    "Régénérer ÉCRASE le document "
                    "ouvrage actuel : chapitres, "
                    "sous-titres, séparateurs et "
                    "éditions disparaissent — seuls "
                    "les textes validés de l'étude "
                    "sont réimportés.\n\n"
                    "Continuer ?"
                ),
                (
                    QMessageBox.StandardButton.Yes
                    | QMessageBox
                    .StandardButton.No
                ),
                (
                    QMessageBox
                    .StandardButton.No
                ),
            )

            if reponse != (
                QMessageBox.StandardButton.Yes
            ):
                return

        self.document = generer_document(
            self.etude
        )

        sauvegarder_ouvrage(
            self.document,
            self.etude.dossier
        )

        self.modifie = False

        self._reconstruire_zones()

    def _ajouter_element(self, type_element, texte):
        """
        Ajoute un élément de structure AVANT
        l'élément sélectionné dans l'arborescence
        (au début si rien n'est sélectionné) —
        les chapitres sont ajoutés MANUELLEMENT.
        """

        from models.ouvrage import (
            ElementOuvrage,
        )

        prefixes = {
            TYPE_TITRE_1: "t1",
            TYPE_SOUS_TITRE: "st",
            TYPE_SEPARATEUR: "sep",
        }

        element = ElementOuvrage(
            id=self.document.nouvel_id(
                prefixes[type_element]
            ),
            type=type_element,
            texte=texte,
        )

        position = self._position_selection()

        self.document.elements.insert(
            position,
            element
        )

        self.modifie = True

        self._reconstruire_zones()

    def _position_selection(self) -> int:
        """
        Index d'insertion : avant l'élément
        sélectionné dans l'arborescence (son id →
        position dans le document), au début si
        rien n'est sélectionné.
        """

        item = self.arbre.currentItem()

        if item is None:
            return 0

        identifiant = item.data(
            0,
            Qt.ItemDataRole.UserRole
        )

        if not identifiant:
            return 0

        for index, element in enumerate(
            self.document.elements
        ):

            if element.id == identifiant:
                return index

        return 0

    def _sur_texte_element(self, element, texte):
        """
        Édition en place : le texte de l'élément du
        document suit l'éditeur (l'ouvrage vit sa
        propre vie — il diverge des textes validés).
        """

        if element.texte == texte:
            return

        element.texte = texte

        self.modifie = True

        self.sauvegarder_button.setEnabled(True)

    def sauvegarder_document(self):
        """
        Écrit le document dans l'étude (ouvrage.json)
        — le dossier reste autonome et portable.
        """

        if self.document is None:
            return

        sauvegarder_ouvrage(
            self.document,
            self.etude.dossier
        )

        self.modifie = False

        self._maj_outils()

    # ==================================================
    # Navigation.
    # ==================================================

    def ouvrir_etude(self):

        navigation = getattr(
            self,
            "navigation",
            None
        )

        if navigation is not None:
            navigation.ouvrir_etude(
                self.etude.dossier
            )

    def ouvrir_accueil(self):

        navigation = getattr(
            self,
            "navigation",
            None
        )

        if navigation is not None:
            navigation.ouvrir_accueil()

    def ouvrir_parametres(self):

        from ui.settings_dialog import SettingsDialog

        dialogue = SettingsDialog(
            self,
            settings=self.settings
        )

        if dialogue.exec():
            self.settings.load()

    # ==================================================
    # Export final (P18.3).
    # ==================================================

    def exporter_ouvrage(self):
        """
        « Exporter… » : assemble les textes validés
        (résumés en tête de section si souhaité,
        reformulations dans l'ordre d'ouvrage) et
        exporte en DOCX (ou TXT). Flux P13 : message
        de fin avec ouverture du fichier ou du
        dossier.
        """

        import re as _re

        from services.export_ouvrage import (
            assembler_ouvrage,
            exporter_docx,
            exporter_txt,
        )

        apercu = assembler_ouvrage(
            self.etude,
            inclure_resumes=True,
            en_tetes_reunions=True
        )

        if not apercu["reunions"]:

            QMessageBox.information(
                self,
                "Rien à exporter",
                (
                    "Aucun texte validé dans l'étude : "
                    "validez des reformulations (ou un "
                    "résumé) avant d'exporter l'ouvrage."
                )
            )

            return

        dialogue = QDialog(self)
        dialogue.setWindowTitle("Exporter l'ouvrage")

        options = QVBoxLayout(dialogue)

        resumes_check = QCheckBox(
            "Inclure les résumés validés "
            "en tête de section"
        )
        resumes_check.setChecked(True)

        tetes_check = QCheckBox(
            "Titres de réunion"
        )
        tetes_check.setChecked(True)

        options.addWidget(resumes_check)
        options.addWidget(tetes_check)

        boutons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        boutons.accepted.connect(dialogue.accept)
        boutons.rejected.connect(dialogue.reject)

        options.addWidget(boutons)

        if dialogue.exec() != (
            QDialog.DialogCode.Accepted
        ):
            return

        nom_defaut = _re.sub(
            r"[^\w\- ]",
            "",
            apercu["titre"]
        ).strip() or "ouvrage"

        chemin, filtre = QFileDialog.getSaveFileName(
            self,
            "Exporter l'ouvrage",
            str(
                self.etude.dossier
                / f"{nom_defaut}.docx"
            ),
            "Document Word (*.docx);;"
            "Texte (*.txt)"
        )

        if not chemin:
            return

        ouvrage = assembler_ouvrage(
            self.etude,
            inclure_resumes=(
                resumes_check.isChecked()
            ),
            en_tetes_reunions=(
                tetes_check.isChecked()
            )
        )

        try:

            if filtre.startswith("Document"):
                chemin = exporter_docx(
                    ouvrage,
                    chemin
                )
            else:
                chemin = exporter_txt(
                    ouvrage,
                    chemin
                )

        except Exception as e:

            QMessageBox.critical(
                self,
                "Export impossible",
                str(e)
            )

            return

        message = QMessageBox(self)
        message.setWindowTitle("Ouvrage exporté")
        message.setText(
            f"L'ouvrage a été exporté :\n\n{chemin}"
        )

        open_file_button = message.addButton(
            "Ouvrir le fichier",
            QMessageBox.ButtonRole.AcceptRole
        )

        open_folder_button = message.addButton(
            "Ouvrir le dossier",
            QMessageBox.ButtonRole.AcceptRole
        )

        message.addButton(
            "Fermer",
            QMessageBox.ButtonRole.RejectRole
        )

        message.exec()

        clicked = message.clickedButton()

        if clicked is open_file_button:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(chemin))
            )

        elif clicked is open_folder_button:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(
                    str(Path(chemin).parent)
                )
            )
