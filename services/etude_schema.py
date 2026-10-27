# services/etude_schema.py
"""
Validation de schéma du format étude v2 (P14.1).

Chaque fichier JSON d'une étude est validé avant d'être
transformé en objet : clés requises, types, énumérations du
contrat (CONTRAT_FORMAT_ETUDE_V2.md §3 à §10).

Une erreur de schéma lève ``EtudeFormatError`` avec un
message indiquant le fichier et le problème exact.
"""

from models.etude import (
    DECLENCHEURS_SYNTHESE,
    SOURCES_RESUME,
    THEMES_ETUDE,
    TYPES_VERSION_REFORMULATION,
)
from services.timecodes import lire_timecode


class EtudeFormatError(Exception):
    """
    Erreur de format d'une étude : schéma invalide
    ou fichier illisible.
    """

    def __init__(self, fichier: str, message: str):

        self.fichier = fichier
        self.message = message

        super().__init__(
            f"[{fichier}] {message}"
        )


def _erreur(fichier: str, message: str):
    """
    Lève une EtudeFormatError formatée.
    """

    raise EtudeFormatError(fichier, message)


def _exiger_cle(
    data: dict,
    cle: str,
    fichier: str,
    types=None
):
    """
    Exige la présence d'une clé et son type.

    Retourne la valeur.
    """

    if cle not in data:
        _erreur(
            fichier,
            f"clé requise absente : {cle}"
        )

    valeur = data[cle]

    if types is not None:

        if not isinstance(valeur, types):

            _erreur(
                fichier,
                (
                    f"clé {cle} : type invalide, "
                    f"attendu {types}, reçu "
                    f"{type(valeur).__name__}"
                )
            )

    return valeur


def _valider_enum(
    valeur,
    valeurs_valides,
    cle: str,
    fichier: str
):
    """
    Exige qu'une valeur appartienne à une énumération
    du contrat.
    """

    if valeur not in valeurs_valides:
        _erreur(
            fichier,
            (
                f"clé {cle} : valeur {valeur!r} "
                f"invalide (attendu : "
                f"{', '.join(valeurs_valides)})"
            )
        )


def _valider_horodatage(
    valeur,
    cle: str,
    fichier: str
):
    """
    Valide un horodatage ISO minimal ``AAAA-MM-JJTHH:MM:SS``.
    """

    if not isinstance(valeur, str):
        _erreur(
            fichier,
            f"clé {cle} : horodatage attendu (texte)"
        )

    if len(valeur) < 19 or valeur[10] != "T":
        _erreur(
            fichier,
            (
                f"clé {cle} : horodatage invalide "
                f"({valeur!r}), format attendu "
                "AAAA-MM-JJTHH:MM:SS"
            )
        )


def _valider_date(valeur, cle: str, fichier: str):
    """
    Valide une date au format ``AAAA-MM-JJ`` (contrat §2).
    """

    if not isinstance(valeur, str):
        _erreur(
            fichier,
            f"clé {cle} : date attendue (texte)"
        )

    if len(valeur) != 10 or valeur[4] != "-" or valeur[7] != "-":
        _erreur(
            fichier,
            (
                f"clé {cle} : date invalide "
                f"({valeur!r}), format attendu "
                "AAAA-MM-JJ"
            )
        )


def valider_etude(data: dict, fichier: str = "etude.json") -> None:
    """
    Valide ``etude.json`` (contrat §3).
    """

    if not isinstance(data, dict):
        _erreur(fichier, "objet JSON attendu")

    version = _exiger_cle(
        data,
        "etude_format_version",
        fichier,
        int
    )

    if version != 1:
        _erreur(
            fichier,
            (
                "etude_format_version non supporté : "
                f"{version}"
            )
        )

    _exiger_cle(data, "titre", fichier, str)
    _exiger_cle(data, "creation", fichier, str)
    _exiger_cle(data, "modification", fichier, str)

    _valider_horodatage(
        data["creation"],
        "creation",
        fichier
    )

    _valider_horodatage(
        data["modification"],
        "modification",
        fichier
    )

    theme = _exiger_cle(data, "theme", fichier, str)
    _valider_enum(theme, THEMES_ETUDE, "theme", fichier)

    _exiger_cle(
        data,
        "gabarit_titre_1",
        fichier,
        str
    )

    ordre = _exiger_cle(
        data,
        "ordre_reunions",
        fichier,
        list
    )

    for nom in ordre:
        if not isinstance(nom, str) or not nom:
            _erreur(
                fichier,
                (
                    "ordre_reunions : noms de "
                    "réunions (texte) attendus"
                )
            )

    if len(set(ordre)) != len(ordre):
        _erreur(
            fichier,
            "ordre_reunions : doublons interdits"
        )


def valider_reunion(
    data: dict,
    fichier: str = "reunions/<nom>.json"
) -> None:
    """
    Valide une référence de réunion (contrat §4).
    """

    if not isinstance(data, dict):
        _erreur(fichier, "objet JSON attendu")

    _exiger_cle(data, "reference", fichier, str)
    _exiger_cle(data, "chemin_projet", fichier, str)

    if not data["chemin_projet"]:
        _erreur(
            fichier,
            "chemin_projet : chemin requis"
        )

    if "chemin_absolu" in data and data["chemin_absolu"] is not None:
        _exiger_cle(
            data,
            "chemin_absolu",
            fichier,
            str
        )

    _exiger_cle(data, "date", fichier, str)
    _valider_date(data["date"], "date", fichier)

    _exiger_cle(data, "numero", fichier, int)
    _exiger_cle(data, "titre_1", fichier, str)

    _exiger_cle(
        data,
        "resume_valide",
        fichier,
        bool
    )


def valider_registre_fid(
    data: dict,
    fichier: str = "journal-fid.json"
) -> None:
    """
    Valide le registre FID de l'étude (contrat §5).
    """

    if not isinstance(data, dict):
        _erreur(fichier, "objet JSON attendu")

    prochain = _exiger_cle(
        data,
        "prochain_fid",
        fichier,
        int
    )

    if prochain < 1:
        _erreur(
            fichier,
            "prochain_fid : entier >= 1 attendu"
        )

    attribues = _exiger_cle(
        data,
        "fid_attribues",
        fichier,
        dict
    )

    for fid, entree in attribues.items():

        try:
            fid_entier = int(fid)
        except (TypeError, ValueError):
            _erreur(
                fichier,
                f"fid_attribues : clé {fid!r} "
                "non entière"
            )

        if not isinstance(entree, dict):
            _erreur(
                fichier,
                f"fid_attribues[{fid}] : "
                "objet attendu"
            )

        _exiger_cle(entree, "reunion", fichier, str)
        _exiger_cle(entree, "cree", fichier, str)
        _exiger_cle(entree, "actif", fichier, bool)

        _valider_horodatage(
            entree["cree"],
            f"fid_attribues[{fid}].cree",
            fichier
        )

        if "fin" in entree and entree["fin"] is not None:
            _valider_horodatage(
                entree["fin"],
                f"fid_attribues[{fid}].fin",
                fichier
            )

        if fid_entier >= prochain:
            _erreur(
                fichier,
                (
                    f"fid_attribues[{fid}] : FID "
                    "attribué >= prochain_fid "
                    f"({prochain}) — registre incohérent"
                )
            )


def valider_decoupage(
    data: dict,
    fichier: str = "decoupage/<reunion>.json"
) -> None:
    """
    Valide un découpage de réunion (contrat §6).
    """

    if not isinstance(data, dict):
        _erreur(fichier, "objet JSON attendu")

    _exiger_cle(data, "reunion", fichier, str)

    blocs = _exiger_cle(data, "blocs", fichier, list)

    fids_vus = set()

    for index, bloc in enumerate(blocs):

        prefixe = f"blocs[{index}]"

        if not isinstance(bloc, dict):
            _erreur(
                fichier,
                f"{prefixe} : objet attendu"
            )

        fid = _exiger_cle(
            bloc,
            "fid",
            fichier,
            int
        )

        if fid in fids_vus:
            _erreur(
                fichier,
                f"{prefixe} : FID {fid} "
                "présent deux fois"
            )

        fids_vus.add(fid)

        locuteurs = _exiger_cle(
            bloc,
            "locuteurs",
            fichier,
            list
        )

        if not locuteurs:
            _erreur(
                fichier,
                f"{prefixe} : au moins un "
                "locuteur requis"
            )

        for locuteur in locuteurs:
            if not isinstance(locuteur, str) or not locuteur:
                _erreur(
                    fichier,
                    f"{prefixe}.locuteurs : "
                    "noms (texte) attendus"
                )

        _exiger_cle(bloc, "source", fichier, str)

        positions = _exiger_cle(
            bloc,
            "positions",
            fichier,
            dict
        )

        for borne in ("debut", "fin"):
            _exiger_cle(
                positions,
                borne,
                fichier,
                str
            )

            try:
                lire_timecode(positions[borne])
            except ValueError as e:
                _erreur(
                    fichier,
                    f"{prefixe}.positions.{borne} : "
                    f"{e}"
                )

        debut = lire_timecode(positions["debut"])
        fin = lire_timecode(positions["fin"])

        if fin < debut:
            _erreur(
                fichier,
                f"{prefixe} : position de fin "
                "antérieure au début"
            )

        origine = bloc.get("origine", {})

        if not isinstance(origine, dict):
            _erreur(
                fichier,
                f"{prefixe}.origine : objet attendu"
            )

        if origine.get("fusion_de") is not None:

            if not isinstance(origine["fusion_de"], list):
                _erreur(
                    fichier,
                    f"{prefixe}.origine.fusion_de : "
                    "liste de FID attendue"
                )

        if not isinstance(
            origine.get("sous_decoupage", False),
            bool
        ):
            _erreur(
                fichier,
                f"{prefixe}.origine.sous_decoupage : "
                "booléen attendu"
            )

    #
    # Ordre d'ouvrage (optionnel, P14.5) : liste
    # de FID de la réunion, sans doublon. Le
    # défaut (absent) est l'ordre chronologique.
    #
    if "ordre_ouvrage" in data and data["ordre_ouvrage"] is not None:

        ordre = data["ordre_ouvrage"]

        if not isinstance(ordre, list):
            _erreur(
                fichier,
                "ordre_ouvrage : liste de FID attendue"
            )

        fids_ordre = []

        for index, fid in enumerate(ordre):

            if not isinstance(fid, int):
                _erreur(
                    fichier,
                    f"ordre_ouvrage[{index}] : "
                    "FID entier attendu"
                )

            fids_ordre.append(fid)

        if len(set(fids_ordre)) != len(fids_ordre):
            _erreur(
                fichier,
                "ordre_ouvrage : doublons interdits"
            )

        fids_inconnus = [
            fid
            for fid in fids_ordre
            if fid not in fids_vus
        ]

        if fids_inconnus:
            _erreur(
                fichier,
                (
                    "ordre_ouvrage : FID absents du "
                    f"découpage : {fids_inconnus}"
                )
            )


def _valider_validation(
    version: dict,
    prefixe: str,
    fichier: str
) -> None:
    """
    Valide le bloc validation d'une version (contrat §7, §8).
    """

    validation = version.get("validation")

    if validation is None:
        return

    if not isinstance(validation, dict):
        _erreur(
            fichier,
            f"{prefixe}.validation : objet attendu"
        )

    statut = _exiger_cle(
        validation,
        "statut",
        fichier,
        str
    )

    if statut != "valide":
        _erreur(
            fichier,
            (
                f"{prefixe}.validation.statut : "
                f"{statut!r} invalide, seul "
                "'valide' existe"
            )
        )

    _exiger_cle(
        validation,
        "horodatage",
        fichier,
        str
    )

    _valider_horodatage(
        validation["horodatage"],
        f"{prefixe}.validation.horodatage",
        fichier
    )

    _exiger_cle(
        validation,
        "validateur",
        fichier,
        str
    )


def valider_reformulation(
    data: dict,
    fichier: str = "traitements/reformulation/<FID>.json"
) -> None:
    """
    Valide un résultat de reformulation versionné
    par bloc (contrat §7).
    """

    if not isinstance(data, dict):
        _erreur(fichier, "objet JSON attendu")

    _exiger_cle(data, "fid", fichier, int)

    versions = _exiger_cle(
        data,
        "versions",
        fichier,
        list
    )

    numeros = []

    for index, version in enumerate(versions):

        prefixe = f"versions[{index}]"

        if not isinstance(version, dict):
            _erreur(
                fichier,
                f"{prefixe} : objet attendu"
            )

        numero = _exiger_cle(
            version,
            "numero",
            fichier,
            int
        )

        numeros.append(numero)

        _exiger_cle(version, "texte", fichier, str)

        _exiger_cle(
            version,
            "horodatage",
            fichier,
            str
        )

        _valider_horodatage(
            version["horodatage"],
            f"{prefixe}.horodatage",
            fichier
        )

        type_version = _exiger_cle(
            version,
            "type",
            fichier,
            str
        )

        _valider_enum(
            type_version,
            TYPES_VERSION_REFORMULATION,
            "type",
            fichier
        )

        if version.get("consigne") is not None:
            _exiger_cle(
                version,
                "consigne",
                fichier,
                str
            )

        if version.get("selection") is not None:

            selection = _exiger_cle(
                version,
                "selection",
                fichier,
                dict
            )

            for borne in ("debut", "fin"):
                _exiger_cle(
                    selection,
                    borne,
                    fichier,
                    int
                )

        if version.get("stats") is not None:

            stats = _exiger_cle(
                version,
                "stats",
                fichier,
                dict
            )

            for cle in (
                "duree_ms",
                "tokens_in",
                "tokens_out"
            ):
                _exiger_cle(stats, cle, fichier, int)

            _exiger_cle(
                stats,
                "cout_estime",
                fichier,
                (int, float)
            )

        _valider_validation(
            version,
            prefixe,
            fichier
        )

        contexte = version.get("contexte", [])

        if not isinstance(contexte, list):
            _erreur(
                fichier,
                f"{prefixe}.contexte : "
                "liste attendue"
            )

    if numeros != sorted(numeros):
        _erreur(
            fichier,
            "versions : numéros non séquentiels "
            "ou non triés"
        )


def valider_resume(
    data: dict,
    fichier: str = "traitements/resume/<reunion>.json"
) -> None:
    """
    Valide un résumé de réunion versionné (contrat §8).
    """

    if not isinstance(data, dict):
        _erreur(fichier, "objet JSON attendu")

    _exiger_cle(data, "reunion", fichier, str)

    versions = _exiger_cle(
        data,
        "versions",
        fichier,
        list
    )

    numeros = []

    for index, version in enumerate(versions):

        prefixe = f"versions[{index}]"

        if not isinstance(version, dict):
            _erreur(
                fichier,
                f"{prefixe} : objet attendu"
            )

        numero = _exiger_cle(
            version,
            "numero",
            fichier,
            int
        )

        numeros.append(numero)

        _exiger_cle(version, "texte", fichier, str)

        _exiger_cle(
            version,
            "source",
            fichier,
            str
        )

        _valider_enum(
            version["source"],
            SOURCES_RESUME,
            f"{prefixe}.source",
            fichier
        )

        _exiger_cle(
            version,
            "horodatage",
            fichier,
            str
        )

        _valider_horodatage(
            version["horodatage"],
            f"{prefixe}.horodatage",
            fichier
        )

        _valider_validation(
            version,
            prefixe,
            fichier
        )

    if numeros != sorted(numeros):
        _erreur(
            fichier,
            "versions : numéros non séquentiels "
            "ou non triés"
        )


def valider_synthese(
    data: dict,
    fichier: str = "synthese/synthese.json"
) -> None:
    """
    Valide la synthèse d'étude versionnée
    (contrat §9).
    """

    if not isinstance(data, dict):
        _erreur(fichier, "objet JSON attendu")

    versions = _exiger_cle(
        data,
        "versions",
        fichier,
        list
    )

    numeros = []

    for index, version in enumerate(versions):

        prefixe = f"versions[{index}]"

        if not isinstance(version, dict):
            _erreur(
                fichier,
                f"{prefixe} : objet attendu"
            )

        numero = _exiger_cle(
            version,
            "numero",
            fichier,
            int
        )

        numeros.append(numero)

        _exiger_cle(version, "texte", fichier, str)

        _exiger_cle(
            version,
            "horodatage",
            fichier,
            str
        )

        _valider_horodatage(
            version["horodatage"],
            f"{prefixe}.horodatage",
            fichier
        )

        declencheur = _exiger_cle(
            version,
            "declencheur",
            fichier,
            str
        )

        _valider_enum(
            declencheur,
            DECLENCHEURS_SYNTHESE,
            f"{prefixe}.declencheur",
            fichier
        )

    if numeros != sorted(numeros):
        _erreur(
            fichier,
            "versions : numéros non séquentiels "
            "ou non triés"
        )


def valider_parametres(
    data: dict,
    fichier: str = "parametres/parametres.json"
) -> None:
    """
    Valide les paramètres de l'étude (contrat §10).

    La structure interne des blocs (reformulation, résumé,
    synthèse) est validée dans ses clés principales ; le
    catalogue LLM détaillé relève de P15 et n'est pas
    contraint ici au-delà de sa forme.
    """

    if not isinstance(data, dict):
        _erreur(fichier, "objet JSON attendu")

    reformulation = _exiger_cle(
        data,
        "reformulation",
        fichier,
        dict
    )

    for cle in (
        "prompt",
        "modele",
        "fenetre_glissante_tokens"
    ):
        _exiger_cle(reformulation, cle, fichier)

    if not isinstance(
        reformulation["fenetre_glissante_tokens"],
        int
    ):
        _erreur(
            fichier,
            "reformulation.fenetre_glissante_"
            "tokens : entier attendu"
        )

    resume = _exiger_cle(
        data,
        "resume",
        fichier,
        dict
    )

    for cle in (
        "prompt",
        "modele",
        "longueur_cible_mots",
        "source_defaut"
    ):
        _exiger_cle(resume, cle, fichier)

    longueur = resume["longueur_cible_mots"]

    if (
        not isinstance(longueur, list)
        or len(longueur) != 2
        or not all(
            isinstance(borne, int)
            for borne in longueur
        )
    ):
        _erreur(
            fichier,
            "resume.longueur_cible_mots : "
            "paire d'entiers [min, max] attendue"
        )

    _valider_enum(
        resume["source_defaut"],
        SOURCES_RESUME,
        "resume.source_defaut",
        fichier
    )

    synthese = _exiger_cle(
        data,
        "synthese",
        fichier,
        dict
    )

    for cle in ("tokens_max", "modele"):
        _exiger_cle(synthese, cle, fichier)

    if not isinstance(synthese["tokens_max"], int):
        _erreur(
            fichier,
            "synthese.tokens_max : "
            "entier attendu"
        )

    controle = _exiger_cle(
        data,
        "controle_qualite",
        fichier,
        dict
    )

    if not isinstance(
        controle.get("lexique_emphase", []),
        list
    ):
        _erreur(
            fichier,
            "controle_qualite.lexique_emphase : "
            "liste attendue"
        )

    llm = _exiger_cle(data, "llm", fichier, dict)

    fournisseurs = llm.get("fournisseurs", [])

    if not isinstance(fournisseurs, list):
        _erreur(
            fichier,
            "llm.fournisseurs : liste attendue"
        )

    for index, fournisseur in enumerate(fournisseurs):

        prefixe = f"llm.fournisseurs[{index}]"

        if not isinstance(fournisseur, dict):
            _erreur(
                fichier,
                f"{prefixe} : objet attendu"
            )

        for cle in ("nom", "url", "cle_ref"):
            _exiger_cle(fournisseur, cle, fichier, str)
