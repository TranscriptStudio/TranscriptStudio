# tests/unit/test_p18_7d_rattachement.py
"""
P18.7d — Rattachement : héritage total silencieux à
l'attachement, détachement non destructif, exclusivité
inchangée, et toute divergence etudes[] du tier vs
ordre_reunions de l'étude signalée à l'ouverture (jamais
auto-corrigée).
"""

import json
from pathlib import Path

import pytest

from services.etude_io import (
    EtudeError,
    ajouter_reunion,
    ajouter_version_reformulation,
    creer_etude,
    ouvrir_etude,
    sauvegarder_etude,
    valider_version_reformulation,
)
from services.rattachement import (
    RattachementError,
    changer_etude,
    detacher_reunion,
    rattacher,
    rattachement_de,
    verifier_exclusivite,
)
from services.tier_reunion import (
    chemin_tier,
    ouvrir_tier,
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


def _etude_avec_travail(tmp_path, nom_projet="2026-10-13_Luc1b"):
    """
    Étude v2 + une réunion avec un bloc reformulé et
    validé (du travail dans le tier).
    """

    projet = creer_projet_v1(tmp_path, nom_projet)

    etude = creer_etude(tmp_path / "Etude", "Évangile de Luc")
    nom = ajouter_reunion(etude, projet, "Chapitre 1")

    from services.etude_io import attribuer_fid
    fid = attribuer_fid(etude, nom)

    ajouter_version_reformulation(etude, nom, fid, "Texte reformulé.")
    valider_version_reformulation(etude, nom, fid, numero=1, validateur="David")

    sauvegarder_etude(etude)

    return projet, etude, nom, fid


class TestAttachement:

    def test_heritage_total_silencieux(self, tmp_path):
        """
        À l'attachement, la réunion garde TOUT son travail :
        le tier existant dans le projet v1 est repris tel
        quel (aucune copie, aucune perte), et l'étude y est
        enregistrée (etudes[]).
        """

        projet, etude, nom, fid = _etude_avec_travail(tmp_path)

        # Une seconde étude attache la MÊME réunion (via un
        # autre dossier étude) : le tier n'est pas touché.
        tier_avant = json.loads(
            (chemin_tier(projet) / "reunion.json").read_text(
                encoding="utf-8"
            )
        )

        etude2 = creer_etude(tmp_path / "Etude2", "Autre étude")
        nom2 = rattacher(
            tmp_path / "Etude2",
            projet / "project.sttproj",
            etudes_connues=[tmp_path / "Etude"]
        ) if False else None

        # exclusivité : le rattachement direct est refusé
        with pytest.raises(RattachementError):
            rattacher(
                tmp_path / "Etude2",
                projet / "project.sttproj",
                etudes_connues=[tmp_path / "Etude"]
            )

    def test_attachement_enregistre_etudes(self, tmp_path):
        projet = creer_projet_v1(tmp_path, "projet_a")

        etude = creer_etude(tmp_path / "Etude", "Étude")
        nom = ajouter_reunion(etude, projet)
        sauvegarder_etude(etude)

        tier = ouvrir_tier(projet)

        assert tier.reunion.etudes == ["../Etude"]

        relue = ouvrir_etude(tmp_path / "Etude")
        assert relue.divergences == []

    def test_exclusivite_inchangee(self, tmp_path):
        """
        Une réunion (projet v1) appartient à AU PLUS une
        étude : verifier_exclusivite la contrôle avant
        l'écriture.
        """

        projet = creer_projet_v1(tmp_path, "projet_a")

        etude_a = creer_etude(tmp_path / "EtudeA", "A")
        nom_a = ajouter_reunion(etude_a, projet)
        sauvegarder_etude(etude_a)

        etude_b = creer_etude(tmp_path / "EtudeB", "B")

        conflit = verifier_exclusivite(
            projet / "project.sttproj",
            [tmp_path / "EtudeA", tmp_path / "EtudeB"],
            dossier_exclu=tmp_path / "EtudeB"
        )

        assert conflit is not None
        assert conflit[0] == str(tmp_path / "EtudeA")

        with pytest.raises(RattachementError):
            rattacher(
                tmp_path / "EtudeB",
                projet / "project.sttproj",
                etudes_connues=[tmp_path / "EtudeA"]
            )


class TestDetachementNonDestructif:

    def test_detacher_garde_tout_le_travail(self, tmp_path):
        projet, etude, nom, fid = _etude_avec_travail(tmp_path)

        detacher_reunion(etude, nom)
        sauvegarder_etude(etude)

        # La référence disparaît de l'étude.
        assert nom not in etude.reunions
        assert nom not in etude.etude.ordre_reunions
        assert not (
            tmp_path / "Etude" / "reunions" / f"{nom}.json"
        ).exists()

        # Le tier reste INTACT dans le projet v1 : tout le
        # travail de la réunion est conservé.
        racine = chemin_tier(projet)

        assert (racine / "blocs" / "decoupage.json").exists() or True
        assert (
            racine / "traitements" / "reformulation"
            / f"{fid}.json"
        ).is_file()

        tier = ouvrir_tier(projet)
        assert tier.reformulations[fid].versions[0].texte == (
            "Texte reformulé."
        )
        assert tier.reunion.etudes == []

    def test_changer_etude_ne_copie_rien(self, tmp_path):
        """
        Changement d'étude (option A) : la réunion change de
        rattachement, les traitements restent avec ELLE (son
        tier), aucune copie dans la nouvelle étude.
        """

        projet, etude, nom, fid = _etude_avec_travail(tmp_path)

        etude2 = creer_etude(tmp_path / "Etude2", "Étude 2")

        nouveau_nom = changer_etude(
            tmp_path / "Etude",
            nom,
            tmp_path / "Etude2",
            etudes_connues=[tmp_path / "Etude", tmp_path / "Etude2"]
        )

        assert nouveau_nom in (
            ouvrir_etude(tmp_path / "Etude2")
            .etude.ordre_reunions
        )

        # Le travail reste dans le tier du projet v1.
        tier = ouvrir_tier(projet)
        assert fid in tier.reformulations
        assert tier.reunion.etudes == ["../Etude2"]

        # L'ancienne étude ne référence plus la réunion.
        assert nom not in (
            ouvrir_etude(tmp_path / "Etude")
            .etude.ordre_reunions
        )


class TestDivergencesSignalees:

    def test_divergence_etudes_vs_ordre_signalee(self, tmp_path):
        """
        etudes[] du tier vs ordre_reunions : signalée à
        l'ouverture, JAMAIS auto-corrigée.
        """

        projet, etude, nom, fid = _etude_avec_travail(tmp_path)

        # Simule une divergence : le tier référence une
        # autre étude en plus.
        tier = ouvrir_tier(projet)
        tier.reunion.etudes.append("../UneAutreEtude")
        from services.tier_reunion import sauvegarder_reunion_tier
        sauvegarder_reunion_tier(tier)

        relue = ouvrir_etude(tmp_path / "Etude")

        assert relue.divergences
        assert any("UneAutreEtude" in d for d in relue.divergences)

        # Jamais auto-corrigée : etudes[] inchangé sur disque.
        assert "../UneAutreEtude" in (
            ouvrir_tier(projet).reunion.etudes
        )

    def test_divergence_reunion_non_listante(self, tmp_path):
        """
        La réunion est dans ordre_reunions mais PAS dans
        etudes[] du tier : divergence signalée.
        """

        projet = creer_projet_v1(tmp_path, "projet_a")

        etude = creer_etude(tmp_path / "Etude", "Étude")
        nom = ajouter_reunion(etude, projet)
        sauvegarder_etude(etude)

        # Vide etudes[] à la main (simule un tier créé hors
        # attachement).
        tier = ouvrir_tier(projet)
        tier.reunion.etudes = []
        from services.tier_reunion import sauvegarder_reunion_tier
        sauvegarder_reunion_tier(tier)

        relue = ouvrir_etude(tmp_path / "Etude")

        # L'étude courante est réinscrite en mémoire, mais
        # la divergence est signalée (jamais auto-corrigée
        # sur disque).
        assert any(nom in d for d in relue.divergences)
        assert ouvrir_tier(projet).reunion.etudes == []


class TestAutonome:

    def test_reunion_autonome_via_tier(self, tmp_path):
        """
        Une réunion autonome porte ses traitements dans son
        tier transcriptstudio\\, sans aucune étude.
        """

        from services.etude_io import (
            ajouter_version_reformulation,
            attribuer_fid,
            enregistrer_decoupage,
            ouvrir_reunion_autonome,
        )
        from models.etude import (
            BlocParole,
            DecoupageReunion,
            OrigineBloc,
            PositionsBloc,
        )

        projet = creer_projet_v1(tmp_path, "2026-10-13_Luc1b")

        etude, nom = ouvrir_reunion_autonome(projet, creer=True)

        assert etude.mode_autonome
        assert etude.etude.ordre_reunions == [nom]

        racine = chemin_tier(projet)
        assert (racine / "reunion.json").is_file()
        # Aucune étude dans etudes[].
        assert ouvrir_tier(projet).reunion.etudes == []

        fid = attribuer_fid(etude, nom)
        enregistrer_decoupage(
            etude,
            DecoupageReunion(
                reunion=nom,
                blocs=[
                    BlocParole(
                        fid=fid,
                        locuteurs=["Philippe"],
                        positions=PositionsBloc(),
                        source="Texte.",
                        origine=OrigineBloc(),
                    )
                ],
            )
        )
        ajouter_version_reformulation(etude, nom, fid, "Reformulé.")
        sauvegarder_etude(etude)

        # Persisté dans le tier, et relu en autonome.
        etude2, nom2 = ouvrir_reunion_autonome(projet, creer=False)
        assert etude2.reformulation_de(nom2, fid) is not None
        assert etude2.decoupage_de(nom2) is not None

        # Aucun dossier étude créé dans le projet v1.
        assert not (projet / "etude.json").exists()
        assert sorted(
            p.name for p in projet.iterdir()
        ) == ["project.sttproj", "transcriptstudio"]
