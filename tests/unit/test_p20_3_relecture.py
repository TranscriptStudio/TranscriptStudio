# tests/unit/test_p20_3_relecture.py
"""
P20.3 — Aide à l'écriture globale, emplacement
UNIQUE page Ouvrage (amendement du 09/11 : plus
rien sur la page Étude) :

- récurrence d'emphase (lexique paramétrable,
  sans LLM) : comptage par bloc/réunion/
  intervenant, signalement des densités anormales
  et systématisations ;
- expressions récurrentes (local sans LLM,
  passe LLM optionnelle sur les familles
  candidates), occurrences cliquables ;
- incohérences/redondances par passe LLM par
  section à la demande ;
- présélection locale (P20.6g) des pensées
  redondantes, liens vers les paragraphes.

Dans tous les cas : signalement uniquement,
jamais de réécriture.
"""

import os

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

pytestmark = pytest.mark.qt

from PySide6.QtWidgets import QApplication

from models.ouvrage import (
    ElementOuvrage,
    ProvenanceParagraphe,
    TYPE_PARAGRAPHE,
    DocumentOuvrage,
)
from services.llm.catalogue import catalogue_par_defaut
from services.llm.client import ResultatCompletion
from services.relecture import (
    emphase_ouvrage,
    expressions_recurrentes_ouvrage,
    familles_expressions,
    lier_pensees_aux_paragraphes,
    normaliser_pour_relecture,
    preselectionner_pensees_redondantes,
)
from services.settings import SettingsManager
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


@pytest.fixture(scope="module")
def qapp():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    yield application


def _prov(reunion, fid, locuteurs="Philippe"):
    return ProvenanceParagraphe(
        reunion=reunion,
        fid=fid,
        numero_reunion=1,
        date_reunion="2026-10-13",
        locuteurs=locuteurs,
        numero_version=1,
        horodatage_version="2026-10-13",
    )


def _document_relecture() -> DocumentOuvrage:
    """
    6 paragraphes sur 3 réunions : p1 (r1) contient
    2× « puissamment », p2 (r2) et p3 (r3) 1× ; les
    p2/p4/p5 partagent l'expression « ce qui s'offre
    à nos cœurs » (r2 + r3), p6 (r3) la variante
    « à la foi ».
    """

    doc = DocumentOuvrage(titre="Ouvrage test")

    textes = [
        ("p1", "r1", 1, "Puissamment, Dieu agit puissamment.", "Philippe"),
        ("p2", "r2", 2, "Ce qui s'offre à nos cœurs est précieux.", "Daniel"),
        ("p3", "r3", 3, "La grâce est puissamment belle. Ce qui s'offre à nos cœurs.", "Philippe"),
        ("p4", "r2", 4, "Ce qui s'offre à la foi encore, et à nos cœurs.", "Daniel"),
        ("p5", "r3", 5, "Ce qui s'offre à nos cœurs toujours.", "Marie"),
        ("p6", "r3", 6, "Ce qui s'offre à la foi aussi.", "Marie"),
    ]

    for id_, reunion, fid, texte, loc in textes:
        doc.elements.append(
            ElementOuvrage(
                id=id_,
                type=TYPE_PARAGRAPHE,
                texte=texte,
                provenances=[_prov(reunion, fid, loc)],
            )
        )

    return doc


class TestNormalisation:

    def test_references_masquees(self):
        """
        Normalisation : minuscules, ponctuation
        retirée, références bibliques masquées.
        """

        assert normaliser_pour_relecture(
            "En Luc 1:5, il est dit : PUISSAMMENT !"
        ) == "en il est dit puissamment"


class TestEmphase:

    def test_comptage_et_signalements(self):

        doc = _document_relecture()

        resultat = emphase_ouvrage(doc)

        # Comptage par paragraphe.
        p1 = next(
            e for e in resultat["par_paragraphe"]
            if e["id"] == "p1"
        )

        assert p1["intensifs"]["puissamment"] == 2

        # Total avec occurrences cliquables.
        total = resultat["totaux"]["puissamment"]

        assert total["occurrences"] == 3
        assert set(total["paragraphes"]) == {
            "p1", "p3"
        }
        assert set(total["reunions"]) == {"r1", "r3"}

        # Signalement : p1 (densité anormale : 2×
        # dans un même paragraphe).
        assert "p1" in resultat["signales"]

    def test_lexique_parametrable(self):

        doc = _document_relecture()

        resultat = emphase_ouvrage(
            doc,
            lexique=["grâce"]
        )

        assert "grâce" in resultat["totaux"]
        assert "puissamment" not in resultat["totaux"]


class TestExpressionsRecurrentes:

    def test_occurrences_cliquables(self):

        doc = _document_relecture()

        candidats = expressions_recurrentes_ouvrage(
            doc,
            occurrences_min=2,
            reunions_min=2
        )

        expr = next(
            c for c in candidats
            if "ce qui s'offre à nos cœurs" in c["expression"]
        )

        # Occurrences cliquables (ids de
        # paragraphes) + réunions + locuteurs.
        assert set(expr["paragraphes"]) == {
            "p2", "p3", "p5"
        }
        assert set(expr["reunions"]) == {"r2", "r3"}
        assert "Daniel" in expr["locuteurs"]

    def test_familles_par_mots_communs(self):

        doc = _document_relecture()

        candidats = expressions_recurrentes_ouvrage(
            doc,
            occurrences_min=2,
            reunions_min=2
        )

        familles = familles_expressions(candidats)

        famille = next(
            f for f in familles
            if len(f["expressions"]) > 1
        )

        # « ce qui s'offre à nos cœurs / à la foi »
        # regroupées (mots communs « ce qui s'offre à »).
        assert any(
            "nos cœurs" in e for e in famille["expressions"]
        )
        assert any(
            "la foi" in e for e in famille["expressions"]
        )

    def test_concentree_dans_une_reunion_non_signalee(self):
        """
        Présente dans UNE seule réunion = insistance
        légitime, non signalée (répartition).
        """

        doc = DocumentOuvrage(titre="t")

        for i in range(1, 5):
            doc.elements.append(
                ElementOuvrage(
                    id=f"p{i}",
                    type=TYPE_PARAGRAPHE,
                    texte=(
                        "Phrase très particulière et "
                        "remarquable du même bloc."
                    ),
                    provenances=[_prov("r1", i)],
                )
            )

        assert expressions_recurrentes_ouvrage(doc) == []


class TestPenseesRedondantes:
    """
    P20.6g : présélection LOCALE sans LLM des
    pensées redondantes de la synthèse, puis liens
    vers les paragraphes de l'ouvrage.
    """

    def test_preselection_locale(self):

        synthese = (
            "R1 — Philippe : la grâce nous sauve "
            "entièrement.\n"
            "R1 — Daniel : le salut vient par la "
            "grâce seule.\n"
            "R2 — Philippe : la grâce nous sauve "
            "entièrement encore.\n"
            "R2 — Marie : pensée tout à fait "
            "différente ici."
        )

        groupes = preselectionner_pensees_redondantes(
            synthese
        )

        assert groupes

        groupe = groupes[0]

        assert len(groupe["phrases"]) >= 2
        assert any(
            "grâce nous sauve" in p
            for p in groupe["phrases"]
        )

    def test_liens_vers_paragraphes(self):

        doc = _document_relecture()

        groupes = [
            {
                "phrases": [
                    "La grâce est puissamment belle.",
                    "La grâce est puissamment belle.",
                ],
                "normalisees": [
                    normaliser_pour_relecture(
                        "La grâce est puissamment belle."
                    )
                ] * 2,
            }
        ]

        lies = lier_pensees_aux_paragraphes(doc, groupes)

        # p3 contient la pensée.
        assert "p3" in lies[0]["paragraphes"]


class TestServiceRelecture:

    def test_analyse_section_un_appel(self, qapp, tmp_path):

        from services.traitements.relecture import (
            ServiceRelecture,
        )

        _p, _pv, etude, _n = construire_etude_test(
            tmp_path
        )

        client = ClientFactice(
            "Aucun signalement."
        )

        service = ServiceRelecture(
            etude,
            parametres_app=PARAMETRES_APP,
            credential_store=StoreFactice(),
            catalogue=catalogue_par_defaut(),
            client_factory=(
                lambda f, c: client
            ),
        )

        rapport, stats = service.analyser_section(
            ["Texte de la section."]
        )

        assert len(client.appels) == 1

        # Signalement uniquement : le prompt
        # interdit la réécriture.
        assert "ne réécris rien" in (
            client.appels[0]["prompt_systeme"]
        )

        assert rapport == "Aucun signalement."

    def test_confirmer_redondances(self, qapp, tmp_path):

        from services.traitements.relecture import (
            ServiceRelecture,
        )

        _p, _pv, etude, _n = construire_etude_test(
            tmp_path
        )

        client = ClientFactice("Groupe 1 : confirmé")

        service = ServiceRelecture(
            etude,
            parametres_app=PARAMETRES_APP,
            credential_store=StoreFactice(),
            catalogue=catalogue_par_defaut(),
            client_factory=(
                lambda f, c: client
            ),
        )

        rapport, _stats = service.confirmer_redondances(
            [{"phrases": ["a", "b"]}]
        )

        assert len(client.appels) == 1
        assert "Groupe 1" in client.appels[0]["message"]
        assert rapport == "Groupe 1 : confirmé"


class TestUiPageOuvrage:
    """
    Page Ouvrage : les aides à la relecture y vivent
    (boutons, filtres, résultats cliquables) — et la
    détection ne modifie JAMAIS l'ouvrage ni la
    synthèse.
    """

    def test_panneau_et_detection_locale(self, qapp, tmp_path):

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

        textes = [
            "Puissamment Dieu agit puissamment ici.",
            "La pensée du deuxième bloc.",
            "Une troisième pensée.",
        ]

        for i, fid in enumerate(fids):

            v = ajouter_version_reformulation(
                etude,
                nom,
                fid,
                textes[i % len(textes)],
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

        try:

            for attr in (
                "emphases_button",
                "expressions_button",
                "coherence_button",
                "redondances_button",
                "resultats_arbre",
                "filtre_reunion",
                "filtre_chapitre",
                "filtre_locuteur",
            ):
                assert hasattr(fenetre, attr)

            avant = [
                e.to_dict() for e in fenetre.document.elements
            ]

            synthese_avant = (
                etude_disco.synthese.versions[-1].texte
                if etude_disco.synthese.versions
                else None
            )

            # Détection locale (emphases) : remplit
            # l'arbre de résultats avec des ids
            # cliquables.
            fenetre.afficher_emphases()

            assert fenetre.resultats_arbre.topLevelItemCount() > 0

            # Jamais de modification de l'ouvrage ni
            # de la synthèse.
            assert [
                e.to_dict() for e in fenetre.document.elements
            ] == avant

            assert (
                etude_disco.synthese.versions[-1].texte
                if etude_disco.synthese.versions
                else None
            ) == synthese_avant

        finally:
            fenetre.close()
