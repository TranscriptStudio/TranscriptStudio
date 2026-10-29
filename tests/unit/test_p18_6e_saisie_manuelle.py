"""
Tests P18.6e — saisie manuelle sans IA (spec
navigation §7) : tout bloc reformulé et tout résumé
est saisissable directement, sans appel LLM ;
invariant §9.6 : une saisie manuelle validée est
équivalente à un résultat IA validé (statut,
compilation de l'ouvrage, aucune discrimination
de provenance) ; invariant §7.3 : toute saisie
manuelle est tracée au log des opérations
(type « édition manuelle »).
"""

import os

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from PySide6.QtWidgets import QApplication

from services.etude_io import (
    ajouter_version_reformulation,
    ajouter_version_resume,
    valider_version_reformulation,
    valider_version_resume,
)
from services.export_ouvrage import (
    assembler_ouvrage,
)
from tests.unit.test_reformulation_ui import (
    construire_etude_test,
)


@pytest.fixture(scope="module")
def qapp():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    yield application


@pytest.fixture
def etude_reunion(tmp_path):

    _p, _pv, etude, nom = (
        construire_etude_test(tmp_path)
    )

    fids = [
        entree.fid
        for entree in (
            etude.registre.entrees.values()
        )
        if entree.reunion == nom
    ]

    return etude, nom, fids, tmp_path


#
# ==================================================
# Reformulation : bloc saisi à la main.
# ==================================================
#

class TestSaisieManuelleReformulation:

    def test_saisie_puis_validation(
        self,
        etude_reunion
    ):
        """
        Un bloc jamais traité par le LLM peut être
        saisi entièrement à la main : édition →
        sauvegarde (version edition_manuelle) →
        validation. Même statut qu'un résultat IA.
        """

        etude, nom, fids, _t = etude_reunion

        version = ajouter_version_reformulation(
            etude,
            fids[0],
            "Texte entièrement saisi à la main, "
            "sans aucun appel LLM.",
            type_version="edition_manuelle"
        )

        assert version.type == "edition_manuelle"
        assert version.stats is None

        valider_version_reformulation(
            etude,
            fids[0],
            version.numero,
            validateur="Test"
        )

        # Statut identique à un résultat IA validé :
        # le bloc validé fait passer la réunion
        # « en cours » (d'autres blocs restent à
        # faire — même règle pour une version IA).
        from services.avancement import (
            EN_COURS,
            etat_reformulation,
        )

        assert etat_reformulation(
            etude, nom
        ) == EN_COURS

    def test_compilation_sans_discrimination(
        self,
        etude_reunion
    ):
        """
        Invariant §9.6 : dans l'ouvrage final, un
        texte validé saisi à la main compile
        EXACTEMENT comme un texte validé produit
        par l'IA — la provenance n'apparaît pas.
        """

        etude, nom, fids, _t = etude_reunion

        texte = (
            "Le Fils de l'homme est venu chercher et "
            "sauver ce qui était perdu."
        )

        # Bloc 1 : version « IA ».
        ajouter_version_reformulation(
            etude,
            fids[0],
            texte,
            type_version="passe",
            stats={"cout_estime": 0.01}
        )

        valider_version_reformulation(
            etude,
            fids[0],
            1,
            validateur="Test"
        )

        ouvrage_ia = assembler_ouvrage(etude)

        # Bloc 2 : version saisie à la main, même
        # texte — la compilation doit être
        # identique.
        from services.etude_io import (
            devalider_version_reformulation,
        )

        devalider_version_reformulation(
            etude,
            fids[0],
            1
        )

        ajouter_version_reformulation(
            etude,
            fids[0],
            texte,
            type_version="edition_manuelle"
        )

        valider_version_reformulation(
            etude,
            fids[0],
            2,
            validateur="Test"
        )

        ouvrage_manuel = assembler_ouvrage(etude)

        blocs_ia = ouvrage_ia["reunions"][0]["blocs"]
        blocs_manuel = (
            ouvrage_manuel["reunions"][0]["blocs"]
        )

        assert blocs_ia == blocs_manuel

        # Aucune trace de provenance dans le
        # document assemblé.
        import json

        serialise = json.dumps(
            ouvrage_manuel,
            ensure_ascii=False
        )

        assert "edition_manuelle" not in serialise
        assert "passe" not in serialise


#
# ==================================================
# Résumé : saisie manuelle, y compris sans version
# préexistante (spec §7.1).
# ==================================================
#

class TestSaisieManuelleResume:

    def test_resume_saisi_de_zero(
        self,
        qapp,
        etude_reunion
    ):
        """
        Un résumé peut être saisi à la main sans
        qu'aucune génération LLM n'ait jamais eu
        lieu (l'ancien code exigeait une version
        préexistante).
        """

        etude, nom, _fids, _t = etude_reunion

        assert nom not in etude.resumes

        from ui.resume_window import ResumeWindow

        fenetre = ResumeWindow(etude, nom)

        try:

            assert (
                fenetre.derniere_version() is None
            )

            fenetre.resume_edit.setPlainText(
                "Résumé entièrement saisi à la main, "
                "collé depuis un texte existant."
            )

            assert fenetre.non_enregistre

            fenetre.sauvegarder_edition()

            version = fenetre.derniere_version()

            assert version is not None
            assert version.texte == (
                "Résumé entièrement saisi à la main, "
                "collé depuis un texte existant."
            )

            assert (
                version.origine
                == "edition_manuelle"
            )

            assert version.stats is None

        finally:
            fenetre.close()

    def test_resume_manuel_valide_compile(
        self,
        etude_reunion
    ):
        """
        Invariant §9.6 : un résumé validé saisi à
        la main alimente la compilation de
        l'ouvrage au même titre qu'un résumé IA.
        """

        etude, nom, _fids, _t = etude_reunion

        version = ajouter_version_resume(
            etude,
            nom,
            "Résumé manuel de la réunion.",
            source="brute_corrigee",
            origine="edition_manuelle"
        )

        valider_version_resume(
            etude,
            nom,
            version.numero,
            validateur="Test"
        )

        assert (
            etude.reunions[nom].resume_valide
        )

        ouvrage = assembler_ouvrage(
            etude,
            inclure_resumes=True
        )

        resume = (
            ouvrage["reunions"][0]["resume"]
        )

        assert resume == (
            "Résumé manuel de la réunion."
        )


#
# ==================================================
# Tracé au log des opérations (spec §7.3).
# ==================================================
#

class TestTraceJournal:

    def test_editions_manuelles_tracees(
        self,
        etude_reunion
    ):

        etude, nom, fids, _t = etude_reunion

        from services.traitements.journal import (
            TYPE_EDITION_MANUELLE,
        )

        ajouter_version_reformulation(
            etude,
            fids[0],
            "Texte manuel.",
            type_version="edition_manuelle"
        )

        ajouter_version_resume(
            etude,
            nom,
            "Résumé manuel.",
            source="brute_corrigee",
            origine="edition_manuelle"
        )

        dernieres = (
            etude.journal.dernieres(20)
        )

        types = [
            entree["type"]
            for entree in dernieres
        ]

        # Toute saisie manuelle est tracée « édition
        # manuelle » (bloc ET résumé).
        assert types.count(
            TYPE_EDITION_MANUELLE
        ) >= 2
