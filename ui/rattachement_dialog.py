# ui/rattachement_dialog.py
"""
Dialogue de rattachement d'une réunion à une
étude (P18.6, spec navigation §6).

« Rattacher à une étude… » est disponible à tout
moment, dès le prétraitement, pour une réunion
autonome (hub, ruban Réunion) ou pour changer
d'étude (confirmation, option A : les
traitements restent à l'ancienne étude).

Le dialogue choisit l'étude cible parmi les
études récentes (ou un dossier au choix) ;
l'exclusivité (une réunion ∈ 0 ou 1 étude,
invariant §9.1) est vérifiée par le service de
rattachement — un conflit déclenche la
proposition de changement d'étude.
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from services.rattachement import (
    RattachementError,
    rattacher,
)


class RattachementDialog(QDialog):
    """
    Choix de l'étude cible d'une réunion, puis
    rattachement (ou changement d'étude confirmé).

    ``nom_reunion`` retourné via ``resultat()``.
    """

    def __init__(
        self,
        chemin_projet,
        settings,
        parent=None,
        etude_courante=None,
        nom_reunion_courante=None
    ):
        super().__init__(parent)

        self.chemin_projet = str(chemin_projet)
        self.settings = settings
        self.etude_courante = etude_courante
        self.nom_reunion_courante = (
            nom_reunion_courante
        )

        self._nom_retour = None

        self.setWindowTitle(
            "Rattacher la réunion à une étude"
        )

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout(self)

        etudes = (
            self.settings.cleanup_recent_etudes()
        )

        if self.etude_courante:

            titre = (
                "La réunion appartient à l'étude :"
                "\n"
                f"« {Path(self.etude_courante).name} »"
                f" (réunion « {self.nom_reunion_courante} »)"
                "\n\nChanger d'étude ? Les traitements "
                "déjà réalisés (reformulations, résumé, "
                "validations) RESTENT à l'ancienne "
                "étude — aucun déplacement, aucune "
                "copie ; la réunion change seulement "
                "de rattachement."
            )

        else:

            titre = (
                "Rattacher cette réunion à une étude ?"
                "\nUne étude regroupe des réunions "
                "ayant pour objet un thème spécifique. "
                "La réunion est référencée, jamais "
                "copiée."
            )

        layout.addWidget(QLabel(titre))

        self.liste_etudes = QListWidget()

        for dossier in etudes:

            if (
                self.etude_courante
                and str(Path(dossier).resolve())
                == str(
                    Path(self.etude_courante).resolve()
                )
            ):
                continue

            item = QListWidgetItem(
                Path(dossier).name
            )

            item.setData(
                0x0100,  # Qt.ItemDataRole.UserRole
                str(dossier)
            )

            item.setToolTip(str(dossier))

            self.liste_etudes.addItem(item)

        layout.addWidget(
            self.liste_etudes,
            stretch=1
        )

        boutons_haut = QHBoxLayout()

        self.parcourir_button = QPushButton(
            "Choisir un dossier d'étude…"
        )

        self.parcourir_button.clicked.connect(
            self.choisir_dossier
        )

        boutons_haut.addWidget(
            self.parcourir_button
        )
        boutons_haut.addStretch()

        layout.addLayout(boutons_haut)

        boutons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)

        layout.addWidget(boutons)

    def choisir_dossier(self):

        dossier = QFileDialog.getExistingDirectory(
            self,
            "Dossier de l'étude",
            self.settings.get_projects_root()
        )

        if not dossier:
            return

        if not (
            Path(dossier) / "etude.json"
        ).is_file():

            QMessageBox.warning(
                self,
                "Ce dossier n'est pas une étude",
                (
                    "Le dossier\n\n"
                    f"{dossier}\n\n"
                    "ne contient pas de etude.json : "
                    "ce n'est pas une étude."
                )
            )

            return

        for index in range(
            self.liste_etudes.count()
        ):

            item = (
                self.liste_etudes.item(index)
            )

            if item.data(0x0100) == dossier:
                self.liste_etudes.setCurrentItem(
                    item
                )
                return

        item = QListWidgetItem(
            Path(dossier).name
        )

        item.setData(0x0100, dossier)
        item.setToolTip(dossier)

        self.liste_etudes.addItem(item)
        self.liste_etudes.setCurrentItem(item)

    def etude_choisie(self):

        item = self.liste_etudes.currentItem()

        if item is None:
            return None

        return item.data(0x0100)

    def resultat(self):

        return self._nom_retour

    def accept(self):
        """
        Valide le choix : rattachement direct, ou
        changement d'étude après confirmation
        (exclusivité §9.1, option A §9.5).
        """

        from services.rattachement import (
            changer_etude,
            verifier_exclusivite,
        )

        dossier = self.etude_choisie()

        if not dossier:

            QMessageBox.information(
                self,
                "Aucune étude sélectionnée",
                (
                    "Choisissez une étude dans la "
                    "liste, ou « Choisir un dossier "
                    "d'étude… »."
                )
            )

            return

        etudes_connues = (
            self.settings.cleanup_recent_etudes()
        )

        conflit = verifier_exclusivite(
            self.chemin_projet,
            etudes_connues,
            dossier_exclu=dossier
        )

        if conflit is not None:

            reponse = QMessageBox.question(
                self,
                "Changement d'étude",
                (
                    "Cette réunion appartient déjà "
                    f"à l'étude « {Path(conflit[0]).name} » "
                    "(une réunion appartient à une "
                    "seule étude).\n\n"
                    "La délier et la rattacher à "
                    f"« {Path(dossier).name} » ?\n\n"
                    "Les traitements déjà réalisés "
                    "resteront à l'ancienne étude — "
                    "aucun déplacement, aucune copie."
                )
            )

            if (
                reponse
                != QMessageBox.StandardButton.Yes
            ):
                return

            try:
                self._nom_retour = changer_etude(
                    conflit[0],
                    conflit[1],
                    dossier,
                    etudes_connues=etudes_connues
                )
            except Exception as e:

                QMessageBox.warning(
                    self,
                    "Changement impossible",
                    str(e)
                )

                return

            super().accept()

            return

        try:
            self._nom_retour = rattacher(
                dossier,
                self.chemin_projet,
                etudes_connues=etudes_connues
            )
        except Exception as e:

            QMessageBox.warning(
                self,
                "Rattachement impossible",
                str(e)
            )

            return

        self.settings.add_recent_etude(dossier)

        super().accept()
