# ui/reunion_window.py
"""
Page Réunion (P18.6b, spec navigation §3) :
la réunion, objet de premier rang, a sa propre
page — qu'elle soit autonome ou rattachée à une
étude.

Ruban : titre de la réunion (configurable),
date · durée, badge « Étude "…" · Bible : [version] »
ou « Réunion autonome », boutons Gestion de
l'étude, Accueil, ⚙, ?.

Stepper fixe en haut : ① Prétraitement ·
② Transcription · ③ Correction · ④ Reformulation ·
⑤ Résumé · ⑥ Export — ④ et ⑤ OPTIONNELLES
(contour pointillé) : « Étape suivante » précise
« (optionnelle) » le cas échéant, « passer
l'étape › » les saute ; le passage direct
② → ⑥ est toujours possible et n'invalide
jamais les contenus existants (invariant §9.3).

Le contenu de chaque étape reprend les pages
existantes (P16/P16-bis/P17) sans changement :
③ = éditeur v1, ④ = page Reformulation, ⑤ =
fenêtre Résumé, ⑥ = export (réunion, y compris
autonome ou intermédiaire).
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from services.avancement import (
    ETAPES_REUNION,
    LIBELLES_ETAPES,
    etapes_reunion,
    etat_export,
)
from services.etude_io import (
    sauvegarder_etude,
)
from services.help import open_user_manual
from services.rattachement import (
    detacher_reunion,
    rattachement_de,
)
from services.settings import SettingsManager

from ui.stepper import StepperBar


def formater_duree(secondes) -> str:
    """
    Durée lisible du ruban : « 1 h 04 min »,
    « 32 min 10 s », « 45 s ».
    """

    if not secondes or secondes <= 0:
        return "—"

    secondes = int(round(secondes))

    heures = secondes // 3600
    minutes = (secondes % 3600) // 60
    reste = secondes % 60

    if heures:
        return f"{heures} h {minutes:02d} min"

    if minutes:
        return f"{minutes} min {reste:02d} s"

    return f"{reste} s"


class ReunionWindow(QWidget):
    """
    Page Réunion : ruban + stepper ①→⑥ + contenu
    de l'étape courante.
    """

    def __init__(
        self,
        projet,
        settings=None,
        etude=None,
        nom=None
    ):
        super().__init__()

        self.settings = (
            settings
            if settings is not None
            else SettingsManager()
        )

        self.projet = projet

        #
        # Étude de rattachement (0 ou 1) : donnée
        # par la page Étude si la réunion en
        # provient, sinon résolue depuis les études
        # récentes.
        #
        self.etude = etude
        self.nom = nom

        if (
            self.etude is None
            and self.nom is None
        ):
            self._resoudre_rattachement()

        self.pages_etape = {}

        self.fenetre_correction = None
        self.fenetre_reformulation = None

        self.etape_courante = "correction"

        self.build_ui()

        self.changer_etape("correction")

    # ==================================================
    # Rattachement (0 ou 1 étude).
    # ==================================================

    def _resoudre_rattachement(self):

        chemin = getattr(
            self.projet,
            "project_file",
            None
        )

        if not chemin:
            return

        etudes = (
            self.settings.cleanup_recent_etudes()
        )

        rattachement = rattachement_de(
            chemin,
            etudes
        )

        if rattachement is None:
            return

        dossier, nom = rattachement

        from services.etude_io import ouvrir_etude

        try:
            self.etude = ouvrir_etude(dossier)
            self.nom = nom
        except Exception:
            self.etude = None
            self.nom = None

    def rattachee(self) -> bool:

        return (
            self.etude is not None
            and self.nom is not None
        )

    # ==================================================
    # UI.
    # ==================================================

    def build_ui(self):

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(8)

        layout.addWidget(
            self._construire_ruban()
        )

        #
        # Stepper fixe en haut (spec §3.2), cliquable.
        #
        self.stepper = StepperBar(cliquable=True)

        self.stepper.etape_cliquee.connect(
            self.changer_etape
        )

        layout.addWidget(self.stepper)

        self.contenu = QStackedWidget()

        for etape in ETAPES_REUNION:
            self.contenu.addWidget(
                QWidget()
            )

        layout.addWidget(
            self.contenu,
            stretch=1
        )

        #
        # « Étape suivante » / « passer l'étape › »
        # (spec §3.3).
        #
        barre_bas = QHBoxLayout()

        self.etape_suivante_button = QPushButton(
            "Étape suivante ›"
        )
        self.etape_suivante_button.clicked.connect(
            self.aller_etape_suivante
        )

        self.passer_button = QPushButton(
            "passer l'étape ›"
        )
        self.passer_button.setToolTip(
            "Passer directement à l'étape suivante "
            "sans rien faire de celle-ci"
        )
        self.passer_button.clicked.connect(
            self.passer_etape
        )

        barre_bas.addWidget(
            self.etape_suivante_button
        )
        barre_bas.addWidget(self.passer_button)
        barre_bas.addStretch()

        layout.addLayout(barre_bas)

        self.maj_stepper()

    def _construire_ruban(self) -> QWidget:
        """
        Ruban : titre, date · durée, badge
        étude/Bible ou « Réunion autonome », boutons
        Gestion de l'étude, Accueil, ⚙, ?.
        """

        ruban = QWidget()
        ruban.setObjectName("ruban_reunion")

        layout = QHBoxLayout(ruban)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        colonne_titre = QVBoxLayout()
        colonne_titre.setSpacing(2)

        titre = self._titre_reunion()

        self.titre_label = QLabel(titre)
        self.titre_label.setStyleSheet(
            "font-size: 18px; font-weight: 600;"
        )

        infos = self._ligne_infos()

        self.infos_label = QLabel(infos)
        self.infos_label.setStyleSheet(
            "font-size: 12px; color: #757575;"
        )

        colonne_titre.addWidget(self.titre_label)
        colonne_titre.addWidget(self.infos_label)

        layout.addLayout(colonne_titre)

        self.badge_label = QLabel(
            self._texte_badge()
        )
        self.badge_label.setStyleSheet(
            "font-size: 12px; color: #1565C0;"
            if self.rattachee()
            else "font-size: 12px; color: #8A8A8A;"
        )

        layout.addWidget(self.badge_label)

        layout.addStretch()

        self.gestion_button = QPushButton(
            "Gestion de l'étude"
        )
        self.gestion_button.setToolTip(
            "Rattachement de la réunion à une étude, "
            "changement d'étude, ouverture de l'étude"
        )
        self.gestion_button.clicked.connect(
            self.afficher_menu_gestion
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
            self.gestion_button,
            self.accueil_button,
            self.parametres_button,
            self.aide_button,
        ):
            layout.addWidget(bouton)

        return ruban

    def _titre_reunion(self) -> str:

        if self.rattachee():

            reunion = (
                self.etude.reunions.get(self.nom)
            )

            if reunion and reunion.titre_1:
                return reunion.titre_1

        nom = getattr(
            self.projet,
            "name",
            None
        )

        if nom:
            return nom

        chemin = getattr(
            self.projet,
            "project_file",
            ""
        )

        return (
            Path(chemin).parent.name
            if chemin
            else "Réunion"
        )

    def _ligne_infos(self) -> str:

        parties = []

        if self.rattachee():

            from services.avancement import (
                date_reunion,
            )

            reunion = (
                self.etude.reunions.get(self.nom)
            )

            # Date de RÉUNION (audio), jamais la
            # date technique de rattachement
            # (spec correctifs §12, invariant 4).
            date = date_reunion(
                self.projet,
                reunion
            )

            if date:
                parties.append(date)

        duree = getattr(
            self.projet,
            "duration_seconds",
            None
        )

        if duree:
            parties.append(
                formater_duree(duree)
            )

        return " · ".join(parties)

    def _texte_badge(self) -> str:

        if not self.rattachee():
            return "Réunion autonome"

        titre = (
            self.etude.etude.titre
        )

        bible = ""

        try:

            from services.bibles import (
                nom_court_bible,
                version_bible_etude,
            )

            version = version_bible_etude(
                self.etude.parametres
            )

            # Nom COURT (spec correctifs §9) :
            # « Bible : Darby révisée », pas de
            # doublon « Bible : Bible ».
            bible = " · Bible : " + (
                nom_court_bible(version)
            )

        except Exception:
            bible = ""

        return f"Étude « {titre} »{bible}"

    # ==================================================
    # Étapes.
    # ==================================================

    def changer_etape(self, etape: str):
        """
        Affiche l'étape demandée (le contenu reprend
        les pages existantes, P16/P16-bis/P17).
        """

        if etape not in ETAPES_REUNION:
            return

        self.etape_courante = etape

        index = list(ETAPES_REUNION).index(etape)

        page = self.pages_etape.get(etape)

        if page is None:

            page = self._construire_page_etape(etape)

            if page is None:
                return

            self.pages_etape[etape] = page

            self.contenu.addWidget(page)

        self.contenu.setCurrentWidget(page)

        self.maj_boutons_etape()
        self.maj_stepper()

    def _construire_page_etape(self, etape):

        if etape == "pretraitement":
            return self._page_pretraitement()

        if etape == "transcription":
            return self._page_transcription()

        if etape == "correction":
            return self._page_correction()

        if etape == "reformulation":
            return self._page_reformulation()

        if etape == "resume":
            return self._page_resume()

        if etape == "export":
            return self._page_export()

        return QWidget()

    def _page_information(
        self,
        titre: str,
        lignes: list
    ) -> QWidget:
        """
        Panneau d'information (étapes ① et ② :
        traitements déjà réalisés en amont).
        """

        panneau = QWidget()

        layout = QVBoxLayout(panneau)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        titre_label = QLabel(titre)
        titre_label.setStyleSheet(
            "font-size: 15px; font-weight: 600;"
        )

        layout.addWidget(titre_label)

        for ligne in lignes:

            label = QLabel(ligne)
            label.setWordWrap(True)
            label.setStyleSheet(
                "color: #555555;"
            )

            layout.addWidget(label)

        layout.addStretch()

        return panneau

    def _page_pretraitement(self):

        from services.avancement import (
            etat_pretraitement,
        )

        dossier = Path(
            getattr(
                self.projet,
                "project_file",
                ""
            )
        ).parent

        journal = (
            dossier / "journal_operations.json"
        ).is_file()

        lignes = []

        if journal:
            lignes.append(
                "Le prétraitement de l'audio a été "
                "réalisé (journal des opérations "
                "présent)."
            )
        else:
            lignes.append(
                "Aucun journal de prétraitement : "
                "l'audio a été importé sans "
                "prétraitement (ou transcrit "
                "directement)."
            )

        audio = getattr(
            self.projet,
            "audio_file",
            None
        )

        if audio:
            lignes.append(
                "Fichier audio : " + str(audio)
            )

        return self._page_information(
            "① Prétraitement",
            lignes
        )

    def _page_transcription(self):

        mots = getattr(
            self.projet,
            "words",
            []
        )

        mots = [
            m for m in mots
            if getattr(
                m,
                "item_type",
                "word"
            ) == "word"
        ]

        lignes = [
            f"Transcription : {len(mots)} mot(s) "
            "horodaté(s).",
            (
                "Langue : "
                + str(
                    getattr(
                        self.projet,
                        "language_code",
                        "—"
                    )
                )
            ),
        ]

        return self._page_information(
            "② Transcription",
            lignes
        )

    def _page_correction(self):
        """
        ③ Correction : l'éditeur v1 existant (P16-bis),
        embarqué tel quel.
        """

        from ui.main_window import MainWindow

        self.fenetre_correction = MainWindow(
            self.projet,
            settings=self.settings
        )

        #
        # L'éditeur embarqué navigue via cette page
        # (« Accueil », « Reformulation… ») : les
        # destinations atterrissent dans la page
        # Réunion ou remontent à la pile de l'app.
        #
        self.fenetre_correction.navigation = self

        return self.fenetre_correction

    def _page_reformulation(self):
        """
        ④ Reformulation (optionnelle) : la page de
        relecture P16/P16-bis. Sans étude : la
        réunion est autonome — rattachement proposé
        (disponible à tout moment, spec §6.2).
        """

        if not self.rattachee():

            return self._page_information(
                "④ Reformulation (optionnelle)",
                [
                    "Cette réunion est autonome : la "
                    "reformulation travaille par blocs "
                    "de parole au sein d'une étude.",
                    "",
                    "Rattachez la réunion à une étude "
                    "(bouton « Gestion de l'étude ») "
                    "pour la reformuler — ou passez "
                    "l'étape (elle est optionnelle).",
                ]
            )

        from ui.etude_window import assurer_decoupage

        if not assurer_decoupage(
            self,
            self.etude,
            self.nom
        ):

            return self._page_information(
                "④ Reformulation (optionnelle)",
                [
                    "La segmentation de la réunion est "
                    "nécessaire à la reformulation. "
                    "Relancez l'étape pour la générer "
                    "à partir de la diarisation validée."
                ]
            )

        from ui.reformulation_window import (
            ReformulationWindow
        )

        self.fenetre_reformulation = (
            ReformulationWindow(
                self.etude,
                self.nom,
                settings=self.settings
            )
        )

        self.fenetre_reformulation.navigation = self

        return self.fenetre_reformulation

    def _page_resume(self):
        """
        ⑤ Résumé (optionnelle) : la fenêtre Résumé
        P17 reste un dialogue — panneau d'état +
        ouverture. Sans étude : rattachement proposé.
        """

        panneau = QWidget()

        layout = QVBoxLayout(panneau)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        titre_label = QLabel(
            "⑤ Résumé (optionnelle)"
        )
        titre_label.setStyleSheet(
            "font-size: 15px; font-weight: 600;"
        )

        layout.addWidget(titre_label)

        self.resume_statut_label = QLabel(
            self._texte_statut_resume()
        )
        self.resume_statut_label.setWordWrap(
            True
        )
        self.resume_statut_label.setStyleSheet(
            "color: #555555;"
        )

        layout.addWidget(self.resume_statut_label)

        actions = QHBoxLayout()

        if self.rattachee():

            self.resume_button = QPushButton(
                "Résumé…"
            )
            self.resume_button.setToolTip(
                "Ouvrir la fenêtre Résumé de la réunion "
                "(P17 : source au choix, éditable, "
                "validable)"
            )
            self.resume_button.clicked.connect(
                self.ouvrir_resume
            )

            actions.addWidget(self.resume_button)

            saisie_note = QLabel(
                "Saisie manuelle possible : tapez ou "
                "collez le résumé dans la fenêtre "
                "« Résumé… », puis « Sauvegarder "
                "l'édition » — sans aucun appel LLM "
                "(statut identique une fois validé)."
            )
            saisie_note.setWordWrap(True)
            saisie_note.setStyleSheet(
                "color: #757575; font-size: 11px;"
            )

            layout.addWidget(saisie_note)

        else:

            info = QLabel(
                "Cette réunion est autonome : le résumé "
                "vit dans une étude. Rattachez la réunion "
                "(bouton « Gestion de l'étude ») — ou "
                "passez l'étape (elle est optionnelle)."
            )
            info.setWordWrap(True)
            info.setStyleSheet("color: #555555;")

            layout.addWidget(info)

        actions.addStretch()
        layout.addLayout(actions)
        layout.addStretch()

        return panneau

    def _texte_statut_resume(self):

        if not self.rattachee():
            return ""

        reunion = (
            self.etude.reunions.get(self.nom)
        )

        if reunion and reunion.resume_valide:
            return "Le résumé de la réunion est validé."

        resultat = (
            self.etude.resumes.get(self.nom)
        )

        if resultat and resultat.versions:
            return (
                f"{len(resultat.versions)} version(s) "
                "de résumé, aucune validée."
            )

        return "Aucun résumé pour cette réunion."

    def ouvrir_resume(self):

        if not self.rattachee():
            return

        from ui.etude_window import assurer_decoupage

        if not assurer_decoupage(
            self,
            self.etude,
            self.nom
        ):
            return

        from ui.resume_window import ResumeWindow

        fenetre = ResumeWindow(
            self.etude,
            self.nom,
            parent=self
        )

        fenetre.exec()

        sauvegarder_etude(self.etude)

        if self.resume_statut_label is not None:
            self.resume_statut_label.setText(
                self._texte_statut_resume()
            )

        self.maj_stepper()

    def _page_export(self):
        """
        ⑥ Export : export de réunion (y compris
        autonome ou intermédiaire, spec §3.4).
        """

        panneau = QWidget()

        layout = QVBoxLayout(panneau)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        titre_label = QLabel("⑥ Export")
        titre_label.setStyleSheet(
            "font-size: 15px; font-weight: 600;"
        )

        layout.addWidget(titre_label)

        self.export_statut_label = QLabel(
            self._texte_statut_export()
        )
        self.export_statut_label.setWordWrap(
            True
        )
        self.export_statut_label.setStyleSheet(
            "color: #555555;"
        )

        layout.addWidget(self.export_statut_label)

        actions = QHBoxLayout()

        self.export_transcription_button = (
            QPushButton(
                "Exporter la transcription…"
            )
        )
        self.export_transcription_button.setToolTip(
            "Exporter la transcription corrigée "
            "(flux v1 : TXT, JSON, DOCX, PDF)"
        )
        self.export_transcription_button.clicked.connect(
            self.exporter_transcription
        )

        actions.addWidget(
            self.export_transcription_button
        )

        if self.rattachee():

            self.export_valides_button = (
                QPushButton(
                    "Exporter les textes validés…"
                )
            )
            self.export_valides_button.setToolTip(
                "Export de réunion (portée P18.6f) : "
                "résumé validé en tête et "
                "reformulations validées dans l'ordre "
                "d'ouvrage — DOCX ou TXT"
            )
            self.export_valides_button.clicked.connect(
                self.exporter_textes_valides
            )

            actions.addWidget(
                self.export_valides_button
            )

        actions.addStretch()

        layout.addLayout(actions)
        layout.addStretch()

        return panneau

    def _texte_statut_export(self):

        chemin = getattr(
            self.projet,
            "project_file",
            None
        )

        if (
            chemin
            and etat_export(chemin, self.settings)
            == "termine"
        ):
            return (
                "Cette réunion a déjà été exportée "
                "au moins une fois."
            )

        return (
            "Exportez la transcription corrigée"
            + (
                ", ou les textes validés de la réunion "
                "(résumé et reformulations)"
                if self.rattachee()
                else ""
            )
            + "."
        )

    def exporter_textes_valides(self):
        """
        Export de réunion (P18.6f, spec §8.1) :
        résumé validé en tête + reformulations
        validées dans l'ordre d'ouvrage — y compris
        intermédiaire (tous les blocs n'ont pas
        besoin d'être validés). Trace d'export dans
        les réglages (étape ⑥ verte).
        """

        if not self.rattachee():
            return

        import re as _re

        from services.export_ouvrage import (
            assembler_reunion,
            exporter_docx,
            exporter_txt,
        )

        from PySide6.QtWidgets import (
            QFileDialog,
        )
        from PySide6.QtGui import (
            QDesktopServices,
        )
        from PySide6.QtCore import QUrl

        ouvrage = assembler_reunion(
            self.etude,
            self.nom
        )

        if not ouvrage["reunions"]:

            QMessageBox.information(
                self,
                "Rien à exporter",
                (
                    "Aucun texte validé pour cette "
                    "réunion : validez des "
                    "reformulations (ou un résumé) "
                    "avant d'exporter."
                )
            )

            return

        nom_defaut = _re.sub(
            r"[^\w\- ]",
            "",
            ouvrage["titre"]
        ).strip() or "reunion"

        dossier = Path(
            getattr(
                self.projet,
                "project_file",
                ""
            )
        ).parent

        chemin, filtre = QFileDialog.getSaveFileName(
            self,
            "Exporter la réunion",
            str(dossier / f"{nom_defaut}.docx"),
            "Document Word (*.docx);;"
            "Texte (*.txt)"
        )

        if not chemin:
            return

        try:

            if filtre.startswith("Document"):
                chemin = exporter_docx(
                    ouvrage, chemin
                )
            else:
                chemin = exporter_txt(
                    ouvrage, chemin
                )

        except Exception as e:

            QMessageBox.critical(
                self,
                "Export impossible",
                str(e)
            )

            return

        chemin_projet = getattr(
            self.projet,
            "project_file",
            None
        )

        if chemin_projet:
            self.settings.enregistrer_export_reunion(
                chemin_projet
            )

        message = QMessageBox(self)
        message.setWindowTitle("Réunion exportée")
        message.setText(
            "La réunion a été exportée :\n\n"
            f"{chemin}"
        )

        open_file_button = message.addButton(
            "Ouvrir le fichier",
            QMessageBox.ButtonRole.AcceptRole
        )

        message.addButton(
            "Fermer",
            QMessageBox.ButtonRole.RejectRole
        )

        message.exec()

        if (
            message.clickedButton()
            is open_file_button
        ):
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(chemin))
            )

        if self.export_statut_label is not None:
            self.export_statut_label.setText(
                self._texte_statut_export()
            )

        self.maj_stepper()

    def exporter_transcription(self):
        """
        Export de la transcription corrigée (flux v1
        de l'éditeur embarqué), puis trace d'export
        dans les réglages (étape ⑥ verte).
        """

        if self.fenetre_correction is None:
            self._page_correction()

        if self.fenetre_correction is None:
            return

        self.fenetre_correction.export_project()

        chemin = getattr(
            self.projet,
            "project_file",
            None
        )

        if chemin:
            self.settings.enregistrer_export_reunion(
                chemin
            )

        if self.export_statut_label is not None:
            self.export_statut_label.setText(
                self._texte_statut_export()
            )

        self.maj_stepper()

    # ==================================================
    # Navigation entre étapes.
    # ==================================================

    def maj_boutons_etape(self):
        """
        « Étape suivante » précise « (optionnelle) »
        quand l'étape qui vient l'est (spec §3.3).
        """

        index = list(ETAPES_REUNION).index(
            self.etape_courante
        )

        if index + 1 >= len(ETAPES_REUNION):
            self.etape_suivante_button.setEnabled(
                False
            )
            self.etape_suivante_button.setText(
                "Étape suivante ›"
            )
            return

        suivante = ETAPES_REUNION[index + 1]

        optionnelle = suivante in (
            "reformulation",
            "resume"
        )

        self.etape_suivante_button.setEnabled(
            True
        )

        self.etape_suivante_button.setText(
            "Étape suivante "
            f"{LIBELLES_ETAPES[suivante]} "
            + ("(optionnelle) ›" if optionnelle
               else "›")
        )

    def aller_etape_suivante(self):

        index = list(ETAPES_REUNION).index(
            self.etape_courante
        )

        if index + 1 >= len(ETAPES_REUNION):
            return

        self.changer_etape(
            ETAPES_REUNION[index + 1]
        )

    def passer_etape(self):
        """
        « passer l'étape › » : saute l'étape courante
        SANS rien invalider (invariant §9.3 — les
        contenus existants sont conservés tels quels).
        """

        self.aller_etape_suivante()

    def maj_stepper(self):
        """
        Recalcule les couleurs du stepper.
        """

        etats = etapes_reunion(
            self.projet,
            etude_ouverte=(
                self.etude if self.rattachee()
                else None
            ),
            nom=self.nom,
            settings=self.settings,
        )

        self.stepper.definir_etats(etats)

    # ==================================================
    # Gestion de l'étude (rattachement, spec §6).
    # ==================================================

    def afficher_menu_gestion(self):
        """
        Menu « Gestion de l'étude » : rattachement,
        changement d'étude, détachement, ouverture
        de l'étude, renommage de la réunion.
        """

        menu = QMenu(self)

        if self.rattachee():

            ouvrir = menu.addAction(
                "Ouvrir l'étude…"
            )
            ouvrir.triggered.connect(
                self.ouvrir_etude_courante
            )

            changer = menu.addAction(
                "Changer d'étude…"
            )
            changer.triggered.connect(
                self.changer_etude_ui
            )

            detacher = menu.addAction(
                "Détacher de l'étude…"
            )
            detacher.triggered.connect(
                self.detacher_ui
            )

            menu.addSeparator()

            renommer = menu.addAction(
                "Renommer la réunion…"
            )
            renommer.triggered.connect(
                self.renommer_reunion
            )

        else:

            rattacher = menu.addAction(
                "Rattacher à une étude…"
            )
            rattacher.triggered.connect(
                self.rattacher_ui
            )

        menu.exec(
            self.gestion_button.mapToGlobal(
                self.gestion_button.rect()
                .bottomLeft()
            )
        )

    def _recharger_apres_rattachement(self):
        """
        Après un changement de rattachement, la page
        se reconstruit sur l'étape Correction (les
        pages d'étape liées à l'ancienne étude ne
        sont plus valables).
        """

        self.pages_etape.clear()
        self.fenetre_correction = None
        self.fenetre_reformulation = None

        while self.contenu.count():
            widget = self.contenu.widget(0)
            self.contenu.removeWidget(widget)
            widget.deleteLater()

        for _etape in ETAPES_REUNION:
            self.contenu.addWidget(QWidget())

        self.badge_label.setText(
            self._texte_badge()
        )
        self.badge_label.setStyleSheet(
            "font-size: 12px; color: #1565C0;"
            if self.rattachee()
            else "font-size: 12px; color: #8A8A8A;"
        )

        self.titre_label.setText(
            self._titre_reunion()
        )
        self.infos_label.setText(
            self._ligne_infos()
        )

        self.changer_etape("correction")

    def rattacher_ui(self):

        from ui.rattachement_dialog import (
            RattachementDialog
        )

        chemin = getattr(
            self.projet,
            "project_file",
            None
        )

        if not chemin:
            return

        dialogue = RattachementDialog(
            chemin,
            self.settings,
            parent=self
        )

        if dialogue.exec():

            self._resoudre_rattachement()

            self._recharger_apres_rattachement()

    def changer_etude_ui(self):

        self.rattacher_ui()

    def detacher_ui(self):
        """
        Détachement : la réunion redevient autonome.
        Les traitements restent à l'étude (option A).
        """

        if not self.rattachee():
            return

        reponse = QMessageBox.question(
            self,
            "Détacher la réunion",
            (
                "Détacher cette réunion de l'étude "
                f"« {self.etude.etude.titre} » ?\n\n"
                "Les traitements déjà réalisés "
                "(reformulations, résumé, validations) "
                "resteront à l'étude — aucun "
                "déplacement, aucune copie. La réunion "
                "devient autonome."
            )
        )

        if reponse != QMessageBox.StandardButton.Yes:
            return

        detacher_reunion(self.etude, self.nom)
        sauvegarder_etude(self.etude)

        self.etude = None
        self.nom = None

        self._recharger_apres_rattachement()

    def ouvrir_etude_courante(self):

        if not self.rattachee():
            return

        navigation = getattr(
            self,
            "navigation",
            None
        )

        if navigation is not None:
            navigation.ouvrir_etude(
                self.etude.dossier
            )
            return

        from ui.etude_window import EtudeWindow

        self.fenetre_etude = EtudeWindow(
            self.etude.dossier,
            settings=self.settings
        )

        self.fenetre_etude.show()

    def renommer_reunion(self):
        """
        Titre de réunion configurable (spec §6.4) —
        stocké dans l'étude (titre_1), le projet v1
        n'est jamais modifié.
        """

        if not self.rattachee():
            return

        reunion = (
            self.etude.reunions.get(self.nom)
        )

        if reunion is None:
            return

        titre, ok = QInputDialog.getText(
            self,
            "Renommer la réunion",
            "Titre de la réunion :",
            text=reunion.titre_1 or ""
        )

        if not ok:
            return

        reunion.titre_1 = titre.strip()

        sauvegarder_etude(self.etude)

        self.titre_label.setText(
            self._titre_reunion()
        )

    # ==================================================
    # Destinations de navigation (adaptateur pour
    # les pages embarquées : l'éditeur v1 et la page
    # Reformulation appellent navigation.*).
    # ==================================================

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

    def ouvrir_accueil(self):

        navigation = getattr(
            self,
            "navigation",
            None
        )

        if navigation is not None:
            navigation.ouvrir_accueil()
            return

    def ouvrir_etude(self, dossier):

        navigation = getattr(
            self,
            "navigation",
            None
        )

        if navigation is not None:
            navigation.ouvrir_etude(dossier)
            return

        from ui.etude_window import EtudeWindow

        self.fenetre_etude = EtudeWindow(
            dossier,
            settings=self.settings
        )

        self.fenetre_etude.show()

    def ouvrir_reformulation(self, etude, nom):
        """
        « Reformulation… » de l'éditeur embarqué :
        bascule sur l'étape ④ de cette même page.
        """

        self.etude = etude
        self.nom = nom

        self.changer_etape("reformulation")

    # ==================================================
    # Hooks de la pile (P16-bis §15.2).
    # ==================================================

    def sur_navigation_sortante(self):
        """
        Quitter la page : les pages embarquées
        sauvegardent leur état (lecteur audio, etc.).
        """

        for page in self.pages_etape.values():

            sortie = getattr(
                page,
                "sur_navigation_sortante",
                None
            )

            if sortie is not None:
                sortie()

    def sur_navigation_entrante(self):
        """
        Retour sur la page : recalcule le stepper et
        redonne la main à la page embarquée courante.
        """

        self.maj_stepper()

        entree = getattr(
            self.contenu.currentWidget(),
            "sur_navigation_entrante",
            None
        )

        if entree is not None:
            entree()
