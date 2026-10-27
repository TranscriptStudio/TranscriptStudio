# models/etude.py
"""
Objets du format étude v2.

Contrat de référence : architecture/spec_v2/CONTRAT_FORMAT_ETUDE_V2.md.

Un dossier étude référence des projets v1 (les réunions) sans les
copier, détient un registre FID unique pour toute l'étude, un
découpage en blocs de parole par réunion, des résultats versionnés
(reformulation par FID, résumé par réunion), une synthèse d'étude
versionnée et des paramètres.

Principes de fond (contrat §1) :
- l'étude référence les projets v1, elle ne les copie pas ;
- non-destructif : le texte source d'un bloc est immuable ;
- FID stable : attribué une seule fois, jamais réutilisé ;
- portabilité : chemins relatifs avec fallback absolu ;
- une étude = un livre biblique par défaut, thème libre possible.
"""

from dataclasses import dataclass, field
from typing import Optional


#
# Énumérations du contrat.
#

THEMES_ETUDE = ("livre", "libre")

TYPES_VERSION_REFORMULATION = (
    "passe",
    "relance",
    "relance_ciblee",
    "edition_manuelle",
)

SOURCES_RESUME = (
    "brute_corrigee",
    "reformulations_valides",
)

DECLENCHEURS_SYNTHESE = (
    "validation_bloc",
    "manuel",
    "creation_etude",
)

#
# Le seul statut de validation possible : la validation se porte
# sur une version précise ; un bloc non validé est simplement
# modifiable (pas de statut « refusé »).
#

STATUT_VALIDATION = "valide"


def normaliser_nom_fichier(nom: str) -> str:
    """
    Normalise un nom de fichier de l'étude :
    sans accents ni espaces (convention du contrat §2).

    Les espaces deviennent des tirets bas, les accents sont
    translittérés, tout caractère non alphanumérique (hors
    tiret bas et point) est supprimé.
    """

    table = str.maketrans(
        "áàâäãéèêëíìîïóòôöõúùûüçñýÿ",
        "aaaaaeeeeiiiiooooouuuucnyy"
    )

    nom = nom.strip().lower().translate(table)

    nom = nom.replace(" ", "_")

    nom = "".join(
        caractere
        for caractere in nom
        if caractere.isalnum()
        or caractere in "_-."
    )

    return nom


@dataclass
class Etude:
    """
    Contrat de l'étude : ``etude.json`` (contrat §3).

    ``ordre_reunions`` fait autorité pour l'ordre de lecture ;
    il correspond aux noms de fichiers de ``reunions/`` sans
    extension.
    """

    etude_format_version: int = 1
    titre: str = ""
    theme: str = "livre"
    gabarit_titre_1: str = "Chapitre {chapitre} — {section}"
    ordre_reunions: list = field(default_factory=list)
    creation: str = ""
    modification: str = ""

    def to_dict(self) -> dict:

        return {
            "etude_format_version":
                self.etude_format_version,
            "titre": self.titre,
            "theme": self.theme,
            "gabarit_titre_1": self.gabarit_titre_1,
            "ordre_reunions": list(self.ordre_reunions),
            "creation": self.creation,
            "modification": self.modification,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Etude":

        return cls(
            etude_format_version=data[
                "etude_format_version"
            ],
            titre=data["titre"],
            theme=data["theme"],
            gabarit_titre_1=data[
                "gabarit_titre_1"
            ],
            ordre_reunions=list(
                data.get("ordre_reunions", [])
            ),
            creation=data["creation"],
            modification=data["modification"],
        )


@dataclass
class ReunionEtude:
    """
    Référence à un projet v1 : ``reunions/<nom>.json``
    (contrat §4).

    ``chemin_projet`` est relatif au dossier étude ;
    ``chemin_absolu`` est le chemin absolu historique,
    stocké en secours à la première résolution réussie.
    """

    nom: str = ""
    reference: str = ""
    chemin_projet: str = ""
    chemin_absolu: Optional[str] = None
    date: str = ""
    numero: int = 0
    titre_1: str = ""
    resume_valide: bool = False

    def to_dict(self) -> dict:

        return {
            "reference": self.reference,
            "chemin_projet": self.chemin_projet,
            "chemin_absolu": self.chemin_absolu,
            "date": self.date,
            "numero": self.numero,
            "titre_1": self.titre_1,
            "resume_valide": self.resume_valide,
        }

    @classmethod
    def from_dict(
        cls,
        nom: str,
        data: dict
    ) -> "ReunionEtude":

        return cls(
            nom=nom,
            reference=data["reference"],
            chemin_projet=data["chemin_projet"],
            chemin_absolu=data.get("chemin_absolu"),
            date=data["date"],
            numero=data["numero"],
            titre_1=data["titre_1"],
            resume_valide=data.get(
                "resume_valide",
                False
            ),
        )


@dataclass
class EntreeFID:
    """
    Une attribution du registre FID de l'étude
    (contrat §5).

    ``actif`` passe à False lorsque le bloc est
    supprimé ou fusionné : le FID reste au registre,
    les résultats associés aussi.
    """

    fid: int
    reunion: str
    cree: str
    actif: bool = True
    fin: Optional[str] = None

    def to_dict(self) -> dict:

        return {
            "reunion": self.reunion,
            "cree": self.cree,
            "actif": self.actif,
            "fin": self.fin,
        }

    @classmethod
    def from_dict(
        cls,
        fid: int,
        data: dict
    ) -> "EntreeFID":

        return cls(
            fid=fid,
            reunion=data["reunion"],
            cree=data["cree"],
            actif=data["actif"],
            fin=data.get("fin"),
        )


@dataclass
class RegistreFID:
    """
    Registre FID, unique pour toute l'étude
    (décision d'atelier du 2026-10-27, contrat §5) :
    un FID désigne toujours le même discours dans
    toute l'étude, y compris entre réunions.

    Les FID sont des entiers séquentiels, attribués à
    la première segmentation d'un bloc, jamais
    réutilisés.
    """

    prochain_fid: int = 1
    entrees: dict = field(default_factory=dict)

    def to_dict(self) -> dict:

        return {
            "prochain_fid": self.prochain_fid,
            "fid_attribues": {
                str(fid): entree.to_dict()
                for fid, entree
                in sorted(
                    self.entrees.items(),
                    key=lambda item: item[0]
                )
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RegistreFID":

        entrees = {
            int(fid): EntreeFID.from_dict(
                int(fid),
                entree
            )
            for fid, entree
            in data.get(
                "fid_attribues",
                {}
            ).items()
        }

        return cls(
            prochain_fid=data["prochain_fid"],
            entrees=entrees,
        )


@dataclass
class PositionsBloc:
    """
    Positions d'un bloc dans l'audio TRAITÉ
    (contrat §6), au format timecode ``HH:MM:SS.mmm``.

    La conversion vers l'audio original se fait via le
    journal des opérations de prétraitement du projet v1.
    """

    debut: str = "00:00:00.000"
    fin: str = "00:00:00.000"

    def to_dict(self) -> dict:

        return {
            "debut": self.debut,
            "fin": self.fin,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PositionsBloc":

        return cls(
            debut=data["debut"],
            fin=data["fin"],
        )


@dataclass
class OrigineBloc:
    """
    Origine d'un bloc : fusion (FID d'origine listés)
    ou sous-découpage automatique (contrat §6).
    """

    fusion_de: Optional[list] = None
    sous_decoupage: bool = False

    def to_dict(self) -> dict:

        return {
            "fusion_de": self.fusion_de,
            "sous_decoupage":
                self.sous_decoupage,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OrigineBloc":

        return cls(
            fusion_de=data.get("fusion_de"),
            sous_decoupage=data.get(
                "sous_decoupage",
                False
            ),
        )


@dataclass
class BlocParole:
    """
    Bloc de parole d'une réunion (contrat §6).

    ``source`` est le texte de la transcription corrigée,
    immuable après enregistrement du bloc.

    Pour un bloc fusionné, ``locuteurs`` porte plusieurs
    noms et ``origine.fusion_de`` liste les FID d'origine.
    """

    fid: int
    locuteurs: list = field(default_factory=list)
    positions: PositionsBloc = field(
        default_factory=PositionsBloc
    )
    source: str = ""
    origine: OrigineBloc = field(
        default_factory=OrigineBloc
    )

    def to_dict(self) -> dict:

        return {
            "fid": self.fid,
            "locuteurs": list(self.locuteurs),
            "positions": self.positions.to_dict(),
            "source": self.source,
            "origine": self.origine.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BlocParole":

        return cls(
            fid=data["fid"],
            locuteurs=list(data["locuteurs"]),
            positions=PositionsBloc.from_dict(
                data["positions"]
            ),
            source=data["source"],
            origine=OrigineBloc.from_dict(
                data.get("origine", {})
            ),
        )


@dataclass
class DecoupageReunion:
    """
    Segmentation en blocs d'une réunion :
    ``blocs/decoupage/<reunion>.json`` (contrat §6).

    ``blocs`` suit l'ordre chronologique (immuable :
    il sert aux fenêtres glissantes, au contexte et
    à l'audio). Les blocs fusionnés ou disparus y
    restent — leur FID est inactif au registre —
    afin que la dé-fusion restaure les mêmes
    discours avec les mêmes FID.

    ``ordre_ouvrage`` est la liste réordonnable des
    FID actifs pour la lecture de l'ouvrage
    (P14.5) ; None = ordre chronologique (défaut).
    Il est stocké en parallèle de l'ordre
    chronologique.
    """

    reunion: str = ""
    blocs: list = field(default_factory=list)
    ordre_ouvrage: Optional[list] = None

    def to_dict(self) -> dict:

        data = {
            "reunion": self.reunion,
            "blocs": [
                bloc.to_dict()
                for bloc in self.blocs
            ],
        }

        if self.ordre_ouvrage is not None:
            data["ordre_ouvrage"] = list(
                self.ordre_ouvrage
            )

        return data

    @classmethod
    def from_dict(cls, data: dict) -> "DecoupageReunion":

        return cls(
            reunion=data["reunion"],
            blocs=[
                BlocParole.from_dict(bloc)
                for bloc in data.get("blocs", [])
            ],
            ordre_ouvrage=(
                list(data["ordre_ouvrage"])
                if "ordre_ouvrage" in data
                and data["ordre_ouvrage"] is not None
                else None
            ),
        )


@dataclass
class Validation:
    """
    Validation portée par une version de résultat
    (contrat §7, §8) : seul le statut « valide »
    existe.
    """

    statut: str = STATUT_VALIDATION
    horodatage: str = ""
    validateur: str = ""

    def to_dict(self) -> dict:

        return {
            "statut": self.statut,
            "horodatage": self.horodatage,
            "validateur": self.validateur,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Validation":

        return cls(
            statut=data["statut"],
            horodatage=data["horodatage"],
            validateur=data["validateur"],
        )


@dataclass
class VersionReformulation:
    """
    Une version du résultat de reformulation d'un bloc
    (contrat §7) : une version par exécution ou édition,
    l'historique complet est conservé, jamais écrasé.

    Une version ``relance_ciblee`` contient l'ensemble
    du bloc, reformulé partiellement.

    ``stats`` (LLM uniquement, None pour une édition
    manuelle) : ``duree_ms``, ``tokens_in``,
    ``tokens_out``, ``cout_estime``.

    ``contexte`` consigne les références de contexte
    utilisées (liste de FID/références) pour la
    reproductibilité.
    """

    numero: int
    texte: str
    horodatage: str
    type: str = "passe"
    consigne: Optional[str] = None
    selection: Optional[dict] = None
    stats: Optional[dict] = None
    validation: Optional[Validation] = None
    contexte: list = field(default_factory=list)

    def to_dict(self) -> dict:

        return {
            "numero": self.numero,
            "texte": self.texte,
            "horodatage": self.horodatage,
            "type": self.type,
            "consigne": self.consigne,
            "selection": self.selection,
            "stats": self.stats,
            "validation": (
                self.validation.to_dict()
                if self.validation
                else None
            ),
            "contexte": list(self.contexte),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict
    ) -> "VersionReformulation":

        return cls(
            numero=data["numero"],
            texte=data["texte"],
            horodatage=data["horodatage"],
            type=data["type"],
            consigne=data.get("consigne"),
            selection=data.get("selection"),
            stats=data.get("stats"),
            validation=(
                Validation.from_dict(
                    data["validation"]
                )
                if data.get("validation")
                else None
            ),
            contexte=list(
                data.get("contexte", [])
            ),
        )


@dataclass
class ResultatReformulation:
    """
    Résultats versionnés d'un bloc :
    ``traitements/reformulation/<FID>.json``
    (contrat §7).
    """

    fid: int
    versions: list = field(default_factory=list)

    def to_dict(self) -> dict:

        return {
            "fid": self.fid,
            "versions": [
                version.to_dict()
                for version in self.versions
            ],
        }

    @classmethod
    def from_dict(
        cls,
        data: dict
    ) -> "ResultatReformulation":

        return cls(
            fid=data["fid"],
            versions=[
                VersionReformulation.from_dict(
                    version
                )
                for version
                in data.get("versions", [])
            ],
        )


@dataclass
class VersionResume:
    """
    Une version du résumé d'une réunion
    (contrat §8).

    La source utilisée est stockée avec le résultat :
    ``brute_corrigee`` ou ``reformulations_valides``.
    """

    numero: int
    texte: str
    source: str
    horodatage: str
    validation: Optional[Validation] = None

    def to_dict(self) -> dict:

        return {
            "numero": self.numero,
            "texte": self.texte,
            "source": self.source,
            "horodatage": self.horodatage,
            "validation": (
                self.validation.to_dict()
                if self.validation
                else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VersionResume":

        return cls(
            numero=data["numero"],
            texte=data["texte"],
            source=data["source"],
            horodatage=data["horodatage"],
            validation=(
                Validation.from_dict(
                    data["validation"]
                )
                if data.get("validation")
                else None
            ),
        )


@dataclass
class ResultatResume:
    """
    Résumé versionné d'une réunion :
    ``traitements/resume/<reunion>.json``
    (contrat §8).
    """

    reunion: str
    versions: list = field(default_factory=list)

    def to_dict(self) -> dict:

        return {
            "reunion": self.reunion,
            "versions": [
                version.to_dict()
                for version in self.versions
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ResultatResume":

        return cls(
            reunion=data["reunion"],
            versions=[
                VersionResume.from_dict(
                    version
                )
                for version
                in data.get("versions", [])
            ],
        )


@dataclass
class VersionSynthese:
    """
    Une version de la synthèse d'étude
    (contrat §9).
    """

    numero: int
    texte: str
    horodatage: str
    declencheur: str = "manuel"

    def to_dict(self) -> dict:

        return {
            "numero": self.numero,
            "texte": self.texte,
            "horodatage": self.horodatage,
            "declencheur": self.declencheur,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict
    ) -> "VersionSynthese":

        return cls(
            numero=data["numero"],
            texte=data["texte"],
            horodatage=data["horodatage"],
            declencheur=data["declencheur"],
        )


@dataclass
class SyntheseEtude:
    """
    Synthèse d'étude versionnée :
    ``synthese/synthese.json`` (contrat §9).
    """

    versions: list = field(default_factory=list)

    def to_dict(self) -> dict:

        return {
            "versions": [
                version.to_dict()
                for version in self.versions
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SyntheseEtude":

        return cls(
            versions=[
                VersionSynthese.from_dict(
                    version
                )
                for version
                in data.get("versions", [])
            ],
        )


@dataclass
class ParametresEtude:
    """
    Réglages de l'étude : ``parametres/parametres.json``
    (contrat §10).

    Les prompts stockés sont les valeurs actives de
    l'étude, initialisés depuis les prompts v2 de
    référence. Aucune clé API en clair : les clés
    vivent dans le CredentialStore v1.
    """

    reformulation: dict = field(default_factory=dict)
    resume: dict = field(default_factory=dict)
    synthese: dict = field(default_factory=dict)
    controle_qualite: dict = field(
        default_factory=dict
    )
    llm: dict = field(default_factory=dict)

    def to_dict(self) -> dict:

        return {
            "reformulation": self.reformulation,
            "resume": self.resume,
            "synthese": self.synthese,
            "controle_qualite":
                self.controle_qualite,
            "llm": self.llm,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict
    ) -> "ParametresEtude":

        return cls(
            reformulation=data[
                "reformulation"
            ],
            resume=data["resume"],
            synthese=data["synthese"],
            controle_qualite=data[
                "controle_qualite"
            ],
            llm=data["llm"],
        )
