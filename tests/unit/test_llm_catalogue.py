"""
Tests unitaires du catalogue LLM (P15.1).

Couvre les règles d'invariance du paramétrage LLM :
- règle 2 : l'UI n'affiche jamais un réglage non
  déclaré dans les capacités du modèle courant
  (fonction ``reglages_affichables``) ;
- règle 3 : le catalogue par défaut est
  reconstituable sans perdre les fournisseurs
  ajoutés par l'utilisateur ;
- règle 5 : les coûts estimés utilisent toujours
  le prix courant du catalogue.
"""

import json

import pytest

from services.llm.catalogue import (
    ORIGINE_UTILISATEUR,
    CatalogueError,
    CatalogueLLM,
    FournisseurCatalogue,
    ModeleCatalogue,
    catalogue_par_defaut,
    charger_catalogue,
    cout_estime,
    cout_estime_avant_passe,
    enregistrer_catalogue,
    estimer_tokens,
    reinitialiser_catalogue,
    reglages_affichables,
    valider_catalogue,
)


class TestConfigLLMReglages:
    """
    Sélection LLM mémorisée app-wide (P15.2) :
    chaque étude peut la surcharger, les clés ne
    passent jamais par là (CredentialStore).
    """

    def test_defaults_et_persistance(self, tmp_path):
        from services.settings import SettingsManager

        manager = SettingsManager(
            app_folder=tmp_path
        )

        config = manager.get_llm_config()

        assert config["fournisseur"] == "openai"
        assert config["modele"] == "gpt-4.1"
        assert config["temperature"] == 0.3
        assert config["max_tokens"] is None

        manager.set_llm_config({
            "fournisseur": "mistral",
            "modele": "mistral-large-latest",
            "temperature": 0.1,
            "max_tokens": 2048,
            "effort_raisonnement": None,
        })

        # Une nouvelle instance relit la sélection.
        relue = SettingsManager(app_folder=tmp_path)

        config = relue.get_llm_config()

        assert config["fournisseur"] == "mistral"
        assert config["modele"] == "mistral-large-latest"
        assert config["max_tokens"] == 2048

        # Aucune clé en clair dans les réglages :
        # elles vivent dans le CredentialStore
        # (règle d'invariance 1).
        contenu = json.dumps(relue.settings)

        assert "sk-" not in contenu
        assert "llm_cle_" not in contenu


class TestCatalogueDefaut:

    def test_trois_fournisseurs_de_la_spec(self):
        catalogue = catalogue_par_defaut()

        assert [
            f.id for f in catalogue.fournisseurs
        ] == ["openai", "mistral", "anthropic"]

        assert all(
            f.origine == "defaut"
            for f in catalogue.fournisseurs
        )

        openai = catalogue.chercher_fournisseur("openai")

        assert openai.famille_api == (
            "openai_compatible"
        )
        assert openai.endpoint_infos_compte == (
            "available"
        )

        anthropic = catalogue.chercher_fournisseur(
            "anthropic"
        )

        assert anthropic.famille_api == "anthropic"
        assert anthropic.endpoint_infos_compte == (
            "none"
        )

    def test_modeles_et_prix(self):
        catalogue = catalogue_par_defaut()

        gpt = catalogue.chercher_modele(
            "openai",
            "gpt-4.1"
        )

        assert gpt is not None
        assert gpt.capacite_temperature is True
        assert gpt.max_contexte_tokens == 1000000
        assert gpt.prix == {
            "in_par_million": 2.0,
            "out_par_million": 8.0,
        }

        mistral = catalogue.chercher_modele(
            "mistral",
            "mistral-large-latest"
        )

        assert mistral.prix["out_par_million"] == 4.18

        #
        # Familles GPT-5.6 / GPT-6.x (2026-10) :
        # modèles de raisonnement — pas de
        # température, effort de raisonnement
        # déclaré, fenêtre de 1,05 M de tokens.
        #
        terra = catalogue.chercher_modele(
            "openai",
            "gpt-6.1-terra"
        )

        assert terra.capacite_temperature is False
        assert terra.capacite_effort_raisonnement is True
        assert terra.max_contexte_tokens == 1050000
        assert terra.prix == {
            "in_par_million": 1.0,
            "out_par_million": 5.0,
        }

    def test_introuvables(self):
        catalogue = catalogue_par_defaut()

        assert (
            catalogue.chercher_fournisseur("inconnu")
            is None
        )

        assert (
            catalogue.chercher_modele("openai", "xxx")
            is None
        )


class TestPersistance:

    def test_round_trip(self, tmp_path):
        catalogue = catalogue_par_defaut()

        chemin = enregistrer_catalogue(
            catalogue,
            tmp_path / "catalogue_llm.json"
        )

        relu = charger_catalogue(chemin)

        assert relu.to_dict() == catalogue.to_dict()

    def test_absent_retourne_le_defaut(self, tmp_path):
        catalogue = charger_catalogue(
            tmp_path / "n_existe_pas.json"
        )

        assert catalogue.to_dict() == (
            catalogue_par_defaut().to_dict()
        )

    def test_reinitialisation_conserve_les_ajouts(self, tmp_path):
        """
        Règle d'invariance 3 : réinitialiser les
        défauts ne perd pas les fournisseurs
        ajoutés par l'utilisateur (ni leurs modèles).
        """

        chemin = tmp_path / "catalogue_llm.json"

        catalogue = catalogue_par_defaut()

        catalogue.ajouter_fournisseur(
            FournisseurCatalogue(
                id="ollama-local",
                nom="Ollama (local)",
                famille_api="openai_compatible",
                base_url="http://localhost:11434/v1",
                endpoint_infos_compte="none",
                modeles=[
                    ModeleCatalogue(
                        id="llama3",
                        nom_affiche="Llama 3",
                        capacites={"temperature": True},
                        prix={
                            "in_par_million": 0.0,
                            "out_par_million": 0.0,
                        },
                        origine=ORIGINE_UTILISATEUR,
                    )
                ],
                origine=ORIGINE_UTILISATEUR,
            )
        )

        enregistrer_catalogue(catalogue, chemin)

        # L'utilisateur peut aussi modifier un prix
        # d'un modèle par défaut.
        relu = charger_catalogue(chemin)

        gpt = relu.chercher_modele("openai", "gpt-4.1")
        gpt.prix["in_par_million"] = 9.9

        enregistrer_catalogue(relu, chemin)

        reinitialise = reinitialiser_catalogue(chemin)

        #
        # Le fournisseur ajouté survit, avec ses
        # modèles.
        #
        ollama = reinitialise.chercher_fournisseur(
            "ollama-local"
        )

        assert ollama is not None
        assert ollama.origine == ORIGINE_UTILISATEUR
        assert ollama.chercher_modele("llama3")

        # Ollama en local : pas de clé requise.
        assert ollama.necessite_cle is False

        #
        # Les défauts sont reconstitués : le prix
        # modifié de gpt-4.1 revient à l'embarqué.
        #
        gpt = reinitialise.chercher_modele(
            "openai",
            "gpt-4.1"
        )

        assert gpt.prix["in_par_million"] == 2.0

    def test_mise_a_jour_version_defauts(self, tmp_path):
        """
        Un catalogue stocké plus ancien que l'embarqué
        est mis à jour au chargement : fournisseurs
        par défaut remplacés par les nouveaux défauts,
        ajouts utilisateur conservés, fichier réécrit
        (l'utilisateur voit les nouveaux modèles sans
        action de sa part).
        """

        chemin = tmp_path / "catalogue_llm.json"

        ancien = catalogue_par_defaut()
        ancien.catalogue_version = 1

        #
        # Simule l'ancien défaut : un seul modèle
        # OpenAI, avant l'ajout des familles GPT-5.6
        # et GPT-6.x.
        #
        openai = ancien.chercher_fournisseur("openai")
        openai.modeles = [
            modele
            for modele in openai.modeles
            if modele.id == "gpt-4.1"
        ]

        ancien.ajouter_fournisseur(
            FournisseurCatalogue(
                id="ollama-local",
                nom="Ollama (local)",
                famille_api="openai_compatible",
                base_url="http://localhost:11434/v1",
                endpoint_infos_compte="none",
                modeles=[
                    ModeleCatalogue(
                        id="llama3",
                        nom_affiche="Llama 3",
                        capacites={"temperature": True},
                        prix={
                            "in_par_million": 0.0,
                            "out_par_million": 0.0,
                        },
                        origine=ORIGINE_UTILISATEUR,
                    )
                ],
                origine=ORIGINE_UTILISATEUR,
            )
        )

        enregistrer_catalogue(ancien, chemin)

        relu = charger_catalogue(chemin)

        assert relu.catalogue_version == (
            catalogue_par_defaut().catalogue_version
        )

        # Nouveaux modèles par défaut visibles.
        assert relu.chercher_modele(
            "openai",
            "gpt-6.1-terra"
        )

        # Ajout utilisateur conservé.
        ollama = relu.chercher_fournisseur(
            "ollama-local"
        )

        assert ollama.origine == ORIGINE_UTILISATEUR
        assert ollama.chercher_modele("llama3")

        # Fichier mis à jour sur le disque.
        reliture = json.loads(
            chemin.read_text(encoding="utf-8")
        )

        assert reliture["catalogue_version"] == 2


class TestValidation:

    def test_famille_inconnue(self):
        catalogue = catalogue_par_defaut()

        catalogue.fournisseurs[0].famille_api = "impairable"

        with pytest.raises(CatalogueError):
            valider_catalogue(catalogue)

    def test_doublon_fournisseur(self):
        catalogue = catalogue_par_defaut()

        with pytest.raises(CatalogueError):
            catalogue.ajouter_fournisseur(
                catalogue.fournisseurs[0]
            )

    def test_prix_manquant(self):
        catalogue = catalogue_par_defaut()

        catalogue.fournisseurs[
            0
        ].modeles[0].prix.pop("in_par_million")

        with pytest.raises(CatalogueError):
            valider_catalogue(catalogue)

    def test_illisible(self, tmp_path):
        chemin = tmp_path / "catalogue_llm.json"

        chemin.write_text("{ pas du json", encoding="utf-8")

        with pytest.raises(CatalogueError):
            charger_catalogue(chemin)


class TestCouts:
    """
    Règle d'invariance 5 : les coûts estimés
    utilisent toujours le prix courant du
    catalogue ; les stats déjà enregistrées ne
    sont pas recalculées rétroactivement.
    """

    def test_cout_estime(self):
        catalogue = catalogue_par_defaut()

        gpt = catalogue.chercher_modele(
            "openai",
            "gpt-4.1"
        )

        # 2 $ / million en entrée, 8 $ / million
        # en sortie.
        assert cout_estime(gpt, 1_000_000, 0) == (
            pytest.approx(2.0)
        )

        assert cout_estime(gpt, 0, 500_000) == (
            pytest.approx(4.0)
        )

        assert cout_estime(gpt, 100_000, 50_000) == (
            pytest.approx(0.6)
        )

    def test_cout_avant_passe(self):
        catalogue = catalogue_par_defaut()

        assert cout_estime_avant_passe(
            catalogue,
            "openai",
            "gpt-4.1",
            tokens_in_estimes=50_000,
            tokens_out_estimes=12_000
        ) == pytest.approx(0.196)

    def test_court_suivant_le_prix_courant(self):
        catalogue = catalogue_par_defaut()

        gpt = catalogue.chercher_modele(
            "openai",
            "gpt-4.1"
        )

        avant = cout_estime(gpt, 1000, 1000)

        gpt.prix["in_par_million"] = 20.0

        apres = cout_estime(gpt, 1000, 1000)

        assert apres > avant
        assert apres == pytest.approx(
            (20.0 * 1000 + 8.0 * 1000) / 1e6
        )

        # Une valeur déjà calculée (une stat stockée,
        # par ex.) ne change pas : seul le futur est
        # recalculé.
        assert avant == pytest.approx(0.01)

    def test_estimation_tokens(self):
        assert estimer_tokens("") == 0
        assert estimer_tokens("ab") == 1
        assert estimer_tokens("a" * 400) == 100


class TestReglagesAffichables:
    """
    Règle d'invariance 2 : l'UI n'affiche jamais
    un réglage non déclaré dans les capacités du
    modèle courant.
    """

    def test_modele_complet(self):
        gpt = catalogue_par_defaut().chercher_modele(
            "openai",
            "gpt-4.1"
        )

        reglages = reglages_affichables(gpt)

        assert "temperature" in reglages
        assert reglages["max_tokens"]["maximum"] == (
            1000000
        )

        # Le modèle ne déclare pas l'effort de
        # raisonnement : jamais affiché.
        assert "effort_raisonnement" not in reglages

    def test_modele_sans_temperature(self):
        modele = ModeleCatalogue(
            id="m",
            nom_affiche="M",
            capacites={"temperature": False},
            prix={
                "in_par_million": 0.0,
                "out_par_million": 0.0,
            },
        )

        reglages = reglages_affichables(modele)

        assert "temperature" not in reglages
        assert "effort_raisonnement" not in reglages

        # max_tokens sans contexte déclaré :
        # pas de plafond.
        assert reglages["max_tokens"]["maximum"] is None

    def test_modele_avec_effort(self):
        modele = ModeleCatalogue(
            id="m",
            nom_affiche="M",
            capacites={
                "temperature": True,
                "effort_raisonnement": True,
                "max_contexte_tokens": 50000,
            },
            prix={
                "in_par_million": 0.0,
                "out_par_million": 0.0,
            },
        )

        reglages = reglages_affichables(modele)

        assert "effort_raisonnement" in reglages
        assert reglages["max_tokens"]["maximum"] == (
            50000
        )
