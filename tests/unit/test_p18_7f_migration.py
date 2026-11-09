# tests/unit/test_p18_7f_migration.py
"""
P18.7f — Migration one-shot v1→v2 (§11) : à l'ouverture
d'une étude version 1, sauvegarde complète dans
sauvegardes\\, éclatement par réunion dans les tiers,
requalification en couples (réunion, FID) des références
de blocs (ouvrage.json y compris instantanés de fusion
et historique de dé-fusion, contexte des versions),
contrôle d'intégrité AVANT toute suppression, idempotente
et reprenable après crash. Non-régression P19 : l'ouvrage
livré fonctionne à l'identique après migration.
"""

import json
import shutil
from pathlib import Path

import pytest

from services.etude_io import (
    ajouter_version_synthese,
    ouvrir_etude,
    parametres_par_defaut,
    sauvegarder_etude,
)
from services.migration_etude import (
    DOSSIER_SAUVEGARDE_V1,
    MigrationError,
    migrer_etude_v1_vers_v2,
    migrer_traitements_internes,
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


def _provenance(reunion, fid, numero_reunion=1):
    return {
        "reunion": reunion,
        "fid": fid,
        "numero_reunion": numero_reunion,
        "date_reunion": "2026-10-13",
        "locuteurs": "Philippe",
        "numero_version": 1,
        "horodatage_version": "2026-11-01T11:00:00",
    }


def fabriquer_etude_v1(tmp_path, avec_ouvrage_fusion=True) -> Path:
    """
    Construit à la main une étude v1 complète (layout
    ancien) : 2 réunions, registre global, découpages,
    reformulations validées (contexte en FID nus),
    résumé + resume_valide, journal, synthèse, paramètres,
    et un ouvrage.json avec provenances + une fusion.
    """

    dossier = tmp_path / "Etude"

    for sd in (
        "reunions",
        "blocs/decoupage",
        "traitements/reformulation",
        "traitements/resume",
        "synthese",
        "parametres",
    ):
        (dossier / sd).mkdir(parents=True)

    (dossier / "etude.json").write_text(
        json.dumps({
            "etude_format_version": 1,
            "titre": "Évangile de Luc",
            "theme": "livre",
            "gabarit_titre_1": "Chapitre {chapitre} — {section}",
            "ordre_reunions": ["r1", "r2"],
            "creation": "2026-11-01T10:00:00",
            "modification": "2026-11-01T10:00:00",
        }),
        encoding="utf-8"
    )

    projets = {}

    for nom in ("r1", "r2"):
        p = creer_projet_v1(tmp_path, nom)
        projets[nom] = p

        (dossier / "reunions" / f"{nom}.json").write_text(
            json.dumps({
                "reference": f"{nom}.json",
                "chemin_projet": f"../{nom}",
                "chemin_absolu": str(p.resolve()),
                "date": "2026-10-13",
                "numero": 1,
                "titre_1": "Chapitre 1",
                "resume_valide": nom == "r1",
            }),
            encoding="utf-8"
        )

    (dossier / "blocs" / "journal-fid.json").write_text(
        json.dumps({
            "prochain_fid": 5,
            "fid_attribues": {
                "1": {"reunion": "r1", "cree": "2026-11-01T10:00:00", "actif": True, "fin": None},
                "2": {"reunion": "r1", "cree": "2026-11-01T10:00:00", "actif": True, "fin": None},
                "3": {"reunion": "r2", "cree": "2026-11-01T10:00:00", "actif": True, "fin": None},
                "4": {"reunion": "r2", "cree": "2026-11-01T10:00:00", "actif": False, "fin": "2026-11-02T10:00:00"},
            },
        }),
        encoding="utf-8"
    )

    for nom, fids in (("r1", [1, 2]), ("r2", [3, 4])):
        blocs = [
            {
                "fid": f,
                "locuteurs": ["Philippe"],
                "positions": {"debut": "00:00:01.000", "fin": "00:00:09.000"},
                "source": f"Texte du bloc {f}.",
                "origine": {"fusion_de": None, "sous_decoupage": False},
            }
            for f in fids
        ]

        (dossier / "blocs" / "decoupage" / f"{nom}.json").write_text(
            json.dumps({"reunion": nom, "blocs": blocs}),
            encoding="utf-8"
        )

    for fid in (1, 2, 3):
        (dossier / "traitements" / "reformulation" / f"{fid}.json").write_text(
            json.dumps({
                "fid": fid,
                "versions": [
                    {
                        "numero": 1,
                        "texte": f"Reformulation {fid}.",
                        "horodatage": "2026-11-01T11:00:00",
                        "type": "passe",
                        "consigne": None,
                        "selection": None,
                        "stats": None,
                        "validation": {
                            "statut": "valide",
                            "horodatage": "2026-11-01T11:30:00",
                            "validateur": "David",
                        },
                        # contexte en FID nus (v1)
                        "contexte": [fid - 1] if fid > 1 else [],
                    }
                ],
            }),
            encoding="utf-8"
        )

    (dossier / "traitements" / "resume" / "r1.json").write_text(
        json.dumps({
            "reunion": "r1",
            "versions": [
                {
                    "numero": 1,
                    "texte": "Résumé r1.",
                    "source": "brute_corrigee",
                    "horodatage": "2026-11-01T12:00:00",
                    "stats": None,
                    "origine": "generation",
                    "consigne": None,
                    "validation": {
                        "statut": "valide",
                        "horodatage": "2026-11-01T12:30:00",
                        "validateur": "David",
                    },
                }
            ],
        }),
        encoding="utf-8"
    )

    (dossier / "traitements" / "journal_operations.json").write_text(
        json.dumps({
            "journal_version": 1,
            "entrees": [
                {"horodatage": "2026-11-01T11:00:00", "type": "reformulation_bloc", "fid": 1, "reunion": "r1", "modele": "m", "version": 1, "resultat": "succes", "stats": None},
                {"horodatage": "2026-11-01T12:00:00", "type": "resume", "fid": None, "reunion": "r1", "modele": "m", "version": 1, "resultat": "succes", "stats": None},
                {"horodatage": "2026-11-01T13:00:00", "type": "synthese", "fid": None, "reunion": None, "modele": "m", "version": 1, "resultat": "succes", "stats": None},
            ],
        }),
        encoding="utf-8"
    )

    (dossier / "synthese" / "synthese.json").write_text(
        json.dumps({
            "versions": [
                {
                    "numero": 1,
                    "texte": "Synthèse.",
                    "horodatage": "2026-11-01T13:00:00",
                    "declencheur": "manuel",
                }
            ]
        }),
        encoding="utf-8"
    )

    (dossier / "parametres" / "parametres.json").write_text(
        json.dumps(parametres_par_defaut().to_dict()),
        encoding="utf-8"
    )

    if avec_ouvrage_fusion:
        elements = [
            {
                "id": "p1",
                "type": "paragraphe",
                "texte": "Reformulation 1.",
                "source": "generation",
                "provenances": [_provenance("r1", 1, 1)],
            },
            {
                "id": "pf",
                "type": "paragraphe",
                "texte": "Fusion de pensées.",
                "source": "fusion",
                "provenances": [
                    _provenance("r1", 2, 1),
                    _provenance("r2", 3, 2),
                ],
                "fusion": {
                    "elements": [
                        {
                            "id": "p2",
                            "type": "paragraphe",
                            "texte": "Reformulation 2.",
                            "source": "generation",
                            "provenances": [_provenance("r1", 2, 1)],
                        },
                        {
                            "id": "p3",
                            "type": "paragraphe",
                            "texte": "Reformulation 3.",
                            "source": "generation",
                            "provenances": [_provenance("r2", 3, 2)],
                        },
                    ]
                },
            },
        ]

        (dossier / "ouvrage.json").write_text(
            json.dumps({
                "format_version": 1,
                "titre": "Évangile de Luc",
                "elements": elements,
                "generation": {
                    "horodatage": "2026-11-01T14:00:00",
                    "reunions": {
                        "r1": {
                            "numero": 1,
                            "date": "2026-10-13",
                            "paragraphes": 2,
                            "versions": {
                                "1": {"numero": 1, "horodatage": "2026-11-01T11:00:00"},
                                "2": {"numero": 1, "horodatage": "2026-11-01T11:00:00"},
                            },
                        },
                        "r2": {
                            "numero": 2,
                            "date": "2026-10-20",
                            "paragraphes": 1,
                            "versions": {
                                "3": {"numero": 1, "horodatage": "2026-11-01T11:00:00"},
                            },
                        },
                    },
                },
                "historique": [],
            }),
            encoding="utf-8"
        )

    return dossier


class TestMigrationRoundTrip:

    def test_round_trip_complet(self, tmp_path):
        """
        Ouvrir une étude v1 déclenche la migration one-shot
        complète : sauvegarde, éclatement par réunion dans
        les tiers, étude réécrite en v2.
        """

        dossier = fabriquer_etude_v1(tmp_path)

        etude = ouvrir_etude(dossier)

        assert etude.etude.etude_format_version == 2
        assert sorted(etude.tiers.keys()) == ["r1", "r2"]

        # Registres éclatés par réunion (mêmes numéros).
        assert sorted(
            etude.tiers["r1"].registre.entrees.keys()
        ) == [1, 2]
        assert sorted(
            etude.tiers["r2"].registre.entrees.keys()
        ) == [3, 4]

        # Reformulations aiguillées par le registre.
        assert sorted(
            etude.tiers["r1"].reformulations.keys()
        ) == [1, 2]
        assert sorted(
            etude.tiers["r2"].reformulations.keys()
        ) == [3]

        # Découpage, résumé, resume_valide migrés.
        assert etude.tiers["r1"].decoupage is not None
        assert etude.tiers["r1"].resume is not None
        assert etude.tiers["r1"].reunion.resume_valide is True
        assert etude.tiers["r2"].reunion.resume_valide is False

        # Contexte requalifié en couples (réunion, FID).
        contexte = etude.tiers["r1"].reformulations[2].versions[
            0
        ].contexte
        assert contexte == [{"reunion": "r1", "fid": 1}]

        # blocs\ et traitements\ supprimés du dossier étude,
        # APRÈS sauvegarde complète dans sauvegardes\.
        assert not (dossier / "blocs").exists()
        assert not (dossier / "traitements").exists()
        assert (
            dossier / "sauvegardes" / DOSSIER_SAUVEGARDE_V1
            / "blocs" / "journal-fid.json"
        ).is_file()

        # Étude v2 : paramètres = surcharges synthèse seule ;
        # journal d'étude à la racine.
        donnees = json.loads(
            (dossier / "parametres" / "parametres.json").read_text(
                encoding="utf-8"
            )
        )
        assert set(donnees.keys()) == {"synthese"}
        assert (dossier / "journal_etude.json").is_file()

        # Journal éclaté : les entrées de r1 dans le tier,
        # la synthèse dans le journal d'étude.
        tier_r1 = ouvrir_tier(tmp_path / "r1")
        assert len(tier_r1.journal.entrees) == 2

        entrees_etude = json.loads(
            (dossier / "journal_etude.json").read_text(
                encoding="utf-8"
            )
        )["entrees"]
        assert [e["type"] for e in entrees_etude] == ["synthese"]

        # etudes[] renseigné dans chaque tier.
        assert tier_r1.reunion.etudes == ["../Etude"]

        # Aucune divergence.
        assert etude.divergences == []

    def test_idempotente(self, tmp_path):
        dossier = fabriquer_etude_v1(tmp_path)

        ouvrir_etude(dossier)
        rapport = migrer_etude_v1_vers_v2(dossier)

        assert rapport == {"deja_v2": True}

        # Réouverture : toujours v2, données intactes.
        etude = ouvrir_etude(dossier)
        assert etude.etude.etude_format_version == 2
        assert etude.reformulation_de("r1", 1).versions[0].texte == (
            "Reformulation 1."
        )

    def test_reprise_apres_crash_simule(self, tmp_path):
        """
        Crash simulé : la migration a écrit le tier de r1
        (marqueur migration_v2) mais l'étude est encore en
        v1 (pas de réécriture). La reprise saute r1, migre
        r2, puis termine.
        """

        dossier = fabriquer_etude_v1(tmp_path)

        # Simule un crash après la migration de r1 seule.
        from services.migration_etude import _migrer_reunion
        from services.etude_io import _lire_json
        from models.etude import (
            Etude,
            RegistreFID,
            ReunionEtude,
            ParametresEtude,
        )

        donnees = _lire_json(dossier / "etude.json")
        etude_v1 = Etude.from_dict(donnees)

        registre = RegistreFID.from_dict(
            _lire_json(dossier / "blocs" / "journal-fid.json")
        )

        parametres = ParametresEtude.from_dict(
            _lire_json(
                dossier / "parametres" / "parametres.json"
            )
        )

        reunion_r1 = ReunionEtude.from_dict(
            "r1",
            _lire_json(dossier / "reunions" / "r1.json")
        )

        rapport = {"reunions": [], "reunions_introuvables": [], "anomalies": []}

        _migrer_reunion(
            dossier,
            "r1",
            reunion_r1,
            registre,
            parametres,
            [],
            rapport
        )

        # L'étude est TOUJOURS en v1 (crash avant réécriture).
        assert json.loads(
            (dossier / "etude.json").read_text(encoding="utf-8")
        )["etude_format_version"] == 1

        # Le tier de r1 porte le marqueur.
        tier_r1 = ouvrir_tier(tmp_path / "r1")
        assert tier_r1.reunion.migration_v2

        # Reprise : migration complète, r1 sautée.
        rapport2 = migrer_etude_v1_vers_v2(dossier)

        statuts = {
            r["nom"]: r["statut"] for r in rapport2["reunions"]
        }
        assert statuts["r1"] == "deja_migree"
        assert statuts["r2"] == "migree"

        etude = ouvrir_etude(dossier)
        assert etude.etude.etude_format_version == 2
        assert etude.reformulation_de("r1", 1) is not None
        assert etude.reformulation_de("r2", 3) is not None

    def test_controle_integrite_avant_suppression(self, tmp_path):
        """
        Contrôle d'intégrité AVANT toute suppression : après
        un crash ayant écrit le tier de r1, si la source v1
        a perdu un fichier entre-temps, le contrôle échoue
        et RIEN n'est supprimé (étude toujours v1, blocs\ et
        traitements\ présents).
        """

        from services.migration_etude import _migrer_reunion
        from services.etude_io import _lire_json
        from models.etude import (
            Etude,
            RegistreFID,
            ReunionEtude,
            ParametresEtude,
        )

        dossier = fabriquer_etude_v1(tmp_path)

        registre = RegistreFID.from_dict(
            _lire_json(dossier / "blocs" / "journal-fid.json")
        )
        parametres = ParametresEtude.from_dict(
            _lire_json(dossier / "parametres" / "parametres.json")
        )
        reunion_r1 = ReunionEtude.from_dict(
            "r1",
            _lire_json(dossier / "reunions" / "r1.json")
        )

        rapport = {"reunions": [], "reunions_introuvables": [], "anomalies": []}

        # Crash simulé : le tier de r1 est entièrement écrit...
        _migrer_reunion(
            dossier,
            "r1",
            reunion_r1,
            registre,
            parametres,
            [],
            rapport
        )

        # ... puis la source v1 perd un fichier.
        (dossier / "traitements" / "reformulation" / "2.json").unlink()

        # La reprise échoue au contrôle d'intégrité : aucune
        # suppression.
        with pytest.raises(MigrationError):
            migrer_etude_v1_vers_v2(dossier)

        assert (dossier / "blocs").exists()
        assert (dossier / "traitements").exists()
        assert json.loads(
            (dossier / "etude.json").read_text(encoding="utf-8")
        )["etude_format_version"] == 1


class TestRequalificationOuvrage:

    def test_provenances_avec_fusion_requalifiees(self, tmp_path):
        """
        Requalification en couples (réunion, FID) des
        provenances d'enspired'ouvrage.json : paragraphes,
        instantanés de fusion, historique de dé-fusion,
        instantané de génération — chaque référence doit se
        résoudre vers le tier de sa réunion.
        """

        from services.ouvrage_document import (
            charger_ouvrage,
            fusionner_pensees,
            defusionner_pensees,
        )

        dossier = fabriquer_etude_v1(tmp_path)

        etude = ouvrir_etude(dossier)

        # L'ouvrage est relu tel quel (provenances inchangées,
        # résolubles vers les tiers).
        doc = charger_ouvrage(dossier)
        assert doc is not None

        fusionne = doc.element("pf")
        assert len(fusionne.provenances) == 2
        assert {(p.reunion, p.fid) for p in fusionne.provenances} == {
            ("r1", 2),
            ("r2", 3),
        }

        # Chaque provenance se résout vers le tier de sa
        # réunion.
        for provenance in fusionne.provenances:
            tier = etude.tier_de(provenance.reunion)
            assert provenance.fid in tier.registre.entrees
            assert (
                tier.reformulations[provenance.fid]
                .versions[0]
                .texte
                == f"Reformulation {provenance.fid}."
            )

        # Instantanés de fusion : idem.
        for instantane in fusionne.fusion["elements"]:
            for provenance in instantane["provenances"]:
                tier = etude.tier_de(provenance["reunion"])
                assert provenance["fid"] in tier.registre.entrees

        # Dé-fusion après migration : l'historique conserve le
        # paragraphe fusionné, les originaux réapparaissent.
        defusionner_pensees(doc, "pf")
        assert len(doc.historique) == 1
        assert doc.historique[0]["paragraphe"]["id"] == "pf"

        # Les provenances de l'historique se résolvent aussi.
        for provenance in doc.historique[0]["paragraphe"][
            "provenances"
        ]:
            tier = etude.tier_de(provenance["reunion"])
            assert provenance["fid"] in tier.registre.entrees

    def test_anomalie_signalee_pas_corrigee(self, tmp_path):
        """
        Une provenance non résoluble est ANNOTÉE (jamais
        auto-corrigée).
        """

        dossier = fabriquer_etude_v1(tmp_path)

        # Ajoute une provenance vers un FID inexistant.
        ouvrage = json.loads(
            (dossier / "ouvrage.json").read_text(encoding="utf-8")
        )
        ouvrage["elements"][0]["provenances"].append(
            _provenance("r1", 99, 1)
        )
        (dossier / "ouvrage.json").write_text(
            json.dumps(ouvrage),
            encoding="utf-8"
        )

        from services.migration_etude import (
            migrer_etude_v1_vers_v2,
        )

        rapport = migrer_etude_v1_vers_v2(dossier)

        assert any("99" in a for a in rapport["anomalies"])

        # La provenance est toujours là, inchangée.
        etude = ouvrir_etude(dossier)
        from services.ouvrage_document import charger_ouvrage
        doc = charger_ouvrage(dossier)
        fids = [
            p.fid for p in doc.element("p1").provenances
        ]
        assert 99 in fids


class TestNonRegressionP19:

    def test_ouvrage_fonctionne_identique_apres_migration(
        self, tmp_path
    ):
        """
        Non-régression P19 : après migration, la page
        Ouvrage fonctionne à l'identique — génération,
        régénération, fusion, dé-fusion, signalements.
        """

        from services.ouvrage_document import (
            charger_ouvrage,
            defusionner_pensees,
            fusionner_pensees,
            generer_document,
            reformulees_depuis_generation,
            sauvegarder_ouvrage,
        )
        from services.etude_io import (
            ajouter_version_reformulation,
        )

        dossier = fabriquer_etude_v1(tmp_path)

        etude = ouvrir_etude(dossier)

        # L'ouvrage existant est relu et inchangé.
        doc = charger_ouvrage(dossier)
        assert [e.id for e in doc.elements] == ["p1", "pf"]

        # Régénération complète depuis les tiers migrés :
        # 3 paragraphes validés (r1: fids 1,2 ; r2: fid 3).
        doc2 = generer_document(etude)
        paragraphes = [
            e for e in doc2.elements if e.type == "paragraphe"
        ]
        assert len(paragraphes) == 3
        assert all(
            p.provenances[0].reunion in ("r1", "r2")
            for p in paragraphes
        )

        sauvegarder_ouvrage(doc2, dossier)

        # Relecture après réouverture.
        etude2 = ouvrir_etude(dossier)
        doc3 = charger_ouvrage(dossier)
        assert len(doc3.elements) == len(doc2.elements)

        # Fusion de pensées entre deux paragraphes migrés.
        fusionne = fusionner_pensees(
            doc3,
            paragraphes[0].id,
            paragraphes[1].id,
            "Pensée fusionnée."
        )
        assert len(fusionne.provenances) == 2

        # Dé-fusion réversible.
        defusionner_pensees(doc3, fusionne.id)
        assert len(doc3.historique) == 1

        # Signalement « re-reformulée depuis la génération ».
        ajouter_version_reformulation(
            etude2, "r1", 1, "Nouvelle version."
        )
        sauvegarder_etude(etude2)

        signaux = reformulees_depuis_generation(doc3, etude2)
        assert any(
            s["reunion"] == "r1" and s["fid"] == 1
            for s in signaux
        )


class TestMigrationTraitementsInternes:

    def test_ancienne_etude_interne_migree(self, tmp_path):
        """
        L'ancienne « étude interne » _traitements d'une
        réunion autonome (P20) est migrée vers le tier
        transcriptstudio\\ puis archivée (jamais supprimée).
        """

        projet = creer_projet_v1(tmp_path, "2026-10-13_Luc1b")

        # Construit une fausse étude interne v1 dans
        # _traitements, dont la réunion référence le projet.
        interne = projet / "_traitements"
        for sd in (
            "reunions",
            "blocs/decoupage",
            "traitements/reformulation",
            "synthese",
            "parametres",
        ):
            (interne / sd).mkdir(parents=True)

        nom = "2026-10-13_luc1b"

        (interne / "etude.json").write_text(
            json.dumps({
                "etude_format_version": 1,
                "titre": nom,
                "theme": "libre",
                "gabarit_titre_1": "",
                "ordre_reunions": [nom],
                "creation": "2026-11-01T10:00:00",
                "modification": "2026-11-01T10:00:00",
            }),
            encoding="utf-8"
        )

        (interne / "reunions" / f"{nom}.json").write_text(
            json.dumps({
                "reference": f"{nom}.json",
                "chemin_projet": "..",
                "chemin_absolu": str(projet.resolve()),
                "date": "2026-10-13",
                "numero": 1,
                "titre_1": "",
                "resume_valide": False,
            }),
            encoding="utf-8"
        )

        (interne / "blocs" / "journal-fid.json").write_text(
            json.dumps({
                "prochain_fid": 2,
                "fid_attribues": {
                    "1": {"reunion": nom, "cree": "2026-11-01T10:00:00", "actif": True, "fin": None},
                },
            }),
            encoding="utf-8"
        )

        (interne / "traitements" / "reformulation" / "1.json").write_text(
            json.dumps({
                "fid": 1,
                "versions": [
                    {
                        "numero": 1,
                        "texte": "Reformulation autonome.",
                        "horodatage": "2026-11-01T11:00:00",
                        "type": "passe",
                        "consigne": None,
                        "selection": None,
                        "stats": None,
                        "validation": None,
                        "contexte": [],
                    }
                ],
            }),
            encoding="utf-8"
        )

        (interne / "synthese" / "synthese.json").write_text(
            json.dumps({"versions": []}),
            encoding="utf-8"
        )

        (interne / "parametres" / "parametres.json").write_text(
            json.dumps(parametres_par_defaut().to_dict()),
            encoding="utf-8"
        )

        rapport = migrer_traitements_internes(projet)

        assert rapport is not None

        # Le tier du projet porte maintenant le travail.
        tier = ouvrir_tier(projet)
        assert tier is not None
        assert tier.reformulations[1].versions[0].texte == (
            "Reformulation autonome."
        )
        assert tier.reunion.migration_v2

        # L'ancien dossier est archivé, pas supprimé.
        assert not interne.exists()
        assert (projet / "_traitements_archive_v1").exists()

        # La réunion s'ouvre en autonome avec son travail.
        from services.etude_io import (
            ouvrir_reunion_autonome,
        )

        etude, nom2 = ouvrir_reunion_autonome(projet, creer=False)
        assert etude.reformulation_de(nom2, 1).versions[0].texte == (
            "Reformulation autonome."
        )
