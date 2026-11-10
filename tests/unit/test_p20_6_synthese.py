# tests/unit/test_p20_6_synthese.py
"""
P20.6 — Synthèse d'étude repensée (feuille
d'autorité SPEC_PAGE_ETUDE_ET_SYNTHESE_MODIFS_
2026-11-09d §3, invariants 8-14) :

8.  aucune écriture automatique de la synthèse à
    la validation d'une réunion ;
9.  « Alimenter la synthèse globale » proposée
    uniquement pour une réunion à blocs validés ;
    l'opération n'altère pas les contributions des
    autres réunions ;
10. ré-alimenter une réunion déjà intégrée
    remplace exactement sa contribution (aucun
    doublon), après avertissement confirmé ;
11. « (Re)générer » exige une confirmation après
    avertissement de remplacement intégral ;
12. « Annuler l'édition » visible en mode édition
    uniquement, restaure le texte antérieur ;
13. détection des pensées redondantes : jamais de
    modification (ouvrage ni synthèse), présélection
    locale sans coût LLM ;
14. la synthèse reste injectable comme contexte
    dans la reformulation des blocs cochés.
"""

import contextlib
import os
from unittest.mock import patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

pytestmark = pytest.mark.qt

from PySide6.QtCore import QObject, QThread
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
from services.prompts import (
    USAGE_SYNTHESE_ETUDE,
    lire_defaut_embarque,
    lire_bibliotheque,
)
from services.settings import SettingsManager
from services.traitements.synthese import (
    ServiceSynthese,
    assembler_blocs,
    extraire_blocs,
    marquer_reunion,
    reunions_a_blocs_valides,
)
from tests.unit.test_reformulation_ui import (
    construire_etude_test,
)


PARAMETRES_APP = {
    "fournisseur": "openai",
    "modele": "gpt-4.1",
    "temperature": 0.3,
    "temperatures": {"reformulation": 0.3},
}


class StoreFactice:

    def get_cle_llm(self, fournisseur_id):
        return f"cle-{fournisseur_id}"


class ClientFactice:

    def __init__(self, reponse=""):
        self.appels = []
        self.reponse = reponse

    def completions(
        self,
        prompt_systeme,
        messages,
        parametres,
        streaming_callback=None,
        annulation=None
    ):
        self.appels.append({
            "prompt_systeme": prompt_systeme,
            "message": messages[0]["content"],
        })

        return ResultatCompletion(
            texte=self.reponse,
            tokens_in=10,
            tokens_out=5,
            duree_ms=5,
            cout_estime=0.01,
            modele=parametres.modele,
            fournisseur="openai",
        )


@contextlib.contextmanager
def lancer_synchrone():
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


@pytest.fixture(scope="module")
def qapp():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    yield application


def _etude_2_reunions_validees(tmp_path):
    """
    Étude de DEUX réunions, toutes deux entièrement
    validées (3 blocs chacune).
    """

    import shutil

    _p, _pv, etude, nom1 = construire_etude_test(
        tmp_path
    )

    dossier2 = tmp_path / "reunion_2"

    shutil.copytree(
        tmp_path / "2026-10-13_Luc1b",
        dossier2
    )

    # PAS de tier copié (les FID du registre copied
    # appartiendraient à la première réunion).
    shutil.rmtree(
        dossier2 / "transcriptstudio",
        ignore_errors=True
    )

    from services.etude_io import (
        ajouter_reunion,
        enregistrer_decoupage,
    )
    from services.decoupage import (
        generer_decoupage,
    )
    from services.project_io import load_project

    nom2 = ajouter_reunion(
        etude,
        dossier2,
        "Chapitre 2"
    )

    # Segmentation de la seconde réunion (sinon
    # aucun bloc actif -> jamais validée).
    projet2 = load_project(
        str(dossier2 / "project.sttproj")
    )

    decoupage2 = generer_decoupage(
        etude,
        nom2,
        projet2
    )

    enregistrer_decoupage(etude, decoupage2)

    for nom in (nom1, nom2):

        fids = [
            e.fid
            for e in etude.registre.entrees.values()
            if e.reunion == nom
        ]

        for fid in fids:

            v = ajouter_version_reformulation(
                etude,
                nom,
                fid,
                f"Pensée du bloc {fid} de {nom}.",
            )

            valider_version_reformulation(
                etude,
                nom,
                fid,
                numero=v.numero,
                validateur="Test",
            )

    sauvegarder_etude(etude)

    return ouvrir_etude(tmp_path / "Etude"), nom1, nom2


def _service(etude, client, tmp_path):
    return ServiceSynthese(
        etude,
        parametres_app=PARAMETRES_APP,
        credential_store=StoreFactice(),
        catalogue=catalogue_par_defaut(),
        client_factory=(
            lambda fournisseur, cle: client
        ),
        dossier_prompts=tmp_path / "prompts",
    )


class TestPromptEditable:

    def test_prompt_dedie_bibliotheque(self, tmp_path):
        """
        P20.6a : prompt dédié éditable
        prompts/synthese_etude.md dans la
        bibliothèque des réglages.
        """

        dossier = tmp_path / "prompts"

        # Défaut embarqué (lecture ne crée rien).
        texte, perso = lire_bibliotheque(
            USAGE_SYNTHESE_ETUDE,
            dossier
        )

        assert not perso
        assert texte == lire_defaut_embarque(
            USAGE_SYNTHESE_ETUDE
        )
        assert not (dossier / "synthese_etude.md").exists()

        assert "phrases courtes" in texte
        assert "locuteur" in texte.lower()


class TestBlocsContributions:

    def test_extraire_assembler(self):

        texte = (
            f"{marquer_reunion('r1')}\n"
            "Philippe : la grâce.\n\n"
            f"{marquer_reunion('r2')}\n"
            "Daniel : la foi."
        )

        blocs = extraire_blocs(texte)

        assert set(blocs) == {"r1", "r2"}

        assert assembler_blocs(blocs, ["r2", "r1"]) == (
            f"{marquer_reunion('r2')}\n"
            "Daniel : la foi.\n\n"
            f"{marquer_reunion('r1')}\n"
            "Philippe : la grâce."
        )


class TestAlimentationIncrementale:
    """
    Invariants 9 et 10.
    """

    def test_alimenter_ajoute_sans_toucher_le_reste(
        self,
        qapp,
        tmp_path
    ):

        etude, nom1, nom2 = _etude_2_reunions_validees(
            tmp_path
        )

        assert set(reunions_a_blocs_valides(etude)) == {
            nom1, nom2
        }

        client = ClientFactice(
            "Philippe : la grâce nous sauve."
        )

        service = _service(etude, client, tmp_path)

        # Alimente r1.
        version, stats, remplace = service.alimenter(
            nom1
        )

        assert remplace is False
        assert version.declencheur == "alimentation"

        texte1 = etude.synthese.versions[-1].texte

        assert marquer_reunion(nom1) in texte1
        assert nom1 in etude.synthese.contributions

        # Empreinte mémorisée (P20.6c).
        assert etude.synthese.contributions[nom1][
            "empreinte"
        ]

        # Alimente r2 : la contribution de r1 est
        # intacte (invariant 9).
        client2 = ClientFactice(
            "Daniel : la foi agit."
        )

        service2 = _service(etude, client2, tmp_path)

        service2.alimenter(nom2)

        texte2 = etude.synthese.versions[-1].texte

        blocs = extraire_blocs(texte2)

        assert set(blocs) == {nom1, nom2}
        assert "la grâce nous sauve" in blocs[nom1]
        assert "la foi agit" in blocs[nom2]

        # Prompt = bibliothèque éditable (P20.6a).
        assert client.appels[0]["prompt_systeme"] == (
            lire_defaut_embarque(USAGE_SYNTHESE_ETUDE)
        )

    def test_realimenter_remplace_exactement(
        self,
        qapp,
        tmp_path
    ):

        etude, nom1, nom2 = _etude_2_reunions_validees(
            tmp_path
        )

        client = ClientFactice("Première version.")

        _service(etude, client, tmp_path).alimenter(nom1)

        # Ré-alimente r1 avec une nouvelle réponse.
        client2 = ClientFactice("Seconde version.")

        version, stats, remplace = _service(
            etude,
            client2,
            tmp_path
        ).alimenter(nom1)

        # Avertissement : remplacement (invariant 10).
        assert remplace is True

        texte = etude.synthese.versions[-1].texte

        blocs = extraire_blocs(texte)

        # Aucun doublon : UNE seule contribution r1,
        # remplacée exactement.
        assert list(blocs).count(nom1) == 1
        assert "Seconde version." in blocs[nom1]
        assert "Première version." not in texte

    def test_reunion_non_validee_refusee(
        self,
        qapp,
        tmp_path
    ):

        from services.etude_io import EtudeError

        _p, _pv, etude, nom = construire_etude_test(
            tmp_path
        )

        # Aucun bloc validé.
        assert reunions_a_blocs_valides(etude) == []

        client = ClientFactice("x")

        service = _service(etude, client, tmp_path)

        with pytest.raises(EtudeError):
            service.alimenter(nom)

        assert not client.appels

    def test_regenerer_remplacement_integral(
        self,
        qapp,
        tmp_path
    ):

        etude, nom1, nom2 = _etude_2_reunions_validees(
            tmp_path
        )

        client = ClientFactice(
            f"{marquer_reunion(nom1)}\nA.\n\n"
            f"{marquer_reunion(nom2)}\nB."
        )

        version, stats = _service(
            etude,
            client,
            tmp_path
        ).generer(declencheur="manuel")

        assert set(
            etude.synthese.contributions
        ) == {nom1, nom2}

        # Une seule version, toutes contributions.
        assert len(etude.synthese.versions) == 1

        blocs = extraire_blocs(
            etude.synthese.versions[-1].texte
        )

        assert set(blocs) == {nom1, nom2}


class TestBlocsRevalides:
    """
    P20.6c : avertissement « blocs re-validés depuis
    la dernière alimentation ».
    """

    def test_detection(self, qapp, tmp_path):

        etude, nom1, _nom2 = _etude_2_reunions_validees(
            tmp_path
        )

        client = ClientFactice("Contribution.")

        service = _service(etude, client, tmp_path)

        service.alimenter(nom1)

        assert service.blocs_revalides() == []

        # Re-valide un bloc de r1 (nouvelle version) :
        # l'empreinte change.
        fids = [
            e.fid
            for e in etude.registre.entrees.values()
            if e.reunion == nom1
        ]

        v = ajouter_version_reformulation(
            etude,
            nom1,
            fids[0],
            "Texte re-travaillé.",
        )

        valider_version_reformulation(
            etude,
            nom1,
            fids[0],
            numero=v.numero,
            validateur="Test",
        )

        assert service.blocs_revalides() == [nom1]


class TestUiPageEtude:
    """
    Invariants 9, 10, 11, 12 côté page Étude.
    """

    def _page(self, qapp, tmp_path):

        from ui.etude_window import EtudeWindow

        etude, nom1, nom2 = _etude_2_reunions_validees(
            tmp_path
        )

        fenetre = EtudeWindow(
            tmp_path / "Etude",
            settings=SettingsManager(
                str(tmp_path / "reglages")
            )
        )

        return fenetre, etude, nom1, nom2

    def test_menu_alimenter_uniquement_si_validee(
        self,
        qapp,
        tmp_path
    ):
        """
        Invariant 9 : « Alimenter la synthèse
        globale » n'est proposée que pour une
        réunion à blocs validés.
        """

        fenetre, etude, nom1, nom2 = self._page(
            qapp,
            tmp_path
        )

        try:

            # nom1 et nom2 sont validées : action
            # proposée.
            for index in range(
                fenetre.reunions_liste.count()
            ):
                item = fenetre.reunions_liste.item(
                    index
                )
                nom = item.data(0x0100)

                menu = fenetre._construire_menu_tuile(
                    nom,
                    item
                )

                textes = [
                    a.text() for a in menu.actions()
                ]

                assert (
                    "Alimenter la synthèse globale"
                    in textes
                )

            # Réunion non validée (nouvelle étude
            # sans validation) : pas d'action.
            (tmp_path / "autre").mkdir()

            _p, _pv, etude2, nom = (
                construire_etude_test(
                    tmp_path / "autre"
                )
            )

            from ui.etude_window import EtudeWindow

            page2 = EtudeWindow(
                tmp_path / "autre" / "Etude",
                settings=SettingsManager(
                    str(tmp_path / "r2")
                ),
            )

            try:

                item = page2.reunions_liste.item(0)

                menu = page2._construire_menu_tuile(
                    item.data(0x0100),
                    item
                )

                textes = [
                    a.text() for a in menu.actions()
                ]

                assert (
                    "Alimenter la synthèse globale"
                    not in textes
                )

            finally:
                page2.close()

        finally:
            fenetre.close()

    def test_realimentation_avec_avertissement(
        self,
        qapp,
        tmp_path
    ):
        """
        Invariant 10 : ré-alimenter une réunion déjà
        intégrée passe par un avertissement confirmé.
        """

        fenetre, etude, nom1, _nom2 = self._page(
            qapp,
            tmp_path
        )

        try:

            # Simule une contribution existante.
            fenetre.etude.synthese.contributions[nom1] = {
                "empreinte": "abc",
                "blocs": [1, 2, 3],
                "horodatage": "2026-11-09",
                "declencheur": "alimentation",
            }

            class FauxSynthese:

                def __init__(self, etude):
                    pass

                def estimer(self, reunions=None):
                    return {
                        "nb_reunions": 1,
                        "modele": "m",
                        "tokens_in_estimes": 1,
                        "tokens_out_estimes": 1,
                        "cout_estime": 0.0,
                    }

                def alimenter(self, nom):
                    return (None, {"cout_estime": 0.0}, True)

            questions = []

            def _question(parent, titre, texte, *a, **k):
                questions.append(texte)
                return QMessageBox.StandardButton.Yes

            with patch(
                "services.traitements.synthese"
                ".ServiceSynthese",
                FauxSynthese,
            ), patch(
                "ui.etude_window.QMessageBox.question",
                _question,
            ), patch(
                "ui.etude_window.QMessageBox.information"
            ), patch(
                "ui.fenetre_chargement_llm"
                ".FenetreChargementLLM"
            ), lancer_synchrone():

                fenetre.alimenter_synthese(nom1)

            # Avertissement de remplacement + demande
            # de confirmation.
            assert any(
                "REMPLACÉE" in q for q in questions
            )

        finally:
            fenetre.close()

    def test_regenerer_confirmation_remplacement_integral(
        self,
        qapp,
        tmp_path
    ):
        """
        Invariant 11 : « (Re)générer » exige une
        confirmation après l'avertissement de
        remplacement intégral.
        """

        from services.etude_io import (
            ajouter_version_synthese,
        )

        fenetre, etude, nom1, _nom2 = self._page(
            qapp,
            tmp_path
        )

        try:

            # Une synthèse existe déjà (sur l'instance
            # de la fenêtre).
            ajouter_version_synthese(
                fenetre.etude,
                "Synthèse existante.",
                declencheur="manuel",
            )

            assert (
                fenetre.synthese_regenerer_button.text()
                == "(Re)générer la synthèse…"
            )

            class FauxSynthese:

                def __init__(self, etude):
                    pass

                def estimer(self):
                    return {
                        "nb_reunions": 2,
                        "modele": "m",
                        "tokens_in_estimes": 1,
                        "tokens_out_estimes": 1,
                        "cout_estime": 0.0,
                    }

                def generer(self, declencheur=None):
                    return (None, {"cout_estime": 0.0})

            textes = []

            def _question(parent, titre, texte, *a, **k):
                textes.append(texte)
                # Annulation : PAS de confirmation.
                return QMessageBox.StandardButton.No

            with patch(
                "services.traitements.synthese"
                ".ServiceSynthese",
                FauxSynthese,
            ), patch(
                "ui.etude_window.QMessageBox.question",
                _question,
            ), lancer_synchrone():

                fenetre.regenerer_synthese()

            # Avertissement de remplacement intégral
            # affiché ; annulation -> rien lancé (la
            # seule version reste la version initiale).
            assert any(
                "ENTIÈREMENT" in t and "REMPLACÉE" in t
                for t in textes
            )

            assert len(
                fenetre.etude.synthese.versions
            ) == 1

        finally:
            fenetre.close()

    def test_annuler_edition(self, qapp, tmp_path):
        """
        Invariant 12 : « Annuler l'édition » n'est
        visible qu'en mode édition et restaure le
        texte antérieur (rien de consigné).
        """

        from services.etude_io import (
            ajouter_version_synthese,
        )

        fenetre, etude, _n1, _n2 = self._page(
            qapp,
            tmp_path
        )

        try:

            ajouter_version_synthese(
                fenetre.etude,
                "Texte de synthèse.",
                declencheur="manuel",
            )

            fenetre.maj_synthese()

            # Hors mode édition : masqué.
            assert not (
                fenetre.synthese_annuler_button
                .isVisibleTo(fenetre)
            )

            fenetre.editer_synthese()

            # En mode édition : visible, à côté de la
            # sauvegarde.
            assert (
                fenetre.synthese_annuler_button
                .isVisibleTo(fenetre)
            )

            assert (
                fenetre.synthese_sauver_button
                .isVisibleTo(fenetre)
            )

            nb_versions = len(etude.synthese.versions)

            fenetre.synthese_edit.setPlainText(
                "Texte modifié."
            )

            fenetre.annuler_edition_synthese()

            # Texte antérieur restauré, mode édition
            # quitté, rien consigné.
            assert (
                fenetre.synthese_edit.toPlainText()
                == "Texte de synthèse."
            )

            assert fenetre.synthese_edit.isReadOnly()

            assert len(
                etude.synthese.versions
            ) == nb_versions

            assert not (
                fenetre.synthese_annuler_button
                .isVisibleTo(fenetre)
            )

        finally:
            fenetre.close()


class TestInjectionContexte:
    """
    Invariant 14 : la synthèse (nouveau format)
    reste injectable comme contexte dans la
    reformulation des blocs cochés (mécanisme P15
    inchangé).
    """

    def test_texte_synthese_injecte(self, qapp, tmp_path):

        from services.etude_io import (
            ajouter_version_synthese,
        )
        from services.traitements.moteur import (
            MoteurTraitements,
        )

        _p, _pv, etude, nom = construire_etude_test(
            tmp_path
        )

        ajouter_version_synthese(
            etude,
            "=== Réunion r1 ===\n"
            "Philippe : la grâce nous sauve.",
            declencheur="alimentation",
        )

        moteur = MoteurTraitements(etude, nom)

        # Le moteur lit la dernière version de la
        # synthèse comme contexte (P15 inchangé).
        assert moteur._texte_synthese() == (
            "=== Réunion r1 ===\n"
            "Philippe : la grâce nous sauve."
        )


class TestPenseesRedondantesSansLlm:
    """
    Invariant 13 : la détection des pensées
    redondantes ne modifie jamais l'ouvrage ni la
    synthèse ; la présélection locale n'entraîne
    aucun coût LLM.
    """

    def test_detection_locale_sans_llm(self, qapp, tmp_path):

        from services.etude_io import (
            ajouter_version_synthese,
        )
        from services.ouvrage_document import (
            generer_document,
            sauvegarder_ouvrage,
        )
        from ui.ouvrage_window import OuvrageWindow

        etude, nom1, _nom2 = _etude_2_reunions_validees(
            tmp_path
        )

        # Synthèse avec une pensée redondante.
        ajouter_version_synthese(
            etude,
            "R1 — Philippe : la grâce nous sauve "
            "entièrement.\n"
            "R2 — Daniel : la grâce nous sauve "
            "entièrement aussi.",
            declencheur="alimentation",
        )

        document = generer_document(etude)

        sauvegarder_ouvrage(document, etude.dossier)

        fenetre = OuvrageWindow(
            etude,
            settings=SettingsManager(
                str(tmp_path / "reglages")
            ),
        )

        try:

            avant_doc = [
                e.to_dict() for e in fenetre.document.elements
            ]

            avant_synth = (
                etude.synthese.versions[-1].texte
            )

            class ServiceInterdit:

                def __init__(self, *a, **k):
                    raise AssertionError(
                        "Pas de LLM pour la "
                        "présélection"
                    )

            with patch(
                "services.traitements.relecture"
                ".ServiceRelecture",
                ServiceInterdit,
            ), patch(
                "ui.ouvrage_window.QMessageBox.question",
                return_value=QMessageBox.StandardButton.No,
            ), patch(
                "ui.ouvrage_window.QMessageBox.information"
            ):

                fenetre.detecter_pensees_redondantes()

            # Groupes proposés (présélection locale).
            assert fenetre.resultats_arbre.topLevelItemCount() > 0

            # Jamais de modification.
            assert [
                e.to_dict() for e in fenetre.document.elements
            ] == avant_doc

            assert (
                etude.synthese.versions[-1].texte
                == avant_synth
            )

        finally:
            fenetre.close()
