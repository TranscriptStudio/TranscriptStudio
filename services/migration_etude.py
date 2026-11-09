# services/migration_etude.py
"""
Migration one-shot v1→v2 d'une étude (P18.7f, §11 du contrat
de stockage des réunions).

Déclenchée à l'ouverture d'une étude ``etude_format_version: 1`` :

1. **sauvegarde complète préalable** dans ``sauvegardes\\``
   (le dossier v1 original est recopié intégralement avant
   toute modification ; une sauvegarde existante d'une
   migration interrompue n'est jamais écrasée) ;
2. pour chaque réunion : découpage, **éclatement du registre
   FID** par réunion, aiguillage des reformulations par le
   registre, résumé + ``resume_valide``, paramètres
   initialisés, éclatement du journal — le tout écrit dans
   le **tier** de la réunion (``transcriptstudio\\`` du
   projet v1), avec un marqueur ``migration_v2`` par réunion
   (idempotence) ;
3. **requalification en couples (réunion, FID)** de toutes
   les références de blocs : provenances d'``ouvrage.json``
   (y compris instantanés de fusion et historique de
   dé-fusion), contexte de synthèse, fenêtre glissante
   (``contexte`` des versions) — vérification que chaque
   référence se résout vers le tier de sa réunion ;
4. **contrôle d'intégrité AVANT toute suppression** :
   nombre de fichiers, FID, versions comparés entre la
   source v1 et le tier avant de supprimer quoi que ce
   soit ;
5. réécriture de l'étude en v2 : etude.json (version 2),
   reunions/<nom>.json sans resume_valide,
   parametres/parametres.json (surcharges synthèse
   uniquement), journal_etude.json (entrées de niveau
   étude), puis suppression de blocs\\ et traitements\\.

Idempotente et **reprenable après crash** : une étude encore
en version 1 est re-migrée ; les réunions déjà migrées
(marqueur ``migration_v2`` dans le tier) sont sautées ;
la sauvegarde n'est pas recréée si elle existe déjà.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

from models.etude import (
    DecoupageReunion,
    Etude,
    ParametresEtude,
    RegistreFID,
    ResultatReformulation,
    ResultatResume,
    ReunionEtude,
    SyntheseEtude,
)
from services.etude_schema import (
    EtudeFormatError,
    valider_decoupage,
    valider_parametres,
    valider_registre_fid,
    valider_reformulation,
    valider_reunion,
    valider_resume,
)
from services.etude_io import (
    DOSSIER_BLOCS,
    DOSSIER_DECOUPAGE,
    DOSSIER_PARAMETRES,
    DOSSIER_REUNIONS,
    DOSSIER_SAUVEGARDES,
    DOSSIER_SYNTHESE,
    DOSSIER_TRAITEMENTS,
    DOSSIER_REFORMULATION,
    DOSSIER_RESUME,
    FICHIER_ETUDE,
    FICHIER_JOURNAL_ETUDE,
    FICHIER_PARAMETRES,
    FICHIER_REGISTRE_FID,
    FICHIER_SYNTHESE,
    _dossier_projet_v1,
    _ecrire_json,
    _est_projet_v1,
    _lire_json,
    horodatage_courant,
)
from services.traitements.journal import (
    FICHIER_JOURNAL,
    JournalEtude,
)
from services.tier_reunion import (
    DOSSIER_BLOCS as TIER_BLOCS,
    DOSSIER_PARAMETRES as TIER_PARAMETRES,
    DOSSIER_REFORMULATION as TIER_REFORMULATION,
    DOSSIER_TIER,
    DOSSIER_TRAITEMENTS as TIER_TRAITEMENTS,
    FICHIER_DECOUPAGE as TIER_DECOUPAGE,
    FICHIER_PARAMETRES as TIER_PARAMETRES_FICHIER,
    FICHIER_REGISTRE_FID as TIER_REGISTRE,
    FICHIER_REUNION as TIER_REUNION_FICHIER,
    FICHIER_RESUME as TIER_RESUME,
    TierReunion,
    creer_tier,
    ouvrir_tier,
    sauvegarder_tier,
)


DOSSIER_SAUVEGARDE_V1 = "v1_avant_migration_v2"
FICHIER_MARQUEUR = "migration_v2.json"


class MigrationError(Exception):
    """
    Échec de la migration v1→v2 : rien n'a été supprimé
    (le contrôle d'intégrité précède toute suppression).
    """

    pass


def _lire_json_ou_none(chemin: Path):
    if not chemin.is_file():
        return None

    with open(chemin, "r", encoding="utf-8") as f:
        return json.load(f)


def _copier_sauvegarde(dossier: Path) -> Path:
    """
    Sauvegarde complète du dossier étude v1 dans
    ``sauvegardes/v1_avant_migration_v2/``. Si elle existe
    déjà (migration interrompue), elle n'est PAS écrasée :
    elle contient l'état v1 original.
    """

    destination = (
        dossier / DOSSIER_SAUVEGARDES
        / DOSSIER_SAUVEGARDE_V1
    )

    if destination.exists():
        return destination

    def ignorer(_src, names):
        return [
            n for n in names if n == DOSSIER_SAUVEGARDES
        ]

    shutil.copytree(
        dossier,
        destination,
        ignore=ignorer
    )

    return destination


def _resoudre_projet(dossier: Path, reunion: ReunionEtude):
    """
    Résout le projet v1 d'une réunion (relatif puis
    absolu) — None si introuvable.
    """

    candidat = dossier / reunion.chemin_projet

    if _est_projet_v1(candidat):
        return _dossier_projet_v1(candidat.resolve())

    if reunion.chemin_absolu:
        absolu = Path(reunion.chemin_absolu)
        if _est_projet_v1(absolu):
            return _dossier_projet_v1(absolu.resolve())

    return None


def _requalifier_contexte_versions(
    reunion: str,
    resultat: ResultatReformulation
) -> int:
    """
    Requalifie le ``contexte`` de chaque version (fenêtre
    glissante) en couples (réunion, FID). Retourne le
    nombre d'entrées requalifiées.
    """

    n = 0

    for version in resultat.versions:

        nouveau = []

        for entree in version.contexte or []:

            if isinstance(entree, dict):
                nouveau.append(
                    {
                        "reunion": str(
                            entree.get("reunion", reunion)
                        ),
                        "fid": int(entree["fid"]),
                    }
                )
            else:
                nouveau.append(
                    {
                        "reunion": reunion,
                        "fid": int(entree),
                    }
                )
                n += 1

        version.contexte = nouveau

    return n


def _migrer_reunion(
    dossier: Path,
    nom: str,
    reunion: ReunionEtude,
    registre: RegistreFID,
    parametres: ParametresEtude,
    journal_entrees: list,
    rapport: dict
) -> dict:
    """
    Migre UNE réunion v1 vers son tier (dans le projet v1).

    Idempotent : si le tier porte déjà le marqueur
    ``migration_v2``, la réunion est sautée.
    """

    dossier_projet = _resoudre_projet(dossier, reunion)

    if dossier_projet is None:
        rapport["reunions_introuvables"].append(nom)
        return {"nom": nom, "statut": "introuvable"}

    tier = ouvrir_tier(dossier_projet)

    if (
        tier is not None
        and tier.reunion.migration_v2
    ):
        # Déjà migrée (reprise après crash).
        return {"nom": nom, "statut": "deja_migree"}

    entrees_reunion = {
        fid: entree
        for fid, entree in registre.entrees.items()
        if entree.reunion == nom
    }

    fids_reunion = sorted(entrees_reunion.keys())

    #
    # 1. Découpage.
    #

    decoupage = None
    chemin_decoupage = (
        dossier / DOSSIER_BLOCS
        / DOSSIER_DECOUPAGE / f"{nom}.json"
    )

    if chemin_decoupage.exists():
        donnees = _lire_json(chemin_decoupage)
        valider_decoupage(donnees, str(chemin_decoupage))
        decoupage = DecoupageReunion.from_dict(donnees)

    #
    # 2. Reformulations aiguillées par le registre.
    #

    reformulations = {}
    nb_versions = 0
    nb_contexte_requalifies = 0

    dossier_ref = (
        dossier / DOSSIER_TRAITEMENTS
        / DOSSIER_REFORMULATION
    )

    for fid in fids_reunion:

        chemin = dossier_ref / f"{fid}.json"

        if not chemin.exists():
            continue

        donnees = _lire_json(chemin)
        valider_reformulation(donnees, str(chemin))

        resultat = ResultatReformulation.from_dict(
            donnees
        )
        resultat.reunion = nom

        nb_contexte_requalifies += (
            _requalifier_contexte_versions(nom, resultat)
        )

        nb_versions += len(resultat.versions)
        reformulations[fid] = resultat

    #
    # 3. Résumé + resume_valide.
    #

    resume = None
    chemin_resume = (
        dossier / DOSSIER_TRAITEMENTS
        / DOSSIER_RESUME / f"{nom}.json"
    )

    if chemin_resume.exists():
        donnees = _lire_json(chemin_resume)
        valider_resume(donnees, str(chemin_resume))
        resume = ResultatResume.from_dict(donnees)

    #
    # 4. Écriture dans le tier (créé si absent).
    #

    if tier is None:
        tier = creer_tier(
            dossier_projet,
            nom=nom,
            parametres=ParametresEtude.from_dict(
                parametres.to_dict()
            ),
        )

    tier.reunion.migration_v2 = horodatage_courant()
    tier.reunion.resume_valide = bool(
        reunion.resume_valide
    )

    # etudes[] : cette étude (chemin relatif au projet).
    import os
    try:
        relatif = os.path.relpath(
            str(dossier.resolve()),
            str(dossier_projet.resolve())
        ).replace("\\", "/")
    except (ValueError, OSError):
        relatif = str(dossier.resolve()).replace("\\", "/")

    if relatif not in tier.reunion.etudes:
        tier.reunion.etudes.append(relatif)

    # Registre éclaté (mêmes numéros de FID).
    prochain = (
        max(fids_reunion, default=0) + 1
        if fids_reunion
        else registre.prochain_fid
    )
    tier.registre = RegistreFID(
        prochain_fid=max(prochain, 1),
        entrees=dict(entrees_reunion),
    )

    tier.decoupage = decoupage
    tier.reformulations = reformulations
    tier.resume = resume

    # Paramètres initialisés depuis ceux de l'étude v1
    # (c'étaient les valeurs actives).
    tier.parametres = ParametresEtude.from_dict(
        parametres.to_dict()
    )

    # Éclatement du journal : les entrées de la réunion
    # vont dans le journal du tier.
    entrees_tier = [
        e for e in journal_entrees
        if e.get("reunion") == nom
    ]

    tier.journal = JournalEtude(
        tier.dossier
        / TIER_TRAITEMENTS
        / FICHIER_JOURNAL
    )
    tier.journal.entrees = list(entrees_tier)
    tier.journal._ecrire()

    sauvegarder_tier(tier)

    return {
        "nom": nom,
        "statut": "migree",
        "fids": len(fids_reunion),
        "fichiers_reformulation": len(reformulations),
        "versions": nb_versions,
        "contextes_requalifies": nb_contexte_requalifies,
        "resume": resume is not None,
        "decoupage": decoupage is not None,
        "entrees_journal": len(entrees_tier),
    }


def _requalifier_ouvrage(
    dossier: Path,
    ordre_reunions: list,
    registres_par_reunion: dict,
    rapport: dict
) -> None:
    """
    Requalifie les références de blocs d'``ouvrage.json``
    en couples (réunion, FID) : provenances des paragraphes,
    instantanés de fusion (``fusion.elements``) et
    historique de dé-fusion — chaque référence doit se
    résoudre vers le tier de sa réunion. Toute référence
    non résoluble est ANNOTÉE dans le rapport, jamais
    auto-corrigée.
    """

    from services.ouvrage_document import (
        charger_ouvrage,
    )

    chemin = dossier / "ouvrage.json"

    if not chemin.is_file():
        return

    document = charger_ouvrage(dossier)

    if document is None:
        return

    def verifier(provenance, ou: str) -> None:

        nom = provenance.reunion
        fid = provenance.fid

        registre = registres_par_reunion.get(nom)

        if registre is None:
            rapport["anomalies"].append(
                f"ouvrage.json ({ou}) : réunion {nom!r} "
                "sans tier/résolution"
            )
            return

        entree = registre.entrees.get(fid)

        if entree is None or entree.reunion != nom:
            rapport["anomalies"].append(
                f"ouvrage.json ({ou}) : ({nom!r}, {fid}) "
                "ne se résout pas vers le tier de la "
                "réunion"
            )

    for element in document.elements:

        for provenance in element.provenances:
            verifier(provenance, f"élément {element.id}")

        fusion = element.fusion or {}

        for instantane in fusion.get("elements", []):
            try:
                from models.ouvrage import ElementOuvrage
                elem = ElementOuvrage.from_dict(instantane)
            except Exception:
                rapport["anomalies"].append(
                    f"ouvrage.json : instantané de fusion "
                    f"illisible (élément {element.id})"
                )
                continue

            for provenance in elem.provenances:
                verifier(
                    provenance,
                    f"fusion de {element.id}"
                )

    for entree_histo in document.historique:
        paragraphe = entree_histo.get("paragraphe")
        if not isinstance(paragraphe, dict):
            continue
        for provenance in paragraphe.get(
            "provenances", []
        ):
            try:
                from models.ouvrage import (
                    ProvenanceParagraphe,
                )
                p = ProvenanceParagraphe.from_dict(
                    provenance
                )
            except Exception:
                rapport["anomalies"].append(
                    "ouvrage.json : historique de "
                    "dé-fusion illisible"
                )
                continue
            verifier(p, "historique de dé-fusion")

    generation = document.generation or {}

    for nom, snapshot in (
        generation.get("reunions", {}).items()
    ):
        registre = registres_par_reunion.get(nom)
        for cle_fid in (snapshot.get("versions") or {}):
            if (
                registre is not None
                and int(cle_fid) not in registre.entrees
            ):
                rapport["anomalies"].append(
                    f"ouvrage.json (génération, réunion "
                    f"{nom!r}) : FID {cle_fid} non résolu"
                )


def _controle_integrite(
    dossier: Path,
    nom: str,
    registre: RegistreFID,
    tier: TierReunion,
    rapport: dict
) -> None:
    """
    Contrôle d'intégrité AVANT toute suppression :
    nombre de fichiers, FID et versions du tier vs source
    v1. Lève MigrationError en cas d'écart — rien n'est
    supprimé.
    """

    entrees = {
        fid: e
        for fid, e in registre.entrees.items()
        if e.reunion == nom
    }

    # FIDs : le registre du tier contient exactement les
    # FID de la réunion.
    if set(tier.registre.entrees.keys()) != set(
        entrees.keys()
    ):
        raise MigrationError(
            f"[{nom}] registre FID : écart entre la "
            f"source v1 ({len(entrees)} entrées) et le "
            f"tier ({len(tier.registre.entrees)} entrées) "
            "— aucune suppression effectuée."
        )

    # Fichiers de reformulation : un par FID ayant un
    # résultat en v1.
    dossier_ref = (
        dossier / DOSSIER_TRAITEMENTS
        / DOSSIER_REFORMULATION
    )
    attendus = {
        fid for fid in entrees
        if (dossier_ref / f"{fid}.json").exists()
    }

    if set(tier.reformulations.keys()) != attendus:
        raise MigrationError(
            f"[{nom}] reformulations : écart de fichiers "
            f"(attendus {sorted(attendus)}, tier "
            f"{sorted(tier.reformulations.keys())}) — "
            "aucune suppression effectuée."
        )

    # Versions : le nombre total de versions du tier ==
    # celui des fichiers source v1.
    total_v1 = 0
    for fid in attendus:
        donnees = _lire_json(dossier_ref / f"{fid}.json")
        total_v1 += len(donnees.get("versions", []))

    total_tier = sum(
        len(r.versions) for r in tier.reformulations.values()
    )

    if total_tier != total_v1:
        raise MigrationError(
            f"[{nom}] versions : {total_tier} dans le "
            f"tier vs {total_v1} en source v1 — aucune "
            "suppression effectuée."
        )

    # Découpage : mêmes blocs (mêmes FID).
    chemin_dec = (
        dossier / DOSSIER_BLOCS
        / DOSSIER_DECOUPAGE / f"{nom}.json"
    )
    if chemin_dec.exists():
        if tier.decoupage is None:
            raise MigrationError(
                f"[{nom}] découpage présent en v1 mais "
                "absent du tier."
            )
        fids_v1 = [
            b["fid"]
            for b in _lire_json(chemin_dec)["blocs"]
        ]
        fids_tier = [b.fid for b in tier.decoupage.blocs]
        if fids_v1 != fids_tier:
            raise MigrationError(
                f"[{nom}] découpage : FID différents entre "
                "v1 et le tier."
            )

    rapport["integrite"].append(
        {
            "nom": nom,
            "fids": len(entrees),
            "fichiers_reformulation": len(attendus),
            "versions": total_tier,
        }
    )


def migrer_etude_v1_vers_v2(dossier) -> dict:
    """
    Migration one-shot v1→v2 de l'étude (appelée à
    l'ouverture d'une étude version 1).

    Retourne le rapport de migration. Idempotente :
    une étude déjà en v2 retourne ``{"deja_v2": True}`` ;
    une migration interrompue est reprise (les réunions
    marquées ``migration_v2`` sont sautées, la sauvegarde
    existante est conservée).
    """

    dossier = Path(dossier)

    fichier_etude = dossier / FICHIER_ETUDE

    donnees = _lire_json(fichier_etude)

    if donnees.get("etude_format_version") == 2:
        return {"deja_v2": True}

    rapport = {
        "debut": horodatage_courant(),
        "reunions": [],
        "reunions_introuvables": [],
        "integrite": [],
        "anomalies": [],
        "requalifications": [],
    }

    #
    # 1. Sauvegarde complète préalable.
    #

    sauvegarde = _copier_sauvegarde(dossier)
    rapport["sauvegarde"] = str(
        sauvegarde.relative_to(dossier).as_posix()
    )

    #
    # 2. Lecture de l'état v1.
    #

    etude = Etude.from_dict(donnees)

    registre = RegistreFID()
    chemin_registre = (
        dossier / DOSSIER_BLOCS / FICHIER_REGISTRE_FID
    )
    if chemin_registre.exists():
        donnees_reg = _lire_json(chemin_registre)
        valider_registre_fid(
            donnees_reg, str(chemin_registre)
        )
        registre = RegistreFID.from_dict(donnees_reg)

    parametres = None
    chemin_param = (
        dossier / DOSSIER_PARAMETRES / FICHIER_PARAMETRES
    )
    if chemin_param.exists():
        donnees_p = _lire_json(chemin_param)
        valider_parametres(donnees_p, str(chemin_param))
        parametres = ParametresEtude.from_dict(donnees_p)
    else:
        from services.etude_io import parametres_par_defaut
        parametres = parametres_par_defaut()

    journal_entrees = []
    chemin_journal = (
        dossier / DOSSIER_TRAITEMENTS / FICHIER_JOURNAL
    )
    if chemin_journal.exists():
        journal_entrees = _lire_json(chemin_journal).get(
            "entrees", []
        )

    #
    # 3. Migration réunion par réunion (dans les tiers).
    #

    registres_par_reunion = {}

    for nom in etude.ordre_reunions:

        chemin_reunion = (
            dossier / DOSSIER_REUNIONS / f"{nom}.json"
        )
        donnees_r = _lire_json(chemin_reunion)
        valider_reunion(donnees_r, str(chemin_reunion))
        reunion = ReunionEtude.from_dict(nom, donnees_r)

        sous = _migrer_reunion(
            dossier,
            nom,
            reunion,
            registre,
            parametres,
            journal_entrees,
            rapport
        )
        rapport["reunions"].append(sous)

        dossier_projet = _resoudre_projet(dossier, reunion)
        if dossier_projet is not None:
            tier = ouvrir_tier(dossier_projet)
            if tier is not None:
                registres_par_reunion[nom] = tier.registre

    #
    # 4. Requalification des références de blocs
    #    (ouvrage.json : provenances, instantanés de
    #    fusion, historique de dé-fusion, génération).
    #

    _requalifier_ouvrage(
        dossier,
        etude.ordre_reunions,
        registres_par_reunion,
        rapport
    )

    #
    # 5. Contrôle d'intégrité AVANT toute suppression.
    #

    for nom in etude.ordre_reunions:

        dossier_projet = None
        chemin_reunion = (
            dossier / DOSSIER_REUNIONS / f"{nom}.json"
        )
        donnees_r = _lire_json(chemin_reunion)
        reunion = ReunionEtude.from_dict(nom, donnees_r)
        dossier_projet = _resoudre_projet(dossier, reunion)

        if dossier_projet is None:
            continue

        tier = ouvrir_tier(dossier_projet)

        if tier is None or not tier.reunion.migration_v2:
            continue

        _controle_integrite(
            dossier,
            nom,
            registre,
            tier,
            rapport
        )

    #
    # 6. Réécriture de l'étude en v2 (seulement si
    #    l'intégrité est OK partout).
    #

    etude.etude_format_version = 2
    etude.modification = horodatage_courant()
    _ecrire_json(fichier_etude, etude.to_dict())

    for nom in etude.ordre_reunions:

        chemin_reunion = (
            dossier / DOSSIER_REUNIONS / f"{nom}.json"
        )
        if not chemin_reunion.exists():
            continue

        donnees_r = _lire_json(chemin_reunion)
        donnees_r.pop("resume_valide", None)
        _ecrire_json(chemin_reunion, donnees_r)

    # Paramètres : surcharges synthèse uniquement.
    _ecrire_json(
        dossier / DOSSIER_PARAMETRES / FICHIER_PARAMETRES,
        {"synthese": dict(parametres.synthese)},
    )

    # Journal d'étude : entrées de niveau étude (hors
    # celles des réunions migrées vers les tiers).
    reunions_noms = set(etude.ordre_reunions)
    entrees_etude = [
        e for e in journal_entrees
        if e.get("reunion") not in reunions_noms
    ]
    journal_etude = JournalEtude(
        dossier / FICHIER_JOURNAL_ETUDE
    )
    journal_etude.entrees = entrees_etude
    journal_etude._ecrire()

    #
    # 7. Suppression des dossiers v1 de l'étude —
    #    APRÈS le contrôle d'intégrité.
    #

    for sous_dossier in (
        DOSSIER_BLOCS,
        DOSSIER_TRAITEMENTS,
    ):
        cible = dossier / sous_dossier
        if cible.exists():
            shutil.rmtree(cible)
            rapport.setdefault("suppressions", []).append(
                sous_dossier
            )

    rapport["fin"] = horodatage_courant()

    _ecrire_json(
        dossier / DOSSIER_SAUVEGARDES / FICHIER_MARQUEUR,
        rapport,
    )

    return rapport


def migrer_traitements_internes(dossier_projet) -> dict:
    """
    Migre l'ancienne « étude interne » d'une réunion
    autonome (``_traitements/`` dans le projet v1, P20)
    vers le tier ``transcriptstudio\\`` du même projet :
    la migration v1→v2 de l'étude interne éclate les
    traitements dans le tier du projet parent (la réunion
    de l'étude interne référence le projet lui-même),
    puis le dossier ``_traitements`` est archivé (renommé,
    jamais supprimé).

    Retourne le rapport, ou None si rien à migrer.
    """

    dossier_projet = _dossier_projet_v1(Path(dossier_projet))

    interne = dossier_projet / "_traitements"

    if not (interne / FICHIER_ETUDE).is_file():
        return None

    donnees = _lire_json(interne / FICHIER_ETUDE)

    if donnees.get("etude_format_version") == 2:
        return {"deja_v2": True}

    rapport = migrer_etude_v1_vers_v2(interne)

    archive = dossier_projet / "_traitements_archive_v1"

    if not archive.exists():
        interne.rename(archive)
        rapport["archive_interne"] = archive.name

    return rapport
