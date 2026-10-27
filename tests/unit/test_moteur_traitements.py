"""
Tests unitaires du moteur de traitement (P15.3) et
du log des opérations (P15.4).

Spécification de référence : SPEC_MOTEUR_P15_V2.md
(fait autorité), CONTRAT_FORMAT_ETUDE_V2.md §7/§10/§11.

Les six règles d'invariance de la spec moteur (§6)
sont couvertes, ainsi que la règle 6 du contrat
(§13) et les critères d'acceptation de la feuille de
route P15 (réunion traitée de bout en bout, coût
estimé, annulation propre à mi-passe, reprise).

Aucun appel réseau : le client LLM est factice et
injecté.
"""

import json
from pathlib import Path

import pytest

from models.etude import (
    BlocParole,
    DecoupageReunion,
    OrigineBloc,
    PositionsBloc,
)
from services.decoupage import fusionner_blocs
from services.etude_io import (
    ajouter_reunion,
    ajouter_version_reformulation,
    attribuer_fid,
    creer_etude,
    devalider_version_reformulation,
    enregistrer_decoupage,
    ouvrir_etude,
    sauvegarder_etude,
    valider_version_reformulation,
)
from services.llm.catalogue import (
    CatalogueLLM,
    FournisseurCatalogue,
    ModeleCatalogue,
    cout_estime,
    estimer_tokens,
    catalogue_par_defaut,
)
from services.llm.client import (
    ErreurLLM,
    ResultatCompletion,
)
from services.traitements.journal import (
    JournalError,
    JournalEtude,
    TYPE_ANNULATION_PASSE,
    TYPE_EDITION_MANUELLE,
    TYPE_ERREUR_API,
    TYPE_FUSION_BLOCS,
    TYPE_PASSE_COMPLETE,
    TYPE_REFORMULATION_BLOC,
    TYPE_VALIDATION,
)
from services.traitements.moteur import (
    ErreurContexte,
    MoteurTraitements,
)
from services.timecodes import formater_timecode


PARAMETRES_APP = {
    "fournisseur": "openai",
    "modele": "gpt-4.1",
    "temperature": 0.3,
    "temperatures": {
        "reformulation": 0.3,
        "resume": 0.2,
    },
}


class StoreFactice:
    """
    CredentialStore factice : une clé par fournisseur.
    """

    def get_cle_llm(self, fournisseur_id):
        return f"cle-{fournisseur_id}"


class ClientFactice:
    """
    Client LLM factice : enregistre chaque appel,
    rejoue des réponses ou lève une erreur.
    """

    def __init__(self, fournisseur, cle, reponses=None, erreur=None):
        self.fournisseur = fournisseur
        self.cle = cle
        self.appels = []
        self.reponses = list(reponses or [])
        self.erreur = erreur

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
            "temperature": parametres.temperature,
            "modele": parametres.modele,
        })

        if self.erreur is not None:
            raise self.erreur

        if self.reponses:
            texte = self.reponses.pop(0)
        else:
            texte = (
                f"Reformulation du bloc "
                f"#{len(self.appels)}."
            )

        modele = self.fournisseur.chercher_modele(
            parametres.modele
        )

        tokens_in = (
            estimer_tokens(prompt_systeme or "")
            + estimer_tokens(messages[0]["content"])
        )

        tokens_out = estimer_tokens(texte)

        cout = 0.0

        if modele is not None:
            cout = cout_estime(
                modele,
                tokens_in,
                tokens_out
            )

        return ResultatCompletion(
            texte=texte,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            duree_ms=5,
            cout_estime=cout,
            modele=parametres.modele,
            fournisseur=self.fournisseur.id,
        )


def creer_projet_v1(dossier_parent: Path, nom: str) -> Path:

    dossier = dossier_parent / nom
    dossier.mkdir(parents=True)

    (dossier / "project.sttproj").write_text(
        json.dumps({
            "project_format_version": 1,
            "name": nom,
            "audio_file": "",
            "transcription_id": None,
            "language_code": "fr",
            "duration_seconds": 10.0,
            "modified": False,
            "speakers": [],
            "words": [],
            "blocks": [],
            "original_elevenlabs_response": {},
        }),
        encoding="utf-8"
    )

    return dossier


def creer_etude_avec_blocs(
    tmp_path,
    nb_blocs: int = 3,
    taille_source: int = 400
):
    """
    Étude d'une réunion dont la segmentation compte
    nb_blocs actifs aux sources de taille donnée.
    """

    projet_v1 = creer_projet_v1(
        tmp_path,
        "2026-10-13_Luc1b"
    )

    etude = creer_etude(
        tmp_path / "Etude",
        "Évangile de Luc"
    )

    nom = ajouter_reunion(etude, projet_v1)

    decoupage = DecoupageReunion(reunion=nom, blocs=[])

    for index in range(nb_blocs):

        fid = attribuer_fid(etude, nom)

        decoupage.blocs.append(
            BlocParole(
                fid=fid,
                locuteurs=["Philippe"],
                positions=PositionsBloc(
                    debut=formater_timecode(index * 10.0),
                    fin=formater_timecode(index * 10.0 + 9.0),
                ),
                source="x" * taille_source,
                origine=OrigineBloc(),
            )
        )

    enregistrer_decoupage(etude, decoupage)
    sauvegarder_etude(etude)

    return etude, nom


def fabriquer_moteur(
    etude,
    nom,
    client,
    catalogue=None,
    parametres_app=None
):
    """
    Moteur branché sur le client factice (aucun
    réseau), catalogue et réglages injectés.
    """

    return MoteurTraitements(
        etude,
        nom,
        parametres_app=(
            parametres_app or PARAMETRES_APP
        ),
        credential_store=StoreFactice(),
        catalogue=(
            catalogue or catalogue_par_defaut()
        ),
        client_factory=(
            lambda fournisseur, cle: client
        )
    )


def lire_journal(etude) -> list:
    """
    Lit le fichier journal sur le disque (l'état
    réel, pas la mémoire).
    """

    chemin = (
        etude.dossier
        / "traitements"
        / "journal_operations.json"
    )

    with open(chemin, "r", encoding="utf-8") as f:
        return json.load(f)["entrees"]


def compter(entrees, type_operation: str) -> int:

    return sum(
        1
        for entree in entrees
        if entree["type"] == type_operation
    )


class TestInvariant1:
    """
    Règle 1 : un appel LLM n'écrit jamais dans un
    document tant qu'il n'a pas abouti — aucun
    résultat partiel n'est stocké (c'est l'invariant
    4 du paramétrage LLM, exigé par l'arbitrage P15).
    """

    def test_erreur_api_ne_stoque_rien(self, tmp_path):
        etude, nom = creer_etude_avec_blocs(tmp_path)

        client = ClientFactice(
            fournisseur=(
                catalogue_par_defaut()
                .chercher_fournisseur("openai")
            ),
            cle="",
            erreur=ErreurLLM(
                "reseau",
                "Impossible de joindre OpenAI.",
            ),
        )

        moteur = fabriquer_moteur(etude, nom, client)

        resultat = moteur.traiter_reunion()

        assert resultat.statut == "erreur"
        assert resultat.nb_traites == 0

        # Aucune version, aucun fichier de résultat.
        assert etude.reformulations == {}

        dossier_resultats = (
            etude.dossier
            / "traitements"
            / "reformulation"
        )

        assert not any(
            dossier_resultats.glob("*.json")
        )

        # L'erreur est consignée, message du
        # fournisseur compris.
        entrees = lire_journal(etude)

        assert compter(entrees, TYPE_ERREUR_API) == 1
        assert compter(entrees, TYPE_PASSE_COMPLETE) == 1

        assert entrees[0]["resultat"] == "erreur"
        assert "OpenAI" in entrees[0]["message"]

        # La passe s'est arrêtée proprement au
        # premier bloc.
        assert resultat.fid_erreur == 1

    def test_erreur_au_bloc_2_conserve_le_bloc_1(self, tmp_path):
        etude, nom = creer_etude_avec_blocs(tmp_path)

        fournisseur = (
            catalogue_par_defaut()
            .chercher_fournisseur("openai")
        )

        client = ClientFactice(
            fournisseur,
            cle="",
            reponses=["Première reformulation."],
        )

        # Le deuxième appel échoue.
        client.erreur = None

        class ClientDeuxAppels(ClientFactice):

            def completions(self, *args, **kwargs):
                if len(self.appels) >= 1:
                    raise ErreurLLM(
                        "reseau",
                        "Panne réseau au bloc 2.",
                    )
                return super().completions(*args, **kwargs)

        client = ClientDeuxAppels(
            fournisseur,
            cle="",
            reponses=["Première reformulation."],
        )

        moteur = fabriquer_moteur(etude, nom, client)

        resultat = moteur.traiter_reunion()

        assert resultat.statut == "erreur"
        assert resultat.nb_traites == 1
        assert resultat.fid_erreur == 2

        # Le bloc 1 est conservé (versionnée,
        # sauvegardée).
        assert len(
            etude.reformulations[1].versions
        ) == 1

        reouverte = ouvrir_etude(etude.dossier)

        assert reouverte.reformulations[
            1
        ].versions[0].texte == (
            "Première reformulation."
        )


class TestInvariant2:
    """
    Règle 2 : une annulation à mi-passe ne détruit
    aucun résultat déjà versionné (décision B2).
    """

    def test_annulation_conserve_les_resultats(self, tmp_path):
        etude, nom = creer_etude_avec_blocs(tmp_path, nb_blocs=4)

        client = ClientFactice(
            fournisseur=(
                catalogue_par_defaut()
                .chercher_fournisseur("openai")
            ),
            cle="",
        )

        moteur = fabriquer_moteur(etude, nom, client)

        annulation = type("A", (), {"demandee": False})()

        def progression(fid, traites, total):
            if traites >= 2:
                annulation.demandee = True

        resultat = moteur.traiter_reunion(
            annulation=annulation,
            progression=progression
        )

        assert resultat.statut == "annulee"
        assert resultat.nb_traites == 2

        # Les deux premiers blocs sont versionnés.
        assert len(etude.reformulations[1].versions) == 1
        assert len(etude.reformulations[2].versions) == 1
        assert 3 not in etude.reformulations
        assert 4 not in etude.reformulations

        # Rien n'est effacé après réouverture.
        reouverte = ouvrir_etude(etude.dossier)

        assert len(
            reouverte.reformulations[1].versions
        ) == 1

        assert len(
            reouverte.reformulations[2].versions
        ) == 1

        # L'annulation est consignée, avec la
        # position d'arrêt et les résultats conservés.
        entrees = lire_journal(etude)

        assert compter(entrees, TYPE_ANNULATION_PASSE) == 1

        annulation_entree = next(
            e
            for e in entrees
            if e["type"] == TYPE_ANNULATION_PASSE
        )

        assert annulation_entree["fid"] == 3
        assert annulation_entree["blocs_traites"] == 2

        assert "résultats conservés" in (
            annulation_entree["message"]
        )

        # Aucune passe_complete « terminee » : la
        # passe n'a pas fini.
        assert compter(entrees, TYPE_PASSE_COMPLETE) == 0


class TestInvariant3:
    """
    Règle 3 : la troncation de contexte ne retire
    jamais la synthèse d'étude ni l'unité courante,
    et retire toujours les blocs les plus anciens de
    la fenêtre en premier (décision C1).
    """

    def _catalogueetroit(self, contexte: int):
        return CatalogueLLM(
            fournisseurs=[
                FournisseurCatalogue(
                    id="test",
                    nom="Test",
                    famille_api="openai_compatible",
                    base_url="https://test.example/v1",
                    modeles=[
                        ModeleCatalogue(
                            id="m-petit",
                            nom_affiche="Modèle étroit",
                            capacites={
                                "temperature": True,
                                "max_contexte_tokens": contexte,
                            },
                            prix={
                                "in_par_million": 1.0,
                                "out_par_million": 1.0,
                            },
                        )
                    ],
                )
            ]
        )

    def test_troncation_par_le_haut(self, tmp_path):
        etude, nom = creer_etude_avec_blocs(
            tmp_path,
            nb_blocs=4,
            taille_source=100,
        )

        from services.etude_io import (
            ajouter_version_synthese
        )

        #
        # Prompt court et synthèse courte : le test
        # isole la troncation de la fenêtre.
        #
        etude.parametres.reformulation["prompt"] = (
            "Prompt court."
        )

        ajouter_version_synthese(
            etude,
            "Pensées déjà développées.",
        )

        # Des résultats antérieurs pour les blocs
        # 1, 2, 3 : chacun ~300 tokens estimés.
        for fid in (1, 2, 3):
            ajouter_version_reformulation(
                etude,
                fid,
                "y" * 1200
            )

        catalogue = self._catalogueetroit(400)

        moteur = fabriquer_moteur(
            etude,
            nom,
            ClientFactice(
                catalogue.chercher_fournisseur("test"),
                "",
            ),
            catalogue=catalogue,
            parametres_app={
                **PARAMETRES_APP,
                "fournisseur": "test",
                "modele": "m-petit",
            }
        )

        bloc_4 = next(
            bloc
            for bloc in etude.decoupages[nom].blocs
            if bloc.fid == 4
        )

        contexte = moteur.assembler_contexte(bloc_4)

        #
        # La fenêtre a été tronquée : les plus
        # anciens (1, puis 2) sont sortis en premier,
        # les plus récents conservés.
        #
        assert contexte.fids_contexte == [3]

        # Jamais la synthèse, jamais l'unité courante,
        # jamais le prompt système.
        assert "Pensées déjà développées." in (
            contexte.message
        )

        assert bloc_4.source in contexte.message

    def test_unite_seule_trop_grande_erreur_propre(self, tmp_path):
        etude, nom = creer_etude_avec_blocs(
            tmp_path,
            nb_blocs=1,
            taille_source=5000,
        )

        etude.parametres.reformulation["prompt"] = (
            "Prompt court."
        )

        catalogue = self._catalogueetroit(300)

        moteur = fabriquer_moteur(
            etude,
            nom,
            ClientFactice(
                catalogue.chercher_fournisseur("test"),
                "",
            ),
            catalogue=catalogue,
            parametres_app={
                **PARAMETRES_APP,
                "fournisseur": "test",
                "modele": "m-petit",
            }
        )

        bloc = etude.decoupages[nom].blocs[0]

        with pytest.raises(ErreurContexte) as infos:
            moteur.assembler_contexte(bloc)

        # Bloc signalé, message orienté sous-découpage.
        assert "1" in str(infos.value)
        assert "sous-découpage" in str(infos.value)


class TestInvariant4:
    """
    Règle 4 : toute opération produit exactement une
    entrée de log, horodatée, avant retour à l'UI.
    """

    def test_passe_complete_une_entree_par_operation(self, tmp_path):
        etude, nom = creer_etude_avec_blocs(tmp_path, nb_blocs=3)

        client = ClientFactice(
            fournisseur=(
                catalogue_par_defaut()
                .chercher_fournisseur("openai")
            ),
            cle="",
        )

        moteur = fabriquer_moteur(etude, nom, client)

        resultat = moteur.traiter_reunion()

        assert resultat.statut == "terminee"
        assert resultat.nb_traites == 3

        entrees = lire_journal(etude)

        # 3 reformulations + 1 passe = 4 entrées.
        assert compter(entrees, TYPE_REFORMULATION_BLOC) == 3
        assert compter(entrees, TYPE_PASSE_COMPLETE) == 1
        assert len(entrees) == 4

        for entree in entrees:
            assert entree["horodatage"]

        # Les entrées reformulation portent fid,
        # réunion, version, stats de l'appel.
        reformulations = [
            e
            for e in entrees
            if e["type"] == TYPE_REFORMULATION_BLOC
        ]

        assert [
            e["fid"] for e in reformulations
        ] == [1, 2, 3]

        for entree in reformulations:
            assert entree["reunion"] == nom
            assert entree["version"] == 1
            assert entree["resultat"] == "succes"
            assert entree["stats"]["tokens_in"] > 0
            assert entree["stats"]["cout_estime"] > 0

        # L'entrée de passe porte le statut et le
        # coût total (champs dédiés de l'entrée).
        passe = entrees[-1]

        assert passe["type"] == TYPE_PASSE_COMPLETE
        assert passe["statut"] == "terminee"
        assert passe["nb_blocs"] == 3
        assert passe["stats"]["cout_estime"] == (
            pytest.approx(resultat.cout_total)
        )

    def test_edition_validation_fusion_une_entree_chacune(self, tmp_path):
        etude, nom = creer_etude_avec_blocs(tmp_path)

        avant = len(lire_journal(etude))

        ajouter_version_reformulation(
            etude,
            1,
            "Correction à la main.",
            type_version="edition_manuelle",
        )

        entrees = lire_journal(etude)

        assert len(entrees) == avant + 1
        assert compter(entrees, TYPE_EDITION_MANUELLE) == 1

        valider_version_reformulation(
            etude,
            1,
            numero=1,
            validateur="David"
        )

        entrees = lire_journal(etude)

        assert len(entrees) == avant + 2
        assert compter(entrees, TYPE_VALIDATION) == 1

        devalider_version_reformulation(etude, 1, numero=1)

        entrees = lire_journal(etude)

        assert len(entrees) == avant + 3
        assert compter(entrees, "devalidation") == 1

        fusionner_blocs(etude, nom, [1, 2])

        entrees = lire_journal(etude)

        assert len(entrees) == avant + 4
        assert compter(entrees, TYPE_FUSION_BLOCS) == 1

        # Le fichier est écrit à chaque opération :
        # il contient tout, dans l'ordre.
        assert [e["type"] for e in entrees[avant:]] == [
            TYPE_EDITION_MANUELLE,
            TYPE_VALIDATION,
            "devalidation",
            TYPE_FUSION_BLOCS,
        ]


class TestInvariant5:
    """
    Règle 5 : la température effective d'un appel
    est la surcharge étude si définie, sinon le
    réglage app ; jamais codée en dur (C2).
    """

    def test_surcharge_etude(self, tmp_path):
        etude, nom = creer_etude_avec_blocs(tmp_path, nb_blocs=1)

        # Surcharge étude : 0.1.
        etude.parametres.reformulation["temperature"] = 0.1

        client = ClientFactice(
            fournisseur=(
                catalogue_par_defaut()
                .chercher_fournisseur("openai")
            ),
            cle="",
        )

        moteur = fabriquer_moteur(etude, nom, client)

        assert moteur.temperature_effective() == 0.1

        moteur.traiter_reunion()

        assert client.appels[0]["temperature"] == 0.1

    def test_sans_surcharge_reglage_app(self, tmp_path):
        etude, nom = creer_etude_avec_blocs(tmp_path, nb_blocs=1)

        client = ClientFactice(
            fournisseur=(
                catalogue_par_defaut()
                .chercher_fournisseur("openai")
            ),
            cle="",
        )

        moteur = fabriquer_moteur(etude, nom, client)

        # La surcharge étude existe (créée avec les
        # défauts 0.3) : c'est elle qui prime.
        assert moteur.temperature_effective() == 0.3

        # Sans surcharge étude, le réglage app
        # s'applique (et le suit).
        etude.parametres.reformulation.pop("temperature")

        assert moteur.temperature_effective() == 0.3

        moteur = fabriquer_moteur(
            etude,
            nom,
            client,
            parametres_app={
                **PARAMETRES_APP,
                "temperatures": {
                    "reformulation": 0.5,
                    "resume": 0.2,
                },
            }
        )

        assert moteur.temperature_effective() == 0.5

        moteur.traiter_reunion()

        assert client.appels[0]["temperature"] == 0.5

    def test_modele_sans_temperature_ne_l_envoie_pas(self, tmp_path):
        etude, nom = creer_etude_avec_blocs(tmp_path, nb_blocs=1)

        catalogue = CatalogueLLM(
            fournisseurs=[
                FournisseurCatalogue(
                    id="test",
                    nom="Test",
                    famille_api="openai_compatible",
                    base_url="https://test.example/v1",
                    modeles=[
                        ModeleCatalogue(
                            id="m-froid",
                            nom_affiche="Modèle",
                            capacites={
                                "temperature": False,
                                "max_contexte_tokens": 100000,
                            },
                            prix={
                                "in_par_million": 1.0,
                                "out_par_million": 1.0,
                            },
                        )
                    ],
                )
            ]
        )

        client = ClientFactice(
            catalogue.chercher_fournisseur("test"),
            "",
        )

        moteur = fabriquer_moteur(
            etude,
            nom,
            client,
            catalogue=catalogue,
            parametres_app={
                **PARAMETRES_APP,
                "fournisseur": "test",
                "modele": "m-froid",
            }
        )

        moteur.traiter_reunion()

        # Le modèle ne déclare pas la température :
        # rien n'est envoyé.
        assert client.appels[0]["temperature"] is None


class TestInvariant6:
    """
    Règle 6 : relancer une passe ne retraite jamais
    un bloc déjà traité sans demande explicite.
    """

    def test_reprise_saute_les_blocs_traites(self, tmp_path):
        etude, nom = creer_etude_avec_blocs(tmp_path, nb_blocs=4)

        client = ClientFactice(
            fournisseur=(
                catalogue_par_defaut()
                .chercher_fournisseur("openai")
            ),
            cle="",
        )

        moteur = fabriquer_moteur(etude, nom, client)

        # Passe interrompue après deux blocs.
        annulation = type("A", (), {"demandee": False})()

        moteur.traiter_reunion(
            annulation=annulation,
            progression=(
                lambda fid, traites, total:
                setattr(
                    annulation,
                    "demandee",
                    traites >= 2
                )
            )
        )

        assert len(client.appels) == 2

        # Reprise : seuls les blocs 3 et 4 restent.
        moteur.traiter_reunion()

        assert len(client.appels) == 4

        # Chaque bloc a exactement une version après
        # la reprise : aucun re-traitement.
        for fid in (1, 2, 3, 4):
            assert len(
                etude.reformulations[fid].versions
            ) == 1

    def test_passe_complete_puis_relance_ne_retraite_rien(self, tmp_path):
        etude, nom = creer_etude_avec_blocs(tmp_path, nb_blocs=3)

        client = ClientFactice(
            fournisseur=(
                catalogue_par_defaut()
                .chercher_fournisseur("openai")
            ),
            cle="",
        )

        moteur = fabriquer_moteur(etude, nom, client)

        premiere = moteur.traiter_reunion()

        assert premiere.nb_traites == 3

        # Tout est traité : une nouvelle passe ne
        # traite rien.
        seconde = moteur.traiter_reunion()

        assert seconde.nb_traites == 0
        assert len(client.appels) == 3

        # La demande explicite (relance d'un bloc)
        # retraite, elle.
        moteur.traiter_bloc(2, consigne="plus concis")

        assert len(client.appels) == 4

        assert len(etude.reformulations[2].versions) == 2

        entrees = lire_journal(etude)

        assert compter(entrees, TYPE_REFORMULATION_BLOC) == 4


class TestCriteresP15:
    """
    Critères d'acceptation de la feuille de route :
    réunion traitée de bout en bout, coût estimé
    affiché, annulation propre, reprise possible.
    """

    def test_reunion_de_bout_en_bout(self, tmp_path):
        etude, nom = creer_etude_avec_blocs(tmp_path, nb_blocs=3)

        client = ClientFactice(
            fournisseur=(
                catalogue_par_defaut()
                .chercher_fournisseur("openai")
            ),
            cle="",
        )

        moteur = fabriquer_moteur(etude, nom, client)

        # Coût estimé avant la passe (B1 : fait
        # office de confirmation de la première
        # passe totale).
        estimation = moteur.estimer_passe()

        assert estimation["nb_blocs"] == 3
        assert estimation["cout_estime"] > 0

        # Passe totale d'abord (les versions
        # nécessaires à la relance ciblée).
        resultat = moteur.traiter_reunion()

        assert resultat.statut == "terminee"
        assert resultat.nb_traites == 3
        assert resultat.cout_total > 0
        assert resultat.duree_ms >= 0

        # Les blocs portent leurs versions, avec le
        # contexte consigné (contrat §7).
        for fid in (1, 2, 3):
            assert etude.reformulations[fid].versions

        assert etude.reformulations[
            1
        ].versions[0].contexte == []
        assert etude.reformulations[
            2
        ].versions[0].contexte == [1]
        assert etude.reformulations[
            3
        ].versions[0].contexte == [1, 2]

        # Aucune confirmation pour un bloc isolé :
        # exécution directe (relance ciblée).
        version = moteur.traiter_bloc(
            1,
            selection={"debut": 0, "fin": 10}
        )

        assert version.type == "relance_ciblee"
        assert len(client.appels) == 4

        # Relance ciblée : la formulation courante et
        # les versions antérieures du bloc sont dans
        # le contexte.
        dernier_appel = client.appels[-1]

        assert "Formulation actuelle" in (
            dernier_appel["message"]
        )

        assert "Versions antérieures" in (
            dernier_appel["message"]
        )

        # Après réouverture, tout est en place.
        reouverte = ouvrir_etude(etude.dossier)

        for fid in (1, 2, 3):
            assert reouverte.reformulations[fid].versions


class TestJournalRegles:
    """
    Contrat §13 règle 6 : le log ne perd jamais une
    entrée — append-only, écrit à chaque opération.
    """

    def test_append_only_ne_perd_rien(self, tmp_path):
        chemin = tmp_path / "journal.json"

        journal = JournalEtude(chemin)

        assert journal.nb_entrees() == 0

        premiere = journal.ajouter(
            TYPE_REFORMULATION_BLOC,
            fid=1,
            reunion="r",
            resultat="succes",
        )

        # Écrit à chaque opération : le fichier
        # existe dès la première entrée.
        assert chemin.exists()

        with open(chemin, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["journal_version"] == 1
        assert len(data["entrees"]) == 1

        for index in range(5):
            journal.ajouter(
                TYPE_EDITION_MANUELLE,
                fid=index + 2,
                reunion="r",
                resultat="succes",
            )

        with open(chemin, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert len(data["entrees"]) == 6

        # La première entrée est inchangée, mot pour
        # mot.
        assert data["entrees"][0] == premiere

        # Rechargement : rien n'est perdu.
        recharge = JournalEtude(chemin)

        assert recharge.nb_entrees() == 6

    def test_type_inconnu_refuse(self, tmp_path):
        journal = JournalEtude(
            tmp_path / "journal.json"
        )

        with pytest.raises(JournalError):
            journal.ajouter("teleportation")

    def test_fichier_corrompu_signale(self, tmp_path):
        chemin = tmp_path / "journal.json"

        chemin.write_text("{ pas du json", encoding="utf-8")

        with pytest.raises(JournalError):
            JournalEtude(chemin)

    def test_etudes_anterieures_sans_journal(self, tmp_path):
        """
        Une étude créée avant P15.4 n'a pas de
        journal : il démarre vide et se crée à la
        première opération.
        """

        etude, nom = creer_etude_avec_blocs(tmp_path)

        chemin = (
            etude.dossier
            / "traitements"
            / "journal_operations.json"
        )

        # La création de l'étude écrit le journal
        # vide (fichier présent).
        assert chemin.exists()

        # Suppression : simulation d'une étude
        # antérieure.
        chemin.unlink()

        reouverte = ouvrir_etude(etude.dossier)

        assert reouverte.journal.nb_entrees() == 0

        # La première opération recrée le fichier.
        ajouter_version_reformulation(
            reouverte,
            1,
            "Nouvelle version."
        )

        assert chemin.exists()

        assert reouverte.journal.nb_entrees() == 1
