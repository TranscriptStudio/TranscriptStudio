"""
Tests — fenêtre de chargement de TOUTE
interrogation du LLM (règle David 2026-11-07) :

- la fenêtre `FenetreChargementLLM`
  (ui/fenetre_chargement_llm.py) affiche
  TOUJOURS le temps écoulé ; barre DÉTERMINÉE
  quand c'est possible (bloc k/N, segment k/N)
  avec estimation indicative du restant ;
  sinon barre INDÉTERMINÉE (un seul appel) ;
  « Annuler » branché sur l'annulation ;
- chaque lancement LLM de l'app l'ouvre et la
  ferme en fin d'opération :
  page Reformulation (relance d'un bloc,
  relance ciblée, passe complète, synthèse
  auto), page Résumé (génération avec
  progression par segment, relance avec
  consigne, retravail de la sélection),
  page Étude (synthèse), dialogue de fusion
  assistée ;
- le service résumé émet la progression des
  segments + assemblage final.

Les workers sont rendus SYNCHRONES en test
(QThread.start émet « started » tout de suite)
pour éviter tout vrai thread Qt en offscreen.
"""

import contextlib
import os
import time
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
)

from services.etude_io import (
    ajouter_version_reformulation,
    ouvrir_etude,
    sauvegarder_etude,
    valider_version_reformulation,
)
from services.llm.catalogue import catalogue_par_defaut
from services.llm.client import ResultatCompletion
from services.settings import SettingsManager
from services.traitements.moteur import ResultatPasse
from tests.unit.test_reformulation_ui import (
    construire_etude_test,
)


@pytest.fixture(scope="module")
def qapp():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    yield application


class EspionChargement:
    """
    Espion : sous-classe de FenetreChargementLLM
    enregistrant chaque fenêtre créée (titre,
    état final) — les modules UI l'importent à
    l'appel depuis le module source, le patch de
    `ui.fenetre_chargement_llm` suffit.
    """

    crees = []

    @classmethod
    def fabriquer(cls):
        from ui.fenetre_chargement_llm import (
            FenetreChargementLLM,
        )

        class Espion(FenetreChargementLLM):

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                cls.crees.append(self)

        return Espion


@contextlib.contextmanager
def lancer_synchrone():
    """
    Contexte : QThread.start émet « started »
    SYNCHRONEMENT et moveToThread est neutre —
    le worker tourne dans le thread de test,
    connexions directes (pas de vrai thread Qt
    en offscreen).
    """

    from PySide6.QtCore import QObject

    with patch.object(
        QThread,
        "start",
        lambda self: self.started.emit(),
    ), patch.object(
        QObject,
        "moveToThread",
        lambda self, thread: None,
    ):
        yield


#
# ==================================================
# La fenêtre elle-même.
# ==================================================
#

class TestFenetreChargement:

    def test_temps_ecoule_toujours_affiche(
        self,
        qapp
    ):
        """
        Le temps écoulé est affiché dès
        l'ouverture (m:ss, h:mm:ss au-delà d'une
        heure).
        """

        from ui.fenetre_chargement_llm import (
            FenetreChargementLLM,
        )

        fenetre = FenetreChargementLLM(
            "Test…",
            message="Appel LLM en cours…"
        )

        try:

            assert (
                "Temps écoulé : 0:00"
                in fenetre.temps_label.text()
            )

            fenetre._depart = (
                time.monotonic() - 65
            )

            fenetre.maj_temps()

            assert (
                "Temps écoulé : 1:05"
                in fenetre.temps_label.text()
            )

            fenetre._depart = (
                time.monotonic() - 3723
            )

            fenetre.maj_temps()

            assert (
                "Temps écoulé : 1:02:03"
                in fenetre.temps_label.text()
            )

        finally:
            fenetre.fermer()

    def test_progression_determinee_et_restant(
        self,
        qapp
    ):
        """
        Total connu : barre déterminée, libellé
        « Bloc k/N — en cours… », estimation du
        restant (indicative).
        """

        from ui.fenetre_chargement_llm import (
            FenetreChargementLLM,
        )

        fenetre = FenetreChargementLLM(
            "Test…",
            message="En cours…"
        )

        try:

            # Par défaut : INDÉTERMINÉE (un appel).
            assert (
                fenetre.barre.minimum() == 0
                and fenetre.barre.maximum() == 0
            )

            fenetre.set_total(4)

            fenetre.definir_progression(2)

            assert fenetre.barre.value() == 2
            assert fenetre.barre.maximum() == 4

            assert (
                "Bloc 2/4 — en cours…"
                in fenetre.etape_label.text()
            )

            # Estimation du restant affichée.
            fenetre._depart = (
                time.monotonic() - 30
            )

            fenetre.maj_temps()

            assert (
                "Reste" in fenetre.restant_label.text()
                and "indicatif"
                in fenetre.restant_label.text()
            )

        finally:
            fenetre.fermer()

    def test_annuler_branche_sur_lannulation(
        self,
        qapp
    ):

        from ui.fenetre_chargement_llm import (
            FenetreChargementLLM,
        )

        annulation = type(
            "A", (), {"demandee": False}
        )()

        fenetre = FenetreChargementLLM(
            "Test…",
            annulation=annulation
        )

        try:

            assert not (
                fenetre.annuler_button.isHidden()
            )

            fenetre.annuler()

            assert annulation.demandee is True
            assert not (
                fenetre.annuler_button.isEnabled()
            )

            # Sans annulation : bouton masqué.
            autre = FenetreChargementLLM("T2")

            try:
                assert (
                    autre.annuler_button.isHidden()
                )
            finally:
                autre.fermer()

            # fermer() est idempotent.
            fenetre.fermer()
            fenetre.fermer()

        finally:
            fenetre.fermer()


#
# ==================================================
# Invariant : tous les sites LLM ouvrent la
# fenêtre.
# ==================================================
#

class TestTousLesSitesLLM:

    def test_sites_llm_referencent_la_fenetre(self):
        """
        Chaque module lançant un appel LLM importe
        FenetreChargementLLM.
        """

        import ui.etude_window as m_etude
        import ui.fusion_pensees_dialog as m_fusion
        import ui.reformulation_window as m_ref
        import ui.resume_window as m_resume

        for module in (
            m_ref,
            m_resume,
            m_etude,
            m_fusion,
        ):
            source = Path(
                module.__file__
            ).read_text(encoding="utf-8")

            assert "FenetreChargementLLM" in source


#
# ==================================================
# Page Reformulation : relance ciblée, passe,
# synthèse auto.
# ==================================================
#

class MoteurFactice:
    """
    Moteur factice : consigne une version par
    appel (jamais de réseau).
    """

    def __init__(self, etude):
        self.etude = etude
        self.appels_bloc = []

    def blocs_a_traiter(self, cible):
        return [1, 2, 3]

    def traiter_bloc(
        self,
        fid,
        consigne=None,
        selection=None,
        annulation=None
    ):
        self.appels_bloc.append(fid)

        version = ajouter_version_reformulation(
            self.etude,
            fid,
            f"Relance du bloc {fid}"
        )

        sauvegarder_etude(self.etude)

        return version

    def traiter_reunion(
        self,
        annulation=None,
        progression=None,
        cible=None
    ):
        traites = 0

        for fid in self.blocs_a_traiter(cible):

            traites += 1

            ajouter_version_reformulation(
                self.etude,
                fid,
                f"Passe du bloc {fid}"
            )

            if progression is not None:
                progression(fid, traites, 3)

        sauvegarder_etude(self.etude)

        return ResultatPasse(
            statut="terminee",
            nb_traites=traites,
            cout_total=0.01,
            duree_ms=5,
        )


@pytest.fixture
def page_reformulation(qapp, tmp_path):

    _p, _pv, _e, nom = construire_etude_test(tmp_path)

    etude = ouvrir_etude(tmp_path / "Etude")

    from ui.reformulation_window import (
        ReformulationWindow,
    )

    fenetre = ReformulationWindow(
        etude,
        nom,
        settings=SettingsManager(
            str(tmp_path / "reglages")
        )
    )

    fenetre.moteur = MoteurFactice(etude)

    yield fenetre, etude, nom

    fenetre.close()


class TestReformulationProgression:

    def test_relance_bloc_avec_fenetre(
        self,
        qapp,
        page_reformulation
    ):
        """
        Relance d'un bloc (individuel ou partie
        de bloc) : la fenêtre de chargement
        s'ouvre (un appel — temps écoulé seul)
        et se ferme à la fin.
        """

        fenetre, _e, _n = page_reformulation

        EspionChargement.crees = []

        with patch(
            "ui.fenetre_chargement_llm"
            ".FenetreChargementLLM",
            EspionChargement.fabriquer(),
        ), lancer_synchrone():
            fenetre.lancer_relance(1, None, None)

        assert len(EspionChargement.crees) == 1

        fenetre_cree = EspionChargement.crees[0]

        assert (
            fenetre_cree.windowTitle()
            == "Reformulation du bloc 1…"
        )

        assert "Temps écoulé" in (
            fenetre_cree.temps_label.text()
        )

        # Un seul appel : barre indéterminée.
        assert fenetre_cree.barre.maximum() == 0

        assert fenetre_cree._fermee is True
        assert fenetre.fenetre_chargement is None

        assert fenetre.moteur.appels_bloc == [1]

    def test_passe_complete_avec_progression(
        self,
        qapp,
        page_reformulation
    ):
        """
        Passe complète : la fenêtre affiche la
        barre DÉTERMINÉE (bloc k/3), le temps,
        l'estimation ; elle se ferme en fin de
        passe.
        """

        fenetre, _e, _n = page_reformulation

        EspionChargement.crees = []

        with patch(
            "ui.fenetre_chargement_llm"
            ".FenetreChargementLLM",
            EspionChargement.fabriquer(),
        ), patch(
            "ui.reformulation_window"
            ".QMessageBox.information"
        ), lancer_synchrone():
            fenetre.lancer_traitement()

        assert len(EspionChargement.crees) == 1

        fenetre_cree = EspionChargement.crees[0]

        assert (
            fenetre_cree.windowTitle()
            == "Reformulation des blocs non validés…"
        )

        # Barre DÉTERMINÉE : la progression du
        # worker a alimenté la fenêtre (3 blocs).
        assert fenetre_cree.barre.maximum() == 3
        assert fenetre_cree.barre.value() == 3
        assert "Bloc 3/3" in (
            fenetre_cree.etape_label.text()
        )

        assert fenetre_cree._fermee is True
        assert fenetre.fenetre_chargement is None

    def test_synthese_auto_avec_fenetre(
        self,
        qapp,
        page_reformulation
    ):
        """
        Synthèse d'étude déclenchée
        automatiquement (réunion entièrement
        validée) : fenêtre de chargement ouverte
        puis fermée (ici : erreur de config LLM
        factice, la fenêtre se ferme quand même).
        """

        fenetre, etude, nom = (
            page_reformulation
        )

        for fid in (1, 2, 3):
            version = ajouter_version_reformulation(
                etude,
                fid,
                f"Validé {fid}"
            )
            valider_version_reformulation(
                etude,
                fid,
                version.numero,
                "Test"
            )

        EspionChargement.crees = []

        with patch(
            "ui.fenetre_chargement_llm"
            ".FenetreChargementLLM",
            EspionChargement.fabriquer(),
        ), lancer_synchrone():
            fenetre.maj_synthese_si_reunion_validee()

        assert len(EspionChargement.crees) == 1

        assert "Synthèse" in (
            EspionChargement.crees[0].windowTitle()
        )

        assert EspionChargement.crees[0]._fermee
        assert fenetre.fenetre_chargement is None


#
# ==================================================
# Page Résumé : génération (segments), relance,
# retravail de sélection.
# ==================================================
#

class FauxServiceResume:

    def __init__(self):
        self.progression = []

    def estimer(
        self,
        reunion,
        source,
        longueur_cible=None
    ):
        return {
            "modele": "m",
            "nb_segments": 3,
            "tokens_in_estimes": 10,
            "tokens_out_estimes": 5,
            "cout_estime": 0.01,
        }

    def generer(
        self,
        reunion,
        source=None,
        longueur_cible=None,
        annulation=None,
        progression=None
    ):
        for index in (1, 2, 3):
            self.progression.append((index, 4))

            if progression is not None:
                progression(index, 4)

        self.progression.append((4, 4))

        if progression is not None:
            progression(4, 4)

        return (None, {"cout_estime": 0.01})

    def relancer(self, reunion, consigne=None, annulation=None):
        return (None, {})

    def relancer_selection(
        self,
        reunion,
        selection=None,
        consigne=None,
        annulation=None
    ):
        return (None, {})


@pytest.fixture
def page_resume_llm(qapp, tmp_path):

    from tests.unit.test_resume_synthese import (
        creer_etude_reunions,
    )

    etude, reunions = creer_etude_reunions(tmp_path)

    from services.etude_io import ajouter_version_resume
    from services.traitements.resume import (
        SOURCE_BRUTE,
    )

    ajouter_version_resume(
        etude,
        reunions[0],
        "Résumé existant.",
        source=SOURCE_BRUTE
    )

    from ui.resume_window import PageResume

    page = PageResume(etude, reunions[0])

    page.service = FauxServiceResume()

    yield page, etude, reunions[0]

    page.close()


class TestPageResumeProgression:

    def test_generation_avec_progression_segments(
        self,
        qapp,
        page_resume_llm
    ):
        """
        « Générer… » : la fenêtre s'ouvre avec la
        progression DÉTERMINÉE par segment
        (Segment k/N + assemblage final), le
        temps écoulé ; elle se ferme à la fin.
        """

        page, _e, _n = page_resume_llm

        EspionChargement.crees = []

        with patch(
            "ui.fenetre_chargement_llm"
            ".FenetreChargementLLM",
            EspionChargement.fabriquer(),
        ), patch(
            "ui.resume_window"
            ".QMessageBox.question",
            return_value=(
                QMessageBox.StandardButton.Yes
            ),
        ), lancer_synchrone():
            page.generer()

        assert len(EspionChargement.crees) == 1

        fenetre_cree = EspionChargement.crees[0]

        assert (
            fenetre_cree.windowTitle()
            == "Génération du résumé…"
        )

        # Progression DÉTERMINÉE par segment
        # (3 segments + assemblage = 4 étapes).
        assert fenetre_cree.barre.maximum() == 4
        assert fenetre_cree.barre.value() == 4
        assert "Segment 4/4" in (
            fenetre_cree.etape_label.text()
        )

        assert page.service.progression == [
            (1, 4), (2, 4), (3, 4), (4, 4)
        ]

        assert fenetre_cree._fermee is True
        assert page.fenetre_chargement is None

    def test_relances_avec_fenetre_indeterminee(
        self,
        qapp,
        page_resume_llm
    ):
        """
        « Relancer avec consigne… » : fenêtre
        ouverte (un appel — barre indéterminée,
        temps écoulé), fermée à la fin.
        """

        page, _e, _n = page_resume_llm

        EspionChargement.crees = []

        with patch(
            "ui.fenetre_chargement_llm"
            ".FenetreChargementLLM",
            EspionChargement.fabriquer(),
        ), patch(
            "ui.resume_window.QInputDialog.getText",
            return_value=("plus court", True),
        ), lancer_synchrone():
            page.relancer()

        assert len(EspionChargement.crees) == 1

        fenetre_cree = EspionChargement.crees[0]

        assert (
            fenetre_cree.windowTitle()
            == "Relance du résumé…"
        )

        # Un seul appel : barre indéterminée,
        # temps écoulé affiché.
        assert fenetre_cree.barre.maximum() == 0
        assert "Temps écoulé" in (
            fenetre_cree.temps_label.text()
        )

        assert fenetre_cree._fermee is True
        assert page.fenetre_chargement is None


#
# ==================================================
# Service résumé : progression des segments.
# ==================================================
#

class StoreFactice:

    def get_cle_llm(self, fournisseur_id):
        return f"cle-{fournisseur_id}"


class ClientFactice:

    def completions(
        self,
        prompt_systeme,
        messages,
        parametres,
        streaming_callback=None,
        annulation=None
    ):
        return ResultatCompletion(
            texte="notes",
            tokens_in=5,
            tokens_out=3,
            duree_ms=1,
            cout_estime=0.0,
            modele=parametres.modele,
            fournisseur="openai",
        )


class TestServiceResumeProgression:

    def test_progression_segments_et_assemblage(
        self,
        qapp,
        tmp_path
    ):
        """
        Source longue (3 segments simulés) :
        progression émise après chaque segment
        puis l'assemblage final — (k, total) avec
        total = segments + 1.
        """

        from tests.unit.test_resume_synthese import (
            creer_etude_reunions,
        )

        etude, reunions = creer_etude_reunions(
            tmp_path
        )

        from services.traitements.resume import (
            ServiceResume,
            SOURCE_BRUTE,
        )

        service = ServiceResume(
            etude,
            parametres_app={
                "fournisseur": "openai",
                "modele": "gpt-4.1",
            },
            credential_store=StoreFactice(),
            catalogue=catalogue_par_defaut(),
            client_factory=(
                lambda fournisseur, cle: (
                    ClientFactice()
                )
            ),
        )

        progression = []

        with patch(
            "services.traitements.resume"
            ".segmenter_source",
            return_value=["s1", "s2", "s3"],
        ):
            service.generer(
                reunions[0],
                source=SOURCE_BRUTE,
                progression=(
                    lambda etape, total: (
                        progression.append(
                            (etape, total)
                        )
                    )
                ),
            )

        assert progression == [
            (1, 4),
            (2, 4),
            (3, 4),
            (4, 4),
        ]


#
# ==================================================
# Page Étude (synthèse) et dialogue de fusion.
# ==================================================
#

class TestEtudeEtFusionProgression:

    def test_synthese_page_etude_avec_fenetre(
        self,
        qapp,
        tmp_path
    ):
        """
        « Régénérer » la synthèse sur la page
        Étude : fenêtre de chargement ouverte
        (temps écoulé), fermée à la fin.
        """

        _p, _pv, etude, nom = (
            construire_etude_test(tmp_path)
        )

        from ui.etude_window import EtudeWindow

        page = EtudeWindow(
            tmp_path / "Etude",
            settings=SettingsManager(
                str(tmp_path / "reglages")
            )
        )

        class FauxSynthese:

            def __init__(self, etude):
                pass

            def estimer(self):
                return {
                    "nb_reunions": 1,
                    "modele": "m",
                    "tokens_in_estimes": 10,
                    "tokens_out_estimes": 5,
                    "cout_estime": 0.01,
                }

            def generer(self, declencheur=None):
                return (None, {"cout_estime": 0.01})

        EspionChargement.crees = []

        try:

            with patch(
                "ui.fenetre_chargement_llm"
                ".FenetreChargementLLM",
                EspionChargement.fabriquer(),
            ), patch(
                "services.traitements.synthese"
                ".ServiceSynthese",
                FauxSynthese,
            ), patch(
                "ui.etude_window"
                ".QMessageBox.question",
                return_value=(
                    QMessageBox.StandardButton.Yes
                ),
            ), patch(
                "ui.etude_window"
                ".QMessageBox.information"
            ), lancer_synchrone():
                page.regenerer_synthese()

            assert len(EspionChargement.crees) == 1
            assert "Synthèse" in (
                EspionChargement.crees[0].windowTitle()
            )
            assert EspionChargement.crees[0]._fermee
            assert page.fenetre_chargement is None

        finally:
            page.close()

    def test_fusion_assistee_avec_fenetre(
        self,
        qapp,
        tmp_path
    ):
        """
        « Fusion assistée (IA) » : fenêtre de
        chargement pendant l'appel, fermée à la
        fin ; la proposition remplit l'éditeur.
        """

        from services.ouvrage_document import (
            generer_document,
        )

        _p, _pv, etude, nom = (
            construire_etude_test(tmp_path)
        )

        for fid in (1, 2, 3):
            v = ajouter_version_reformulation(
                etude, fid, f"Bloc {fid}"
            )
            valider_version_reformulation(
                etude, fid, v.numero, "Test"
            )

        document = generer_document(etude)

        from ui.fusion_pensees_dialog import (
            FusionPenseesDialog,
        )

        class FauxServiceFusion:

            dernier_prompt = "Prompt fusion."
            dernier_prompt_hash = "abcdef12"

            def proposer(
                self,
                texte_1,
                texte_2,
                source_1="",
                source_2="",
                annulation=None
            ):
                return ResultatCompletion(
                    texte="Paragraphe fusionné IA."
                )

        p1, p2, _p3 = document.paragraphes()

        dialogue = FusionPenseesDialog(
            None,
            p1,
            p2,
            service=FauxServiceFusion(),
        )

        EspionChargement.crees = []

        try:

            with patch(
                "ui.fenetre_chargement_llm"
                ".FenetreChargementLLM",
                EspionChargement.fabriquer(),
            ), lancer_synchrone():
                dialogue.assister()

            assert len(EspionChargement.crees) == 1
            assert EspionChargement.crees[0]._fermee
            assert dialogue.fenetre_chargement is None

            assert dialogue.texte_fusionne() == (
                "Paragraphe fusionné IA."
            )

            assert dialogue.stats()[
                "prompt_hash"
            ] == "abcdef12"

        finally:
            dialogue.close()
