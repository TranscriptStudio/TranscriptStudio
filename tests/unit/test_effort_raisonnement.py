"""
Tests — Catalogue LLM + effort de raisonnement
(PARAMETRAGE_LLM_V2_2026-10-31b.md, mises à jour
2026-10-31 (a), (b) et (c)) :

- (a) Mistral Large 4 « Le Chonk » au catalogue
  (version 3) : capacités, prix, libellé
  « (précédent) » pour mistral-large-latest ;
- (b) effort de raisonnement CONFIGURABLE :
  la capacité passe du booléen à la LISTE des
  valeurs acceptées (+ ``effort_defaut``) ;
  sélecteur sans « Défaut de l'API » ; repli
  silencieux si l'API rejette le paramètre ;
  tokens de raisonnement comptés dans la
  sortie ;
- (c) échelles SPÉCIFIQUES à chaque modèle :
  Le Chonk low/medium/high (jamais none),
  Claude jusqu'à max avec traduction vers
  ``output_config.effort`` chez anthropic ;
  ``effort_defaut`` toujours dans la liste,
  sinon la plus haute valeur.

La montée de version du catalogue (2 → 3)
déclenche la fusion automatique : les
utilisateurs existants voient Le Chonk sans
action de leur part.
"""

import json

import pytest

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    yield application

from services.llm.catalogue import (
    CatalogueLLM,
    FournisseurCatalogue,
    ModeleCatalogue,
    effort_effectif,
    catalogue_par_defaut,
    charger_catalogue,
    enregistrer_catalogue,
    reglages_affichables,
)
from services.llm.client import (
    ErreurLLM,
    ParametresCompletion,
    creer_client,
    libelle_effort,
)

from tests.unit.test_llm_client import (
    CLE,
    FausseReponse,
    FausseSession,
    _parametres,
    _sse_openai,
)


#
# ==================================================
# Mise à jour (a) — catalogue v3, Le Chonk.
# ==================================================
#

class TestCatalogueV3:

    def test_version_3(self):
        assert (
            catalogue_par_defaut()
            .catalogue_version
            == 3
        )

    def test_mistral_large_4(self):
        """
        Le Chonk : capacités (température, effort
        low/medium/high, défaut high, contexte
        1 M), prix 0,70 / 2,10 $ par million.
        """

        modele = catalogue_par_defaut(
        ).chercher_modele(
            "mistral",
            "mistral-large-4"
        )

        assert modele is not None

        assert modele.nom_affiche == (
            "Mistral Large 4 « Le Chonk »"
        )

        assert (
            modele.valeurs_effort_raisonnement
            == ["low", "medium", "high"]
        )

        assert modele.effort_defaut == "high"

        assert (
            modele.max_contexte_tokens
            == 1_000_000
        )

        assert modele.capacite_temperature

        assert modele.prix == {
            "in_par_million": 0.7,
            "out_par_million": 2.1,
        }

    def test_mistral_large_latest_precedent(self):
        """
        L'ancien Mistral Large reste au catalogue,
        libellé « (précédent) ».
        """

        modele = catalogue_par_defaut(
        ).chercher_modele(
            "mistral",
            "mistral-large-latest"
        )

        assert modele is not None

        assert modele.nom_affiche == (
            "Mistral Large (précédent)"
        )

        # Sans effort de raisonnement déclaré.
        assert not (
            modele.capacite_effort_raisonnement
        )

    def test_echelles_par_modele(self):
        """
        (c) Le Chonk jamais none ni xhigh ni max ;
        Claude monte jusqu'à max ; OpenAI garde
        son échelle historique (documentée au
        catalogue à la bascule booléen → liste).
        """

        catalogue = catalogue_par_defaut()

        chonk = catalogue.chercher_modele(
            "mistral", "mistral-large-4"
        )

        claude = catalogue.chercher_modele(
            "anthropic", "claude-sonnet-4"
        )

        terra = catalogue.chercher_modele(
            "openai", "gpt-6.1-terra"
        )

        assert "none" not in (
            chonk.valeurs_effort_raisonnement
        )

        assert (
            claude.valeurs_effort_raisonnement
            == [
                "low",
                "medium",
                "high",
                "xhigh",
                "max",
            ]
        )

        assert claude.effort_defaut == "high"

        assert (
            terra.valeurs_effort_raisonnement
            == [
                "minimal",
                "low",
                "medium",
                "high",
                "xhigh",
            ]
        )

    def test_fusion_v3_automatique(self, tmp_path):
        """
        Montée 2 → 3 : la fusion automatique
        existante apporte Le Chonk aux catalogues
        déjà stockés, SANS perdre les
        fournisseurs ajoutés par l'utilisateur.
        """

        utilisateur = FournisseurCatalogue(
            id="ollama-local",
            nom="Ollama local",
            famille_api="openai_compatible",
            base_url="http://localhost:11434/v1",
            origine="utilisateur",
        )

        stocke = CatalogueLLM(
            catalogue_version=2,
            fournisseurs=[utilisateur],
        )

        chemin = tmp_path / "catalogue.json"

        enregistrer_catalogue(stocke, chemin)

        charge = charger_catalogue(chemin)

        assert charge.catalogue_version == 3

        assert (
            charge.chercher_modele(
                "mistral",
                "mistral-large-4"
            )
            is not None
        )

        assert (
            charge.chercher_fournisseur(
                "ollama-local"
            )
            is not None
        )


#
# ==================================================
# Mise à jour (c) — effort_effectif et défauts.
# ==================================================
#

class TestEffortEffectif:

    def test_valeur_acceptee(self):
        catalogue = catalogue_par_defaut()

        chonk = catalogue.chercher_modele(
            "mistral", "mistral-large-4"
        )

        assert effort_effectif(chonk, "low") == (
            "low"
        )

        # Valeur d'un AUTRE modèle (jamais none
        # pour Le Chonk, jamais xhigh) : le
        # DÉFAUT du modèle est substitué.
        assert effort_effectif(chonk, "xhigh") == (
            "high"
        )

        assert effort_effectif(chonk, None) == (
            "high"
        )

    def test_modele_sans_capacite(self):
        catalogue = catalogue_par_defaut()

        gpt = catalogue.chercher_modele(
            "openai", "gpt-4.1"
        )

        assert effort_effectif(gpt, "high") is None

    def test_defaut_toujours_dans_la_liste(self):
        """
        (c) ``effort_defaut`` hors liste → la
        valeur la plus HAUTE disponible ; absent →
        la plus haute aussi.
        """

        invalide = ModeleCatalogue(
            id="m",
            nom_affiche="M",
            capacites={
                "effort_raisonnement": [
                    "low",
                    "high"
                ],
                "effort_defaut": "medium",
            },
        )

        assert invalide.effort_defaut == "high"

        absent = ModeleCatalogue(
            id="m",
            nom_affiche="M",
            capacites={
                "effort_raisonnement": [
                    "low",
                    "medium",
                    "high",
                ],
            },
        )

        assert absent.effort_defaut == "high"

    def test_catalogue_ancien_booleen(self):
        """
        Un catalogue édité à la main peut encore
        porter l'ancien booléen : repli sur
        l'échelle historique, jamais bloqué.
        """

        ancien = ModeleCatalogue(
            id="m",
            nom_affiche="M",
            capacites={
                "effort_raisonnement": True
            },
        )

        assert (
            ancien.capacite_effort_raisonnement
            is True
        )

        assert "high" in (
            ancien.valeurs_effort_raisonnement
        )

    def test_libelles_et_reglages(self):
        """
        Libellés UI (Faible/Moyen/Élevé/Très
        élevé/Max), valeur inconnue affichée telle
        quelle ; ``reglages_affichables`` porte la
        liste exacte du modèle et son défaut.
        """

        assert libelle_effort("low") == "Faible"
        assert libelle_effort("medium") == "Moyen"
        assert libelle_effort("high") == "Élevé"
        assert libelle_effort("xhigh") == (
            "Très élevé"
        )
        assert libelle_effort("max") == "Max"
        assert libelle_effort("turbo") == "turbo"

        catalogue = catalogue_par_defaut()

        chonk = catalogue.chercher_modele(
            "mistral", "mistral-large-4"
        )

        reglages = reglages_affichables(chonk)

        assert reglages["effort_raisonnement"] == {
            "valeurs": [
                "low",
                "medium",
                "high"
            ],
            "defaut": "high",
        }


#
# ==================================================
# Mise à jour (b) — client : envoi, repli
# silencieux, tokens de raisonnement.
# ==================================================
#

class TestClientEffort:

    def _fournisseur(self, id_fournisseur):
        return (
            catalogue_par_defaut()
            .chercher_fournisseur(id_fournisseur)
        )

    def test_repli_silencieux_sur_rejet(self):
        """
        L'API rejette la requête (400) alors que
        l'effort était envoyé : l'appel est
        RETENTÉ SANS le paramètre — jamais d'échec
        bloquant de la passe.
        """

        lignes = _sse_openai(
            ["Réponse."],
            usage={
                "prompt_tokens": 10,
                "completion_tokens": 5,
            }
        )

        session = FausseSession([
            FausseReponse(
                statut=400,
                texte=json.dumps({
                    "error": "reasoning_effort "
                    "is not supported"
                })
            ),
            FausseReponse(
                statut=200,
                lignes=lignes
            ),
        ])

        client = creer_client(
            self._fournisseur("mistral"),
            CLE,
            session=session,
        )

        resultat = client.completions(
            "Système.",
            [{"role": "user", "content": "Texte."}],
            _parametres(
                modele="mistral-large-4",
                temperature=None,
                effort_raisonnement="high",
            ),
        )

        # Deux appels : avec l'effort, puis sans.
        assert len(session.appels) == 2

        assert session.appels[0]["json"][
            "reasoning_effort"
        ] == "high"

        assert "reasoning_effort" not in (
            session.appels[1]["json"]
        )

        assert resultat.texte == "Réponse."

    def test_rejet_sans_effort_bloque(self):
        """
        Un 400 sans effort envoyé n'est PAS
        transitoire : l'erreur remonte clairement
        (type « requete »), sans boucle de
        relance.
        """

        session = FausseSession([
            FausseReponse(
                statut=400,
                texte=json.dumps({
                    "error": "bad request"
                })
            ),
        ])

        client = creer_client(
            self._fournisseur("mistral"),
            CLE,
            session=session,
        )

        with pytest.raises(ErreurLLM) as infos:
            client.completions(
                "Système.",
                [{"role": "user", "content": "T."}],
                _parametres(
                    modele="mistral-large-4",
                    temperature=None,
                ),
            )

        assert infos.value.type == "requete"

        assert len(session.appels) == 1

    def test_tokens_raisonnement_dans_la_sortie(self):
        """
        Les tokens de raisonnement rapportés
        SÉPARÉMENT (sommet de l'usage) sont AJOUTÉS
        à la sortie — facturés comme des tokens de
        sortie ; le détail nested OpenAI est une
        répartition DÉJÀ INCLUSE, jamais compté
        deux fois.
        """

        lignes = _sse_openai(
            ["Texte."],
            usage={
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "reasoning_tokens": 30,
            }
        )

        session = FausseSession([
            FausseReponse(statut=200, lignes=lignes)
        ])

        client = creer_client(
            self._fournisseur("mistral"),
            CLE,
            session=session,
        )

        resultat = client.completions(
            "Système.",
            [{"role": "user", "content": "T."}],
            _parametres(modele="mistral-large-4"),
        )

        assert resultat.tokens_in == 10
        assert resultat.tokens_out == 50

        lignes = _sse_openai(
            ["Texte."],
            usage={
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "completion_tokens_details": {
                    "reasoning_tokens": 8
                },
            }
        )

        session = FausseSession([
            FausseReponse(statut=200, lignes=lignes)
        ])

        client = creer_client(
            self._fournisseur("openai"),
            CLE,
            session=session,
        )

        resultat = client.completions(
            "Système.",
            [{"role": "user", "content": "T."}],
            _parametres(modele="gpt-4.1"),
        )

        # Détail inclus : pas de double comptage.
        assert resultat.tokens_out == 20

    def test_anthropic_output_config(self):
        """
        (c) L'adaptateur anthropic traduit l'effort
        vers le bloc ``output_config`` → champ
        ``effort`` — PAS de paramètre top-level.
        """

        fournisseur = (
            catalogue_par_defaut()
            .chercher_fournisseur("anthropic")
        )

        lignes = [
            "data: " + json.dumps({
                "type": "message_start",
                "message": {
                    "usage": {"input_tokens": 10}
                },
            }),
            "data: " + json.dumps({
                "type": "content_block_delta",
                "delta": {"text": "Ok."},
            }),
            "data: " + json.dumps({
                "type": "message_delta",
                "usage": {"output_tokens": 5},
            }),
            "data: " + json.dumps({
                "type": "message_stop"
            }),
        ]

        session = FausseSession([
            FausseReponse(statut=200, lignes=lignes)
        ])

        client = creer_client(
            fournisseur,
            CLE,
            session=session,
        )

        client.completions(
            "Système.",
            [{"role": "user", "content": "T."}],
            _parametres(
                modele="claude-sonnet-4",
                temperature=None,
                effort_raisonnement="max",
            ),
        )

        appel = session.appels[0]

        assert appel["json"]["output_config"] == {
            "effort": "max"
        }

        assert "reasoning_effort" not in (
            appel["json"]
        )


#
# ==================================================
# UI : sélecteur « Effort de raisonnement » de
# l'onglet LLM (mise à jour (b)/(c)).
# ==================================================
#

class TestSelecteurEffort:

    def test_chonk_faible_moyen_eleve(
        self, qapp, tmp_path
    ):
        """
        Pour Mistral Large 4 : le sélecteur ne
        propose QUE low/medium/high (libellés
        Faible/Moyen/Élevé), SANS « Défaut de
        l'API » — l'effort d'un modèle à
        raisonnement est TOUJOURS explicite —
        défaut Élevé pour un réglage vierge.
        """

        from services.settings import (
            SettingsManager
        )
        from ui.settings_dialog import (
            SettingsDialog
        )

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        settings.save()

        config = settings.get_llm_config()

        config["fournisseur"] = "mistral"
        config["modele"] = "mistral-large-4"

        settings.set_llm_config(config)

        dialogue = SettingsDialog(
            settings=settings
        )

        dialogue.show()

        # Onglet LLM : les réglages du modèle y
        # vivent (l'effort n'est visible que sur
        # l'onglet actif).
        onglet_llm = next(
            i for i in range(dialogue.tabs.count())
            if "LLM" in dialogue.tabs.tabText(i)
        )

        dialogue.tabs.setCurrentIndex(onglet_llm)

        try:

            assert (
                dialogue.llm_effort_ligne
                .isVisible()
            )

            libelles = [
                dialogue.llm_effort_combo
                .itemText(i)
                for i in range(
                    dialogue
                    .llm_effort_combo
                    .count()
                )
            ]

            assert libelles == [
                "Faible",
                "Moyen",
                "Élevé",
            ]

            # Aucune entrée « Défaut de l'API »
            # (None) — jamais none pour Le Chonk.
            assert all(
                dialogue
                .llm_effort_combo
                .itemData(i)
                is not None
                for i in range(
                    dialogue
                    .llm_effort_combo
                    .count()
                )
            )

            # Réglage vierge : DÉFAUT du modèle.
            assert (
                dialogue
                .llm_effort_combo
                .currentData()
                == "high"
            )

            # Sélection puis enregistrement :
            # la valeur est mémorisée.
            index = (
                dialogue
                .llm_effort_combo
                .findData("low")
            )

            dialogue.llm_effort_combo.setCurrentIndex(
                index
            )

            dialogue.save_settings()

        finally:
            dialogue.close()

        assert settings.get_llm_config().get(
            "effort_raisonnement"
        ) == "low"

    def test_masque_sans_capacite(
        self, qapp, tmp_path
    ):
        """
        Un modèle sans effort déclaré (gpt-4.1,
        mistral-large-latest) : la ligne est
        MASQUÉE (règle d'invariance 2) — jamais
        de réglage non déclaré.
        """

        from services.settings import (
            SettingsManager
        )
        from ui.settings_dialog import (
            SettingsDialog
        )

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        settings.save()

        config = settings.get_llm_config()

        config["fournisseur"] = "mistral"
        config["modele"] = "mistral-large-latest"

        settings.set_llm_config(config)

        dialogue = SettingsDialog(
            settings=settings
        )

        dialogue.show()

        onglet_llm = next(
            i for i in range(dialogue.tabs.count())
            if "LLM" in dialogue.tabs.tabText(i)
        )

        dialogue.tabs.setCurrentIndex(onglet_llm)

        try:

            assert not (
                dialogue.llm_effort_ligne
                .isVisible()
            )

        finally:
            dialogue.close()


#
# ==================================================
# Moteur : effort validé contre la liste du
# modèle (jamais de valeur hors échelle).
# ==================================================
#

class TestMoteurEffort:

    def test_valeur_hors_echelle_substituee(
        self, tmp_path
    ):
        """
        Une valeur mémorisée qui n'est pas
        acceptée par le modèle courant (changement
        de modèle, valeur retirée du catalogue)
        devient le DÉFAUT du modèle — Le Chonk
        n'envoie JAMAIS none ni xhigh.
        """

        from tests.unit.test_moteur_traitements import (
            PARAMETRES_APP,
            ClientFactice,
            creer_etude_avec_blocs,
            fabriquer_moteur,
        )

        etude, nom = creer_etude_avec_blocs(
            tmp_path
        )

        # L'étude surcharge le modèle des réglages
        # de l'app (contrat §10, bloc
        # reformulation) : Le Chonk.
        etude.parametres.reformulation["modele"] = (
            "mistral-large-4"
        )

        moteur = fabriquer_moteur(
            etude,
            nom,
            ClientFactice(None, ""),
            parametres_app={
                **PARAMETRES_APP,
                "fournisseur": "mistral",
                "modele": "mistral-large-4",
                "effort_raisonnement": "xhigh",
            },
        )

        _f, modele = moteur.resoudre()

        parametres = moteur._parametres_completion(
            modele,
            0.3
        )

        assert (
            parametres.effort_raisonnement
            == "high"
        )
