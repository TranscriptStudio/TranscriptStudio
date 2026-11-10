# services/ouvrage_document.py
"""
Document ouvrage d'une étude (P19.1-P19.3,
feuille de route v2.1 §P19) :

- **génération** : initialise le document à partir
  des reformulations VALIDÉES de l'étude, réunion
  par réunion (ordre de l'étude), chaque réunion
  dans son **ordre d'ouvrage** — chaque paragraphe
  porte sa provenance (FID, réunion, date,
  version) ;
- **régénération complète** : écrase le document
  existant (l'avertissement relève de l'UI) ;
  JAMAIS de mise à jour automatique incrémentale ;
- **vie propre** : l'ouvrage diverge des textes
  validés par réunion — au mieux un signalement
  « réunion re-reformulée depuis la génération »
  (``reformulees_depuis_generation``), calculé
  en comparant l'instantané de génération aux
  versions courantes ;
- **persistance** : ``ouvrage.json`` dans le
  dossier de l'étude (fichier additionnel au
  contrat format étude — le dossier reste
  autonome et portable).
"""

import json
from pathlib import Path

from models.ouvrage import (
    DocumentOuvrage,
    ElementOuvrage,
    OuvrageFormatError,
    ProvenanceParagraphe,
    SOURCE_FUSION,
    SOURCE_GENERATION,
    TYPE_PARAGRAPHE,
)
from services.timecodes import horodatage_iso

NOM_FICHIER_OUVRAGE = "ouvrage.json"


class FusionPenseesError(ValueError):
    """
    Opération de fusion de pensées impossible
    (P19.4) : paragraphe introuvable, pas un
    paragraphe, texte fusionné vide, ou dé-fusion
    demandée sur un paragraphe non fusionné.
    """


def chemin_ouvrage(dossier) -> Path:
    """
    Chemin du document ouvrage d'une étude.
    """

    return Path(dossier) / NOM_FICHIER_OUVRAGE


def charger_ouvrage(dossier):
    """
    Charge le document ouvrage d'une étude —
    None s'il n'existe pas encore (l'ouvrage
    n'est généré qu'à la demande).

    Lève OuvrageFormatError si le fichier existe
    mais n'est pas lisible comme un document
    ouvrage.
    """

    chemin = chemin_ouvrage(dossier)

    if not chemin.is_file():
        return None

    try:

        with open(
            chemin,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

    except (OSError, ValueError) as e:

        raise OuvrageFormatError(
            f"ouvrage.json illisible : {e}"
        )

    return DocumentOuvrage.from_dict(data)


def sauvegarder_ouvrage(
    document: DocumentOuvrage,
    dossier
) -> Path:
    """
    Écrit le document ouvrage dans le dossier de
    l'étude. Retourne le chemin écrit.
    """

    chemin = chemin_ouvrage(dossier)

    with open(
        chemin,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            document.to_dict(),
            f,
            ensure_ascii=False,
            indent=2
        )

        f.write("\n")

    return chemin


def _version_validee(resultat):
    """
    Dernière version VALIDÉE d'un résultat de
    reformulation (None sinon) — même règle que
    l'export ouvrage (P18.3).
    """

    if not resultat or not resultat.versions:
        return None

    for version in reversed(resultat.versions):

        if (
            version.validation
            and version.validation.statut
            == "valide"
        ):
            return version

    return None


def generer_document(
    etude_ouverte
) -> DocumentOuvrage:
    """
    Génère (ou régénère — l'opération ÉCRASE tout)
    le document ouvrage de l'étude :

    - titre = titre de l'étude (défaut : thème,
      « Ouvrage ») ;
    - pour chaque réunion de l'étude dans l'ordre
      de l'étude : les reformulations VALIDÉES de
      ses blocs, dans l'**ordre d'ouvrage** — un
      paragraphe par bloc, avec provenance complète
      (FID, réunion, numéro, date, version
      utilisée) ;
    - une réunion sans découpage ou sans texte
      validé ne produit AUCUN paragraphe : elle
      figure dans l'instantané de génération avec
      zéro paragraphe (la page Ouvrage l'affiche
      comme non placée).

    Aucune structure de chapitre n'est créée :
    les titres (chapitres) sont ajoutés
    MANUELLEMENT (maquette validée 2026-10-29) —
    tout est donc en « Réserves » à la génération.
    """

    from services.decoupage import (
        DecoupageError,
        ordre_ouvrage_effectif,
    )

    etude = etude_ouverte.etude

    document = DocumentOuvrage(
        titre=(
            etude.titre
            or etude.theme
            or "Ouvrage"
        )
    )

    reunions_snapshot = {}

    for nom_reunion in etude.ordre_reunions:

        reunion = (
            etude_ouverte.reunions.get(nom_reunion)
        )

        numero = (
            reunion.numero if reunion else 0
        )

        date_reunion = (
            reunion.date if reunion else ""
        )

        paragraphes_reunion = 0
        versions_snapshot = {}

        try:
            ordre = ordre_ouvrage_effectif(
                etude_ouverte,
                nom_reunion
            )
        except DecoupageError:
            ordre = []

        # Locuteurs du bloc (P19.4 : la provenance
        # porte FIDs, LOCUTEURS et réunions) —
        # chaîne vide si le découpage est absent.
        decoupage = (
            etude_ouverte.decoupages.get(
                nom_reunion
            )
        )

        locuteurs_par_fid = {
            bloc.fid: ", ".join(
                bloc.locuteurs
            )
            for bloc in (
                decoupage.blocs
                if decoupage is not None
                else []
            )
        }

        for fid in ordre:

            version = _version_validee(
                etude_ouverte
                .reformulation_de(
                    nom_reunion,
                    fid
                )
            )

            if version is None:
                continue

            provenance = ProvenanceParagraphe(
                reunion=nom_reunion,
                fid=fid,
                numero_reunion=numero,
                date_reunion=date_reunion,
                locuteurs=(
                    locuteurs_par_fid.get(
                        fid,
                        ""
                    )
                ),
                numero_version=version.numero,
                horodatage_version=(
                    version.horodatage
                ),
            )

            document.elements.append(
                ElementOuvrage(
                    id=document.nouvel_id("p"),
                    type=TYPE_PARAGRAPHE,
                    texte=version.texte,
                    provenances=[provenance],
                    source=SOURCE_GENERATION,
                )
            )

            paragraphes_reunion += 1

            versions_snapshot[str(fid)] = {
                "numero": version.numero,
                "horodatage": (
                    version.horodatage
                ),
            }

        reunions_snapshot[nom_reunion] = {
            "numero": numero,
            "date": date_reunion,
            "paragraphes": paragraphes_reunion,
            "versions": versions_snapshot,
        }

    document.generation = {
        "horodatage": horodatage_iso(),
        "reunions": reunions_snapshot,
    }

    return document


def reformulees_depuis_generation(
    document: DocumentOuvrage,
    etude_ouverte
) -> list:
    """
    Signalement « réunion re-reformulée depuis la
    génération » (le document dérivé n'est JAMAIS
    mis à jour automatiquement — au mieux
    signalement) : pour chaque bloc capturé dans
    l'instantané de génération, une version
    PLUS RÉCENTE que la version utilisée existe
    (passe, relance ciblée ou édition manuelle —
    validée ou non : toute nouvelle version
    signifie que le texte source a bougé).

    Retour : liste
    ``{"reunion", "fid", "version_generation",
    "version_courante"}``, triée par réunion
    puis FID.
    """

    if not document.generation:
        return []

    reunions = (
        document.generation.get("reunions")
        or {}
    )

    signalements = []

    for nom_reunion, snapshot in (
        reunions.items()
    ):

        versions = (
            snapshot.get("versions") or {}
        )

        for cle_fid, version_snapshot in (
            versions.items()
        ):

            fid = int(cle_fid)

            resultat = (
                etude_ouverte
                .reformulation_de(
                    nom_reunion,
                    fid
                )
            )

            if not resultat or (
                not resultat.versions
            ):
                continue

            numero_courant = max(
                version.numero
                for version in (
                    resultat.versions
                )
            )

            if (
                numero_courant
                > version_snapshot["numero"]
            ):

                signalements.append({
                    "reunion": nom_reunion,
                    "fid": fid,
                    "version_generation": (
                        version_snapshot["numero"]
                    ),
                    "version_courante": (
                        numero_courant
                    ),
                })

    return signalements


def reunions_non_placees(
    document: DocumentOuvrage,
    etude_ouverte
) -> list:
    """
    Réunions de l'étude dont AUCUN paragraphe n'est
    placé sous un chapitre (ou qui n'ont produit
    aucun paragraphe) — l'arborescence de la page
    Ouvrage les montre en « Réserves ».
    """

    etude = etude_ouverte.etude

    ids_reserves = {
        p.id
        for p in document.paragraphes_reserves()
    }

    placees = set()

    for p in document.paragraphes():

        if p.id in ids_reserves:
            continue

        for provenance in p.provenances:
            placees.add(provenance.reunion)

    return [
        nom
        for nom in etude.ordre_reunions
        if nom not in placees
    ]


#
# P20.1 — mobilité inter-blocs des paragraphes :
# déplacement (à travers blocs et sections),
# suppression, et contrôle des renvois orphelins
# après déplacement (détection locale).
#


def deplacer_element(
    document: DocumentOuvrage,
    id_element: str,
    nouvelle_position: int
) -> int:
    """
    **Déplacement inter-blocs** (P20.1) : déplace un
    élément (paragraphe le plus souvent) à la
    position demandée dans la liste PLATTE du
    document — à travers blocs et sections, la
    provenance du paragraphe est conservée (l'élément
    entier est déplacé).

    Retour : la nouvelle position effective.
    """

    element = document.element(id_element)

    if element is None:
        raise FusionPenseesError(
            "Élément introuvable (il a peut-être "
            "été supprimé)."
        )

    ancienne_position = document.elements.index(
        element
    )

    document.elements.pop(ancienne_position)

    nouvelle_position = max(
        0,
        min(
            int(nouvelle_position),
            len(document.elements)
        )
    )

    document.elements.insert(
        nouvelle_position,
        element
    )

    return nouvelle_position


def supprimer_element(
    document: DocumentOuvrage,
    id_element: str
) -> ElementOuvrage:
    """
    **Suppression** (P20.1) : retire un élément du
    document (la suppression porte sur le document
    dérivé — jamais sur les textes validés des
    réunions, §8bis). Retour : l'élément retiré.
    """

    element = document.element(id_element)

    if element is None:
        raise FusionPenseesError(
            "Élément introuvable (il a peut-être "
            "été supprimé)."
        )

    document.elements.remove(element)

    return element


#
# Renvois orphelins (P20.1) : expressions de renvoi
# (« comme on l'a dit », « précédemment »…) détectées
# LOCALEMENT (sans LLM) dans un paragraphe déplacé.
#

import re as _re

_MOTIFS_RENVOI = [
    r"comme (?:on|nous) l['’]a (?:dit|vu)",
    r"comme (?:nous )?l['’]avons (?:dit|vu)",
    r"comme (?:cela|ceci) (?:a|à) été (?:dit|vu)",
    r"(?:dit|vu) (?:plus|précédemment|plus haut)",
    r"précédemment",
    r"plus haut",
    r"déjà (?:dit|vu|mentionné|souligné)",
    r"on l['’]a (?:dit|vu)",
    r"nous (?:l['’])?avons (?:déjà )?(?:dit|vu)",
    r"rappelons(?:[- ]le)?",
    r"comme on l['’]a (?:déjà )?(?:dit|vu)",
]

_MOTIF_RENVOI_COMPILE = _re.compile(
    "|".join(f"(?:{_m})" for _m in _MOTIFS_RENVOI),
    _re.IGNORECASE,
)


def _normaliser_renvoi(texte: str) -> str:
    """
    Normalisation pour la détection des renvois :
    minuscules, apostrophes ramenées, ponctuation
    retirée, espaces resserrés.
    """

    if not texte:
        return ""

    nettoye = (
        texte.lower()
        .replace("’", "'")
    )

    nettoye = _re.sub(
        r"[^\w\s']",
        " ",
        nettoye,
        flags=_re.UNICODE,
    )

    return _re.sub(r"\s+", " ", nettoye).strip()


def detecter_renvois(texte: str) -> list:
    """
    Expressions de renvoi trouvées dans un texte
    (détection locale, sans LLM) — liste des
    occurrences normalisées.
    """

    normalise = _normaliser_renvoi(texte)

    if not normalise:
        return []

    return _MOTIF_RENVOI_COMPILE.findall(normalise)


def controler_renvois_apres_deplacement(
    document: DocumentOuvrage,
    id_element: str,
    ancienne_position: int,
    precedent_avant_id: str = None
) -> list:
    """
    **Contrôle des renvois orphelins** (P20.1) après
    déplacement d'un paragraphe : si le paragraphe
    contient des renvois (« comme on l'a dit »…) et
    que l'élément qui le PRÉCÉDAIT avant le
    déplacement (``precedent_avant_id``, capturé
    AVANT le déplacement par l'appelant) ne le
    précède PLUS, le renvoi peut être orphelin —
    signalement local (liste de ``{"id", "renvois",
    "precedent_avant", "precedent_apres"}``),
    jamais de modification.
    """

    element = document.element(id_element)

    if element is None:
        return []

    if element.type != TYPE_PARAGRAPHE:
        return []

    renvois = detecter_renvois(element.texte)

    if not renvois:
        return []

    nouvelle_position = document.elements.index(
        element
    )

    if nouvelle_position == ancienne_position:
        return []

    precedent_apres = (
        document.elements[nouvelle_position - 1]
        if nouvelle_position > 0
        else None
    )

    precedent_apres_id = (
        precedent_apres.id
        if precedent_apres is not None
        else None
    )

    if precedent_avant_id == precedent_apres_id:
        return []

    return [{
        "id": element.id,
        "renvois": renvois,
        "precedent_avant": precedent_avant_id,
        "precedent_apres": precedent_apres_id,
    }]


def fusionner_pensees(
    document: DocumentOuvrage,
    id_1: str,
    id_2: str,
    texte_fusionne: str,
    stats: dict = None
) -> ElementOuvrage:
    """
    **Fusion de pensées** (P19.4, feuille de
    route v2.1 §P19) : deux paragraphes dont la
    pensée est très similaire (même locuteur ou
    locuteurs différents) deviennent UN SEUL
    paragraphe portant les **provenances
    multiples** (FIDs, locuteurs, réunions).

    Opération de COMPOSITION DE L'OUVRAGE
    uniquement — jamais de la page Reformulation
    (qui reste 1 bloc = 1 reformulation, sans
    exception d'attribution) : elle ne touche que
    le document dérivé, jamais les textes validés
    ni le registre de l'étude.

    - le paragraphe fusionné prend la place du
      PREMIER des deux dans l'ordre du document ;
    - ses provenances sont celles des deux
      paragraphes, dans l'ordre du document ;
    - l'instantané des deux paragraphes d'origine
      (texte, provenances, source) est conservé
      dans l'élément pour la **dé-fusion** ;
    - ``stats`` (facultatif, P19.4-bis) : traçabilité
      de l'ASSISTANCE LLM éventuelle — texte du
      prompt EFFECTIF (``prompt``) et hash court
      (``prompt_hash``), plus modèle/coût si fournis ;
      consignée dans l'instantané de fusion, donc
      dans ouvrage.json.

    Retour : le paragraphe fusionné (déjà en place
    dans le document).
    """

    if id_1 == id_2:
        raise FusionPenseesError(
            "Un paragraphe ne peut pas être "
            "fusionné avec lui-même."
        )

    if (
        not isinstance(texte_fusionne, str)
        or not texte_fusionne.strip()
    ):
        raise FusionPenseesError(
            "Le texte du paragraphe fusionné est vide."
        )

    element_1 = document.element(id_1)
    element_2 = document.element(id_2)

    for element in (element_1, element_2):

        if element is None:
            raise FusionPenseesError(
                "Paragraphe introuvable (il a peut-être "
                "été supprimé)."
            )

        if element.type != TYPE_PARAGRAPHE:
            raise FusionPenseesError(
                "Seuls deux PARAGRAPHES peuvent être "
                "fusionnés (pas un titre ni un "
                "séparateur)."
            )

    # Ordre du document : le premier des deux
    # donne la position du paragraphe fusionné
    # et l'ordre des provenances.
    if (
        document.elements.index(element_1)
        > document.elements.index(element_2)
    ):
        element_1, element_2 = (
            element_2,
            element_1
        )

    fusionne = ElementOuvrage(
        id=document.nouvel_id("pf"),
        type=TYPE_PARAGRAPHE,
        texte=texte_fusionne,
        provenances=(
            list(element_1.provenances)
            + list(element_2.provenances)
        ),
        source=SOURCE_FUSION,
        fusion={
            "elements": [
                element_1.to_dict(),
                element_2.to_dict(),
            ]
        },
    )

    if stats:
        fusionne.fusion["stats"] = dict(stats)

    position = document.elements.index(
        element_1
    )

    document.elements[position] = fusionne
    document.elements.remove(element_2)

    return fusionne


def defusionner_pensees(
    document: DocumentOuvrage,
    id_fusionne: str
) -> ElementOuvrage:
    """
    **Dé-fusion** (P19.4) : le paragraphe fusionné
    disparaît du corps du document et chacun des
    deux paragraphes d'origine REPREND son texte
    (et sa provenance), à la place du fusionné,
    dans l'ordre de la fusion.

    Le paragraphe fusionné est CONSERVÉ dans
    l'historique de l'ouvrage (son texte n'est
    pas perdu : il reste consultable et peut
    relancer une fusion manuelle).

    Retour : le paragraphe fusionné retiré (avec
    son instantané complet).
    """

    fusionne = document.element(id_fusionne)

    if fusionne is None:
        raise FusionPenseesError(
            "Paragraphe introuvable (il a peut-être "
            "été supprimé)."
        )

    if fusionne.type != TYPE_PARAGRAPHE:
        raise FusionPenseesError(
            "Seul un PARAGRAPHE issu d'une fusion "
            "peut être dé-fusionné."
        )

    if (
        fusionne.source != SOURCE_FUSION
        or not fusionne.fusion
    ):
        raise FusionPenseesError(
            "Ce paragraphe n'est pas issu d'une "
            "fusion de pensées."
        )

    instantanes = (
        fusionne.fusion.get("elements")
    )

    if (
        not isinstance(instantanes, list)
        or len(instantanes) != 2
    ):
        raise OuvrageFormatError(
            "ouvrage.json : historique de fusion "
            "illisible (deux paragraphes attendus)"
        )

    originaux = [
        ElementOuvrage.from_dict(instantane)
        for instantane in instantanes
    ]

    ids_vivants = {
        e.id
        for e in document.elements
        if e is not fusionne
    }

    for original in originaux:

        if original.id in ids_vivants:
            raise FusionPenseesError(
                f"Conflit d'identifiant « {original.id} » "
                "à la dé-fusion : le document a été "
                "régénéré depuis la fusion."
            )

    position = document.elements.index(
        fusionne
    )

    document.elements[
        position:position + 1
    ] = originaux

    document.historique.append({
        "horodatage": horodatage_iso(),
        "paragraphe": fusionne.to_dict(),
    })

    return fusionne
