# ui/fusion_pensees_dialog.py
"""
Dialogue de fusion de pensées (P19.4, feuille de
route v2.1 §P19) — page Ouvrage uniquement.

Deux paragraphes dont la pensée est très similaire
(même locuteur ou locuteurs différents) sont
fusionnés en un seul paragraphe portant les
provenances multiples :

- fusion **manuelle** : les deux textes sont
  présentés côte à côte, le paragraphe fusionné
  est rédigé (ou ajusté) dans l'éditeur du bas ;
- fusion **assistée LLM** : « Fusion assistée (IA) »
  propose un paragraphe unique (relance avec les
  deux textes en entrée + consigne) — le résultat
  reste ÉDITABLE, rien n'est appliqué sans
  l'acceptation explicite de l'utilisateur
  (invariant des suggestions IA, spec navigation
  §9.7).

« Annuler » ne touche à rien. La dé-fusion est
disponible depuis la page Ouvrage après la fusion.
"""

from PySide6.QtCore import (
    QObject,
    QThread,
    Signal,
    Slot,
)
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from models.ouvrage import (
    ElementOuvrage,
)


def libelle_provenance(element: ElementOuvrage) -> str:
    """
    Libellé de provenance d'un paragraphe du
    dialogue : réunion, date, bloc — métadonnées
    NON structurelles (plusieurs provenances
    séparées par « — » après une fusion).
    """

    morceaux = []

    for p in element.provenances:

        morceau = (
            f"R{p.numero_reunion}"
            if p.numero_reunion
            else (p.reunion or "?")
        )

        if p.locuteurs:
            morceau += f" · {p.locuteurs}"

        if p.date_reunion:
            morceau += f" · {p.date_reunion}"

        if p.fid:
            morceau += f" · bloc {p.fid}"

        morceaux.append(morceau)

    return " — ".join(morceaux)


class FusionWorker(QObject):
    """
    Exécute la proposition de fusion dans un
    thread (un seul appel LLM) : le dialogue reste
    réactif.
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


class FusionPenseesDialog(QDialog):
    """
    Dialogue de fusion : deux paragraphes côte à
    côte (sources), le paragraphe fusionné en
    dessous (prérempli avec les deux textes pour
    une fusion manuelle), assistance IA en option.
    """

    def __init__(
        self,
        parent,
        element_1: ElementOuvrage,
        element_2: ElementOuvrage,
        service=None,
    ):
        super().__init__(parent)

        self.element_1 = element_1
        self.element_2 = element_2
        self.service = service

        self.thread = None
        self.worker = None
        self.annulation = None

        # Traçabilité de l'assistance éventuelle
        # (P19.4-bis : prompt EFFECTIF texte + hash,
        # modèle, coûts — consignés dans ouvrage.json
        # par la page à la fusion).
        self.stats_assistance = None

        self.setWindowTitle("Fusionner les pensées")
        self.resize(760, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        entete = QLabel(
            "Les deux paragraphes deviennent un seul "
            "— le paragraphe fusionné portera toutes "
            "les provenances. Vous pourrez le "
            "dé-fusionner depuis la page Ouvrage."
        )
        entete.setWordWrap(True)

        layout.addWidget(entete)

        #
        # Les deux textes sources, côte à côte.
        #
        sources = QHBoxLayout()
        sources.setSpacing(10)

        self.zone_1 = self._zone_source(
            element_1
        )
        self.zone_2 = self._zone_source(
            element_2
        )

        sources.addWidget(self.zone_1)
        sources.addWidget(self.zone_2)

        layout.addLayout(sources, stretch=1)

        #
        # Le paragraphe fusionné.
        #
        titre_fusion = QLabel(
            "Paragraphe fusionné (éditable)"
        )
        titre_fusion.setStyleSheet(
            "font-weight: 600;"
        )

        layout.addWidget(titre_fusion)

        self.editeur_fusion = QTextEdit()

        # setPlainText : le constructeur de QTextEdit
        # lirait la chaîne comme du HTML (les
        # retours à la ligne seraient avalés).
        self.editeur_fusion.setPlainText(
            (element_1.texte or "")
            + "\n\n"
            + (element_2.texte or "")
        )
        self.editeur_fusion.setAcceptRichText(False)

        layout.addWidget(self.editeur_fusion, stretch=1)

        #
        # Actions : assistance IA, fusion, annulation.
        #
        actions = QHBoxLayout()

        self.assistance_button = QPushButton(
            "Fusion assistée (IA)"
        )
        self.assistance_button.setToolTip(
            "Proposer le paragraphe fusionné par LLM "
            "(les deux textes en entrée + une "
            "consigne) — la proposition reste "
            "éditable, rien n'est appliqué sans "
            "votre acceptation"
        )
        self.assistance_button.clicked.connect(
            self.assister
        )

        actions.addWidget(self.assistance_button)
        actions.addStretch()

        boutons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        boutons.button(
            QDialogButtonBox.StandardButton.Ok
        ).setText("Fusionner")

        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)

        actions.addWidget(boutons)

        layout.addLayout(actions)

        self._maj_assistance()

    def _zone_source(
        self,
        element: ElementOuvrage
    ) -> QWidget:
        """
        Colonne d'un des deux paragraphes sources :
        provenance en tête, texte en lecture seule
        (les sources s'éditent dans le manuscrit).
        """

        colonne = QWidget()

        cible = QVBoxLayout(colonne)
        cible.setContentsMargins(0, 0, 0, 0)
        cible.setSpacing(4)

        provenance = QLabel(
            libelle_provenance(element)
        )
        provenance.setStyleSheet(
            "color: #8a8b92; font-size: 11px;"
        )

        texte = QPlainTextEdit(
            element.texte or ""
        )
        texte.setReadOnly(True)

        cible.addWidget(provenance)
        cible.addWidget(texte, stretch=1)

        return colonne

    def _maj_assistance(self):
        """
        L'assistance IA n'est disponible que si un
        service de fusion a été fourni (l'étude
        porte les paramètres LLM).
        """

        self.assistance_button.setVisible(
            self.service is not None
        )

    #
    # Assistance LLM (un appel, en thread).
    #

    def assister(self):

        if self.service is None:
            return

        if self.thread is not None:
            return

        self.annulation = type(
            "A", (), {"demandee": False}
        )()

        self.assistance_button.setEnabled(False)

        #
        # Fenêtre de chargement (règle 2026-11-07) :
        # un appel LLM — temps écoulé + Annuler.
        #
        from ui.fenetre_chargement_llm import (
            FenetreChargementLLM,
        )

        self.fenetre_chargement = FenetreChargementLLM(
            "Fusion assistée (IA) en cours…",
            parent=self,
            annulation=self.annulation,
            message="Appel LLM en cours (fusion)…",
            unite="Appel",
        )

        self.fenetre_chargement.set_indeterminee()
        self.fenetre_chargement.show()

        self.thread = QThread(self)
        self.worker = FusionWorker(
            lambda: self.service.proposer(
                self.element_1.texte or "",
                self.element_2.texte or "",
                source_1=libelle_provenance(
                    self.element_1
                ),
                source_2=libelle_provenance(
                    self.element_2
                ),
                annulation=self.annulation
            )
        )

        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)

        self.worker.terminee.connect(
            self.sur_assistance_terminee
        )
        self.worker.erreur.connect(
            self.sur_assistance_erreur
        )

        self.thread.start()

    def sur_assistance_terminee(self, resultat):

        if getattr(
            self,
            "fenetre_chargement",
            None
        ) is not None:
            self.fenetre_chargement.fermer()
            self.fenetre_chargement = None

        if self.thread is not None:
            self.thread.quit()

        self.thread = None
        self.worker = None
        self.annulation = None

        self.assistance_button.setEnabled(True)

        if resultat is not None and resultat.texte:
            self.editeur_fusion.setPlainText(
                resultat.texte.strip()
            )

            #
            # Traçabilité (P19.4-bis) : le prompt
            # EFFECTIF (texte + hash court) et les
            # conditions de l'appel accompagnet la
            # fusion — la page les consignera dans
            # ouvrage.json.
            #
            stats = {}

            for cle in (
                "modele",
                "fournisseur",
                "tokens_in",
                "tokens_out",
                "duree_ms",
                "cout_estime",
            ):
                if getattr(resultat, cle, None):
                    stats[cle] = (
                        getattr(resultat, cle)
                    )

            if (
                self.service is not None
                and getattr(
                    self.service,
                    "dernier_prompt",
                    ""
                )
            ):
                stats["prompt"] = getattr(
                    self.service,
                    "dernier_prompt"
                )
                stats["prompt_hash"] = getattr(
                    self.service,
                    "dernier_prompt_hash",
                    ""
                )

            self.stats_assistance = stats

    def sur_assistance_erreur(self, message):

        if getattr(
            self,
            "fenetre_chargement",
            None
        ) is not None:
            self.fenetre_chargement.fermer()
            self.fenetre_chargement = None

        if self.thread is not None:
            self.thread.quit()

        self.thread = None
        self.worker = None
        self.annulation = None

        self.assistance_button.setEnabled(True)

        QMessageBox.warning(
            self,
            "Fusion assistée impossible",
            message
        )

    #
    # Résultat.
    #

    def texte_fusionne(self) -> str:
        """
        Le texte du paragraphe fusionné, tel
        qu'accepté par l'utilisateur.
        """

        return (
            self.editeur_fusion.toPlainText().strip()
        )

    def stats(self) -> dict:
        """
        Traçabilité de l'assistance LLM éventuelle
        (P19.4-bis) : prompt EFFECTIF + hash court,
        modèle, coûts ; None pour une fusion purement
        manuelle.
        """

        return self.stats_assistance
