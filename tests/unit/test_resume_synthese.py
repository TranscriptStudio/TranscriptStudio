"""
Tests unitaires du bloc Résumé (P17.1), de la
synthèse d'étude (P17.2) et du contrôle qualité
étendu (P17.3).

Références : feuille de route §4/P17, CONTRAT_FORMAT_ETUDE_V2
§8 (résumé versionné, source stockée) et §9 (synthèse
versionnée, déclencheurs).

Aucun appel réseau : client LLM factice injecté.
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
from services.etude_io import (
    ajouter_reunion,
    ajouter_version_reformulation,
    ajouter_version_resume,
    attribuer_fid,
    creer_etude,
    devalider_version_resume,
    enregistrer_decoupage,
    sauvegarder_etude,
    valider_version_reformulation,
    valider_version_resume,
)
from services.llm.catalogue import (
    catalogue_par_defaut,
    cout_estime,
    estimer_tokens,
)
from services.llm.client import (
    ErreurLLM,
    ResultatCompletion,
)
from services.traitements.resume import (
    ErreurSource,
    ServiceResume,
    SOURCE_BRUTE,
    SOURCE_REFORMULEES,
    segmenter_source,
    source_a_evolve,
    texte_source,
)
from services.traitements.synthese import (
    PROMPT_SYNTHESE,
    ServiceSynthese,
    assembler_source_synthese,
    reunion_entierement_validee,
    texte_reunion_valide,
)
from services.traitements.moteur import (
    MoteurTraitements,
)
from services.controle_qualite import (
    expressions_recurrentes,
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

    def get_cle_llm(self, fournisseur_id):
        return f"cle-{fournisseur_id}"


class ClientFactice:
    """
    Client LLM factice : enregistre chaque appel,
    rejoue des réponses ou lève une erreur.
    """

    def __init__(self, reponses=None, erreur=None):
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
                f"Réponse #{len(self.appels)}."
            )

        tokens_in = (
            estimer_tokens(prompt_systeme or "")
            + estimer_tokens(messages[0]["content"])
        )

        tokens_out = estimer_tokens(texte)

        return ResultatCompletion(
            texte=texte,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            duree_ms=5,
            cout_estime=0.001,
            modele=parametres.modele,
            fournisseur="openai",
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


def creer_etude_reunions(
    tmp_path,
    sources: dict = None
):
    """
    Étude à deux réunions ; ``sources`` : nom ->
    liste des textes sources des blocs de la réunion.
    """

    sources = sources or {
        "2026-10-13_Luc1b": [
            "Première intervention.",
            "Deuxième intervention.",
        ],
    }

    etude = creer_etude(
        tmp_path / "Etude",
        "Évangile de Luc"
    )

    noms = []

    for nom, textes in sources.items():

        dossier_projet = creer_projet_v1(
            tmp_path,
            nom
        )

        reunion = ajouter_reunion(etude, dossier_projet)

        noms.append(reunion)

        decoupage = DecoupageReunion(
            reunion=reunion,
            blocs=[]
        )

        for texte in textes:

            fid = attribuer_fid(etude, reunion)

            decoupage.blocs.append(
                BlocParole(
                    fid=fid,
                    locuteurs=["Philippe"],
                    positions=PositionsBloc(
                        debut=formater_timecode(0.0),
                        fin=formater_timecode(9.0),
                    ),
                    source=texte,
                    origine=OrigineBloc(),
                )
            )

        enregistrer_decoupage(etude, decoupage)

    sauvegarder_etude(etude)

    return etude, noms


def fabriquer_service(service_cls, etude, client):

    return service_cls(
        etude,
        parametres_app=PARAMETRES_APP,
        credential_store=StoreFactice(),
        catalogue=catalogue_par_defaut(),
        client_factory=(
            lambda fournisseur, cle: client
        )
    )


def lire_journal(etude) -> list:

    chemin = (
        etude.dossier
        / "traitements"
        / "journal_operations.json"
    )

    with open(chemin, "r", encoding="utf-8") as f:
        return json.load(f)["entrees"]


class TestTexteSource:

    def test_brute_corrigee(self, tmp_path):

        etude, reunions = creer_etude_reunions(tmp_path)

        texte = texte_source(
            etude,
            reunions[0],
            SOURCE_BRUTE
        )

        assert texte == (
            "Première intervention.\n\n"
            "Deuxième intervention."
        )

    def test_reformulations_valides_uniquement(
        self, tmp_path
    ):
        """
        Seules les versions validées alimentent la
        source reformulée (contrat §7).
        """

        etude, reunions = creer_etude_reunions(tmp_path)
        reunion = reunions[0]

        fids = [
            bloc.fid
            for bloc in etude.decoupages[reunion].blocs
        ]

        ajouter_version_reformulation(
            etude,
            fids[0],
            "Reformulation A v1."
        )

        ajouter_version_reformulation(
            etude,
            fids[0],
            "Reformulation A v2."
        )

        valider_version_reformulation(
            etude,
            fids[0],
            numero=1,
            validateur="David"
        )

        ajouter_version_reformulation(
            etude,
            fids[1],
            "Reformulation B v1."
        )

        texte = texte_source(
            etude,
            reunion,
            SOURCE_REFORMULEES
        )

        # v1 validée retenue (pas la v2 non validée),
        # bloc sans version validée sauté.
        assert texte == "Reformulation A v1."

    def test_aucune_reformulation_validee(
        self, tmp_path
    ):
        """
        Source reformulée sans aucune version validée :
        erreur claire (la brute corrigée reste
        disponible).
        """

        etude, reunions = creer_etude_reunions(tmp_path)

        with pytest.raises(ErreurSource):
            texte_source(
                etude,
                reunions[0],
                SOURCE_REFORMULEES
            )


class TestSegmentation:

    def test_petite_source_un_segment(self):

        segments = segmenter_source(
            "Un court texte.\nDeuxième paragraphe."
        )

        assert len(segments) == 1

    def test_grande_source_bornee(self):
        """
        3 à 5 segments, coupés aux frontières de
        paragraphes, avec chevauchement.
        """

        paragraphes = [
            f"Paragraphe {index} " + "mot " * 200
            for index in range(200)
        ]

        segments = segmenter_source(
            "\n".join(paragraphes)
        )

        assert 3 <= len(segments) <= 5

        # Frontières de paragraphes : chaque segment
        # commence par un début de paragraphe.
        for segment in segments:
            assert segment.startswith("Paragraphe")

        # Chevauchement : le 2e segment reprend des
        # paragraphes du 1er.
        premiers = set(segments[0].split("\n"))
        deuxieme = set(segments[1].split("\n"))

        assert premiers & deuxieme


class TestGenerationResume:

    def test_generation_source_brute(self, tmp_path):
        """
        Un résumé peut se générer depuis la brute
        corrigée sans aucune reformulation (vue
        d'ensemble rapide).
        """

        etude, reunions = creer_etude_reunions(tmp_path)
        reunion = reunions[0]

        client = ClientFactice(
            reponses=["Le résumé sobre de la réunion."]
        )

        service = fabriquer_service(
            ServiceResume,
            etude,
            client
        )

        version, stats = service.generer(
            reunion,
            source=SOURCE_BRUTE
        )

        assert version.numero == 1
        assert version.texte == (
            "Le résumé sobre de la réunion."
        )
        assert version.source == SOURCE_BRUTE
        assert version.origine == "generation"
        assert version.validation is None

        # Stats de l'appel stockées avec la version.
        assert stats["tokens_in"] > 0
        assert version.stats["tokens_in"] == (
            stats["tokens_in"]
        )

        # Un seul appel : source courte.
        assert len(client.appels) == 1

        # Le prompt système actif de l'étude (résumé v2).
        assert "résumé" in (
            client.appels[0]["prompt_systeme"].lower()
        )

        # Longueur cible passée au message.
        assert "650" in client.appels[0]["message"]
        assert "700" in client.appels[0]["message"]

        # Journal : une entrée resume.
        entrees = lire_journal(etude)
        assert sum(
            1
            for entree in entrees
            if entree["type"] == "resume"
        ) == 1

    def test_generation_source_reformulees(
        self, tmp_path
    ):
        """
        Source reformulations validées : le chemin
        recommandé.
        """

        etude, reunions = creer_etude_reunions(tmp_path)
        reunion = reunions[0]

        for bloc in etude.decoupages[reunion].blocs:

            ajouter_version_reformulation(
                etude,
                bloc.fid,
                f"Reformulation {bloc.fid}."
            )

            valider_version_reformulation(
                etude,
                bloc.fid,
                numero=1,
                validateur="David"
            )

        sauvegarder_etude(etude)

        client = ClientFactice(
            reponses=["Résumé depuis reformulations."]
        )

        service = fabriquer_service(
            ServiceResume,
            etude,
            client
        )

        version, _stats = service.generer(reunion)

        assert version.source == (
            SOURCE_REFORMULEES
        )

        message = client.appels[0]["message"]

        assert "Reformulation" in message

    def test_source_inconnue(self, tmp_path):

        etude, reunions = creer_etude_reunions(tmp_path)

        client = ClientFactice()

        service = fabriquer_service(
            ServiceResume,
            etude,
            client
        )

        with pytest.raises(ErreurSource):
            service.generer(
                reunions[0],
                source="inconnue"
            )

    def test_persiste_sur_disque(self, tmp_path):
        """
        Le résumé est rechargé depuis le disque
        (contrat §8) avec sa source et ses stats.
        """

        from services.etude_io import ouvrir_etude

        etude, reunions = creer_etude_reunions(tmp_path)

        client = ClientFactice(
            reponses=["Résumé persistant."]
        )

        service = fabriquer_service(
            ServiceResume,
            etude,
            client
        )

        service.generer(
            reunions[0],
            source=SOURCE_BRUTE
        )

        relue = ouvrir_etude(etude.dossier)

        resultat = relue.resumes[reunions[0]]

        assert len(resultat.versions) == 1
        assert resultat.versions[0].texte == (
            "Résumé persistant."
        )
        assert resultat.versions[0].source == (
            SOURCE_BRUTE
        )
        assert resultat.versions[0].stats

    def test_segmentation_appels_multiples(
        self, tmp_path
    ):
        """
        Source longue : notes de segment puis
        assemblage final — la version est le texte
        final, les stats sont cumulées.
        """

        sources = {
            "2026-10-13_Luc1b": [
                "\n".join(
                    "Paragraphe %d %s" % (index, "mot " * 150)
                    for index in range(300)
                )
            ],
        }

        etude, reunions = creer_etude_reunions(
            tmp_path,
            sources
        )

        client = ClientFactice(
            reponses=[
                "Notes du segment 1.",
                "Notes du segment 2.",
                "Notes du segment 3.",
                "Résumé final assemblé."
            ]
        )

        service = fabriquer_service(
            ServiceResume,
            etude,
            client
        )

        version, stats = service.generer(
            reunions[0],
            source=SOURCE_BRUTE
        )

        assert version.texte == "Résumé final assemblé."

        # 3 notes de segment + 1 assemblage final.
        assert len(client.appels) == 4

        assert "segment" in (
            client.appels[0]["message"].lower()
        )

        assert "Notes du segment 1" in (
            client.appels[-1]["message"]
        )

        # Stats cumulées des quatre appels.
        assert stats["duree_ms"] == 20
        assert version.stats["duree_ms"] == 20

    def test_estimation(self, tmp_path):

        etude, reunions = creer_etude_reunions(tmp_path)

        client = ClientFactice()

        service = fabriquer_service(
            ServiceResume,
            etude,
            client
        )

        estimation = service.estimer(
            reunions[0],
            SOURCE_BRUTE
        )

        assert estimation["nb_segments"] == 1
        assert estimation["source"] == SOURCE_BRUTE
        assert estimation["tokens_source"] > 0
        assert estimation["tokens_in_estimes"] > 0
        assert estimation["cout_estime"] >= 0.0

        # Aucun appel pour une estimation.
        assert client.appels == []

    def test_temperature_jamais_envoyee_si_non_supportee(
        self, tmp_path
    ):
        """
        Modèle de raisonnement (température non
        supportée) : jamais de température dans
        l'appel (décision C2, catalogue v2).
        """

        from services.llm.catalogue import (
            ModeleCatalogue,
        )

        etude, reunions = creer_etude_reunions(tmp_path)

        client = ClientFactice(
            reponses=["Résumé."]
        )

        service = ServiceResume(
            etude,
            parametres_app=PARAMETRES_APP,
            credential_store=StoreFactice(),
            catalogue=catalogue_par_defaut(),
            client_factory=(
                lambda fournisseur, cle: client
            )
        )

        # Le modèle de l'étude devient gpt-6.1-terra
        # (capacite_temperature False).
        etude.parametres.resume["modele"] = (
            "gpt-6.1-terra"
        )

        service.generer(
            reunions[0],
            source=SOURCE_BRUTE
        )

        assert client.appels[0]["temperature"] is None
        assert client.appels[0]["modele"] == (
            "gpt-6.1-terra"
        )


class TestRelancesResume:

    def _etude_avec_resume(self, tmp_path):

        etude, reunions = creer_etude_reunions(tmp_path)

        client = ClientFactice(
            reponses=["Premier résumé."]
        )

        service = fabriquer_service(
            ServiceResume,
            etude,
            client
        )

        service.generer(
            reunions[0],
            source=SOURCE_BRUTE
        )

        return etude, reunions[0], service

    def test_relance_avec_versions_anterieures(
        self, tmp_path
    ):
        """
        Relance complète : contexte = source +
        formulation courante + TOUTES les versions
        antérieures (pour ne pas tourner en rond) +
        consigne.
        """

        etude, reunion, service = (
            self._etude_avec_resume(tmp_path)
        )

        client = ClientFactice(
            reponses=["Résumé amélioré."]
        )

        service._client_factory = (
            lambda fournisseur, cle: client
        )

        version, stats = service.relancer(
            reunion,
            consigne="plus concis"
        )

        assert version.numero == 2
        assert version.origine == "relance"
        assert version.consigne == "plus concis"
        assert version.source == SOURCE_BRUTE

        message = client.appels[0]["message"]

        assert "Premier résumé." in message
        assert "Version 1" in message
        assert "plus concis" in message

    def test_relance_ciblee_sur_selection(
        self, tmp_path
    ):
        """
        Relance ciblée : contexte identique +
        versions antérieures + portion délimitée ; la
        version contient le résumé entier retravaillé
        partiellement.
        """

        etude, reunion, service = (
            self._etude_avec_resume(tmp_path)
        )

        client = ClientFactice(
            reponses=["Résumé partiellement retravaillé."]
        )

        service._client_factory = (
            lambda fournisseur, cle: client
        )

        selection = {
            "debut": 10,
            "fin": 42,
            "texte": "passage visé",
        }

        version, _stats = service.relancer_selection(
            reunion,
            selection=selection,
            consigne=None
        )

        assert version.numero == 2
        assert version.origine == "relance_ciblee"

        message = client.appels[0]["message"]

        assert "10" in message
        assert "42" in message
        assert "conservé tel quel" in message

    def test_edition_manuelle_puis_validation(
        self, tmp_path
    ):
        """
        Outillage commun : édition = nouvelle version
        edition_manuelle (stats None) ; validation
        fige le résumé (resume_valide) ; dévalidation
        rouvre l'édition.
        """

        etude, reunion, service = (
            self._etude_avec_resume(tmp_path)
        )

        version = ajouter_version_resume(
            etude,
            reunion,
            "Résumé corrigé à la main.",
            source=SOURCE_BRUTE,
            origine="edition_manuelle"
        )

        assert version.numero == 2
        assert version.stats is None

        valider_version_resume(
            etude,
            reunion,
            numero=2,
            validateur="David"
        )

        assert etude.reunions[
            reunion
        ].resume_valide is True

        devalider_version_resume(
            etude,
            reunion,
            numero=2
        )

        assert etude.reunions[
            reunion
        ].resume_valide is False

    def test_relance_sans_resume_impossible(
        self, tmp_path
    ):
        """
        Pas de relance sans version existante :
        erreur claire, aucun appel.
        """

        etude, reunions = creer_etude_reunions(tmp_path)

        client = ClientFactice()

        service = fabriquer_service(
            ServiceResume,
            etude,
            client
        )

        with pytest.raises(Exception):
            service.relancer(reunions[0])

        assert client.appels == []


class TestInvariantResume:

    def test_echec_appel_aucune_version(
        self, tmp_path
    ):
        """
        Un appel qui échoue ne consigne rien (règle
        d'invariance 1 du moteur, appliquée au
        résumé) : pas de version, pas de fichier
        resume.
        """

        etude, reunions = creer_etude_reunions(tmp_path)

        client = ClientFactice(
            erreur=ErreurLLM(
                "reseau",
                "Serveur injoignable."
            )
        )

        service = fabriquer_service(
            ServiceResume,
            etude,
            client
        )

        with pytest.raises(ErreurLLM):
            service.generer(
                reunions[0],
                source=SOURCE_BRUTE
            )

        assert reunions[0] not in etude.resumes

        dossier_resume = (
            etude.dossier / "traitements" / "resume"
        )

        fichiers = (
            list(dossier_resume.glob("*.json"))
            if dossier_resume.exists()
            else []
        )

        assert fichiers == []


class TestSourceEvolvee:

    def test_reformulation_posterieure_signalee(
        self, tmp_path
    ):
        """
        Avertissement feuille de route §4 : une
        reformulation validée postérieure à la
        génération signale une source évoluée
        (jamais de mise à jour automatique).
        """

        etude, reunions = creer_etude_reunions(tmp_path)
        reunion = reunions[0]

        #
        # Le projet v1 existe depuis longtemps : pas
        # d'avertissement « source évoluée » (la
        # comparaison de mtime est stable).
        #
        import os as _os

        for nom, chemin_resolu in (
            etude.chemins_resolus.items()
        ):
            for sttproj in (
                Path(chemin_resolu).glob("*.sttproj")
            ):
                st = sttproj.stat()
                vieux = st.st_mtime - 3600
                _os.utime(sttproj, (vieux, vieux))

        client = ClientFactice(
            reponses=["Résumé v1."]
        )

        service = fabriquer_service(
            ServiceResume,
            etude,
            client
        )

        version, _stats = service.generer(
            reunion,
            source=SOURCE_BRUTE
        )

        assert source_a_evolve(
            etude,
            reunion,
            version
        ) is False

        fid = etude.decoupages[reunion].blocs[0].fid

        ajouter_version_reformulation(
            etude,
            fid,
            "Nouvelle reformulation."
        )

        valider_version_reformulation(
            etude,
            fid,
            numero=1,
            validateur="David"
        )

        # La source brute n'est pas impactée par les
        # reformulations : pas d'avertissement.
        assert source_a_evolve(
            etude,
            reunion,
            version
        ) is False

        # Une version générée depuis les reformulations
        # serait signalée.
        client2 = ClientFactice(
            reponses=["Résumé v2."]
        )

        service2 = fabriquer_service(
            ServiceResume,
            etude,
            client2
        )

        version2, _stats = service2.generer(
            reunion,
            source=SOURCE_REFORMULEES
        )

        assert source_a_evolve(
            etude,
            reunion,
            version2
        ) is False

        #
        # Les horodatages sont à la seconde : décaler
        # celui de la version en arrière rend la
        # postériorité déterministe dans le test.
        #
        from datetime import (
            datetime,
            timedelta,
        )

        version2.horodatage = (
            datetime.fromisoformat(
                version2.horodatage
            )
            - timedelta(seconds=10)
        ).isoformat()

        fid2 = etude.decoupages[reunion].blocs[1].fid

        ajouter_version_reformulation(
            etude,
            fid2,
            "Reformulation postérieure."
        )

        valider_version_reformulation(
            etude,
            fid2,
            numero=1,
            validateur="David"
        )

        assert source_a_evolve(
            etude,
            reunion,
            version2
        ) is True


class TestSynthese:

    def _valider_tout(self, etude, reunion, numero=1):

        for bloc in etude.decoupages[reunion].blocs:

            if bloc.fid not in etude.reformulations:

                ajouter_version_reformulation(
                    etude,
                    bloc.fid,
                    f"Reformulation {bloc.fid}."
                )

            valider_version_reformulation(
                etude,
                bloc.fid,
                numero=numero,
                validateur="David"
            )

    def test_reunion_entierement_validee(self, tmp_path):

        etude, reunions = creer_etude_reunions(tmp_path)
        reunion = reunions[0]

        assert reunion_entierement_validee(
            etude,
            reunion
        ) is False

        self._valider_tout(etude, reunion)

        assert reunion_entierement_validee(
            etude,
            reunion
        ) is True

    def test_texte_reunion_valide_resume_prioritaire(
        self, tmp_path
    ):
        """
        Le résumé validé (plus compact) prime sur les
        reformulations validées comme source de la
        synthèse.
        """

        etude, reunions = creer_etude_reunions(tmp_path)
        reunion = reunions[0]

        self._valider_tout(etude, reunion)

        ajouter_version_resume(
            etude,
            reunion,
            "Résumé validé compact.",
            source=SOURCE_BRUTE
        )

        valider_version_resume(
            etude,
            reunion,
            numero=1,
            validateur="David"
        )

        texte = texte_reunion_valide(etude, reunion)

        assert texte == "Résumé validé compact."

    def test_assemblage_ordre_et_troncation(
        self, tmp_path
    ):
        """
        Source de la synthèse : réunions dans l'ordre
        de l'étude ; troncation par le haut (les plus
        récentes restent).
        """

        sources = {
            "R1": ["Premier texte court."],
            "R2": ["Deuxième texte court."],
            "R3": ["Troisième texte court."],
        }

        etude, reunions = creer_etude_reunions(
            tmp_path,
            sources
        )

        for reunion in reunions:
            self._valider_tout(etude, reunion)

        assemblees = assembler_source_synthese(etude)

        assert [nom for nom, _ in assemblees] == (
            reunions
        )

        # Budget minuscule : une seule réunion, la
        # plus récente.
        resserrees = assembler_source_synthese(
            etude,
            budget_tokens=1
        )

        assert len(resserrees) == 1
        assert resserrees[0][0] == reunions[-1]

    def test_generation_version_et_journal(
        self, tmp_path
    ):
        """
        Génération : version contrats §9 (déclencheur,
        stats en journal — exactement une entrée par
        opération), persistée sur le disque.
        """

        from services.etude_io import ouvrir_etude

        etude, reunions = creer_etude_reunions(tmp_path)
        reunion = reunions[0]

        self._valider_tout(etude, reunion)

        avant = len(lire_journal(etude))

        client = ClientFactice(
            reponses=["Synthèse de l'étude."]
        )

        service = fabriquer_service(
            ServiceSynthese,
            etude,
            client
        )

        version, stats = service.generer(
            declencheur="manuel"
        )

        assert version.numero == 1
        assert version.declencheur == "manuel"
        assert version.texte == "Synthèse de l'étude."

        # Une entrée synthese (pas deux).
        entrees = lire_journal(etude)

        nouvelles = entrees[avant:]

        assert sum(
            1
            for entree in nouvelles
            if entree["type"] == "synthese"
        ) == 1

        # Prompt système dédié + longueur passée.
        assert client.appels[0][
            "prompt_systeme"
        ] == PROMPT_SYNTHESE

        assert "tokens" in client.appels[0]["message"]

        # Persisté.
        relue = ouvrir_etude(etude.dossier)

        assert len(relue.synthese.versions) == 1

    def test_generation_sans_texte_valide(self, tmp_path):

        etude, reunions = creer_etude_reunions(tmp_path)

        client = ClientFactice()

        service = fabriquer_service(
            ServiceSynthese,
            etude,
            client
        )

        with pytest.raises(Exception):
            service.generer()

        assert client.appels == []

    def test_estimation(self, tmp_path):

        etude, reunions = creer_etude_reunions(tmp_path)
        reunion = reunions[0]

        self._valider_tout(etude, reunion)

        client = ClientFactice()

        service = fabriquer_service(
            ServiceSynthese,
            etude,
            client
        )

        estimation = service.estimer()

        assert estimation["nb_reunions"] == 1
        assert estimation["cout_estime"] >= 0.0
        assert client.appels == []


class TestContexteCases:
    """
    P17.2 : cases de contexte du bloc reformulation
    (feuille de route §3.1) — cochées par défaut,
    une étude peut les décocher.
    """

    def _fabriquer(self, etude, reunion, client):

        return MoteurTraitements(
            etude,
            reunion,
            parametres_app=PARAMETRES_APP,
            credential_store=StoreFactice(),
            catalogue=catalogue_par_defaut(),
            client_factory=(
                lambda fournisseur, cle: client
            )
        )

    def _contexte(self, etude, reunion):

        moteur = self._fabriquer(etude, reunion, ClientFactice())

        bloc = moteur.blocs_a_traiter()[0]

        return moteur.assembler_contexte(bloc)

    def test_decochee_synthese_absente(self, tmp_path):

        etude, reunions = creer_etude_reunions(tmp_path)

        ajouter_version_synthese_manuelle(etude)

        contexte = self._contexte(etude, reunions[0])

        assert "Synthèse de l'étude" in contexte.message

        etude.parametres.reformulation["contexte"] = {
            "synthese_etude": False
        }

        contexte = self._contexte(etude, reunions[0])

        assert "Synthèse de l'étude" not in (
            contexte.message
        )

    def test_decochee_fenetre_absente(self, tmp_path):

        etude, reunions = creer_etude_reunions(tmp_path)
        reunion = reunions[0]

        fid = etude.decoupages[reunion].blocs[0].fid

        ajouter_version_reformulation(
            etude,
            fid,
            "Reformulation précédente."
        )

        etude.parametres.reformulation["contexte"] = {
            "fenetre_glissante": False
        }

        contexte = self._contexte(etude, reunion)

        assert "Reformulations précédentes" not in (
            contexte.message
        )

    def test_absentes_activées_par_défaut(self, tmp_path):

        etude, reunions = creer_etude_reunions(tmp_path)
        reunion = reunions[0]

        fid = etude.decoupages[reunion].blocs[0].fid

        ajouter_version_reformulation(
            etude,
            fid,
            "Reformulation précédente."
        )

        ajouter_version_synthese_manuelle(etude)

        # Une étude créée avant P17 n'a pas la clé
        # contexte : les deux restent actives.
        etude.parametres.reformulation.pop(
            "contexte",
            None
        )

        contexte = self._contexte(etude, reunion)

        assert "Synthèse de l'étude" in contexte.message
        assert "Reformulations précédentes" in (
            contexte.message
        )


def ajouter_version_synthese_manuelle(etude):

    from services.etude_io import (
        ajouter_version_synthese
    )

    ajouter_version_synthese(
        etude,
        "Thème : Luc 1. Pensée développée : l'annonce "
        "à Marie.",
        declencheur="manuel"
    )


class TestRecurrences:
    """
    P17.3 : formules les plus fréquentes de
    l'étude, présentes dans plusieurs réunions —
    gratuit, sans LLM, indicatif seulement.
    """

    def test_expression_partagee_signalée(self, tmp_path):

        sources = {
            "R1": [
                "Ce qui s'offre à nos cœurs est précieux. "
                "Une autre pensée suit. "
                "Ce qui s'offre à nos cœurs encore."
            ],
            "R2": [
                "Texte différent. "
                "Ce qui s'offre à nos cœurs dans un autre "
                "contexte. Une pensée autre."
            ],
        }

        etude, reunions = creer_etude_reunions(
            tmp_path,
            sources
        )

        for reunion in reunions:

            for bloc in etude.decoupages[reunion].blocs:

                ajouter_version_reformulation(
                    etude,
                    bloc.fid,
                    (
                        etude.decoupages[reunion]
                        .blocs[0].source
                    )
                )

                valider_version_reformulation(
                    etude,
                    bloc.fid,
                    numero=1,
                    validateur="David"
                )

        recurrentes = expressions_recurrentes(etude)

        expressions = [
            item["expression"]
            for item in recurrentes
        ]

        assert (
            "ce qui s'offre à nos cœurs"
            in expressions
        )

        item = next(
            item
            for item in recurrentes
            if item["expression"]
            == "ce qui s'offre à nos cœurs"
        )

        assert item["occurrences"] == 3
        assert len(item["reunions"]) == 2

    def test_expression_d_une_seule_reunion_ignorée(
        self, tmp_path
    ):

        sources = {
            "R1": [
                "Pensée unique répétée. "
                "Pensée unique répétée. "
                "Pensée unique répétée."
            ],
        }

        etude, reunions = creer_etude_reunions(
            tmp_path,
            sources
        )

        assert expressions_recurrentes(etude) == []

    def test_sans_texte_valide(self, tmp_path):

        etude, _reunions = creer_etude_reunions(tmp_path)

        assert expressions_recurrentes(etude) == []
