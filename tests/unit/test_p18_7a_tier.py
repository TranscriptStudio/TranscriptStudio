# tests/unit/test_p18_7a_tier.py
"""
P18.7a — Tier réunion : sous-dossier additif
``transcriptstudio\\`` dans le projet v1, structure exacte
§2 du contrat de stockage des réunions.

Couvre : création, structure exacte, aucune autre
modification du projet v1, réouverture, etudes[],
idempotence (double création refusée), projet sans tier.
"""

import json
from pathlib import Path

import pytest

from services.etude_schema import EtudeFormatError
from services.tier_reunion import (
    DOSSIER_TIER,
    FICHIER_REUNION,
    TierError,
    chemin_tier,
    creer_tier,
    ouvrir_tier,
    sauvegarder_tier,
    tier_existe,
)


def creer_projet_v1(dossier_parent: Path, nom: str) -> Path:
    """
    Crée un faux projet v1 : un dossier avec un
    project.sttproj minimal.
    """

    dossier = dossier_parent / nom
    dossier.mkdir(parents=True)

    donnees = {
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
    }

    (dossier / "project.sttproj").write_text(
        json.dumps(donnees),
        encoding="utf-8"
    )

    return dossier


class TestStructureTier:

    def test_structure_exacte(self, tmp_path):
        projet = creer_projet_v1(tmp_path, "2026-10-13_Luc1b")

        assert not tier_existe(projet)

        tier = creer_tier(projet, nom="2026-10-13_Luc1b")

        assert tier_existe(projet)

        racine = chemin_tier(projet)
        assert racine == projet / DOSSIER_TIER

        # Structure exacte §2.
        assert (racine / "reunion.json").is_file()
        assert (racine / "blocs" / "journal-fid.json").is_file()
        assert (racine / "blocs").is_dir()
        assert (
            racine / "traitements" / "reformulation"
        ).is_dir()
        assert (
            racine / "traitements" / "journal_operations.json"
        ).is_file()
        assert (
            racine / "parametres" / "parametres.json"
        ).is_file()

        # reunion.json : identité + etudes[] + resume_valide.
        donnees = json.loads(
            (racine / "reunion.json").read_text(
                encoding="utf-8"
            )
        )
        assert donnees["reunion_tier_version"] == 1
        assert donnees["nom"] == "2026-10-13_Luc1b"
        assert donnees["etudes"] == []
        assert donnees["resume_valide"] is False

    def test_aucune_autre_modification_projet_v1(self, tmp_path):
        projet = creer_projet_v1(tmp_path, "reunion_a")

        avant = sorted(
            p.relative_to(projet).as_posix()
            for p in projet.rglob("*")
        )

        creer_tier(projet, nom="reunion_a")

        apres_hors_tier = sorted(
            p.relative_to(projet).as_posix()
            for p in projet.rglob("*")
            if not p.relative_to(projet).as_posix().startswith(
                DOSSIER_TIER
            )
        )

        assert apres_hors_tier == avant

        # Le contenu du project.sttproj est inchangé.
        assert json.loads(
            (projet / "project.sttproj").read_text(
                encoding="utf-8"
            )
        )["name"] == "reunion_a"

    def test_double_creation_refusee(self, tmp_path):
        projet = creer_projet_v1(tmp_path, "reunion_b")

        creer_tier(projet, nom="reunion_b")

        with pytest.raises(TierError):
            creer_tier(projet, nom="reunion_b")

    def test_projet_sans_tier(self, tmp_path):
        projet = creer_projet_v1(tmp_path, "reunion_c")

        assert not tier_existe(projet)
        assert ouvrir_tier(projet) is None

    def test_reouverture(self, tmp_path):
        projet = creer_projet_v1(tmp_path, "reunion_d")

        creer_tier(projet, nom="reunion_d")

        tier = ouvrir_tier(projet)

        assert tier is not None
        assert tier.nom == "reunion_d"
        assert tier.registre.prochain_fid == 1
        assert tier.reformulations == {}
        assert tier.decoupage is None
        assert tier.resume is None
        assert tier.parametres.reformulation["modele"]
        assert tier.journal is not None


class TestEtudesDuTier:

    def test_enregistrer_et_returer_etude(self, tmp_path):
        projet = creer_projet_v1(tmp_path, "reunion_e")
        etude = tmp_path / "Etude_Luc"
        etude.mkdir()

        tier = creer_tier(projet, nom="reunion_e")

        tier.enregistrer_etude(etude, ajouter=True)

        relu = ouvrir_tier(projet)
        assert relu.reunion.etudes == ["../Etude_Luc"]

        # Le détachement est non destructif : seul etudes[]
        # change, le reste du tier est intact.
        relu.enregistrer_etude(etude, ajouter=False)

        relu2 = ouvrir_tier(projet)
        assert relu2.reunion.etudes == []
        assert (relu2.dossier / "blocs" / "journal-fid.json").exists()

    def test_enregistrer_deux_etudes(self, tmp_path):
        """
        etudes[] est une liste (la divergence éventuelle avec
        l'exclusivité est signalée à l'ouverture de l'étude,
        jamais auto-corrigée ici).
        """

        projet = creer_projet_v1(tmp_path, "reunion_f")
        etude_a = tmp_path / "Etude_A"
        etude_b = tmp_path / "Etude_B"
        etude_a.mkdir()
        etude_b.mkdir()

        tier = creer_tier(projet, nom="reunion_f")
        tier.enregistrer_etude(etude_a, ajouter=True)
        tier.enregistrer_etude(etude_b, ajouter=True)

        relu = ouvrir_tier(projet)
        assert relu.reunion.etudes == [
            "../Etude_A",
            "../Etude_B",
        ]


class TestSauvegardeTier:

    def test_round_trip_complet(self, tmp_path):
        from models.etude import (
            DecoupageReunion,
            ResultatReformulation,
            ResultatResume,
            VersionReformulation,
            VersionResume,
        )

        projet = creer_projet_v1(tmp_path, "reunion_g")
        tier = creer_tier(projet, nom="reunion_g")

        tier.registre.prochain_fid = 3
        tier.decoupage = DecoupageReunion(
            reunion="reunion_g",
            blocs=[],
        )
        tier.reformulations[2] = ResultatReformulation(
            fid=2,
            versions=[
                VersionReformulation(
                    numero=1,
                    texte="texte reformulé",
                    horodatage="2026-11-08T10:00:00",
                )
            ],
        )
        tier.resume = ResultatResume(
            reunion="reunion_g",
            versions=[
                VersionResume(
                    numero=1,
                    texte="résumé",
                    source="reformulations_valides",
                    horodatage="2026-11-08T10:05:00",
                )
            ],
        )
        tier.reunion.resume_valide = True

        sauvegarder_tier(tier)

        relu = ouvrir_tier(projet)

        assert relu.registre.prochain_fid == 3
        assert relu.decoupage is not None
        assert relu.decoupage.reunion == "reunion_g"
        assert relu.reformulations[2].versions[0].texte == (
            "texte reformulé"
        )
        assert relu.resume.versions[0].texte == "résumé"
        assert relu.reunion.resume_valide is True

        # Fichiers écrits à l'emplacement exact §2.
        racine = chemin_tier(projet)
        assert (racine / "blocs" / "decoupage.json").is_file()
        assert (
            racine / "traitements" / "reformulation" / "2.json"
        ).is_file()
        assert (
            racine / "traitements" / "resume.json"
        ).is_file()

    def test_fichier_tier_invalide(self, tmp_path):
        projet = creer_projet_v1(tmp_path, "reunion_h")
        creer_tier(projet, nom="reunion_h")

        racine = chemin_tier(projet)
        (racine / "reunion.json").write_text(
            json.dumps({"nom": "x"}),
            encoding="utf-8"
        )

        with pytest.raises(EtudeFormatError):
            ouvrir_tier(projet)
