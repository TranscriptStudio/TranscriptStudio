# tests/unit/test_p18_7e_params_invariants.py
"""
P18.7e — Paramètres et écritures (§8/§8bis) : toute
opération sur les traitements d'une réunion, où qu'elle
soit lancée, utilise les paramètres DU TIER ; les
surcharges d'étude s'appliquent à la synthèse uniquement ;
aucune écriture en retour (ni l'étude ni l'ouvrage
n'écrivent dans le tier).

Contient aussi les 8 invariants du §12 du contrat de
stockage des réunions.
"""

import json
from pathlib import Path

import pytest

from services.etude_io import (
    ajouter_reunion,
    ajouter_version_reformulation,
    ajouter_version_synthese,
    attribuer_fid,
    creer_etude,
    ouvrir_etude,
    parametres_par_defaut,
    sauvegarder_etude,
)
from services.tier_reunion import (
    chemin_tier,
    ouvrir_tier,
    sauvegarder_tier,
)


def creer_projet_v1(dossier_parent: Path, nom: str) -> Path:
    dossier = dossier_parent / nom
    dossier.mkdir(parents=True)

    (dossier / "project.sttproj").write_text(
        json.dumps({
            "project_format_version": 1,
            "name": nom,
            "audio_file": "audio.wav",
            "transcription_id": None,
            "language_code": "fr",
            "duration_seconds": 100.0,
            "modified": False,
            "speakers": [],
            "words": [],
            "blocks": [],
            "original_elevenlabs_response": {},
        }),
        encoding="utf-8"
    )

    return dossier


def _etude_avec_reunion(tmp_path, nom_projet="2026-10-13_Luc1b"):
    projet = creer_projet_v1(tmp_path, nom_projet)
    etude = creer_etude(tmp_path / "Etude", "Évangile de Luc")
    nom = ajouter_reunion(etude, projet, "Chapitre 1")
    sauvegarder_etude(etude)
    return projet, etude, nom


class TestParametresDuTier:

    def test_parametres_traitement_viennent_du_tier(self, tmp_path):
        """
        §8 : les paramètres utilisés par les traitements
        d'une réunion sont ceux du tier — pas ceux de
        l'étude.
        """

        projet, etude, nom = _etude_avec_reunion(tmp_path)

        tier = etude.tier_de(nom)

        # Le tier a ses propres paramètres complets.
        assert tier.parametres.reformulation["modele"]
        assert tier.parametres.resume["source_defaut"]

        # paramétrage différent dans le tier.
        tier.parametres.reformulation["temperature"] = 0.9
        tier.parametres.resume["longueur_cible_mots"] = [100, 200]

        assert (
            etude.parametres_traitement_de(nom)
            .reformulation["temperature"]
            == 0.9
        )

        # L'étude ne garde que la surcharge de synthèse.
        etude.parametres.synthese["tokens_max"] = 900

        donnees = json.loads(
            (
                tmp_path / "Etude" / "parametres"
                / "parametres.json"
            ).read_text(encoding="utf-8")
        )

        sauvegarder_etude(etude)

        donnees = json.loads(
            (
                tmp_path / "Etude" / "parametres"
                / "parametres.json"
            ).read_text(encoding="utf-8")
        )

        assert set(donnees.keys()) == {"synthese"}
        assert donnees["synthese"]["tokens_max"] == 900

    def test_surcharge_etude_synthese_seule(self, tmp_path):
        """
        §8bis : après réouverture, les surcharges d'étude
        ne concernent que la synthèse ; les paramètres de
        traitement sont relus dans le tier.
        """

        projet, etude, nom = _etude_avec_reunion(tmp_path)

        etude.parametres.synthese["tokens_max"] = 4242
        sauvegarder_etude(etude)

        etude.tier_de(nom).parametres.reformulation[
            "temperature"
        ] = 0.77
        sauvegarder_tier(etude.tier_de(nom))

        relue = ouvrir_etude(tmp_path / "Etude")

        assert relue.parametres.synthese["tokens_max"] == 4242
        assert (
            relue.parametres_traitement_de(nom)
            .reformulation["temperature"]
            == 0.77
        )

    def test_moteur_utilise_les_parametres_du_tier(self, tmp_path):
        """
        Le moteur lit la température/modele DU TIER de la
        réunion, où que la passe soit lancée.
        """

        from tests.unit.test_moteur_traitements import (
            ClientFactice,
            creer_etude_avec_blocs,
            fabriquer_moteur,
        )
        from services.llm.catalogue import (
            catalogue_par_defaut,
        )

        etude, nom = creer_etude_avec_blocs(tmp_path, nb_blocs=1)

        etude.tier_de(nom).parametres.reformulation[
            "temperature"
        ] = 0.11

        client = ClientFactice(
            fournisseur=(
                catalogue_par_defaut()
                .chercher_fournisseur("openai")
            ),
            cle="",
        )

        moteur = fabriquer_moteur(etude, nom, client)

        assert moteur.temperature_effective() == 0.11

        moteur.traiter_reunion()

        assert client.appels[0]["temperature"] == 0.11


class TestAucuneEcritureEnRetour:

    def test_sauvegarder_etude_n_ecrit_pas_dans_le_tier(
        self, tmp_path
    ):
        """
        §8 : sauvegarder_etude n'écrit JAMAIS dans le tier
        d'une réunion (aucune écriture en retour).
        """

        projet, etude, nom = _etude_avec_reunion(tmp_path)

        fid = attribuer_fid(etude, nom)
        ajouter_version_reformulation(etude, nom, fid, "R1")

        racine = chemin_tier(projet)

        empreintes = {
            p.relative_to(racine).as_posix(): p.read_bytes()
            for p in racine.rglob("*")
            if p.is_file()
        }

        # Sauvegarde de l'étude seule : le tier ne bouge pas
        # (les opérations de traitement, elles, sauvegardent
        # le tier explicitement — déjà fait ci-dessus).
        sauvegarder_etude(etude)

        apres = {
            p.relative_to(racine).as_posix(): p.read_bytes()
            for p in racine.rglob("*")
            if p.is_file()
        }

        assert empreintes == apres

    def test_ouvrage_n_ecrit_pas_dans_le_tier(self, tmp_path):
        """
        La génération de l'ouvrage (couche ouvrage) ne
        modifie jamais le tier.
        """

        from services.ouvrage_document import (
            charger_ouvrage,
            generer_document,
            sauvegarder_ouvrage,
        )

        projet, etude, nom = _etude_avec_reunion(tmp_path)

        fid = attribuer_fid(etude, nom)
        ajouter_version_reformulation(etude, nom, fid, "R1")
        from services.etude_io import (
            valider_version_reformulation,
        )
        valider_version_reformulation(
            etude, nom, fid, numero=1, validateur="David"
        )
        sauvegarder_etude(etude)

        racine = chemin_tier(projet)

        avant = {
            p.relative_to(racine).as_posix(): p.read_bytes()
            for p in racine.rglob("*")
            if p.is_file()
        }

        doc = generer_document(etude)
        sauvegarder_ouvrage(doc, tmp_path / "Etude")
        assert charger_ouvrage(tmp_path / "Etude") is not None

        apres = {
            p.relative_to(racine).as_posix(): p.read_bytes()
            for p in racine.rglob("*")
            if p.is_file()
        }

        assert avant == apres


class TestInvariants12:
    """
    Les 8 invariants du §12 du contrat de stockage des
    réunions.
    """

    def test_inv1_ouvrir_ne_modifie_pas_le_projet_v1(
        self, tmp_path
    ):
        """
        1. Ouvrir une étude ne modifie jamais aucun projet
        v1 référencé (hors création additive du tier à
        l'attachement / première opération de traitement).
        """

        projet = creer_projet_v1(tmp_path, "projet_a")
        sttproj = projet / "project.sttproj"
        empreinte_avant = sttproj.read_bytes()

        etude = creer_etude(tmp_path / "Etude", "Étude")
        nom = ajouter_reunion(etude, projet)
        sauvegarder_etude(etude)

        # L'attachement crée UNIQUEMENT le tier additif.
        assert sorted(
            p.name for p in projet.iterdir()
        ) == ["project.sttproj", "transcriptstudio"]

        contenu_tier = sorted(
            p.relative_to(projet).as_posix()
            for p in (projet / "transcriptstudio").rglob("*")
        )

        # Ouvrir/sauvegarder l'étude : le projet ne bouge pas.
        for _ in range(2):
            relue = ouvrir_etude(tmp_path / "Etude")
            sauvegarder_etude(relue)

        assert sttproj.read_bytes() == empreinte_avant
        assert sorted(
            p.relative_to(projet).as_posix()
            for p in (projet / "transcriptstudio").rglob("*")
        ) == contenu_tier

    def test_inv2_couple_fid_stable(self, tmp_path):
        """
        2. Le couple (réunion, FID), une fois attribué,
        désigne pour toujours le même discours ; les
        versions ne s'écrasent pas.
        """

        projet, etude, nom = _etude_avec_reunion(tmp_path)

        fid = attribuer_fid(etude, nom)
        ajouter_version_reformulation(etude, nom, fid, "V1")
        ajouter_version_reformulation(etude, nom, fid, "V2")

        relue = ouvrir_etude(tmp_path / "Etude")

        resultat = relue.reformulation_de(nom, fid)
        assert [v.numero for v in resultat.versions] == [1, 2]
        assert resultat.versions[0].texte == "V1"

    def test_inv3_detachement_non_destructif(self, tmp_path):
        """
        3. Le détachement d'une réunion est non destructif :
        la réunion garde tout son travail (tier intact).
        """

        from services.rattachement import detacher_reunion

        projet, etude, nom = _etude_avec_reunion(tmp_path)

        fid = attribuer_fid(etude, nom)
        ajouter_version_reformulation(etude, nom, fid, "R1")
        sauvegarder_etude(etude)

        detacher_reunion(etude, nom)
        sauvegarder_etude(etude)

        assert nom not in etude.etude.ordre_reunions

        tier = ouvrir_tier(projet)
        assert fid in tier.reformulations
        assert tier.reformulations[fid].versions[0].texte == "R1"
        assert tier.reunion.etudes == []

    def test_inv4_exclusivite(self, tmp_path):
        """
        4. Une réunion (projet v1) est rattachée à AU PLUS
        une étude à la fois.
        """

        from services.rattachement import (
            verifier_exclusivite,
        )

        projet = creer_projet_v1(tmp_path, "projet_a")

        etude_a = creer_etude(tmp_path / "EtudeA", "A")
        ajouter_reunion(etude_a, projet)
        sauvegarder_etude(etude_a)

        conflit = verifier_exclusivite(
            projet / "project.sttproj",
            [tmp_path / "EtudeA", tmp_path / "EtudeB"]
        )

        assert conflit is not None
        assert conflit[0] == str(tmp_path / "EtudeA")

    def test_inv5_portabilite_chemins(self, tmp_path):
        """
        5. Déplacer le dossier étude (ou le projet) reste
        sûr : résolution relatif → absolu → relocalisation.
        """

        projet, etude, nom = _etude_avec_reunion(tmp_path)

        # Déplace le dossier étude : le chemin relatif casserait,
        # le chemin absolu de secours prend le relais.
        deplace = tmp_path / "Ailleurs" / "Etude"
        deplace.parent.mkdir()
        (tmp_path / "Etude").rename(deplace)

        relue = ouvrir_etude(deplace)

        assert relue.reunion_joignable(nom)
        assert relue.chemins_resolus[nom] == projet.resolve()

    def test_inv6_aucune_ecriture_en_retour(self, tmp_path):
        """
        6. Ni l'étude ni l'ouvrage n'écrivent jamais dans le
        tier ; seules les opérations sur les traitements
        d'une réunion y écrivent.
        """

        # couvert par TestAucuneEcritureEnRetour.
        pass

    def test_inv7_parametres_du_tier(self, tmp_path):
        """
        7. Toute opération sur les traitements d'une
        réunion utilise les paramètres du tier de cette
        réunion.
        """

        # couvert par TestParametresDuTier.
        pass

    def test_inv8_divergences_signalees_pas_corrigees(
        self, tmp_path
    ):
        """
        8. Toute divergence etudes[] du tier vs
        ordre_reunions est signalée à l'ouverture, jamais
        auto-corrigée.
        """

        from services.tier_reunion import (
            sauvegarder_reunion_tier,
        )

        projet, etude, nom = _etude_avec_reunion(tmp_path)

        tier = ouvrir_tier(projet)
        tier.reunion.etudes.append("../EtudeInconnue")
        sauvegarder_reunion_tier(tier)

        relue = ouvrir_etude(tmp_path / "Etude")

        assert any(
            "EtudeInconnue" in d for d in relue.divergences
        )

        # Pas de correction automatique sur disque.
        assert "../EtudeInconnue" in (
            ouvrir_tier(projet).reunion.etudes
        )
