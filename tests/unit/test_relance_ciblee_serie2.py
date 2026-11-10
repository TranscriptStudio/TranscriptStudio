"""
Tests — relance ciblée, SÉRIE 2 anti-résidu
(CORRECTIFS_RELANCE_CIBLEE_V2_2026-11-07b.md,
prime sur la série a pour ses points) :

- Inv. S6 : le message contient, EN DERNIER,
  l'instruction anti-reproduction explicite
  (« …complet (du premier au dernier mot du
  passage)… sans reproduire aucun fragment du
  texte original. ») ;
- Inv. S7 : garde anti-résidu — si la réponse
  contient ≥ 6 mots consécutifs présents dans le
  passage original (comparaison normalisée :
  minuscules, ponctuation ignorée, espaces
  ramenés à un), la version est consignée MAIS
  marquée (stats.avertissement_residu) et l'UI
  affiche « La réponse contient un fragment du
  texte original — vérifiez la zone retravaillée. »
  — JAMAIS de blocage, JAMAIS de modification
  automatique ;
- Inv. S8 : le passage envoyé est le texte EXACT de
  la tranche [debut, fin] ;
- testé sur LES DEUX services (moteur /
  reformulation par bloc, ServiceResume / résumé).
"""

import os

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from services.traitements.ciblee import (
    AVERTISSEMENT_RESIDU,
    detecter_residu,
    message_ciblee,
    verifier_reponse,
)


#
# ==================================================
# Unitaire : détection du résidu et message S6.
# ==================================================
#

class TestDetecteurResidu:

    def test_residu_detecte(
        self
    ):
        """
        ≥ 6 mots consécutifs du passage original dans
        la réponse → résidu détecté.
        """

        passage = (
            "il devait couvrir beaucoup de terrain "
            "technique avant de pouvoir travailler "
            "seul avec les ordinateurs."
        )

        reponse = (
            "Il devait couvrir beaucoup de terrain "
            "technique avant de pouvoir travailler "
            "seul. — avec les ordinateurs."
        )

        assert detecter_residu(reponse, passage)

    def test_reponse_propre_non_signalee(
        self
    ):

        passage = (
            "il devait couvrir beaucoup de terrain "
            "technique avant de pouvoir travailler "
            "seul avec les ordinateurs."
        )

        reponse = (
            "Il devait parcourir un long chemin "
            "technique avant de voler de ses propres "
            "ailes."
        )

        assert not detecter_residu(reponse, passage)

    def test_normalisation_casse_ponctuation(
        self
    ):
        """
        La comparaison est normalisée : casse et
        ponctuation ignorées.
        """

        passage = (
            "il devait couvrir beaucoup de terrain "
            "technique avant de pouvoir travailler "
            "seul avec les ordinateurs."
        )

        reponse = (
            "IL devait couvrir beaucoup de terrain, "
            "TECHNIQUE avant de pouvoir travailler "
            "seul..."
        )

        assert detecter_residu(reponse, passage)

    def test_passage_trop_court(
        self
    ):
        """
        Passage de moins de 6 mots : aucune détection
        possible (pas de faux positif).
        """

        assert not detecter_residu(
            "un deux trois quatre cinq six sept",
            "un deux trois"
        )

    def test_verifier_reponse_marqueurs(
        self
    ):

        passage = (
            "il devait couvrir beaucoup de terrain "
            "technique avant de pouvoir travailler "
            "seul avec les ordinateurs."
        )

        reponse, avertissements = verifier_reponse(
            "Il devait couvrir beaucoup de terrain "
            "technique avant de pouvoir travailler "
            "seul avec les ordinateurs traduits.",
            passage
        )

        assert reponse
        assert AVERTISSEMENT_RESIDU in (
            avertissements
        )


class TestMessageS6:

    def test_instruction_anti_reproduction_en_dernier(
        self
    ):
        """
        Inv. S6 : la dernière ligne du message est
        l'instruction anti-reproduction explicite.
        """

        message = message_ciblee(
            "passage à traduire",
            consigne="traduis en français",
            contexte="texte courant complet…",
        )

        assert message.rstrip().endswith(
            "sans reproduire "
            "aucun fragment du texte original."
        )

        assert (
            "complet (du premier au dernier mot "
            "du passage)"
        ) in message

        # La consigne reste juste avant (prioritaire).
        assert "PRIORITAIRE" in message
        assert message.index(
            "traduis en français"
        ) > message.index("Passage à retravailler")

    def test_passage_exact_envoye(
        self
    ):
        """
        Inv. S8 : le passage envoyé est le texte
        exact de la tranche, non tronqué.
        """

        passage = (
            "Phrase exacte du passage sélectionné, "
            "avec sa ponctuation et sa fin."
        )

        message = message_ciblee(passage)

        assert passage in message


#
# ==================================================
# Moteur (reformulation par bloc).
# ==================================================
#

class TestMoteurSerie2:

    def test_residu_signale_version_consignee(
        self,
        tmp_path
    ):
        """
        Réponse contenant un fragment du passage
        original → version consignée (jamais de
        blocage) AVEC stats.avertissement_residu.
        """

        from services.llm.catalogue import (
            catalogue_par_defaut,
        )
        from services.traitements.moteur import (
            MoteurTraitements,
        )
        from tests.unit.test_moteur_traitements import (
            ClientFactice,
            creer_etude_avec_blocs,
            fabriquer_moteur,
        )
        from services.etude_io import (
            ajouter_version_reformulation,
        )

        etude, nom = creer_etude_avec_blocs(
            tmp_path,
            nb_blocs=1
        )

        texte = (
            "Le christ est venu sauver les "
            "pécheurs repentants de leurs fautes "
            "et de leurs peines."
        )

        ajouter_version_reformulation(
            etude,
            nom,
            1,
            texte
        )

        client = ClientFactice(
            fournisseur=(
                catalogue_par_defaut()
                .chercher_fournisseur("openai")
            ),
            cle="",
            reponses=[
                "Le CHRIST est venu sauver les "
                "pécheurs repentants traduits."
            ],
        )

        moteur = fabriquer_moteur(
            etude,
            nom,
            client
        )

        passage = texte[:30]

        version = moteur.traiter_bloc(
            1,
            selection={"debut": 0, "fin": 30}
        )

        # Jamais de blocage : version consignée.
        assert version.type == "relance_ciblee"

        # Mais le résidu est signalé.
        assert version.stats.get(
            "avertissement_residu"
        ) is True

        # Le raccord a bien eu lieu.
        assert version.texte.endswith(
            texte[30:]
        )

        # Le message envoyé contient le passage
        # exact (Inv. S8) et l'instruction S6.
        message = client.appels[-1]["message"]

        assert passage in message
        assert message.rstrip().endswith(
            "sans reproduire "
            "aucun fragment du texte original."
        )

    def test_reponse_propre_non_marquee(
        self,
        tmp_path
    ):

        from services.llm.catalogue import (
            catalogue_par_defaut,
        )
        from tests.unit.test_moteur_traitements import (
            ClientFactice,
            creer_etude_avec_blocs,
            fabriquer_moteur,
        )
        from services.etude_io import (
            ajouter_version_reformulation,
        )

        etude, nom = creer_etude_avec_blocs(
            tmp_path,
            nb_blocs=1
        )

        texte = (
            "Le christ est venu sauver les "
            "pécheurs repentants de leurs fautes "
            "et de leurs peines."
        )

        ajouter_version_reformulation(
            etude,
            nom,
            1,
            texte
        )

        client = ClientFactice(
            fournisseur=(
                catalogue_par_defaut()
                .chercher_fournisseur("openai")
            ),
            cle="",
            reponses=["Le Christ vint sauver les âmes."],
        )

        moteur = fabriquer_moteur(
            etude,
            nom,
            client
        )

        version = moteur.traiter_bloc(
            1,
            selection={"debut": 0, "fin": 30}
        )

        assert version.type == "relance_ciblee"

        assert "avertissement_residu" not in (
            version.stats or {}
        )


#
# ==================================================
# Résumé (ServiceResume.relancer_selection).
# ==================================================
#

class TestResumeSerie2:

    def _service_avec_resume(
        self,
        tmp_path,
        client,
        texte
    ):
        from tests.unit.test_resume_synthese import (
            creer_etude_reunions,
            fabriquer_service,
        )
        from services.etude_io import (
            ajouter_version_resume,
        )
        from services.traitements.resume import (
            ServiceResume,
            SOURCE_BRUTE,
        )

        etude, reunions = creer_etude_reunions(
            tmp_path
        )

        ajouter_version_resume(
            etude,
            reunions[0],
            texte,
            source=SOURCE_BRUTE
        )

        service = fabriquer_service(
            ServiceResume,
            etude,
            client
        )

        return etude, reunions[0], service

    def test_residu_signale_version_consignee(
        self,
        tmp_path
    ):

        from tests.unit.test_resume_synthese import (
            ClientFactice,
        )

        texte = (
            "Il devait couvrir beaucoup de terrain "
            "technique avant de pouvoir travailler "
            "seul avec les ordinateurs."
        )

        client = ClientFactice(
            reponses=[
                "Il devait couvrir beaucoup de terrain "
                "technique avant de pouvoir travailler "
                "seul — traduit avec les machines."
            ]
        )

        etude, reunion, service = (
            self._service_avec_resume(
                tmp_path,
                client,
                texte
            )
        )

        version, stats = service.relancer_selection(
            reunion,
            selection={"debut": 0, "fin": 40},
            consigne="traduis en français",
        )

        # Jamais de blocage : version consignée.
        assert version.origine == "relance_ciblee"

        # Résidu signalé.
        assert stats.get(
            "avertissement_residu"
        ) is True

        # Raccord applicatif.
        assert version.texte.endswith(texte[40:])

        # Message : passage exact (S8) + S6 en dernier.
        message = client.appels[-1]["message"]

        assert texte[:40] in message
        assert message.rstrip().endswith(
            "sans reproduire "
            "aucun fragment du texte original."
        )

    def test_reponse_propre_non_marquee(
        self,
        tmp_path
    ):

        from tests.unit.test_resume_synthese import (
            ClientFactice,
        )

        texte = (
            "Il devait couvrir beaucoup de terrain "
            "technique avant de pouvoir travailler "
            "seul avec les ordinateurs."
        )

        client = ClientFactice(
            reponses=[
                "Il devait parcourir un long chemin "
                "avant de voler seul."
            ]
        )

        etude, reunion, service = (
            self._service_avec_resume(
                tmp_path,
                client,
                texte
            )
        )

        version, stats = service.relancer_selection(
            reunion,
            selection={"debut": 0, "fin": 40},
        )

        assert "avertissement_residu" not in stats
