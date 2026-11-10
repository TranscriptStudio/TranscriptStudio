# tests/unit/test_p20_2_sous_titres.py
"""
P20.2 — Sous-titres proposés par IA : UNE passe
LLM par section (« proposer 2 à 5 niveaux de
sous-titres sobres pour structurer ce texte ») ;
suggestions à valider/éditer, JAMAIS insérées
automatiquement.
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
from PySide6.QtWidgets import QApplication

from models.ouvrage import (
    ElementOuvrage,
    ProvenanceParagraphe,
    TYPE_PARAGRAPHE,
    TYPE_TITRE_1,
    DocumentOuvrage,
)
from services.llm.catalogue import catalogue_par_defaut
from services.llm.client import ResultatCompletion
from services.settings import SettingsManager
from services.traitements.sous_titres import (
    PROMPT_SOUS_TITRES,
    ServiceSousTitres,
    nettoyer_suggestions,
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

    def __init__(self, reponse):
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
            "modele": parametres.modele,
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
    """
    QThread.start émet « started » SYNCHRONEMENT :
    le worker tourne dans le thread de test.
    """

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


def _document_section() -> DocumentOuvrage:

    doc = DocumentOuvrage(titre="Ouvrage test")

    doc.elements.append(
        ElementOuvrage(
            id="t1_1",
            type=TYPE_TITRE_1,
            texte="Chapitre 1",
        )
    )

    for i in range(1, 4):
        doc.elements.append(
            ElementOuvrage(
                id=f"p{i}",
                type=TYPE_PARAGRAPHE,
                texte=f"Pensée {i} du chapitre.",
                provenances=[
                    ProvenanceParagraphe(
                        reunion="r1",
                        fid=i,
                        numero_reunion=1,
                        date_reunion="2026-10-13",
                        locuteurs="Philippe",
                        numero_version=1,
                        horodatage_version="2026-10-13",
                    )
                ],
            )
        )

    return doc


class TestNettoyage:

    def test_numerotation_et_puces(self):

        assert nettoyer_suggestions(
            "1. La grâce\n2) Le salut\n- L'amour\n"
            "• La foi\n\"La paix\""
        ) == [
            "La grâce",
            "Le salut",
            "L'amour",
            "La foi",
            "La paix",
        ]

    def test_borne_a_cinq(self):

        texte = "\n".join(f"Suggestion {i}" for i in range(1, 9))

        assert len(nettoyer_suggestions(texte)) == 5

    def test_vides_ecartes(self):

        assert nettoyer_suggestions("\n\n  \n") == []


class TestService:

    def test_une_passe_par_section(self, qapp, tmp_path):
        """
        UNE passe LLM sur la section ; le prompt
        système est la consigne P20.2 ; RIEN n'est
        écrit dans le document (la suggestion
        revient à l'appelant).
        """

        _p, _pv, etude, _n = construire_etude_test(
            tmp_path
        )

        client = ClientFactice(
            "1. La grâce qui sauve\n"
            "2. La foi qui agit\n"
            "3. L'espérance"
        )

        service = ServiceSousTitres(
            etude,
            parametres_app=PARAMETRES_APP,
            credential_store=StoreFactice(),
            catalogue=catalogue_par_defaut(),
            client_factory=(
                lambda fournisseur, cle: client
            ),
        )

        doc = _document_section()

        avant = [e.to_dict() for e in doc.elements]

        suggestions, stats = service.proposer(
            [p.texte for p in doc.paragraphes()]
        )

        # Un seul appel, prompt de la consigne.
        assert len(client.appels) == 1
        assert (
            client.appels[0]["prompt_systeme"]
            == PROMPT_SOUS_TITRES
        )
        assert "structurer" in (
            client.appels[0]["prompt_systeme"]
        )

        assert suggestions == [
            "La grâce qui sauve",
            "La foi qui agit",
            "L'espérance",
        ]

        assert stats["prompt_hash"]

        # Jamais d'insertion automatique.
        assert [e.to_dict() for e in doc.elements] == avant

    def test_section_vide(self, qapp, tmp_path):

        _p, _pv, etude, _n = construire_etude_test(
            tmp_path
        )

        service = ServiceSousTitres(
            etude,
            parametres_app=PARAMETRES_APP,
            credential_store=StoreFactice(),
            catalogue=catalogue_par_defaut(),
            client_factory=(
                lambda f, c: ClientFactice("x")
            ),
        )

        with pytest.raises(ValueError):
            service.proposer([])


class TestUiValidation:
    """
    Page Ouvrage : les suggestions passent par le
    dialogue de validation/édition — insertion
    UNIQUEMENT après validation explicite.
    """

    def _page(self, qapp, tmp_path):

        from services.etude_io import (
            ajouter_version_reformulation,
            ouvrir_etude,
            sauvegarder_etude,
            valider_version_reformulation,
        )
        from services.ouvrage_document import (
            generer_document,
            sauvegarder_ouvrage,
        )
        from ui.ouvrage_window import OuvrageWindow

        _p, _pv, etude, nom = (
            construire_etude_test(tmp_path)
        )

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
                f"Pensée du bloc {fid}.",
            )

            valider_version_reformulation(
                etude,
                nom,
                fid,
                numero=v.numero,
                validateur="Test",
            )

        sauvegarder_etude(etude)

        etude_disco = ouvrir_etude(tmp_path / "Etude")

        document = generer_document(etude_disco)

        # Ajoute un chapitre pour avoir une section.
        from models.ouvrage import TYPE_TITRE_1

        document.elements.insert(
            0,
            ElementOuvrage(
                id="t1_1",
                type=TYPE_TITRE_1,
                texte="Chapitre 1",
            ),
        )

        sauvegarder_ouvrage(
            document,
            etude_disco.dossier
        )

        fenetre = OuvrageWindow(
            etude_disco,
            settings=SettingsManager(
                str(tmp_path / "reglages")
            ),
        )

        return fenetre

    def test_insertion_apres_validation(self, qapp, tmp_path):

        fenetre = self._page(qapp, tmp_path)

        try:

            class ServiceFictif:

                def __init__(self, etude):
                    pass

                def proposer(self, textes):
                    assert textes
                    return (
                        [
                            "La grâce",
                            "La foi",
                        ],
                        {"cout_estime": 0.001},
                    )

            class DialogueFictif:

                def __init__(
                    self,
                    suggestions,
                    titre_section="",
                    parent=None
                ):
                    self.suggestions = suggestions

                def exec(self):
                    from PySide6.QtWidgets import QDialog
                    return QDialog.DialogCode.Accepted

                def suggestions_retenues(self):
                    # Édition + validation : un seul
                    # retenu, édité.
                    return ["La grâce (édité)"]

            # Sélectionne le chapitre (section).
            fenetre.arbre.setCurrentItem(
                fenetre.arbre.topLevelItem(0)
            )

            with patch(
                "services.traitements.sous_titres"
                ".ServiceSousTitres",
                ServiceFictif,
            ), patch(
                "ui.sous_titres_dialog.SousTitresDialog",
                DialogueFictif,
            ), patch(
                "ui.ouvrage_window.QMessageBox.information"
            ), lancer_synchrone():

                fenetre.proposer_sous_titres()

            # Inséré après le titre, UNE seule fois
            # (celle validée/éditée).
            sous_titres = [
                e for e in fenetre.document.elements
                if e.type == "sous_titre"
            ]

            assert len(sous_titres) == 1
            assert sous_titres[0].texte == (
                "La grâce (édité)"
            )

            position = fenetre.document.elements.index(
                sous_titres[0]
            )

            assert (
                fenetre.document.elements[position - 1]
                .type
                == TYPE_TITRE_1
            )

        finally:
            fenetre.close()

    def test_pas_d_insertion_si_annule(self, qapp, tmp_path):

        fenetre = self._page(qapp, tmp_path)

        try:

            class ServiceFictif:

                def __init__(self, etude):
                    pass

                def proposer(self, textes):
                    return (
                        ["La grâce", "La foi"],
                        {"cout_estime": 0.0},
                    )

            class DialogueAnnule:

                def __init__(
                    self,
                    suggestions,
                    titre_section="",
                    parent=None
                ):
                    pass

                def exec(self):
                    from PySide6.QtWidgets import QDialog
                    return QDialog.DialogCode.Rejected

                def suggestions_retenues(self):
                    return []

            avant = [
                e.to_dict() for e in fenetre.document.elements
            ]

            fenetre.arbre.setCurrentItem(
                fenetre.arbre.topLevelItem(0)
            )

            with patch(
                "services.traitements.sous_titres"
                ".ServiceSousTitres",
                ServiceFictif,
            ), patch(
                "ui.sous_titres_dialog.SousTitresDialog",
                DialogueAnnule,
            ), lancer_synchrone():

                fenetre.proposer_sous_titres()

            # Annulé : RIEN n'est inséré.
            assert [
                e.to_dict() for e in fenetre.document.elements
            ] == avant

        finally:
            fenetre.close()
